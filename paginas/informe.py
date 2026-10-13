import streamlit as st
import streamlit.components.v1 as components

import agente_core
import informe_generador as ig
from marca import encabezado

encabezado("Informe", "Descarga la sesión con Luna como informe profesional y los datos en CSV.")

consultas = ig.agrupar_consultas(st.session_state.get("mensajes", []))

if not consultas:
    st.info("Todavía no hay consultas en esta sesión. Conversa con Luna en el Asistente "
            "y vuelve aquí para generar tu informe.", icon=":material/info:")
    st.page_link("paginas/asistente.py", label="Ir al Asistente", icon=":material/forum:")
    st.stop()


@st.cache_resource
def obtener_cliente():
    return agente_core.crear_cliente()


# Ficha rapida de la sesion
datos_ficha = ig.ficha(consultas)
c1, c2, c3 = st.columns(3)
c1.metric("Consultas", len(consultas))
c2.metric("Gráficas", datos_ficha["graficas"])
c3.metric("Países", len(datos_ficha["paises"]))

if st.button("Generar informe", type="primary", icon=":material/auto_awesome:"):
    with st.spinner("Luna está redactando el resumen ejecutivo..."):
        try:
            cliente = obtener_cliente()
        except Exception:
            cliente = None
        st.session_state.informe = ig.generar_informe(consultas, cliente)

informe = st.session_state.get("informe")
if informe:
    if informe["n"] != len(consultas):
        st.warning("Hiciste nuevas consultas después de generar este informe. "
                   "Presiona «Generar informe» para incluirlas.")
    if not informe["resumen_con_ia"]:
        st.caption("El resumen ejecutivo se generó de forma automática porque no se pudo "
                   "contactar a la IA (posible límite de uso de Groq).")

    d1, d2 = st.columns(2)
    d1.download_button("Descargar informe (HTML)", data=informe["html"],
                       file_name=informe["nombre"] + ".html", mime="text/html",
                       icon=":material/description:", use_container_width=True)
    d2.download_button("Descargar datos (CSV)", data=informe["csv"],
                       file_name=informe["nombre"] + ".csv", mime="text/csv",
                       icon=":material/table:", use_container_width=True)
    st.caption("Para guardarlo como PDF: abre el HTML en el navegador → Ctrl + P → "
               "Guardar como PDF. En «Más opciones», desactiva «Encabezados y pies de página».")

    st.markdown("##### Vista previa")
    components.html(informe["html"], height=900, scrolling=True)