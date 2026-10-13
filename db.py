#######################################
# Luna Economics                      #
# Conexion con Supabase (base de datos)#
#######################################
# Todas las funciones son "seguras": si Supabase falla, la app sigue
# funcionando (solo no guarda) y el error se imprime en la terminal.

import functools
import os
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

HERRAMIENTAS_SIMULACION = {"diversificar_inversion", "interes_compuesto", "tasa_real"}


def _config(nombre):
    """Lee la variable del .env (local) o de los secretos de Streamlit (nube)."""
    valor = os.environ.get(nombre)
    if valor:
        return valor
    try:
        return st.secrets[nombre]
    except Exception:
        return None


@st.cache_resource
def _cliente():
    from supabase import create_client

    url, clave = _config("SUPABASE_URL"), _config("SUPABASE_KEY")
    if not url or not clave:
        return None
    return create_client(url, clave)


def disponible():
    try:
        return _cliente() is not None
    except Exception:
        return False


def _seguro(defecto=None):
    """Si la funcion falla, imprime el error y devuelve un valor por defecto."""
    def decorador(funcion):
        @functools.wraps(funcion)
        def envoltura(*args, **kwargs):
            if not disponible():
                return defecto
            try:
                return funcion(*args, **kwargs)
            except Exception as error:
                print(f"[Supabase] Error en {funcion.__name__}: {error}")
                return defecto
        return envoltura
    return decorador


def _ahora():
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------
# Conversaciones y mensajes
# ---------------------------------------------------------------
@_seguro()
def crear_conversacion(titulo):
    r = _cliente().table("conversaciones").insert({"titulo": titulo[:80]}).execute()
    return r.data[0]["id"]


@_seguro()
def guardar_mensaje(conversacion_id, mensaje, graficas_datos=None):
    _cliente().table("mensajes").insert({
        "conversacion_id": conversacion_id,
        "rol": mensaje["role"],
        "contenido": mensaje["content"],
        "hora": mensaje.get("hora"),
        "graficas": mensaje.get("graficas", []),
        "graficas_datos": graficas_datos or [],
        "herramientas": mensaje.get("herramientas", []),
    }).execute()
    _cliente().table("conversaciones").update({"actualizada": _ahora()}) \
        .eq("id", conversacion_id).execute()


@_seguro(defecto=[])
def listar_conversaciones(limite=10):
    return _cliente().table("conversaciones").select("id, titulo, actualizada") \
        .order("actualizada", desc=True).limit(limite).execute().data


@_seguro(defecto=[])
def cargar_mensajes(conversacion_id):
    filas = _cliente().table("mensajes").select("*") \
        .eq("conversacion_id", conversacion_id).order("id").execute().data
    mensajes = []
    for f in filas:
        m = {"role": f["rol"], "content": f["contenido"]}
        if f["rol"] == "user":
            m["hora"] = f.get("hora") or ""
        else:
            m["graficas"] = f.get("graficas") or []
            m["graficas_datos"] = f.get("graficas_datos") or []
            m["herramientas"] = f.get("herramientas") or []
        mensajes.append(m)
    return mensajes


@st.cache_data(ttl=60, show_spinner=False)
def conversaciones_recientes(limite=8):
    """Version con cache (1 minuto) para el menu lateral: evita consultar en cada clic."""
    return listar_conversaciones(limite)


@_seguro()
def borrar_conversacion(conversacion_id):
    _cliente().table("conversaciones").delete().eq("id", conversacion_id).execute()


# ---------------------------------------------------------------
# Perfil del inversionista (una sola fila, id = 1)
# ---------------------------------------------------------------
@_seguro()
def obtener_perfil():
    filas = _cliente().table("perfil_inversor").select("*").eq("id", 1).execute().data
    return filas[0] if filas else None


@_seguro(defecto=False)
def guardar_perfil(perfil, monto, moneda, horizonte_anios, objetivo):
    _cliente().table("perfil_inversor").upsert({
        "id": 1, "perfil": perfil, "monto": monto, "moneda": moneda,
        "horizonte_anios": horizonte_anios, "objetivo": objetivo, "actualizado": _ahora(),
    }).execute()
    return True


def perfil_como_texto(perfil):
    """Resume el perfil para que el agente lo tome en cuenta."""
    if not perfil or not perfil.get("perfil"):
        return ""
    partes = [f"perfil de riesgo {perfil['perfil']}"]
    if perfil.get("monto"):
        partes.append(f"monto disponible {float(perfil['monto']):,.2f} {perfil.get('moneda') or ''}".strip())
    if perfil.get("horizonte_anios"):
        partes.append(f"horizonte de {perfil['horizonte_anios']} años")
    if perfil.get("objetivo"):
        partes.append(f"objetivo: {perfil['objetivo']}")
    return "; ".join(partes)


# ---------------------------------------------------------------
# Simulaciones de inversion
# ---------------------------------------------------------------
@_seguro()
def guardar_simulaciones(conversacion_id, herramientas):
    filas = [
        {"conversacion_id": conversacion_id, "herramienta": h["nombre"],
         "argumentos": h.get("argumentos", {}), "resultado": h.get("resultado")}
        for h in herramientas if h.get("nombre") in HERRAMIENTAS_SIMULACION
    ]
    if filas:
        _cliente().table("simulaciones").insert(filas).execute()


@_seguro(defecto=[])
def listar_simulaciones(limite=20):
    return _cliente().table("simulaciones").select("*") \
        .order("creada", desc=True).limit(limite).execute().data


@_seguro()
def borrar_simulacion(simulacion_id):
    _cliente().table("simulaciones").delete().eq("id", simulacion_id).execute()


# ---------------------------------------------------------------
# Paises y empresas en seguimiento
# ---------------------------------------------------------------
@_seguro(defecto=False)
def agregar_seguimiento(tipo, nombre, codigo, diagnostico=None, nota=None):
    _cliente().table("seguimiento").upsert({
        "tipo": tipo, "nombre": nombre, "codigo": codigo.upper(),
        "diagnostico": diagnostico, "nota": nota, "agregado": _ahora(),
    }, on_conflict="tipo,codigo").execute()
    return True


@_seguro(defecto=[])
def listar_seguimiento():
    return _cliente().table("seguimiento").select("*") \
        .order("agregado", desc=True).execute().data


@_seguro()
def quitar_seguimiento(seguimiento_id):
    _cliente().table("seguimiento").delete().eq("id", seguimiento_id).execute()