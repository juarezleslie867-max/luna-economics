import streamlit as st

import db
from marca import encabezado
from semaforo_config import COLORES_ESTADO

PERFILES = ["conservador", "moderado", "agresivo"]
DESCRIPCIONES = [
    "Prioriza proteger el capital",
    "Equilibrio entre rendimiento y riesgo",
    "Busca más rendimiento aceptando más volatilidad",
]
NOMBRES_SIMULACION = {
    "diversificar_inversion": "Diversificación",
    "interes_compuesto": "Interés compuesto",
    "tasa_real": "Tasa de interés real",
}

# En esta pagina los botones son normales (no tarjetas grandes como en el Asistente)
# y los titulos de los desplegables usan el fondo de la tarjeta (se leen de dia y de noche)
st.markdown("<style>[data-testid='stMainBlockContainer'] .stButton button "
            "{min-height:0 !important; padding:6px 14px !important;}"
            "[data-testid='stExpander'] summary {background: transparent !important;}"
            "[data-testid='stExpander'] summary p {color: inherit !important;}</style>",
            unsafe_allow_html=True)


def tabla_resultado(resultado, prefijo=""):
    """Convierte el resultado (diccionario anidado) en filas Campo | Valor."""
    filas = []
    if isinstance(resultado, dict):
        for k, v in resultado.items():
            filas += tabla_resultado(v, f"{prefijo} › {k}" if prefijo else str(k))
    elif isinstance(resultado, list):
        for i, v in enumerate(resultado):
            filas += tabla_resultado(v, f"{prefijo} › {i + 1}" if prefijo else str(i + 1))
    else:
        valor = f"{resultado:,.2f}" if isinstance(resultado, float) else str(resultado)
        filas.append(f"| {prefijo.replace('_', ' ')} | {valor} |")
    return filas

encabezado("Mi perfil",
           "Tu perfil de inversionista, lo que sigues y tus simulaciones. "
           "Luna usa este perfil para orientar sus análisis.")

if not db.disponible():
    st.warning("No hay conexión con la base de datos (Supabase). Revisa SUPABASE_URL y "
               "SUPABASE_KEY en el archivo .env.")
    st.stop()


def fecha_corta(texto):
    return (texto or "")[:10]


tab_perfil, tab_seguimiento, tab_simulaciones = st.tabs(
    ["Perfil de inversión", "Seguimiento", "Simulaciones"])

# ---------------------------------------------------------------
# 1) Perfil del inversionista
# ---------------------------------------------------------------
with tab_perfil:
    actual = db.obtener_perfil() or {}
    with st.form("form_perfil"):
        perfil = st.radio(
            "Perfil de riesgo", PERFILES, horizontal=True, captions=DESCRIPCIONES,
            index=PERFILES.index(actual["perfil"]) if actual.get("perfil") in PERFILES else 1,
            format_func=str.capitalize,
        )
        c1, c2 = st.columns([2, 1])
        monto = c1.number_input("Monto disponible para invertir", min_value=0.0, step=1000.0,
                                value=float(actual.get("monto") or 0), format="%.2f")
        moneda = c2.selectbox("Moneda", ["GTQ", "USD"],
                              index=1 if actual.get("moneda") == "USD" else 0)
        horizonte = st.slider("Horizonte de inversión (años)", 1, 30,
                              value=int(actual.get("horizonte_anios") or 5))
        objetivo = st.text_area("Objetivo", value=actual.get("objetivo") or "",
                                placeholder="Ej.: ahorrar para la jubilación, comprar una casa en 5 años...")
        if st.form_submit_button("Guardar perfil", type="primary", icon=":material/save:"):
            if db.guardar_perfil(perfil, monto, moneda, horizonte, objetivo.strip()):
                st.success("Perfil guardado. Luna lo tomará en cuenta desde tu próxima pregunta.")
            else:
                st.error("No se pudo guardar el perfil. Revisa la terminal para ver el error.")
    if actual.get("actualizado"):
        st.caption(f"Última actualización: {fecha_corta(actual['actualizado'])}")

