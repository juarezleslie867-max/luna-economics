from datetime import date

import requests
import streamlit as st

from intermediate_tools import IntermediateTools
from semaforo_config import INDICADORES, CONTEXTO, evaluar

ANIOS_HISTORIA = 10
_tools = IntermediateTools()


def _serie_imf(codigo_pais, codigo_ind, anio_actual):
    """Serie del FMI (DataMapper). Solo años cerrados, sin proyecciones."""
    url = f"https://www.imf.org/external/datamapper/api/v1/{codigo_ind}/{codigo_pais}"
    try:
        respuesta = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        respuesta.raise_for_status()
        valores = respuesta.json()["values"][codigo_ind][codigo_pais]
    except Exception:
        return []
    serie = [
        (int(anio), float(valor))
        for anio, valor in valores.items()
        if valor is not None and int(anio) < anio_actual
    ]
    return sorted(serie)[-ANIOS_HISTORIA:]


def _serie(indicador, codigo_pais, anio_actual):
    """Elige la fuente correcta y devuelve [(anio, valor), ...] ordenado."""
    if indicador["fuente"] == "imf":
        return _serie_imf(codigo_pais, indicador["codigo"], anio_actual)
    serie = _tools._serie_wb(
        codigo_pais, indicador["codigo"], {"mrv": ANIOS_HISTORIA, "per_page": 100}
    )
    return sorted((int(a), float(v)) for a, v in (serie or []))


def _resumen(indicador, serie):
    """Ultimo valor, su año y el promedio de la serie."""
    if not serie:
        return None, None, None
    anio, valor = serie[-1]
    promedio = sum(v for _, v in serie) / len(serie)
    return anio, valor, promedio


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def obtener_semaforo(pais):
    codigo, nombre = _tools._buscar_codigo_pais(pais)
    if not codigo:
        return None

    anio_actual = date.today().year
    indicadores = []

    for ind in INDICADORES:
        serie = _serie(ind, codigo, anio_actual)
        anio, valor, promedio = _resumen(ind, serie)
        indicadores.append({
            "clave": ind["clave"], "bloque": ind["bloque"], "nombre": ind["nombre"],
            "unidad": ind["unidad"], "fuente": ind["fuente"], "nota": ind["nota"],
            "anio": anio, "valor": valor, "promedio": promedio, "serie": serie,
            "estado": evaluar(valor, ind["rangos"], anio, anio_actual),
        })

    contexto = []
    for ind in CONTEXTO:
        serie = _serie(ind, codigo, anio_actual)
        anio, valor, promedio = _resumen(ind, serie)
        contexto.append({
            "clave": ind["clave"], "nombre": ind["nombre"], "unidad": ind["unidad"],
            "anio": anio, "valor": valor, "promedio": promedio, "serie": serie,
        })

    return {"pais": nombre, "codigo": codigo, "anio_actual": anio_actual,
            "indicadores": indicadores, "contexto": contexto}


if __name__ == "__main__":
    resultado = obtener_semaforo("Guatemala")
    print("\nPaís:", resultado["pais"])
    for i in resultado["indicadores"]:
        valor = "sin dato" if i["valor"] is None else f'{i["valor"]:.1f} ({i["anio"]})'
        print(f'{i["nombre"]:<32} {valor:<16} {i["estado"]}')
    for c in resultado["contexto"]:
        valor = "sin dato" if c["valor"] is None else f'{c["valor"]:,.1f} ({c["anio"]})'
        print(f'{c["nombre"]:<32} {valor}')