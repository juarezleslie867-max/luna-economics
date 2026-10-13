import streamlit as st

# Logo: circulo, luna creciente y las letras LE
LOGO_SVG = (
    '<svg width="48" height="48" viewBox="0 0 120 120" role="img" aria-label="Logo de Luna Economics">'
    '<circle cx="60" cy="60" r="58" fill="#0C1E29"></circle>'
    '<path d="M76 13 A47 47 0 1 0 84 103 A38 38 0 1 1 76 13 Z" fill="#A6C9D8"></path>'
    '<text x="62" y="77" text-anchor="middle" font-family="Vidaloka, Georgia, serif" '
    'font-size="48" fill="#F7F8F9">LE</text>'
    '<circle cx="60" cy="60" r="57" fill="none" stroke="#376C89" stroke-width="3"></circle>'
    '</svg>'
)


def mostrar_marca():
    """Dibuja el logo y el nombre en la parte de arriba de la barra lateral."""
    html = (
        '<div style="display: flex; align-items: center; gap: 12px; margin: 4px 0 18px;">'
        + LOGO_SVG
        + '<div>'
        + '<div class="marca-nombre" style="font-weight: 600; font-size: 18px; line-height: 1.1;">'
        + 'Luna Economics</div>'
        + '<div class="marca-lema" style="font-size: 9px; font-weight: 600; letter-spacing: 0.1em; '
        + 'text-transform: uppercase;">'
        + 'Economic Intelligence &amp; Analytics</div>'
        + '</div>'
        + '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def encabezado(titulo: str, subtitulo: str = ""):
    """Titulo de la seccion a la izquierda y el icono del clima a la derecha."""
    from clima import mostrar_clima

    col_titulo, col_clima = st.columns([5, 1], vertical_alignment="center")
    with col_titulo:
        st.title(titulo)
        if subtitulo:
            st.caption(subtitulo)
    with col_clima:
        mostrar_clima()

def hora_local():
    """Hora del navegador de la persona, no la del servidor."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    zona = st.context.timezone
    try:
        return datetime.now(ZoneInfo(zona)) if zona else datetime.now()
    except Exception:
        return datetime.now()


def saludo():
    """Buenos dias, buenas tardes o buenas noches segun la hora local."""
    hora = hora_local().hour
    if 5 <= hora < 12:
        return "Buenos días"
    if 12 <= hora < 19:
        return "Buenas tardes"
    return "Buenas noches"