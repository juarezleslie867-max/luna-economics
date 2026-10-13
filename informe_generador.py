#######################################
# Luna Economics                      #
# Generador del informe de consulta   #
#######################################

import base64
import csv
import html
import io
import json
import os
import re
from datetime import datetime

import markdown

# Nombres legibles de las herramientas del agente
NOMBRES_HERRAMIENTAS = {
    "consultar_tipo_cambio_api": "Tipo de cambio",
    "convertir_moneda": "Conversión de moneda",
    "diversificar_inversion": "Diversificación de inversión",
    "interes_compuesto": "Interés compuesto",
    "datos_pais": "Datos del país",
    "indicadores_economicos": "Indicadores económicos",
    "pronostico_fmi": "Pronóstico del FMI",
    "serie_historica": "Serie histórica",
    "comparar_paises": "Comparación de países",
    "indicadores_sociales": "Indicadores sociales",
    "tasa_real": "Tasa de interés real",
    "poder_adquisitivo": "Poder adquisitivo",
    "graficar": "Gráfica",
    "analizar_empresa": "Análisis de empresa",
    "comparar_empresas": "Comparación de empresas",
    "estados_financieros": "Estados financieros (SEC)",
}

BANCO_MUNDIAL = "Banco Mundial · World Development Indicators"
FMI = "FMI · World Economic Outlook (DataMapper)"
TIPO_CAMBIO = "ExchangeRate-API (open.er-api.com)"
CALCULO = "Cálculo de Luna Economics"
YAHOO = "Yahoo Finance (vía yfinance)"
SEC = "SEC EDGAR · Estados financieros oficiales (10-K)"

FUENTE_HERRAMIENTA = {
    "consultar_tipo_cambio_api": TIPO_CAMBIO,
    "convertir_moneda": TIPO_CAMBIO,
    "diversificar_inversion": CALCULO,
    "interes_compuesto": CALCULO,
    "tasa_real": CALCULO,
    "pronostico_fmi": FMI,
    "analizar_empresa": YAHOO,
    "comparar_empresas": YAHOO,
    "estados_financieros": SEC,
}

ENLACES_FUENTES = {
    BANCO_MUNDIAL: "https://data.worldbank.org",
    FMI: "https://www.imf.org/external/datamapper",
    TIPO_CAMBIO: "https://www.exchangerate-api.com",
    CALCULO: None,
    YAHOO: "https://finance.yahoo.com",
    SEC: "https://www.sec.gov/edgar",
}

NOMBRES_INDICADORES = {
    "pib": "PIB", "pib_per_capita": "PIB per cápita", "crecimiento": "Crecimiento del PIB",
    "inflacion": "Inflación", "desempleo": "Desempleo", "deuda": "Deuda pública",
    "exportaciones": "Exportaciones", "importaciones": "Importaciones", "remesas": "Remesas",
    "inversion_extranjera": "Inversión extranjera directa", "poblacion": "Población",
    "cuenta_corriente": "Cuenta corriente",
}

PAISES_ISO = {
    "GTM": "Guatemala", "HND": "Honduras", "SLV": "El Salvador", "NIC": "Nicaragua",
    "CRI": "Costa Rica", "PAN": "Panamá", "BLZ": "Belice", "MEX": "México",
    "DOM": "República Dominicana", "CUB": "Cuba", "HTI": "Haití", "JAM": "Jamaica",
    "COL": "Colombia", "VEN": "Venezuela", "ECU": "Ecuador", "PER": "Perú",
    "BOL": "Bolivia", "CHL": "Chile", "ARG": "Argentina", "URY": "Uruguay",
    "PRY": "Paraguay", "BRA": "Brasil", "USA": "Estados Unidos", "CAN": "Canadá",
    "ESP": "España", "DEU": "Alemania", "FRA": "Francia", "ITA": "Italia",
    "GBR": "Reino Unido", "CHN": "China", "JPN": "Japón", "IND": "India",
    "KOR": "Corea del Sur", "RUS": "Rusia",
}

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def fuente_de(nombre_herramienta):
    return FUENTE_HERRAMIENTA.get(nombre_herramienta, BANCO_MUNDIAL)