# ---------------------------------------------------------------
# 2) Paises y empresas en seguimiento
# ---------------------------------------------------------------
with tab_seguimiento:
    st.markdown("##### Agregar una empresa")
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    ticker = c1.text_input("Ticker o nombre", placeholder="Ej.: AAPL, Walmart, KO")
    if c2.button("Seguir empresa", icon=":material/bookmark_add:", use_container_width=True) and ticker.strip():
        from empresas_tools import EmpresasTools

        with st.spinner("Consultando Yahoo Finance..."):
            r = EmpresasTools().analizar_empresa(ticker.strip())
        if "error" in r:
            st.error(r["error"])
        else:
            rr, val = r["rendimiento_y_riesgo"], r["valuacion"]
            diagnostico = {
                "fecha": r["fecha_ultimo_precio"], "precio": r["precio_actual"], "moneda": r["moneda"],
                "sector": r["sector"],
                "rendimiento_anual_promedio_pct": rr["rendimiento_anual_promedio_pct"],
                "volatilidad_anual_pct": rr["volatilidad_anual_pct"],
                "per": val["per_ultimos_12_meses"],
            }
            if db.agregar_seguimiento("empresa", r["empresa"], r["ticker"], diagnostico):
                st.toast(f"{r['empresa']} se agregó a tu seguimiento", icon=":material/bookmark_added:")
    st.caption("Para seguir un país, búscalo en el Semáforo y presiona «Seguir país».")

    items = db.listar_seguimiento()
    paises = [i for i in items if i["tipo"] == "pais"]
    empresas = [i for i in items if i["tipo"] == "empresa"]

    st.markdown("##### Países")
    if not paises:
        st.caption("Todavía no sigues ningún país.")
    for item in paises:
        d = item.get("diagnostico") or {}
        conteo = d.get("conteo", {})
        with st.container(border=True):
            c1, c2, c3 = st.columns([4, 1, 1], vertical_alignment="center")
            resumen = " · ".join(
                f'<span style="color:{COLORES_ESTADO[e]}">●</span> {e}: {n}'
                for e, n in conteo.items() if n
            )
            c1.markdown(f"**{item['nombre']}**  \n<small>{resumen}<br>Diagnóstico del "
                        f"{d.get('fecha', fecha_corta(item['agregado']))}</small>",
                        unsafe_allow_html=True)
            if c2.button("Ver", key=f"ver_{item['id']}", icon=":material/traffic:"):
                st.session_state.pais_semaforo = item["nombre"]
                st.switch_page("paginas/semaforo.py")
            if c3.button("Quitar", key=f"quitar_{item['id']}", icon=":material/delete:"):
                db.quitar_seguimiento(item["id"])
                st.rerun()

    st.markdown("##### Empresas")
    if not empresas:
        st.caption("Todavía no sigues ninguna empresa.")
    for item in empresas:
        d = item.get("diagnostico") or {}
        with st.container(border=True):
            c1, c2 = st.columns([5, 1], vertical_alignment="center")
            c1.markdown(
                f"**{item['nombre']}** ({item['codigo']})  \n<small>"
                f"Precio: {d.get('precio')} {d.get('moneda') or ''} · "
                f"Rend. anual promedio: {d.get('rendimiento_anual_promedio_pct')} % · "
                f"Volatilidad: {d.get('volatilidad_anual_pct')} % · PER: {d.get('per')}"
                f"<br>Datos del {d.get('fecha', fecha_corta(item['agregado']))} · Yahoo Finance</small>",
                unsafe_allow_html=True,
            )
            if c2.button("Quitar", key=f"quitar_{item['id']}", icon=":material/delete:"):
                db.quitar_seguimiento(item["id"])
                st.rerun()

# ---------------------------------------------------------------
# 3) Simulaciones guardadas
# ---------------------------------------------------------------
with tab_simulaciones:
    st.caption("Cada vez que Luna calcula una diversificación, un interés compuesto o una tasa "
               "real, el resultado se guarda aquí para que compares escenarios.")
    simulaciones = db.listar_simulaciones(30)
    if not simulaciones:
        st.info("Aún no hay simulaciones. Prueba en el Asistente: «Tengo Q50,000 y perfil "
                "moderado, ¿cómo los diversifico y cuánto tendría en 5 años al 7 %?»",
                icon=":material/calculate:")
    for sim in simulaciones:
        nombre = NOMBRES_SIMULACION.get(sim["herramienta"], sim["herramienta"])
        argumentos = ", ".join(f"{k}: {v}" for k, v in (sim.get("argumentos") or {}).items())
        with st.expander(f"{nombre} · {argumentos} · {fecha_corta(sim['creada'])}"):
            resultado = sim.get("resultado")
            if resultado:
                st.markdown("\n".join(["| Campo | Valor |", "|---|---|"] + tabla_resultado(resultado)))
            else:
                st.caption("Esta simulación se guardó sin resultado (versión anterior de la app).")
            if st.button("Borrar", key=f"borrar_sim_{sim['id']}", icon=":material/delete:"):
                db.borrar_simulacion(sim["id"])
                st.rerun()