import requests
import streamlit as st

# Codigos de clima de Open-Meteo (WMO) -> icono y descripcion
# Iconos: Material Symbols, los mismos del menu
def describir_clima(codigo: int, es_de_dia: bool):
    if codigo == 0:
        return (":material/sunny:" if es_de_dia else ":material/clear_night:"), "Despejado"
    if codigo in (1, 2):
        icono = ":material/partly_cloudy_day:" if es_de_dia else ":material/partly_cloudy_night:"
        return icono, "Parcialmente nublado"
    if codigo == 3:
        return ":material/cloud:", "Nublado"
    if codigo in (45, 48):
        return ":material/foggy:", "Niebla"
    if codigo in (95, 96, 99):
        return ":material/thunderstorm:", "Tormenta"
    if codigo in (71, 73, 75, 77, 85, 86):
        return ":material/weather_snowy:", "Nieve"
    if 51 <= codigo <= 82:
        return ":material/rainy:", "Lluvia"
    return ":material/cloud:", "Variable"


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def buscar_ciudad(nombre: str):
    """Convierte el nombre de una ciudad en coordenadas (Open-Meteo, sin clave)."""
    try:
        resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": nombre, "count": 1, "language": "es"},
            timeout=10,
        )
        resp.raise_for_status()
        resultados = resp.json().get("results")
        if not resultados:
            return None
        r = resultados[0]
        return {
            "nombre": r.get("name", nombre),
            "pais": r.get("country", ""),
            "lat": r["latitude"],
            "lon": r["longitude"],
        }
    except Exception:
        return None


@st.cache_data(ttl=15 * 60, show_spinner=False)
def clima_actual(lat: float, lon: float):
    """Temperatura y condicion actual. Se guarda 15 minutos para no repetir consultas."""
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,weather_code,is_day",
                "timezone": "auto",
            },
            timeout=10,
        )
        resp.raise_for_status()
        actual = resp.json()["current"]
        return {
            "temperatura": actual["temperature_2m"],
            "codigo": actual["weather_code"],
            "es_de_dia": actual["is_day"] == 1,
            "hora": actual["time"][-5:],
        }
    except Exception:
        return None


def mostrar_clima():
    """Icono pequeño del clima. Si no hay conexion, no muestra nada."""
    if "ciudad" not in st.session_state:
        st.session_state.ciudad = "Ciudad de Guatemala"

    lugar = buscar_ciudad(st.session_state.ciudad)
    datos = clima_actual(lugar["lat"], lugar["lon"]) if lugar else None

    if not datos:
        return

    icono, texto = describir_clima(datos["codigo"], datos["es_de_dia"])
    temperatura = f'{datos["temperatura"]:.0f} °C'
    ciudad = f'{lugar["nombre"]}, {lugar["pais"]}'

    with st.popover(
        f"{icono} {temperatura}",
        help=f"{ciudad} · {temperatura} · {texto} · Actualizado {datos['hora']}",
    ):
        st.markdown(f"**{ciudad}**")
        st.markdown(f"{temperatura} · {texto}")
        st.caption(f"Actualizado a las {datos['hora']} · Datos de Open-Meteo")

        nueva = st.text_input("Cambiar ciudad", value=st.session_state.ciudad)
        if st.button("Actualizar clima") and nueva.strip():
            st.session_state.ciudad = nueva.strip()
            st.rerun()