# ---------------------------------------------------------------
# 1) Ordenar la conversacion en consultas (pregunta + respuesta)
# ---------------------------------------------------------------
def agrupar_consultas(mensajes):
    consultas = []
    pregunta = None
    for m in mensajes:
        if m["role"] == "user":
            pregunta = m
        elif m["role"] == "assistant" and pregunta is not None:
            consultas.append({
                "n": len(consultas) + 1,
                "pregunta": pregunta["content"],
                "hora": pregunta.get("hora", ""),
                "respuesta": m["content"],
                "graficas": m.get("graficas", []),
                "graficas_datos": m.get("graficas_datos", []),
                "herramientas": m.get("herramientas", []),
            })
            pregunta = None
    return consultas


def ficha(consultas):
    """Resumen de lo consultado: paises, indicadores, fuentes, graficas."""
    paises, indicadores, fuentes, empresas = [], [], [], []
    n_graficas = 0
    for c in consultas:
        n_graficas += len(c["graficas"])
        for h in c["herramientas"]:
            args = h.get("argumentos", {})
            for clave in ("pais", "paises"):
                for p in str(args.get(clave, "")).split(","):
                    p = p.strip()
                    p = PAISES_ISO.get(p.upper(), p.upper() if len(p) == 3 else p)
                    if p and p not in paises:
                        paises.append(p)
            for clave in ("empresa", "empresas"):
                for e in str(args.get(clave, "")).split(","):
                    e = e.strip()
                    if e and e not in empresas:
                        empresas.append(e)
            ind = args.get("indicador")
            if ind:
                nombre = NOMBRES_INDICADORES.get(ind, ind)
                if nombre not in indicadores:
                    indicadores.append(nombre)
            f = fuente_de(h["nombre"])
            if f not in fuentes:
                fuentes.append(f)
    return {"paises": paises, "indicadores": indicadores, "empresas": empresas,
            "fuentes": fuentes, "graficas": n_graficas}


# ---------------------------------------------------------------
# 2) Datos para el CSV (formato largo, listo para R o Excel)
# ---------------------------------------------------------------
def _aplanar(valor, prefijo=""):
    """Convierte un diccionario anidado en pares (campo, valor)."""
    if isinstance(valor, dict):
        for k, v in valor.items():
            yield from _aplanar(v, f"{prefijo} > {k}" if prefijo else str(k))
    elif isinstance(valor, list):
        for i, v in enumerate(valor):
            yield from _aplanar(v, f"{prefijo} > {i}" if prefijo else str(i))
    else:
        yield prefijo, valor


def filas_de_datos(consultas):
    filas = []
    for c in consultas:
        for h in c["herramientas"]:
            resultado = h.get("resultado")
            if not isinstance(resultado, (dict, list)):
                resultado = {"resultado": resultado}
            for campo, valor in _aplanar(resultado):
                if "grafica_guardada_en" in campo:
                    continue
                filas.append({
                    "consulta": c["n"],
                    "hora": c["hora"],
                    "herramienta": NOMBRES_HERRAMIENTAS.get(h["nombre"], h["nombre"]),
                    "fuente": fuente_de(h["nombre"]),
                    "argumentos": json.dumps(h.get("argumentos", {}), ensure_ascii=False),
                    "campo": campo,
                    "valor": valor,
                })
    return filas


def generar_csv(consultas):
    salida = io.StringIO()
    columnas = ["consulta", "hora", "herramienta", "fuente", "argumentos", "campo", "valor"]
    escritor = csv.DictWriter(salida, fieldnames=columnas)
    escritor.writeheader()
    escritor.writerows(filas_de_datos(consultas))
    # utf-8-sig: Excel reconoce las tildes; R lo lee con read.csv(..., encoding = "UTF-8")
    return salida.getvalue().encode("utf-8-sig")


