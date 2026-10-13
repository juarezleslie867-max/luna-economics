from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

import db
from marca import mostrar_marca
from estilos import aplicar_estilos


# 1) Configuracion de la pagina (solo aqui, una vez para toda la app)
st.set_page_config(
    page_title="Luna Economics",
    page_icon="🌙",
    layout="centered"
)

# 2) Las secciones de la plataforma
paginas = [
    st.Page("paginas/asistente.py", title="Asistente", icon=":material/forum:", default=True),
    st.Page("paginas/semaforo.py", title="Semáforo", icon=":material/traffic:"),
    st.Page("paginas/informe.py", title="Informe", icon=":material/description:"),
    st.Page("paginas/perfil.py", title="Mi perfil", icon=":material/account_balance_wallet:"),
]

# position="hidden": Streamlit no dibuja su menu; lo dibujamos nosotras abajo
pagina_actual = st.navigation(paginas, position="hidden")


# 3) Apariencia: Auto / Claro / Oscuro
OPCIONES_APARIENCIA = ["Auto", "Claro", "Oscuro"]

# La primera vez, se toma la preferencia guardada en la URL (?tema=...)
if "apariencia" not in st.session_state:
    guardada = st.query_params.get("tema", "Auto")
    st.session_state.apariencia = guardada if guardada in OPCIONES_APARIENCIA else "Auto"


def hora_local():
    """Hora del navegador del usuario, no la del servidor."""
    zona = st.context.timezone
    try:
        return datetime.now(ZoneInfo(zona)) if zona else datetime.now()
    except Exception:
        return datetime.now()


def modo_actual():
    """Decide el modo: la eleccion manual manda; en Auto decide la hora."""
    eleccion = st.session_state.apariencia
    if eleccion == "Claro":
        return "claro"
    if eleccion == "Oscuro":
        return "oscuro"
    hora = hora_local().hour
    return "claro" if 6 <= hora < 18 else "oscuro"


@st.fragment(run_every="5min")
def estilos_vivos():
    """Aplica los estilos y se revisa sola cada 5 minutos (cambio a las 18:00 y 06:00)."""
    aplicar_estilos(modo_actual(), pagina_actual.url_path)


estilos_vivos()


def guardar_apariencia():
    """Guarda la eleccion en la URL para recordarla en la proxima visita."""
    if st.session_state.apariencia is None:
        st.session_state.apariencia = "Auto"
    st.query_params["tema"] = st.session_state.apariencia


# 4) Conversaciones guardadas en Supabase
if "conversacion_id" not in st.session_state:
    st.session_state.conversacion_id = None


def nueva_conversacion():
    st.session_state.mensajes = []
    st.session_state.conversacion_id = None
    st.session_state.pop("informe", None)


def abrir_conversacion(conversacion_id):
    st.session_state.mensajes = db.cargar_mensajes(conversacion_id)
    st.session_state.conversacion_id = conversacion_id
    st.session_state.pop("informe", None)


# Colores de los botones del menu lateral (dia / noche)
BOTONES_LATERALES = {
    "claro": {"texto": "#142F40", "hover": "#579AB9"},
    "oscuro": {"texto": "#A6C9D8", "hover": "#20475D"},
}


def estilos_botones_laterales(modo):
    c = BOTONES_LATERALES[modo]
    st.markdown(f"""<style>
[data-testid="stSidebar"] .stButton button[kind="secondary"] {{
  background: #376C89 !important; color: #F7F8F9 !important; border: 0 !important; }}
[data-testid="stSidebar"] .stButton button[kind="secondary"] p {{ color: #F7F8F9 !important; }}
[data-testid="stSidebar"] .stButton button[kind="tertiary"] {{
  justify-content: flex-start !important; text-align: left !important; }}
[data-testid="stSidebar"] .stButton button[kind="tertiary"] p,
[data-testid="stSidebar"] .stButton button[kind="tertiary"] span {{ color: {c["texto"]} !important; }}
[data-testid="stSidebar"] .stButton button[kind="tertiary"]:hover {{ background: {c["hover"]} !important; }}
[data-testid="stSidebar"] .stButton button[kind="primary"] {{ justify-content: flex-start !important; }}
</style>""", unsafe_allow_html=True)


# 5) Barra lateral: marca, menu, conversaciones, apariencia y pie
with st.sidebar:
    estilos_botones_laterales(modo_actual())
    mostrar_marca()

    for pagina in paginas:
        st.page_link(pagina)

    st.divider()
    if st.button("Nueva conversación", icon=":material/add_comment:", use_container_width=True):
        nueva_conversacion()
        st.switch_page(paginas[0])

    if db.disponible():
        recientes = db.conversaciones_recientes(8)
        if recientes:
            st.caption("Conversaciones recientes")
        for conv in recientes:
            titulo = conv.get("titulo") or "Sin título"
            titulo = titulo if len(titulo) <= 34 else titulo[:33] + "…"
            activa = conv["id"] == st.session_state.conversacion_id
            if st.button(titulo, key=f"conv_{conv['id']}", icon=":material/chat_bubble:",
                         type="primary" if activa else "tertiary", use_container_width=True):
                abrir_conversacion(conv["id"])
                st.switch_page(paginas[0])
    else:
        st.caption("⚠ Sin conexión a la base de datos: el historial no se está guardando.")

    st.divider()
    st.segmented_control(
        "Apariencia",
        OPCIONES_APARIENCIA,
        key="apariencia",
        on_change=guardar_apariencia,
    )
    st.caption("Leslie Giselle Juárez Tobar | Data Analytics")

# 6) Mostrar la seccion elegida
st.session_state["modo"] = modo_actual()
pagina_actual.run()