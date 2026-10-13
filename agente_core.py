#######################
# Agente Economico    #
# Nucleo del agente   #
#######################

import os
import json

from dotenv import load_dotenv
from groq import Groq

from intermediate_tools import IntermediateTools
from empresas_tools import EmpresasTools


# Cargar variables de entorno (.env)
load_dotenv()

MODELO = "openai/gpt-oss-120b"
MEMORY_MAX_MESSAGES = 10
MAX_RONDAS_HERRAMIENTAS = 8

# En la interfaz web la grafica se muestra en la pagina, no en otra ventana
IntermediateTools.abrir_grafica = False


class Herramientas(IntermediateTools, EmpresasTools):
    """Une las herramientas de paises (IntermediateTools) y de empresas (EmpresasTools)."""
    pass


SYSTEM_PROMPT = r"""Eres Luna, la asesora economica y de inversiones de Luna Economics. Hablas en español y ayudas
a analizar la situacion economica de paises y empresas, y a orientar decisiones de inversion
de forma responsable.

Tu objetivo es entregar analisis claros y profesionales, siempre basados en datos reales
de las herramientas, y ayudar a la persona a decidir por si misma.

Herramientas disponibles:
- consultar_tipo_cambio_api: da el tipo de cambio actual de una moneda respecto al quetzal.
- convertir_moneda: convierte un monto de una moneda a otra usando tipos de cambio actuales.
- diversificar_inversion: reparte un monto entre renta fija, acciones y efectivo segun el perfil.
- interes_compuesto: calcula el valor futuro de una inversion segun capital, tasa anual y años.
- datos_pais: entrega region, nivel de ingreso y capital de un pais.
- indicadores_economicos: entrega indicadores del Banco Mundial como PIB, PIB per capita,
  crecimiento, inflacion, desempleo, deuda publica y exportaciones de un pais.
- pronostico_fmi: entrega los ultimos 5 años observados y las proyecciones del FMI de
  crecimiento, inflacion, desempleo, deuda o cuenta corriente de un pais.
- serie_historica: muestra la evolucion de un indicador en los ultimos años con promedio,
  maximo, minimo, volatilidad y crecimiento promedio anual compuesto.
- comparar_paises: compara de 2 a 8 paises en un mismo indicador y devuelve un ranking.
- indicadores_sociales: entrega poblacion, urbanizacion, esperanza de vida, Gini, pobreza,
  remesas y alfabetizacion de un pais.
- tasa_real: calcula la tasa de interes real con la ecuacion de Fisher.
- poder_adquisitivo: calcula cuanto vale hoy un monto de un año pasado segun la inflacion.
- graficar: crea una grafica de la evolucion de un indicador para uno o varios paises
  y la guarda como imagen PNG en la carpeta graficas.
- analizar_empresa: analiza una empresa que cotiza en bolsa (Yahoo Finance): precio, rendimiento,
  volatilidad, caida maxima, valuacion (PER), dividendos, margen, ROE, deuda y comparacion con el S&P 500.
- comparar_empresas: compara de 2 a 6 empresas en rendimiento, riesgo y valuacion, ordenadas por
  rendimiento por unidad de riesgo.
- estados_financieros: entrega ingresos, utilidad, activos, pasivos y ratios oficiales de los
  ultimos 5 años desde la SEC de EE. UU. (solo empresas que reportan en EE. UU.).

QUE HERRAMIENTA USAR SEGUN LA PREGUNTA:
- Situacion actual de un pais: indicadores_economicos.
- Como ha evolucionado algo o tendencias: serie_historica.
- Futuro, pronosticos o proyecciones: pronostico_fmi.
- Comparar paises o rankings: comparar_paises.
- Pobreza, desigualdad o temas sociales: indicadores_sociales.
- Si una inversion o un ahorro realmente gana: tasa_real.
- Cuanto vale hoy dinero del pasado: poder_adquisitivo.
- Cuando pidan una grafica, ver, dibujar o visualizar datos: graficar.
- Para un analisis completo de un pais puedes combinar varias herramientas.
- Analizar una empresa o accion: analizar_empresa; si cotiza en EE. UU., complementa con
  estados_financieros para verificar con cifras oficiales.
- Comparar empresas o acciones: comparar_empresas.

COMO ORIENTAR SOBRE INVERSIONES:
1) Segun el perfil de la persona (conservador, moderado o agresivo), usa diversificar_inversion
   para recomendar como repartir su dinero entre renta fija, acciones y efectivo, y explica
   por que ese reparto encaja con su perfil.
2) Cuando la persona pregunte en que pais invertir o compare paises, usa indicadores_economicos
   para cada pais y recomienda cual luce mas favorable, explicando con los datos reales por que
   (por ejemplo menor inflacion, mayor crecimiento, menor deuda). Marca esto como interpretacion.
3) Sobre empresas o acciones: analiza SOLO las empresas que la persona mencione, usando
   analizar_empresa, comparar_empresas y estados_financieros. Evalua cuatro dimensiones con los
   datos: rendimiento (rendimiento anual promedio y frente al S&P 500), riesgo (volatilidad y
   caida maxima), valuacion (PER frente a su historia o su sector si lo sabes) y salud financiera
   (margen, ROE, deuda). Relaciona el resultado con el perfil de riesgo de la persona: una
   volatilidad alta encaja mejor con un perfil agresivo que con uno conservador.
   - No inventes empresas ni sugieras por iniciativa propia una lista de acciones para comprar.
   - Nunca digas "compra" o "vende"; presenta fortalezas, riesgos y que encaja con cada perfil.
   - Recuerda que rendimientos pasados no garantizan rendimientos futuros, que Yahoo Finance no
     es una fuente oficial y que los datos del año en curso son parciales.
   - Si la persona invierte en quetzales, menciona el riesgo cambiario (USD/GTQ).
   - Al comparar empresas, verifica que cada cifra corresponda a la empresa correcta antes de
     escribirla. Diferencias menores a 1 punto porcentual se describen como "similares", no
     como ventaja de una sobre otra.
   - No menciones promedios del sector, PER historico ni otros datos que las herramientas no
     devolvieron. Si serian utiles, di que no los tienes.
   - Nunca escribas en la respuesta el JSON o los argumentos de una herramienta, ni un
     "resultado esperado". Si necesitas un calculo, ejecuta la herramienta; si no la ejecutaste,
     no presentes resultados.

PREGUNTAS CONCEPTUALES O TEORICAS DE ECONOMIA:
- Si la pregunta es de teoria o conceptos (inflacion, IS-LM, ley de Okun, curva de Phillips,
  convergencia economica, politica monetaria o fiscal, oferta y demanda, comercio internacional),
  responde con tu conocimiento de economista: define el concepto, explica el mecanismo,
  da la formula si existe y un ejemplo aplicado, idealmente a Guatemala o America Latina.
- Marca ese tipo de respuesta como "Explicacion conceptual". No necesitas herramientas para eso,
  pero si un dato real ayuda a ilustrar el concepto, usa una herramienta para traerlo.
- Si la pregunta no tiene relacion con economia, finanzas o inversion, indica amablemente que
  eres un asesor economico y ofrece ayuda con un tema relacionado.

FORMATO DE RESPUESTA:
- Empieza con la respuesta directa en una o dos oraciones y despues desarrolla.
- Usa titulos cortos, listas y tablas en formato Markdown cuando ayuden a leer los datos.
- Escribe las formulas en LaTeX entre dobles signos de dolar, por ejemplo:
  $$ r = \frac{1 + i}{1 + \pi} - 1 $$
  Nunca uses \[ \] ni \( \) para las formulas.
- Cuando una herramienta devuelva un valor exacto, usa ese valor en la interpretacion,
  no el aproximado.
- Redondea todas las cifras a 2 decimales como maximo. Usa punto decimal y coma para miles
  (ej. 4.28 %, 6,598.18 USD). Escribe montos muy grandes en millones o miles de millones
  (ej. 123,306 millones de USD).
   
REGLAS MUY IMPORTANTES:
- Cuando presentes cifras economicas, usa siempre los datos que devuelven las herramientas,
  e indica el año de cada indicador. Estos datos son reales y verificables.
- Separa siempre y claramente los DATOS de la INTERPRETACION.
- Toda recomendacion o explicacion de causas va marcada como "Interpretacion general" y aclaras
  que no proviene de las herramientas y que se recomienda verificar en fuentes oficiales.
- Nunca afirmes con certeza que algo ES una buena inversion ni garantices rentabilidad.
  Ofrece orientacion informativa para que la persona decida, no ordenes de compra.
- Nunca inventes datos, nombres de empresas, ni cifras que no vengan de las herramientas.
- Responde de forma ordenada y profesional.

REGLAS DE ANALISIS ECONOMICO:
- Distingue los datos observados de las proyecciones del FMI; las proyecciones no son datos confirmados.
  Los datos del Banco Mundial son siempre observados, nunca proyecciones.
- Si un dato del Banco Mundial tiene mas de 3 años de antigüedad (por ejemplo la deuda publica),
  usa pronostico_fmi con el indicador correspondiente para obtener un dato mas reciente, y di
  de que fuente y año es cada cifra.
- Distingue el crecimiento nominal del crecimiento real.
- Compara la inflacion con la meta del banco central de ese pais si la conoces
  (para Guatemala, la meta del Banguat es 4% +/- 1 punto). Si no conoces la meta, dilo.
- Cuando uses una herramienta que reciba un pais, envia siempre el codigo ISO3 del pais
  (por ejemplo GTM, MEX, BRA, DEU, USA), aunque el usuario lo escriba en español.
  En comparar_paises y graficar envia los codigos separados por coma, ej. GTM, HND, CRI.
- Cuando hagas una grafica, indica la ruta donde quedo guardada y describe en pocas
  lineas lo que muestra, usando los datos que devolvio la herramienta.
- Si la deuda publica supera el 60% del PIB, advierte el riesgo fiscal como interpretacion general.
- Cuando compares paises, avisa si los datos son de años distintos.
- Si una herramienta no tiene datos, dilo con claridad y no inventes la cifra.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "consultar_tipo_cambio_api",
            "description": "Consulta el tipo de cambio actual de una moneda respecto al quetzal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "moneda": {
                        "type": "string",
                        "description": "Código de moneda, por ejemplo USD"
                    }
                },
                "required": ["moneda"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "convertir_moneda",
            "description": "Convierte un monto de una moneda a otra usando tipos de cambio actuales.",
            "parameters": {
                "type": "object",
                "properties": {
                    "monto": {"type": "number"},
                    "origen": {"type": "string"},
                    "destino": {"type": "string"}
                },
                "required": ["monto", "origen", "destino"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "diversificar_inversion",
            "description": "Distribuye un monto según el perfil de inversión.",
            "parameters": {
                "type": "object",
                "properties": {
                    "monto": {"type": "number"},
                    "perfil": {"type": "string"}
                },
                "required": ["monto", "perfil"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "interes_compuesto",
            "description": "Calcula el interés compuesto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "capital": {"type": "number"},
                    "tasa_anual": {"type": "number"},
                    "anios": {"type": "integer"}
                },
                "required": ["capital", "tasa_anual", "anios"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "datos_pais",
            "description": "Obtiene región, nivel de ingreso y capital de un país.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pais": {"type": "string"}
                },
                "required": ["pais"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "indicadores_economicos",
            "description": (
                "Obtiene indicadores economicos reales de un pais desde el Banco Mundial: "
                "PIB, PIB per capita, crecimiento del PIB, inflacion, desempleo, "
                "deuda publica y exportaciones. Usar para analizar la economia de un pais."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pais": {
                        "type": "string",
                        "description": "Nombre del pais a analizar, por ejemplo Guatemala"
                    }
                },
                "required": ["pais"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pronostico_fmi",
            "description": (
                "Obtiene los ultimos 5 anios observados y las proyecciones del FMI "
                "para un pais. Usala cuando pregunten por el futuro, pronosticos o "
                "cuanto crecera, cuanta inflacion habra, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pais": {
                        "type": "string",
                        "description": "Nombre del pais en ingles o codigo ISO3, ej. Guatemala o GTM"
                    },
                    "indicador": {
                        "type": "string",
                        "enum": ["crecimiento", "inflacion", "desempleo", "deuda", "cuenta_corriente"],
                        "description": "Indicador a proyectar"
                    }
                },
                "required": ["pais"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "serie_historica",
            "description": (
                "Devuelve la evolucion de un indicador en los ultimos N anios con "
                "promedio, maximo, minimo, volatilidad y crecimiento promedio anual "
                "compuesto. Usala para tendencias o preguntas de como ha evolucionado algo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pais": {"type": "string", "description": "Nombre del pais"},
                    "indicador": {
                        "type": "string",
                        "enum": [
                            "pib", "pib_per_capita", "crecimiento", "inflacion",
                            "desempleo", "deuda", "exportaciones", "importaciones",
                            "remesas", "inversion_extranjera", "poblacion"
                        ],
                        "description": "Indicador a analizar"
                    },
                    "anios": {
                        "type": "integer",
                        "description": "Cantidad de anios hacia atras, entre 2 y 50. Por defecto 10"
                    }
                },
                "required": ["pais", "indicador"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "comparar_paises",
            "description": (
                "Compara de 2 a 8 paises en un mismo indicador y devuelve un ranking "
                "de mayor a menor con el promedio del grupo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "paises": {
                        "type": "string",
                        "description": "Paises separados por coma, ej. Guatemala, Honduras, Costa Rica"
                    },
                    "indicador": {
                        "type": "string",
                        "enum": [
                            "pib", "pib_per_capita", "crecimiento", "inflacion",
                            "desempleo", "deuda", "exportaciones", "importaciones",
                            "remesas", "inversion_extranjera", "poblacion"
                        ],
                        "description": "Indicador para comparar"
                    }
                },
                "required": ["paises", "indicador"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "indicadores_sociales",
            "description": (
                "Devuelve indicadores sociales de un pais: poblacion, urbanizacion, "
                "esperanza de vida, Gini, pobreza, remesas y alfabetizacion."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pais": {"type": "string", "description": "Nombre del pais"}
                },
                "required": ["pais"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tasa_real",
            "description": (
                "Calcula la tasa de interes real con la ecuacion de Fisher a partir "
                "de una tasa nominal y una inflacion, ambas en porcentaje."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tasa_nominal": {"type": "number", "description": "Tasa nominal en %, ej. 6"},
                    "inflacion": {"type": "number", "description": "Inflacion en %, ej. 4"}
                },
                "required": ["tasa_nominal", "inflacion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "poder_adquisitivo",
            "description": (
                "Calcula cuanto vale hoy un monto de un anio pasado usando el indice "
                "de precios al consumidor del pais. Ej. cuanto valen hoy Q100 de 2010."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "monto": {"type": "number", "description": "Monto en moneda local"},
                    "anio_inicial": {"type": "integer", "description": "Anio del monto original"},
                    "pais": {"type": "string", "description": "Nombre del pais, por defecto Guatemala"}
                },
                "required": ["monto", "anio_inicial"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "graficar",
            "description": (
                "Crea una grafica de lineas con la evolucion de un indicador para uno "
                "o varios paises (maximo 8) y la guarda como imagen PNG. Usala cuando "
                "pidan graficar, ver, dibujar o visualizar datos."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "paises": {
                        "type": "string",
                        "description": "Codigos ISO3 separados por coma, ej. GTM, HND, CRI"
                    },
                    "indicador": {
                        "type": "string",
                        "enum": [
                            "pib", "pib_per_capita", "crecimiento", "inflacion",
                            "desempleo", "deuda", "exportaciones", "importaciones",
                            "remesas", "inversion_extranjera", "poblacion"
                        ],
                        "description": "Indicador a graficar"
                    },
                    "anios": {
                        "type": "integer",
                        "description": "Cantidad de anios hacia atras, entre 2 y 50. Por defecto 10"
                    }
                },
                "required": ["paises", "indicador"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analizar_empresa",
            "description": (
                "Analiza una empresa que cotiza en bolsa: precio, rendimiento anual promedio, "
                "volatilidad, caida maxima, PER, dividendos, margen, ROE, deuda y comparacion "
                "con el S&P 500. Crea una grafica de 100 invertidos."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "empresa": {
                        "type": "string",
                        "description": "Ticker bursatil si lo conoces (ej. AAPL, MSFT, WMT) o el nombre de la empresa"
                    },
                    "anios": {
                        "type": "integer",
                        "description": "Años de historia a analizar, entre 1 y 20. Por defecto 5"
                    }
                },
                "required": ["empresa"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "comparar_empresas",
            "description": (
                "Compara de 2 a 6 empresas en rendimiento, volatilidad, caida maxima, PER, "
                "margen y dividendos, ordenadas por rendimiento por unidad de riesgo. Crea una grafica."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "empresas": {
                        "type": "string",
                        "description": "Tickers separados por coma, ej. AAPL, MSFT, GOOGL"
                    },
                    "anios": {
                        "type": "integer",
                        "description": "Años de historia a analizar, entre 1 y 20. Por defecto 5"
                    }
                },
                "required": ["empresas"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "estados_financieros",
            "description": (
                "Estados financieros oficiales de los ultimos 5 años desde la SEC de EE. UU.: "
                "ingresos, utilidad neta, activos, pasivos, patrimonio, efectivo, margen neto, ROE "
                "y endeudamiento. Solo empresas que reportan en EE. UU."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "empresa": {
                        "type": "string",
                        "description": "Ticker de EE. UU. (ej. AAPL) o nombre de la empresa"
                    }
                },
                "required": ["empresa"]
            }
        }
    }
]



def crear_cliente(api_key: str = None) -> Groq:
    """Crea el cliente de Groq. Si no se pasa la clave, la toma del .env."""
    clave = api_key or os.environ.get("GROQ_API_KEY")

    if not clave:
        raise ValueError(
            "No se encontro GROQ_API_KEY. Agregala al archivo .env "
            "o en los secretos de Streamlit."
        )

    return Groq(api_key=clave, max_retries=5) 


def ejecutar_herramienta(tools: IntermediateTools, name: str, args: dict):
    """Busca la funcion con ese nombre en IntermediateTools y la ejecuta."""
    nombres_validos = {t["function"]["name"] for t in TOOLS}

    if name not in nombres_validos:
        print(f"Se intento llamar a una herramienta desconocida: {name}")
        return {"error": f"Herramienta desconocida: {name}"}

    funcion = getattr(tools, name)

    try:
        return funcion(**args)
    except TypeError as error:
        return {"error": f"Argumentos invalidos para {name}: {error}"}
    except Exception as error:
        return {"error": f"Fallo la herramienta {name}: {error}"}

def responder(client: Groq, historial: list, user_text: str, perfil_texto: str = "") -> dict:
    """
    Envia la pregunta al modelo, ejecuta las herramientas que pida
    y devuelve un diccionario con:
      - texto: la respuesta final del agente
      - herramientas: lista de herramientas usadas con sus argumentos
      - graficas: rutas de las imagenes creadas por la herramienta graficar
    """
    sistema = SYSTEM_PROMPT
    if perfil_texto:
        sistema += (
            "\n\nPERFIL GUARDADO DE LA PERSONA: " + perfil_texto + ". Usalo para orientar las "
            "recomendaciones de inversion. Si en su pregunta indica otro perfil, usa el de la pregunta."
        )
    messages = [{"role": "system", "content": sistema}]
    messages.extend(historial[-MEMORY_MAX_MESSAGES:])
    messages.append({"role": "user", "content": user_text})

    tools = Herramientas()
    herramientas_usadas = []
    graficas = []

    for _ in range(MAX_RONDAS_HERRAMIENTAS):
        resp = client.chat.completions.create(
            model=MODELO,
            messages=messages,
            tools=TOOLS
        )

        msg = resp.choices[0].message

        if not getattr(msg, "tool_calls", None):
            return {
                "texto": msg.content or "",
                "herramientas": herramientas_usadas,
                "graficas": graficas
            }

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [tc.model_dump() for tc in msg.tool_calls]
        })

        for tool_call in msg.tool_calls:
            name = tool_call.function.name

            try:
                args = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            result = ejecutar_herramienta(tools, name, args)
            herramientas_usadas.append({"nombre": name, "argumentos": args, "resultado": result})

            if isinstance(result, dict) and result.get("grafica_guardada_en"):
                graficas.append(result["grafica_guardada_en"])

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False)
            })

    return {
        "texto": (
            "La consulta necesito demasiados pasos y la detuve para no quedar en un ciclo. "
            "Intenta hacer una pregunta mas especifica."
        ),
        "herramientas": herramientas_usadas,
        "graficas": graficas
    }