# ---------------------------------------------------------------
# 3) Resumen ejecutivo (IA con respaldo automatico)
# ---------------------------------------------------------------
def resumen_automatico(consultas, datos_ficha):
    partes = [f"Durante la sesión se realizaron {len(consultas)} consulta(s) a Luna Economics"]
    if datos_ficha["paises"]:
        partes.append(f" sobre {', '.join(datos_ficha['paises'])}")
    texto = "".join(partes) + "."
    if datos_ficha["indicadores"]:
        texto += f" Se analizaron los indicadores: {', '.join(datos_ficha['indicadores'])}."
    if datos_ficha["fuentes"]:
        texto += f" Las cifras provienen de: {'; '.join(datos_ficha['fuentes'])}."
    texto += " El detalle de cada consulta, con sus datos y gráficas, se presenta a continuación."
    return texto


def resumen_ia(cliente, consultas):
    import agente_core

    bloques, total = [], 0
    for c in consultas:
        bloque = f"PREGUNTA {c['n']}: {c['pregunta']}\nRESPUESTA: {c['respuesta'][:1500]}"
        if total + len(bloque) > 9000:
            break
        bloques.append(bloque)
        total += len(bloque)

    instrucciones = (
        "Eres Luna, analista economica de Luna Economics. Redacta el RESUMEN EJECUTIVO de un "
        "informe a partir de la conversacion que se te entrega. Escribe en español, en tono "
        "profesional, en 2 o 3 parrafos breves (maximo 220 palabras en total). Incluye los "
        "hallazgos principales y una conclusion. Usa SOLO las cifras que aparecen en la "
        "conversacion, con su año; no inventes datos. Si hubo datos faltantes, mencionalo. "
        "No uses titulos, listas ni tablas; solo parrafos."
    )
    resp = cliente.chat.completions.create(
        model=agente_core.MODELO,
        messages=[
            {"role": "system", "content": instrucciones},
            {"role": "user", "content": "\n\n".join(bloques)},
        ],
        temperature=0.3,
    )
    return (resp.choices[0].message.content or "").strip()


# ---------------------------------------------------------------
# 4) Piezas del HTML
# ---------------------------------------------------------------
def md_a_html(texto):
    """Markdown -> HTML, protegiendo las formulas $$...$$ para KaTeX."""
    texto = re.sub(r"`[^`\n]*\.png`", "(ver la gráfica de esta consulta)", texto)
    formulas = []

    def guardar(m):
        formulas.append(m.group(0))
        return f"@@FORMULA{len(formulas) - 1}@@"

    texto = re.sub(r"\$\$.+?\$\$", guardar, texto, flags=re.S)
    cuerpo = markdown.markdown(texto, extensions=["tables", "sane_lists", "fenced_code"])
    for i, f in enumerate(formulas):
        cuerpo = cuerpo.replace(f"@@FORMULA{i}@@", html.escape(f))
    return cuerpo


def _formato(valor):
    if isinstance(valor, bool) or valor is None:
        return html.escape(str(valor if valor is not None else "—"))
    if isinstance(valor, (int, float)):
        if isinstance(valor, int):
            return str(valor) if 1800 <= valor <= 2100 else f"{valor:,}"
        return f"{valor:,.2f}".rstrip("0").rstrip(".")
    return html.escape(str(valor))


def figura_html(ruta_png, n_figura, datos_respaldo=None):
    partes = []
    titulo, fuente = "Gráfica", BANCO_MUNDIAL
    ruta_json = os.path.splitext(ruta_png)[0] + ".json"
    datos = None
    if os.path.exists(ruta_json):
        with open(ruta_json, encoding="utf-8") as f:
            datos = json.load(f)
    elif datos_respaldo:
        datos = datos_respaldo  # el archivo ya no existe (p. ej. en la nube): usar los datos guardados
    if datos:
        titulo = datos.get("titulo", titulo)
        fuente = datos.get("fuente", fuente)

    partes.append('<figure class="figura">')
    if os.path.exists(ruta_png):
        with open(ruta_png, "rb") as f:
            imagen = base64.b64encode(f.read()).decode()
        partes.append(f'<img src="data:image/png;base64,{imagen}" alt="{html.escape(titulo)}">')
    partes.append(
        f'<figcaption><b>Figura {n_figura}.</b> {html.escape(titulo)}. '
        f'Fuente: {html.escape(fuente)}.</figcaption>'
    )

    if datos:
        series = datos["series"]
        anios = sorted({int(a) for s in series.values() for a in s["anios"]})
        filas = ['<table class="tabla tabla-datos"><thead><tr><th>Año</th>']
        filas += [f"<th>{html.escape(p)}</th>" for p in series]
        filas.append("</tr></thead><tbody>")
        for anio in anios:
            filas.append(f"<tr><td>{anio}</td>")
            for s in series.values():
                mapa = {int(a): v for a, v in zip(s["anios"], s["valores"])}
                v = mapa.get(anio)
                filas.append(f'<td class="num">{"—" if v is None else f"{v:,.2f}"}</td>')
            filas.append("</tr>")
        filas.append("</tbody></table>")
        partes.append('<div class="tabla-titulo">Datos de la figura</div>' + "".join(filas))

    partes.append("</figure>")
    return "".join(partes)


