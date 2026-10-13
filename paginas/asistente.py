import json
import os
from datetime import datetime

import streamlit as st

import agente_core
import db
from marca import encabezado, saludo
from graficas_plotly import figura_desde_json, figura_desde_datos

AVATAR_USUARIO = ":material/person:"
AVATAR_AGENTE = ":material/dark_mode:"

# Preguntas sugeridas de la pantalla de bienvenida: (icono, titulo, pregunta)
SUGERENCIAS = [
    (":material/trending_up:", "Pronóstico", "¿Cuánto crecerá Guatemala según el FMI?"),
    (":material/public:", "Comparar países", "Compara la inflación de Guatemala, Honduras y Costa Rica"),
    (":material/business_center:", "Analizar empresa", "Soy un inversionista moderado, analiza Apple: rendimiento, riesgo y valuación"),
    (":material/candlestick_chart:", "Comparar acciones", "Compara Walmart, Microsoft y Coca-Cola en rendimiento y riesgo"),
    (":material/show_chart:", "Graficar", "Grafica el PIB per cápita de México y Brasil en los últimos 20 años"),
    (":material/school:", "Teoría", "Explícame la ley de Okun con un ejemplo de Guatemala"),
]


# 1) Memoria de la sesion
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

if "pregunta_pendiente" not in st.session_state:
    st.session_state.pregunta_pendiente = None

if "conversacion_id" not in st.session_state:
    st.session_state.conversacion_id = None


def usar_sugerencia(texto):
    """Al hacer clic en una tarjeta, su pregunta se envia como si la hubieras escrito."""
    st.session_state.pregunta_pendiente = texto


def leer_datos_graficas(rutas):
    """Lee los JSON de las graficas para guardarlos tambien en Supabase."""
    datos = []
    for ruta in rutas:
        ruta_json = os.path.splitext(ruta)[0] + ".json"
        try:
            with open(ruta_json, encoding="utf-8") as archivo:
                datos.append(json.load(archivo))
        except Exception:
            datos.append(None)
    return datos


def mostrar_graficas(mensaje, n_mensaje):
    """Dibuja las graficas de un mensaje: desde el archivo JSON o, si ya no existe, desde Supabase."""
    modo = st.session_state.get("modo", "claro")
    respaldos = mensaje.get("graficas_datos") or []
    for i, ruta in enumerate(mensaje.get("graficas", [])):
        ruta_json = os.path.splitext(ruta)[0] + ".json"
        clave = f"graf_{n_mensaje}_{i}"
        if os.path.exists(ruta_json):
            figura = figura_desde_json(ruta_json, modo)
        elif i < len(respaldos) and respaldos[i]:
            figura = figura_desde_datos(respaldos[i], modo)
        elif os.path.exists(ruta):
            st.image(ruta)
            continue
        else:
            continue
        st.plotly_chart(figura, key=clave, config={"displaylogo": False})


# 2) Entrada: caja de chat o tarjeta de sugerencia
# (la caja siempre se dibuja abajo, aunque se lea aqui primero)
pregunta = st.chat_input("Escribe tu pregunta de economía...")

if not pregunta and st.session_state.pregunta_pendiente:
    pregunta = st.session_state.pregunta_pendiente
    st.session_state.pregunta_pendiente = None


# 3) Bienvenida (solo si la conversacion esta vacia) o encabezado normal
if not st.session_state.mensajes and not pregunta:
    encabezado(
        f"{saludo()}, soy Luna",
        "Tu analista económica y de inversiones. Analizo la economía de cualquier país "
        "—crecimiento, inflación, deuda y proyecciones— y evalúo empresas para invertir, "
        "con datos oficiales del Banco Mundial, el FMI y la SEC.",
    )
    st.markdown("##### ¿Qué quieres analizar hoy?")

    columnas = st.columns(2)
    for i, (icono, titulo, texto) in enumerate(SUGERENCIAS):
        with columnas[i % 2]:
            st.button(
                f"**{titulo}**  \n{texto}",
                icon=icono,
                key=f"sugerencia_{i}",
                on_click=usar_sugerencia,
                args=(texto,),
                use_container_width=True,
            )
else:
    encabezado(
        "Asistente",
        "Economía de países y empresas, con datos oficiales y fuentes verificables.",
    )


# 4) Historial del chat
for n, mensaje in enumerate(st.session_state.mensajes):
    avatar = AVATAR_USUARIO if mensaje["role"] == "user" else AVATAR_AGENTE
    with st.chat_message(mensaje["role"], avatar=avatar):
        st.markdown(mensaje["content"])
        mostrar_graficas(mensaje, n)


# 5) Cliente de Groq: se crea una sola vez
@st.cache_resource
def obtener_cliente():
    return agente_core.crear_cliente()


# 6) Responder la pregunta
if pregunta:
    with st.chat_message("user", avatar=AVATAR_USUARIO):
        st.markdown(pregunta)

    historial = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.mensajes
    ]
    perfil_texto = db.perfil_como_texto(db.obtener_perfil())

    with st.chat_message("assistant", avatar=AVATAR_AGENTE):
        try:
            cliente = obtener_cliente()
            with st.spinner("Analizando datos..."):
                resultado = agente_core.responder(cliente, historial, pregunta, perfil_texto)
        except Exception as error:
            resultado = None
            if "rate_limit" in str(error) or "429" in str(error):
                st.warning(
                    "Se alcanzó el límite de uso por minuto de Groq. "
                    "Espera unos segundos y vuelve a enviar tu pregunta."
                )
            else:
                st.error(f"No pude completar la consulta: {error}")

        if resultado:
            st.markdown(resultado["texto"])

    if resultado:
        mensaje_usuario = {
            "role": "user",
            "content": pregunta,
            "hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
        mensaje_luna = {
            "role": "assistant",
            "content": resultado["texto"],
            "graficas": resultado["graficas"],
            "graficas_datos": leer_datos_graficas(resultado["graficas"]),
            "herramientas": resultado["herramientas"],
        }
        st.session_state.mensajes.extend([mensaje_usuario, mensaje_luna])

        # Guardar en Supabase (si no hay conexion, la app sigue funcionando)
        if db.disponible():
            if st.session_state.conversacion_id is None:
                st.session_state.conversacion_id = db.crear_conversacion(pregunta)
                db.conversaciones_recientes.clear()
            conv_id = st.session_state.conversacion_id
            if conv_id:
                db.guardar_mensaje(conv_id, mensaje_usuario)
                db.guardar_mensaje(conv_id, mensaje_luna, mensaje_luna["graficas_datos"])
                db.guardar_simulaciones(conv_id, resultado["herramientas"])

        st.rerun()