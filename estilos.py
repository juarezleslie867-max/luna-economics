import streamlit as st

# Colores de cada modo (tabla aprobada)
PALETAS = {
    "claro": {
        "sidebar_fondo": "#A6C9D8",
        "sidebar_marca": "#0C1E29",
        "sidebar_texto": "#142F40",
        "activo": "#376C89",
        "hover": "#579AB9",
        "fondo": "#F7F8F9",
        "tarjeta": "#FFFFFF",
        "titulo": "#142F40",
        "texto": "#0C1E29",
        "texto_suave": "#20475D",
        "borde": "#A6C9D8",
    },
    "oscuro": {
        "sidebar_fondo": "#0C1E29",
        "sidebar_marca": "#F7F8F9",
        "sidebar_texto": "#A6C9D8",
        "activo": "#376C89",
        "hover": "#20475D",
        "fondo": "#142F40",
        "tarjeta": "#20475D",
        "titulo": "#F7F8F9",
        "texto": "#F7F8F9",
        "texto_suave": "#A6C9D8",
        "borde": "#376C89",
    },
}


def aplicar_estilos(modo: str = "claro", pagina_activa: str = ""):
    """
    Inyecta el CSS del modo elegido.
    modo: 'claro' u 'oscuro'.
    pagina_activa: la url de la seccion actual, para resaltarla en el menu.
    """
    c = PALETAS[modo]

    css = f"""
<style>
/* Fondo general y texto */
[data-testid="stApp"], [data-testid="stHeader"], [data-testid="stBottom"] > div {{
    background-color: {c["fondo"]};
}}
[data-testid="stApp"] {{ color: {c["texto"]}; }}
[data-testid="stMainBlockContainer"] h1, [data-testid="stMainBlockContainer"] h2, [data-testid="stMainBlockContainer"] h3 {{
    color: {c["titulo"]};
}}
[data-testid="stMainBlockContainer"] p, [data-testid="stMainBlockContainer"] li, [data-testid="stMainBlockContainer"] td,
[data-testid="stMainBlockContainer"] th, [data-testid="stMainBlockContainer"] strong, [data-testid="stMainBlockContainer"] summary span {{
    color: {c["texto"]} !important;
}}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{
    color: {c["texto_suave"]} !important;
}}

/* Barra lateral */
[data-testid="stSidebar"] {{ background-color: {c["sidebar_fondo"]}; }}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span {{ color: {c["sidebar_texto"]}; }}
.marca-nombre {{ color: {c["sidebar_marca"]} !important; }}
.marca-lema {{ color: {c["sidebar_texto"]} !important; }}

/* Opciones del menu */
[data-testid="stPageLink-NavLink"] {{ border-radius: 10px; transition: background-color 0.15s ease; }}
[data-testid="stPageLink-NavLink"]:hover {{ background-color: {c["hover"]}; }}
[data-testid="stPageLink-NavLink"][href="{pagina_activa}"] {{ background-color: {c["activo"]}; }}
[data-testid="stPageLink-NavLink"][href="{pagina_activa}"] span,
[data-testid="stPageLink-NavLink"][href="{pagina_activa}"] p {{ color: #F7F8F9 !important; }}

/* Selector de apariencia (Auto / Claro / Oscuro) */
[data-testid="stButtonGroup"] > div {{ flex-wrap: nowrap; }}
[data-testid^="stBaseButton-segmented_control"] {{
    background-color: transparent;
    border-color: {c["activo"]};
    padding: 4px 12px;
    min-height: 34px;
}}
[data-testid^="stBaseButton-segmented_control"] p {{ color: {c["sidebar_texto"]} !important; font-size: 13px; }}
[data-testid^="stBaseButton-segmented_control"]:hover {{ background-color: {c["hover"]}; }}
[data-testid="stBaseButton-segmented_controlActive"] {{
    background-color: {c["activo"]} !important;
    border-color: {c["activo"]} !important;
}}
[data-testid="stBaseButton-segmented_controlActive"] p {{ color: #F7F8F9 !important; }}

/* Icono del clima y su ventana */
[data-testid="stPopover"] button {{
    background-color: transparent;
    border: none;
    box-shadow: none;
}}
[data-testid="stPopover"] button p, [data-testid="stPopover"] button span {{ color: {c["titulo"]} !important; }}
[data-testid="stPopover"] button:hover {{ background-color: {c["tarjeta"]}; }}
[data-testid="stPopoverBody"] {{
    background-color: {c["tarjeta"]};
    border: 1px solid {c["borde"]};
}}
[data-testid="stPopoverBody"] > div {{ background-color: transparent !important; }}
[data-testid="stPopoverBody"] p, [data-testid="stPopoverBody"] label {{ color: {c["texto"]} !important; }}
[data-testid="stPopoverBody"] [data-testid="stTextInputRootElement"],
[data-testid="stPopoverBody"] [data-testid="stTextInputRootElement"] div,
[data-testid="stPopoverBody"] input {{
    background-color: {c["fondo"]} !important;
    color: {c["texto"]} !important;
}}
[data-testid="stPopoverBody"] button {{
    background-color: transparent;
    border-color: {c["activo"]};
}}
[data-testid="stPopoverBody"] button:hover {{ background-color: {c["hover"]}; }}
[data-testid="stPopoverBody"] [data-testid="stCaptionContainer"] p {{ color: {c["texto_suave"]} !important; }}

/* Tarjetas de sugerencias de la bienvenida */
[data-testid="stMainBlockContainer"] .stButton button {{
    background-color: {c["tarjeta"]};
    border: 1px solid {c["borde"]};
    border-radius: 14px;
    min-height: 84px;
    justify-content: flex-start;
    text-align: left;
    padding: 14px 18px;
    box-shadow: 0 4px 18px rgba(12, 30, 41, 0.05);
    transition: border-color 0.15s ease, transform 0.15s ease;
}}
[data-testid="stMainBlockContainer"] .stButton button:hover {{
    border-color: {c["activo"]};
    transform: translateY(-1px);
}}
[data-testid="stMainBlockContainer"] .stButton button span {{ color: {c["texto_suave"]} !important; }}

/* Avatares del chat */
[data-testid="stChatMessageAvatarCustom"], [data-testid^="stChatMessageAvatar"] {{
    background-color: {c["activo"]};
    color: #F7F8F9;
}}

/* Tarjetas: mensajes del chat y desplegables */
[data-testid="stChatMessage"] {{
    background-color: {c["tarjeta"]};
    border-radius: 14px;
    box-shadow: 0 4px 18px rgba(12, 30, 41, 0.06);
}}
[data-testid="stExpander"] details {{
    background-color: {c["tarjeta"]};
    border-color: {c["borde"]};
    border-radius: 12px;
}}

/* Caja de chat */
[data-testid="stChatInput"], [data-testid="stChatInput"] > div, [data-testid="stChatInput"] [data-baseweb="textarea"],
[data-testid="stChatInput"] [data-baseweb="base-input"], [data-testid="stChatInputTextArea"] {{
    background-color: {c["tarjeta"]} !important;
}}
[data-testid="stChatInput"] {{ border: 1px solid {c["borde"]}; border-radius: 14px; }}
[data-testid="stChatInputTextArea"] {{ color: {c["texto"]} !important; }}
[data-testid="stChatInputTextArea"]::placeholder {{ color: {c["texto_suave"]} !important; }}

/* Movimiento reducido */
@media (prefers-reduced-motion: reduce) {{
    * {{ transition: none !important; }}
}}
</style>
"""
    st.markdown(css, unsafe_allow_html=True)