def anexo_html(consultas):
    partes = []
    for c in consultas:
        for h in c["herramientas"]:
            nombre = NOMBRES_HERRAMIENTAS.get(h["nombre"], h["nombre"])
            args = ", ".join(f"{k}: {v}" for k, v in h.get("argumentos", {}).items())
            resultado = h.get("resultado")
            if not isinstance(resultado, (dict, list)):
                resultado = {"resultado": resultado}
            pares = [(k, v) for k, v in _aplanar(resultado) if "grafica_guardada_en" not in k]
            recorte = len(pares) > 120
            pares = pares[:120]
            filas = "".join(
                f"<tr><td>{html.escape(k)}</td><td class='num'>{_formato(v)}</td></tr>"
                for k, v in pares
            )
            nota = '<p class="nota-tabla">Tabla recortada; el detalle completo está en el CSV.</p>' if recorte else ""
            partes.append(
                f'<div class="anexo-bloque"><h3>Consulta {c["n"]} · {html.escape(nombre)}</h3>'
                f'<p class="meta">{html.escape(args)} · Fuente: {html.escape(fuente_de(h["nombre"]))}</p>'
                f'<table class="tabla"><thead><tr><th>Campo</th><th>Valor</th></tr></thead>'
                f"<tbody>{filas}</tbody></table>{nota}</div>"
            )
    return "".join(partes) or "<p>No se usaron herramientas de datos en esta sesión.</p>"


LOGO = (
    '<svg viewBox="0 0 120 120" aria-hidden="true">'
    '<circle cx="60" cy="60" r="57" fill="#0C1E29" stroke="#376C89" stroke-width="3"/>'
    '<path d="M76 13 A47 47 0 1 0 84 103 A38 38 0 1 1 76 13 Z" fill="#A6C9D8"/>'
    '<text x="62" y="77" text-anchor="middle" font-family="Vidaloka, Georgia, serif" '
    'font-size="48" fill="#F7F8F9">LE</text></svg>'
)

