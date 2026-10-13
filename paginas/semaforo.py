from datetime import date

import streamlit as st

import db
from marca import encabezado
from estilos import PALETAS
from semaforo_config import COLORES_ESTADO, INDICADORES
from semaforo_datos import obtener_semaforo
from graficas_plotly import mini_grafica

ICONOS = {"Favorable": "✓", "Precaución": "!", "Crítico": "✕", "Sin evaluación": "–"}
ORDEN = ["Favorable", "Precaución", "Crítico", "Sin evaluación"]
FUENTES = {"wb": "Banco Mundial", "imf": "FMI"}

modo = st.session_state.get("modo", "claro")
p = PALETAS[modo]

# Estilos propios de las tarjetas del semaforo
st.markdown(f"""<style>
.sem-info {{cursor:help; font-weight:400; color:{p["texto_suave"]};}}
.sem-bloque {{font-size:11px; font-weight:600; letter-spacing:.1em; text-transform:uppercase; color:{p["texto_suave"]};}}
.sem-nombre {{font-size:15px; font-weight:600; color:{p["titulo"]}; margin:2px 0 6px;}}
.sem-valor {{font-family:Vidaloka, serif; font-size:30px; line-height:1.1; color:{p["titulo"]};}}
.sem-detalle {{font-size:12px; color:{p["texto_suave"]}; margin-bottom:8px;}}
.sem-estado {{display:inline-flex; align-items:center; gap:6px; font-size:13px; font-weight:600; color:{p["texto"]}; margin-right:14px;}}
.st-key-seguir_pais button {{min-height:0 !important; padding:6px 14px !important;}}
.sem-punto {{width:18px; height:18px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; color:#FFFFFF; font-size:11px; font-weight:700;}}
</style>""", unsafe_allow_html=True)


def etiqueta_estado(estado):
    color = COLORES_ESTADO[estado]
    return (f'<span class="sem-estado"><span class="sem-punto" style="background:{color}">'
            f'{ICONOS[estado]}</span>{estado}</span>')


def texto_rango(minimo, maximo):
    if minimo is None:
        return f"< {maximo}"
    if maximo is None:
        return f"≥ {minimo}"
    return f"{minimo} a {maximo}"


encabezado("Semáforo macroeconómico",
           "Diagnóstico rápido de un país con umbrales de referencia. Datos: Banco Mundial y FMI.")

if "pais_semaforo" not in st.session_state:
    st.session_state.pais_semaforo = "Guatemala"
pais = st.text_input("País", key="pais_semaforo", placeholder="Ej.: Guatemala, Costa Rica, México")
if not pais.strip():
    st.stop()

with st.spinner("Consultando Banco Mundial y FMI..."):
    datos = obtener_semaforo(pais.strip())

if datos is None:
    st.warning(f"No encontré el país «{pais}». Prueba con otro nombre.")
    st.stop()

# Resumen
conteo = {e: sum(1 for i in datos["indicadores"] if i["estado"] == e) for e in ORDEN}
col_titulo, col_boton = st.columns([3, 1], vertical_alignment="center")
with col_titulo:
    st.subheader(datos["pais"])
with col_boton:
    if st.button("Seguir país", key="seguir_pais", icon=":material/bookmark_add:",
                 use_container_width=True, disabled=not db.disponible()):
        diagnostico = {
            "fecha": date.today().isoformat(),
            "conteo": conteo,
            "indicadores": {
                i["clave"]: {"nombre": i["nombre"], "valor": i["valor"],
                             "anio": i["anio"], "estado": i["estado"]}
                for i in datos["indicadores"]
            },
        }
        if db.agregar_seguimiento("pais", datos["pais"], datos["codigo"], diagnostico):
            st.toast(f"{datos['pais']} se agregó a tu seguimiento", icon=":material/bookmark_added:")
        else:
            st.toast("No se pudo guardar. Revisa la conexión con Supabase.", icon=":material/error:")
st.markdown(" ".join(f"{etiqueta_estado(e)}<b>{conteo[e]}</b> &nbsp;" for e in ORDEN if conteo[e]),
            unsafe_allow_html=True)

# Tarjetas (4 por fila)
columnas = st.columns(4)
for n, ind in enumerate(datos["indicadores"]):
    with columnas[n % 4]:
        with st.container(border=True):
            if ind["valor"] is None:
                valor_txt, detalle = "Sin dato", "No hay datos disponibles"
            else:
                valor_txt = f'{ind["valor"]:,.1f}'
                detalle = f'{ind["unidad"]} · {ind["anio"]} · {FUENTES[ind["fuente"]]}'
            st.markdown(
                f'<div class="sem-bloque">{ind["bloque"]}</div>'
                f'<div class="sem-nombre">{ind["nombre"]} <span class="sem-info" title="{ind["nota"]}">ⓘ</span></div>'
                f'<div class="sem-valor">{valor_txt}</div>'
                f'<div class="sem-detalle">{detalle}</div>'
                f'{etiqueta_estado(ind["estado"])}',
                unsafe_allow_html=True,
            )
            if ind["serie"]:
                st.plotly_chart(mini_grafica(ind["serie"], ind["promedio"], modo),
                                key=f'mini_{ind["clave"]}', config={"displayModeBar": False})
                st.caption(f'┈ Promedio {len(ind["serie"])} años: {ind["promedio"]:,.1f}')

# Contexto (sin semaforo)
st.markdown("#### Contexto")
st.caption("Sin semáforo: describen la economía, pero no son buenos ni malos por sí mismos.")
for col, c in zip(st.columns(len(datos["contexto"])), datos["contexto"]):
    with col:
        if c["valor"] is None:
            st.metric(c["nombre"], "Sin dato")
        else:
            st.metric(f'{c["nombre"]} ({c["anio"]})', f'{c["valor"]:,.1f} {c["unidad"]}',
                      delta=f'{c["valor"] - c["promedio"]:+,.1f} vs. promedio {len(c["serie"])} años',
                      delta_color="off")

# Metodologia
with st.expander("¿Cómo se calcula el semáforo?"):
    filas = ["| Indicador | Favorable | Precaución | Crítico |", "|---|---|---|---|"]
    for ind in INDICADORES:
        por_estado = {e: [] for e in ORDEN}
        for minimo, maximo, estado in ind["rangos"]:
            por_estado[estado].append(texto_rango(minimo, maximo))
        filas.append(f'| {ind["nombre"]} | ' + " | ".join(
            " o ".join(por_estado[e]) for e in ["Favorable", "Precaución", "Crítico"]) + " |")
    st.markdown("\n".join(filas))
    st.caption("Se evalúa el dato más reciente de años ya cerrados. Si no hay dato, o tiene más de "
               "3 años de antigüedad, el indicador queda como «Sin evaluación».")