CSS = """
@page { size: A4; margin: 20mm 18mm 22mm 18mm;
  @bottom-left { content: "Luna Economics · Informe de consulta económica"; font: 8pt Montserrat, sans-serif; color: #376C89; }
  @bottom-right { content: "Página " counter(page); font: 8pt Montserrat, sans-serif; color: #376C89; }
}
@page :first { margin: 0; @bottom-left { content: none; } @bottom-right { content: none; } }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; background: #E4EBEF; color: #142F40; font-family: Montserrat, "Segoe UI", sans-serif; font-size: 10.5pt; line-height: 1.6; }
h1, h2, h3, .serif { font-family: Vidaloka, Georgia, serif; font-weight: 400; color: #0C1E29; }
a { color: #376C89; }
.hoja { width: 210mm; max-width: 100%; margin: 24px auto; background: #FFFFFF; box-shadow: 0 6px 30px rgba(12,30,41,.15); }
.pagina { padding: 20mm 18mm; }
.salto { break-before: page; }

/* Portada */
.portada { min-height: 297mm; background: #0C1E29; color: #F7F8F9; padding: 26mm 22mm; display: flex; flex-direction: column; position: relative; overflow: hidden; break-after: page; }
.portada::after { content: ""; position: absolute; right: -38mm; top: -30mm; width: 120mm; height: 120mm; border-radius: 50%; box-shadow: -16mm 12mm 0 0 #142F40; }
.marca { display: flex; align-items: center; gap: 14px; position: relative; z-index: 1; }
.marca svg { width: 58px; height: 58px; }
.marca-nombre { font-size: 17pt; font-weight: 600; }
.marca-lema { font-size: 7pt; letter-spacing: .16em; text-transform: uppercase; color: #A6C9D8; font-weight: 600; }
.portada-centro { margin-top: auto; position: relative; z-index: 1; }
.etiqueta { font-size: 8pt; letter-spacing: .2em; text-transform: uppercase; color: #A6C9D8; font-weight: 600; }
.portada h1 { color: #F7F8F9; font-size: 40pt; line-height: 1.08; margin: 10px 0 14px; }
.portada .fecha { color: #A6C9D8; font-size: 11pt; }
.ficha { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 34px; }
.ficha div { border-top: 1px solid #376C89; padding-top: 10px; }
.ficha b { display: block; font-family: Vidaloka, Georgia, serif; font-weight: 400; font-size: 20pt; color: #F7F8F9; line-height: 1.2; }
.ficha span { font-size: 8.5pt; color: #A6C9D8; }
.ficha .lista { font-family: Montserrat, sans-serif; font-size: 10pt; font-weight: 600; }
.portada-pie { margin-top: 40px; font-size: 8pt; color: #A6C9D8; position: relative; z-index: 1; }

/* Secciones */
.seccion-num { font-size: 8pt; letter-spacing: .2em; text-transform: uppercase; color: #376C89; font-weight: 700; }
h2 { font-size: 24pt; margin: 4px 0 16px; padding-bottom: 10px; border-bottom: 2px solid #A6C9D8; }
.resumen p { font-size: 11pt; }
.resumen p:first-child::first-line { font-weight: 600; }
.indice ol { padding-left: 0; list-style: none; counter-reset: c; }
.indice li { counter-increment: c; display: flex; gap: 14px; padding: 9px 0; border-bottom: 1px solid #E3ECF0; }
.indice li::before { content: counter(c, decimal-leading-zero); font-family: Vidaloka, Georgia, serif; color: #376C89; font-size: 13pt; min-width: 26px; }
.indice a { color: #142F40; text-decoration: none; }
.indice .hora { margin-left: auto; color: #376C89; font-size: 8.5pt; white-space: nowrap; }

/* Consultas */
.consulta-meta { display: flex; justify-content: space-between; font-size: 8pt; letter-spacing: .14em; text-transform: uppercase; color: #376C89; font-weight: 700; }
.pregunta { font-family: Vidaloka, Georgia, serif; font-size: 18pt; line-height: 1.3; color: #0C1E29; border-left: 4px solid #376C89; padding: 4px 0 4px 16px; margin: 12px 0 22px; }
.respuesta h1, .respuesta h2, .respuesta h3, .respuesta h4 { font-family: Montserrat, sans-serif; font-weight: 700; font-size: 11.5pt; color: #0C1E29; border: 0; margin: 20px 0 6px; padding: 0; }
.respuesta hr { border: 0; border-top: 1px solid #E3ECF0; margin: 18px 0; }
.respuesta blockquote { margin: 14px 0; padding: 10px 16px; background: #F2F6F8; border-left: 3px solid #A6C9D8; color: #20475D; }
.respuesta code { background: #F2F6F8; padding: 1px 5px; border-radius: 4px; font-size: 9pt; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 20px 0 6px; }
.chip { font-size: 8pt; font-weight: 600; padding: 3px 10px; border-radius: 999px; background: #E3ECF0; color: #20475D; }
.fuentes-consulta { font-size: 8.5pt; color: #376C89; }

/* Tablas y figuras */
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 9pt; break-inside: auto; }
th { background: #142F40; color: #F7F8F9; text-align: left; font-weight: 600; padding: 7px 10px; }
td { padding: 6px 10px; border-bottom: 1px solid #E3ECF0; vertical-align: top; }
tbody tr:nth-child(even) td { background: #F5F8FA; }
tr { break-inside: avoid; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.figura { margin: 22px 0; break-inside: avoid; }
.figura img { width: 100%; border: 1px solid #E3ECF0; border-radius: 6px; }
figcaption { font-size: 8.5pt; color: #20475D; margin-top: 6px; }
.tabla-titulo { font-size: 8pt; letter-spacing: .14em; text-transform: uppercase; color: #376C89; font-weight: 700; margin-top: 14px; }
.tabla-datos { max-width: 100%; }
.anexo-bloque { margin-bottom: 22px; }
.anexo-bloque h3 { font-size: 13pt; margin: 0 0 2px; }
.meta, .nota-tabla { font-size: 8.5pt; color: #376C89; margin: 0 0 4px; }
.fuentes li { margin-bottom: 6px; }
.aviso { margin-top: 26px; padding: 14px 18px; background: #F2F6F8; border-left: 3px solid #376C89; font-size: 9pt; color: #20475D; }

@media print {
  body { background: #FFFFFF; }
  .hoja { width: auto; margin: 0; box-shadow: none; }
  .pagina { padding: 0; }
  .portada { min-height: 297mm; height: 297mm; }
}
"""


def generar_html(consultas, resumen, fecha=None):
    fecha = fecha or datetime.now()
    fecha_txt = f"{fecha.day} de {MESES[fecha.month - 1]} de {fecha.year} · {fecha:%H:%M}"
    datos_ficha = ficha(consultas)

    def lista(valores):
        return html.escape(", ".join(valores)) if valores else "—"

    # Portada
    portada = (
        '<section class="portada">'
        f'<div class="marca">{LOGO}<div><div class="marca-nombre">Luna Economics</div>'
        '<div class="marca-lema">Economic Intelligence &amp; Analytics</div></div></div>'
        '<div class="portada-centro"><div class="etiqueta">Informe de sesión</div>'
        '<h1>Informe de consulta económica</h1>'
        f'<div class="fecha">{fecha_txt}</div>'
        '<div class="ficha">'
        f'<div><b>{len(consultas)}</b><span>Consultas realizadas</span></div>'
        f'<div><b>{datos_ficha["graficas"]}</b><span>Gráficas generadas</span></div>'
        f'<div><b class="lista">{lista(datos_ficha["paises"])}</b><span>Países consultados</span></div>'
        f'<div><b class="lista">{lista(datos_ficha["indicadores"])}</b><span>Indicadores analizados</span></div>'
        + (f'<div><b class="lista">{lista(datos_ficha["empresas"])}</b><span>Empresas analizadas</span></div>'
           if datos_ficha["empresas"] else "") +
        '</div></div>'
        '<div class="portada-pie">Datos oficiales del Banco Mundial y el Fondo Monetario Internacional. '
        'Documento generado automáticamente por Luna Economics.</div>'
        '</section>'
    )

    # Resumen ejecutivo + indice
    parrafos = "".join(f"<p>{html.escape(p.strip())}</p>" for p in resumen.split("\n") if p.strip())
    items = "".join(
        f'<li><a href="#consulta-{c["n"]}">{html.escape(c["pregunta"])}</a>'
        f'<span class="hora">{html.escape(c["hora"])}</span></li>'
        for c in consultas
    )
    inicio = (
        '<section class="pagina">'
        '<div class="seccion-num">01</div><h2>Resumen ejecutivo</h2>'
        f'<div class="resumen">{parrafos}</div>'
        '<div class="seccion-num" style="margin-top:34px">02</div><h2>Índice de consultas</h2>'
        f'<div class="indice"><ol>{items}</ol></div>'
        '</section>'
    )

    # Consultas
    bloques, n_figura = [], 0
    for c in consultas:
        figuras = ""
        respaldos = c.get("graficas_datos") or []
        for i, ruta in enumerate(c["graficas"]):
            n_figura += 1
            figuras += figura_html(ruta, n_figura, respaldos[i] if i < len(respaldos) else None)
        nombres = []
        for h in c["herramientas"]:
            n = NOMBRES_HERRAMIENTAS.get(h["nombre"], h["nombre"])
            if n not in nombres:
                nombres.append(n)
        fuentes = []
        for h in c["herramientas"]:
            f = fuente_de(h["nombre"])
            if f not in fuentes:
                fuentes.append(f)
        chips = "".join(f'<span class="chip">{html.escape(n)}</span>' for n in nombres)
        bloques.append(
            f'<section class="pagina salto" id="consulta-{c["n"]}">'
            f'<div class="consulta-meta"><span>03 · Consulta {c["n"]:02d}</span>'
            f'<span>{html.escape(c["hora"])}</span></div>'
            f'<div class="pregunta">{html.escape(c["pregunta"])}</div>'
            f'<div class="respuesta">{md_a_html(c["respuesta"])}</div>'
            f'{figuras}'
            + (f'<div class="chips">{chips}</div>' if chips else "")
            + (f'<div class="fuentes-consulta">Fuentes: {html.escape("; ".join(fuentes))}</div>'
               if fuentes else '<div class="fuentes-consulta">Explicación conceptual, sin consulta de datos.</div>')
            + '</section>'
        )

    # Anexo, fuentes y metodologia
    fuentes_li = "".join(
        f'<li><b>{html.escape(f)}</b>'
        + (f' · <a href="{ENLACES_FUENTES[f]}">{ENLACES_FUENTES[f]}</a>' if ENLACES_FUENTES.get(f) else "")
        + "</li>"
        for f in (datos_ficha["fuentes"] or [BANCO_MUNDIAL])
    )
    cierre = (
        '<section class="pagina salto">'
        '<div class="seccion-num">04</div><h2>Anexo de datos</h2>'
        '<p class="meta">Resultados exactos devueltos por cada herramienta. '
        'El archivo CSV que acompaña este informe contiene el detalle completo.</p>'
        f'{anexo_html(consultas)}'
        '</section>'
        '<section class="pagina salto">'
        '<div class="seccion-num">05</div><h2>Fuentes y metodología</h2>'
        f'<ul class="fuentes">{fuentes_li}</ul>'
        '<p>Las respuestas fueron generadas por Luna, un agente de inteligencia artificial que '
        'consulta las fuentes anteriores mediante sus API públicas. Las cifras citadas provienen '
        'directamente de esas consultas, con el año de cada dato. Las proyecciones del FMI se '
        'distinguen de los datos observados. Las secciones marcadas como «Interpretación general» '
        'o «Explicación conceptual» son análisis del agente y no datos de las fuentes.</p>'
        '<div class="aviso"><b>Nota de responsabilidad.</b> Este informe tiene fines informativos y '
        'académicos. No constituye una recomendación de inversión ni asesoría financiera. '
        'Verifique las cifras en las fuentes oficiales antes de tomar decisiones.</div>'
        '</section>'
    )

    return (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>Informe de consulta económica · Luna Economics · {fecha:%d-%m-%Y}</title>'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link href="https://fonts.googleapis.com/css2?family=Vidaloka&family=Montserrat:wght@400;600;700&display=swap" rel="stylesheet">'
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">'
        f'<style>{CSS}</style></head><body><div class="hoja">'
        f'{portada}{inicio}{"".join(bloques)}{cierre}'
        '</div>'
        '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>'
        '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js" '
        'onload="renderMathInElement(document.body,{delimiters:[{left:\'$$\',right:\'$$\',display:true}]});"></script>'
        '</body></html>'
    )


# ---------------------------------------------------------------
# 5) Todo junto
# ---------------------------------------------------------------
def generar_informe(consultas, cliente=None):
    datos_ficha = ficha(consultas)
    resumen, con_ia = None, False
    if cliente is not None:
        try:
            resumen = resumen_ia(cliente, consultas)
            con_ia = bool(resumen)
        except Exception as error:
            print(f"No se pudo generar el resumen con IA: {error}")
    if not resumen:
        resumen = resumen_automatico(consultas, datos_ficha)

    fecha = datetime.now()
    return {
        "html": generar_html(consultas, resumen, fecha),
        "csv": generar_csv(consultas),
        "n": len(consultas),
        "nombre": f"informe_luna_{fecha:%Y%m%d_%H%M}",
        "resumen_con_ia": con_ia,
    }