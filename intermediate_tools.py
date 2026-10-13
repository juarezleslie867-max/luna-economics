#######################
# Agente Economico    #
# Herramientas        #
#######################

# Importacion para el manejo de sistema y peticiones HTTP
import os
import json
import statistics
from datetime import datetime
from urllib.parse import quote

import requests


class IntermediateTools:

    def __init__(self):
        pass

    # -----------------------------------------------------------------
    # Metodo interno de apoyo: busca el codigo de un pais en el Banco
    # Mundial a partir de su nombre. Devuelve (codigo, nombre) o (None, None).
    # No es una herramienta del agente, solo apoya a las otras.
    # -----------------------------------------------------------------
    def _buscar_codigo_pais(self, pais: str):
        # La lista de paises se descarga una sola vez y se guarda (cache)
        if not hasattr(self, "_paises_cache"):
            url = "https://api.worldbank.org/v2/country"
            params = {"format": "json", "per_page": 400}

            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                datos = response.json()

                if not isinstance(datos, list) or len(datos) < 2:
                    return None, None

                # Solo paises reales, sin agregados regionales
                type(self)._paises_cache = [
                    p for p in datos[1]
                    if p.get("region", {}).get("value", "") not in ("", "Aggregates")
                ]

            except Exception as error:
                print(f"Error al buscar codigo de pais: {error}")
                return None, None

        objetivo = pais.strip().lower()

        # 1) Coincidencia exacta: codigo ISO3, codigo ISO2 o nombre completo
        for p in self._paises_cache:
            if objetivo in (
                p.get("id", "").lower(),
                p.get("iso2Code", "").lower(),
                p.get("name", "").lower()
            ):
                return p.get("id"), p.get("name", pais)

        # 2) Coincidencia parcial del nombre, ej. "korea" en "Korea, Rep."
        if len(objetivo) > 3:
            for p in self._paises_cache:
                if objetivo in p.get("name", "").lower():
                    return p.get("id"), p.get("name", pais)

        return None, None

    # -----------------------------------------------------------------
    # Metodo interno de apoyo: descarga la serie de un indicador del
    # Banco Mundial. Devuelve una lista [(anio, valor), ...] ordenada de
    # menor a mayor anio, sin valores vacios. Devuelve None si hubo error.
    # -----------------------------------------------------------------
    def _serie_wb(self, codigo_pais: str, codigo_ind: str, params: dict):
        url = f"https://api.worldbank.org/v2/country/{codigo_pais}/indicator/{codigo_ind}"
        params = dict(params)
        params["format"] = "json"

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            datos = response.json()

            if (
                not isinstance(datos, list)
                or len(datos) < 2
                or not isinstance(datos[1], list)
            ):
                return []

            serie = [
                (int(d["date"]), d["value"])
                for d in datos[1]
                if d.get("value") is not None
            ]
            return sorted(serie)

        except Exception as error:
            print(f"Error al consultar el Banco Mundial ({codigo_ind}): {error}")
            return None

    # -----------------------------------------------------------------
    # Metodo interno de apoyo: catalogo de indicadores que usan las
    # herramientas 8 y 9. "nivel" = un monto, "tasa" = un porcentaje.
    # -----------------------------------------------------------------
    def _catalogo_indicadores(self):
        return {
            "pib": ("NY.GDP.MKTP.CD", "PIB (USD actuales)", "nivel"),
            "pib_per_capita": ("NY.GDP.PCAP.CD", "PIB per capita (USD actuales)", "nivel"),
            "crecimiento": ("NY.GDP.MKTP.KD.ZG", "Crecimiento del PIB real (%)", "tasa"),
            "inflacion": ("FP.CPI.TOTL.ZG", "Inflacion, precios al consumidor (%)", "tasa"),
            "desempleo": ("SL.UEM.TOTL.ZS", "Desempleo (% de la fuerza laboral)", "tasa"),
            "deuda": ("GC.DOD.TOTL.GD.ZS", "Deuda del gobierno central (% del PIB)", "tasa"),
            "exportaciones": ("NE.EXP.GNFS.ZS", "Exportaciones (% del PIB)", "tasa"),
            "importaciones": ("NE.IMP.GNFS.ZS", "Importaciones (% del PIB)", "tasa"),
            "remesas": ("BX.TRF.PWKR.DT.GD.ZS", "Remesas recibidas (% del PIB)", "tasa"),
            "inversion_extranjera": (
                "BX.KLT.DINV.WD.GD.ZS",
                "Inversion extranjera directa neta (% del PIB)",
                "tasa"
            ),
            "poblacion": ("SP.POP.TOTL", "Poblacion total", "nivel")
        }

    # 1) Tipo de cambio de una moneda usando una API real (sin API key)
    def consultar_tipo_cambio_api(self, moneda: str = ""):
        print(f"Herramienta consultar_tipo_cambio_api llamada con moneda: {moneda}")

        if not moneda:
            return "Error: se requiere el código de la moneda."

        url = f"https://open.er-api.com/v6/latest/{moneda.upper()}"

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            datos = response.json()

            tasas = datos.get("rates", {})

            if "GTQ" not in tasas:
                return f"No se encontró el tipo de cambio para {moneda}"

            return {
                "moneda": moneda.upper(),
                "tipo_cambio_gtq": tasas["GTQ"],
                "descripcion": f"1 {moneda.upper()} equivale a {tasas['GTQ']} quetzales"
            }

        except Exception as error:
            print(f"Error al consultar_tipo_cambio_api: {error}")
            return f"ERROR: No se pudo obtener el tipo de cambio de {moneda}"

    # 2) Convertir un monto de una moneda a otra usando una API real
    def convertir_moneda(self, monto: float, origen: str, destino: str):
        print(
            f"Herramienta convertir_moneda llamada con "
            f"monto: {monto}, origen: {origen}, destino: {destino}"
        )

        if monto < 0 or not origen or not destino:
            return "Error: datos inválidos para la conversión."

        origen = origen.upper()
        destino = destino.upper()
        url = f"https://open.er-api.com/v6/latest/{origen}"

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            datos = response.json()

            tasas = datos.get("rates", {})

            if destino not in tasas:
                return f"No tengo información para la moneda {destino}"

            tasa = tasas[destino]
            convertido = round(monto * tasa, 2)

            return {
                "monto_original": monto,
                "origen": origen,
                "destino": destino,
                "tasa": tasa,
                "resultado": convertido
            }

        except Exception as error:
            print(f"Error al convertir_moneda: {error}")
            return f"ERROR: No se pudo convertir de {origen} a {destino}"

    # 3) Diversificar una inversion segun el perfil (calculo)
    def diversificar_inversion(self, monto: float, perfil: str = "moderado"):
        print(
            f"Herramienta diversificar_inversion llamada con "
            f"monto: {monto}, perfil: {perfil}"
        )

        perfil = perfil.lower()

        repartos = {
            "conservador": {"renta_fija": 0.70, "acciones": 0.20, "efectivo": 0.10},
            "moderado": {"renta_fija": 0.50, "acciones": 0.40, "efectivo": 0.10},
            "agresivo": {"renta_fija": 0.30, "acciones": 0.60, "efectivo": 0.10}
        }

        if perfil not in repartos:
            return "Error: el perfil debe ser conservador, moderado o agresivo."

        reparto = repartos[perfil]

        return {
            "perfil": perfil,
            "monto_total": monto,
            "renta_fija": round(monto * reparto["renta_fija"], 2),
            "acciones": round(monto * reparto["acciones"], 2),
            "efectivo": round(monto * reparto["efectivo"], 2)
        }

    # 4) Interes compuesto (calculo)
    def interes_compuesto(self, capital: float, tasa_anual: float, anios: int):
        print(
            f"Herramienta interes_compuesto llamada con "
            f"capital: {capital}, tasa_anual: {tasa_anual}, anios: {anios}"
        )

        if capital <= 0 or anios <= 0:
            return "Error: el capital y los años deben ser mayores que cero."

        tasa = tasa_anual / 100
        valor_futuro = capital * ((1 + tasa) ** anios)
        interes_ganado = valor_futuro - capital

        return {
            "capital_inicial": capital,
            "tasa_anual": tasa_anual,
            "anios": anios,
            "valor_futuro": round(valor_futuro, 2),
            "interes_ganado": round(interes_ganado, 2)
        }

    # 5) Datos generales de un pais usando el Banco Mundial (sin API key)
    def datos_pais(self, pais: str):
        print(f"Herramienta datos_pais llamada con pais: {pais}")

        if not pais or not pais.strip():
            return "Error: se requiere el nombre del país."

        codigo, nombre = self._buscar_codigo_pais(pais)

        if not codigo:
            return f"No se encontró información para el país {pais}"

        url = f"https://api.worldbank.org/v2/country/{codigo}"
        params = {"format": "json"}

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            datos = response.json()

            if not isinstance(datos, list) or len(datos) < 2 or len(datos[1]) == 0:
                return f"No se encontró información para el país {pais}"

            info = datos[1][0]

            return {
                "pais": info.get("name", nombre),
                "codigo": codigo,
                "region": info.get("region", {}).get("value", "Desconocida"),
                "nivel_ingreso": info.get("incomeLevel", {}).get("value", "Desconocido"),
                "capital": info.get("capitalCity", "Desconocida")
            }

        except Exception as error:
            print(f"Error al procesar datos_pais: {error}")
            return f"ERROR: No se pudo obtener información del país {pais}"

    # 6) Indicadores economicos de un pais usando el Banco Mundial (sin API key)
    def indicadores_economicos(self, pais: str):
        print(f"Herramienta indicadores_economicos llamada con pais: {pais}")

        if not pais or not pais.strip():
            return "Error: se requiere el nombre del país."

        codigo, nombre = self._buscar_codigo_pais(pais)

        if not codigo:
            return f"No se encontró el país {pais}"

        indicadores = {
            "PIB (USD actuales)": "NY.GDP.MKTP.CD",
            "PIB per capita (USD)": "NY.GDP.PCAP.CD",
            "Crecimiento del PIB (%)": "NY.GDP.MKTP.KD.ZG",
            "Inflacion (%)": "FP.CPI.TOTL.ZG",
            "Desempleo (%)": "SL.UEM.TOTL.ZS",
            "Deuda publica (% del PIB)": "GC.DOD.TOTL.GD.ZS",
            "Exportaciones (% del PIB)": "NE.EXP.GNFS.ZS"
        }

        resultado = {"pais": nombre, "codigo": codigo, "indicadores": {}}

        for nombre_ind, codigo_ind in indicadores.items():
            url_wb = (
                f"https://api.worldbank.org/v2/country/{codigo}/indicator/{codigo_ind}"
            )
            params_wb = {"format": "json", "per_page": 1, "mrnev": 1}

            try:
                resp = requests.get(url_wb, params=params_wb, timeout=30)
                datos = resp.json()

                if (
                    isinstance(datos, list)
                    and len(datos) > 1
                    and isinstance(datos[1], list)
                    and len(datos[1]) > 0
                    and datos[1][0].get("value") is not None
                ):
                    valor = datos[1][0]["value"]
                    anio = datos[1][0]["date"]
                    resultado["indicadores"][nombre_ind] = {
                        "valor": valor,
                        "anio": anio
                    }
                else:
                    resultado["indicadores"][nombre_ind] = "Sin datos disponibles"

            except Exception as error:
                print(f"Error al obtener {nombre_ind}: {error}")
                resultado["indicadores"][nombre_ind] = "Error al consultar"

        return resultado

    # 7) Pronosticos del FMI: datos recientes y proyecciones (sin API key)
    def pronostico_fmi(self, pais: str, indicador: str = "crecimiento"):
        print(
            f"Herramienta pronostico_fmi llamada con "
            f"pais: {pais}, indicador: {indicador}"
        )
        if not pais or not pais.strip():
            return "Error: se requiere el nombre del país."
        indicadores = {
            "crecimiento": ("NGDP_RPCH", "Crecimiento del PIB real (%)"),
            "inflacion": ("PCPIPCH", "Inflacion promedio anual (%)"),
            "desempleo": ("LUR", "Tasa de desempleo (%)"),
            "deuda": ("GGXWDG_NGDP", "Deuda publica bruta (% del PIB)"),
            "cuenta_corriente": ("BCA_NGDPD", "Saldo de cuenta corriente (% del PIB)")
        }
        indicador = indicador.lower()
        if indicador not in indicadores:
            return f"Error: usa uno de estos indicadores: {', '.join(indicadores.keys())}"
        codigo, nombre = self._buscar_codigo_pais(pais)
        if not codigo:
            return f"No se encontró el país {pais}"
        codigo_imf, nombre_ind = indicadores[indicador]
        url = f"https://www.imf.org/external/datamapper/api/v1/{codigo_imf}/{codigo}"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            datos = response.json()
            serie = datos.get("values", {}).get(codigo_imf, {}).get(codigo)
            if not serie:
                return f"El FMI no tiene datos de {nombre_ind} para {nombre}"
            anio_actual = datetime.now().year
            anios = sorted(serie.keys())
            observados = [a for a in anios if int(a) < anio_actual][-5:]
            proyectados = [a for a in anios if int(a) >= anio_actual][:5]
            return {
                "pais": nombre,
                "codigo": codigo,
                "indicador": nombre_ind,
                "fuente": "FMI - World Economic Outlook",
                "ultimos_5_anios": {a: serie[a] for a in observados},
                "proyecciones": {a: serie[a] for a in proyectados},
                "nota": "Las proyecciones son estimaciones del FMI, no datos confirmados."
            }
        except Exception as error:
            print(f"Error al consultar pronostico_fmi: {error}")
            return f"ERROR: No se pudo obtener el pronóstico del FMI para {pais}"

    # 8) Serie historica de un indicador con estadisticas (Banco Mundial)
    def serie_historica(self, pais: str, indicador: str = "crecimiento", anios: int = 10):
        print(
            f"Herramienta serie_historica llamada con "
            f"pais: {pais}, indicador: {indicador}, anios: {anios}"
        )
        if not pais or not pais.strip():
            return "Error: se requiere el nombre del país."
        catalogo = self._catalogo_indicadores()
        indicador = indicador.lower()
        if indicador not in catalogo:
            return f"Error: usa uno de estos indicadores: {', '.join(catalogo.keys())}"
        anios = int(anios)
        if anios < 2 or anios > 50:
            return "Error: el número de años debe estar entre 2 y 50."
        codigo, nombre = self._buscar_codigo_pais(pais)
        if not codigo:
            return f"No se encontró el país {pais}"
        codigo_ind, nombre_ind, tipo = catalogo[indicador]
        serie = self._serie_wb(codigo, codigo_ind, {"mrv": anios, "per_page": 100})
        if serie is None:
            return f"ERROR: No se pudo consultar la serie de {nombre_ind}"
        if len(serie) < 2:
            return f"No hay suficientes datos de {nombre_ind} para {nombre}"
        valores = [v for _, v in serie]
        anio_ini, val_ini = serie[0]
        anio_fin, val_fin = serie[-1]
        maximo = max(serie, key=lambda x: x[1])
        minimo = min(serie, key=lambda x: x[1])

        resumen = {
            "promedio": round(statistics.mean(valores), 2),
            "maximo": {"anio": maximo[0], "valor": round(maximo[1], 2)},
            "minimo": {"anio": minimo[0], "valor": round(minimo[1], 2)},
            "volatilidad_desviacion_estandar": round(statistics.stdev(valores), 2)
        }
        if tipo == "nivel" and val_ini > 0:
            periodos = anio_fin - anio_ini
            tcac = ((val_fin / val_ini) ** (1 / periodos) - 1) * 100
            resumen["crecimiento_promedio_anual_compuesto_pct"] = round(tcac, 2)
            resumen["variacion_total_pct"] = round((val_fin / val_ini - 1) * 100, 2)
            nota = (
                "Si el indicador esta en USD corrientes, su crecimiento incluye "
                "inflacion y tipo de cambio; no equivale a crecimiento real."
            )
        else:
            resumen["cambio_en_puntos_porcentuales"] = round(val_fin - val_ini, 2)
            nota = "Indicador en porcentaje: se compara en puntos porcentuales."
        return {
            "pais": nombre,
            "codigo": codigo,
            "indicador": nombre_ind,
            "periodo": f"{anio_ini}-{anio_fin}",
            "serie": {str(a): round(v, 2) for a, v in serie},
            "resumen": resumen,
            "nota": nota,
            "fuente": "Banco Mundial - World Development Indicators"
        }

    # 9) Comparar varios paises en un mismo indicador (Banco Mundial)
    def comparar_paises(self, paises: str, indicador: str = "pib_per_capita"):
        print(
            f"Herramienta comparar_paises llamada con "
            f"paises: {paises}, indicador: {indicador}"
        )
        if not paises or not paises.strip():
            return "Error: se requieren los nombres de los países separados por coma."
        lista = [p.strip() for p in paises.split(",") if p.strip()]
        if len(lista) < 2:
            return "Error: se necesitan al menos dos países para comparar."
        if len(lista) > 8:
            return "Error: se pueden comparar como máximo 8 países a la vez."
        catalogo = self._catalogo_indicadores()
        indicador = indicador.lower()
        if indicador not in catalogo:
            return f"Error: usa uno de estos indicadores: {', '.join(catalogo.keys())}"
        codigo_ind, nombre_ind, _ = catalogo[indicador]
        resultados = []
        sin_datos = []
        for p in lista:
            codigo, nombre = self._buscar_codigo_pais(p)
            if not codigo:
                sin_datos.append(f"{p} (país no encontrado)")
                continue
            serie = self._serie_wb(codigo, codigo_ind, {"mrnev": 1, "per_page": 1})
            if serie:
                anio, valor = serie[-1]
                resultados.append({"pais": nombre, "valor": round(valor, 2), "anio": anio})
            else:
                sin_datos.append(f"{nombre} (sin datos)")
        if not resultados:
            return f"No se encontraron datos de {nombre_ind} para esos países."
        ranking = sorted(resultados, key=lambda x: x["valor"], reverse=True)
        for posicion, fila in enumerate(ranking, start=1):
            fila["posicion"] = posicion
        anios_distintos = len({fila["anio"] for fila in ranking}) > 1
        return {
            "indicador": nombre_ind,
            "ranking_de_mayor_a_menor": ranking,
            "promedio_del_grupo": round(statistics.mean([f["valor"] for f in ranking]), 2),
            "sin_datos": sin_datos,
            "advertencia": (
                "Los datos no son del mismo año; compare con cautela."
                if anios_distintos else "Todos los datos son del mismo año."
            ),
            "fuente": "Banco Mundial - World Development Indicators"
        }

    # 10) Indicadores sociales de un pais (Banco Mundial)
    def indicadores_sociales(self, pais: str):
        print(f"Herramienta indicadores_sociales llamada con pais: {pais}")
        if not pais or not pais.strip():
            return "Error: se requiere el nombre del país."
        codigo, nombre = self._buscar_codigo_pais(pais)
        if not codigo:
            return f"No se encontró el país {pais}"
        indicadores = {
            "Poblacion total": "SP.POP.TOTL",
            "Poblacion urbana (%)": "SP.URB.TOTL.IN.ZS",
            "Esperanza de vida (anios)": "SP.DYN.LE00.IN",
            "Indice de Gini (0 = igualdad, 100 = desigualdad)": "SI.POV.GINI",
            "Pobreza extrema, linea internacional (% poblacion)": "SI.POV.DDAY",
            "Pobreza, linea nacional (% poblacion)": "SI.POV.NAHC",
            "Remesas recibidas (% del PIB)": "BX.TRF.PWKR.DT.GD.ZS",
            "Alfabetizacion adultos (%)": "SE.ADT.LITR.ZS"
        }
        resultado = {"pais": nombre, "codigo": codigo, "indicadores": {}}
        for nombre_ind, codigo_ind in indicadores.items():
            serie = self._serie_wb(codigo, codigo_ind, {"mrnev": 1, "per_page": 1})
            if serie is None:
                resultado["indicadores"][nombre_ind] = "Error al consultar"
            elif serie:
                anio, valor = serie[-1]
                resultado["indicadores"][nombre_ind] = {
                    "valor": round(valor, 2),
                    "anio": anio
                }
            else:
                resultado["indicadores"][nombre_ind] = "Sin datos disponibles"
        resultado["nota"] = (
            "Los indicadores sociales se miden con menos frecuencia; "
            "revise el año de cada dato."
        )
        resultado["fuente"] = "Banco Mundial - World Development Indicators"
        return resultado

    # 11) Tasa de interes real con la ecuacion de Fisher (calculo)
    def tasa_real(self, tasa_nominal: float, inflacion: float):
        print(
            f"Herramienta tasa_real llamada con "
            f"tasa_nominal: {tasa_nominal}, inflacion: {inflacion}"
        )
        if inflacion <= -100:
            return "Error: la inflación debe ser mayor que -100%."
        i = tasa_nominal / 100
        pi = inflacion / 100
        real_exacta = ((1 + i) / (1 + pi) - 1) * 100
        real_aproximada = tasa_nominal - inflacion
        if real_exacta > 0:
            interpretacion = (
                "Rendimiento real positivo: el dinero gana poder de compra."
            )
        elif real_exacta < 0:
            interpretacion = (
                "Rendimiento real negativo: aunque el saldo crece en números, "
                "el dinero pierde poder de compra."
            )
        else:
            interpretacion = "El rendimiento solo compensa la inflación."
        return {
            "tasa_nominal_pct": tasa_nominal,
            "inflacion_pct": inflacion,
            "tasa_real_exacta_pct": round(real_exacta, 2),
            "tasa_real_aproximada_pct": round(real_aproximada, 2),
            "formula": "Ecuacion de Fisher: (1 + nominal) / (1 + inflacion) - 1",
            "interpretacion": interpretacion
        }

    # 12) Poder adquisitivo: cuanto vale hoy un monto del pasado (Banco Mundial)
    def poder_adquisitivo(self, monto: float, anio_inicial: int, pais: str = "Guatemala"):
        print(
            f"Herramienta poder_adquisitivo llamada con "
            f"monto: {monto}, anio_inicial: {anio_inicial}, pais: {pais}"
        )
        anio_inicial = int(anio_inicial)
        anio_actual = datetime.now().year
        if monto <= 0:
            return "Error: el monto debe ser mayor que cero."
        if anio_inicial < 1960 or anio_inicial >= anio_actual:
            return f"Error: el año inicial debe estar entre 1960 y {anio_actual - 1}."
        codigo, nombre = self._buscar_codigo_pais(pais)
        if not codigo:
            return f"No se encontró el país {pais}"
        serie = self._serie_wb(
            codigo,
            "FP.CPI.TOTL",
            {"date": f"{anio_inicial}:{anio_actual}", "per_page": 100}
        )
        if serie is None:
            return "ERROR: No se pudo consultar el índice de precios."
        if not serie or serie[0][0] != anio_inicial:
            return f"No hay índice de precios de {anio_inicial} para {nombre}"
        anio_ini, ipc_ini = serie[0]
        anio_fin, ipc_fin = serie[-1]
        if anio_fin == anio_ini:
            return f"No hay datos de precios posteriores a {anio_inicial} para {nombre}"
        equivalente = monto * ipc_fin / ipc_ini
        inflacion_acumulada = (ipc_fin / ipc_ini - 1) * 100
        perdida = (1 - ipc_ini / ipc_fin) * 100
        return {
            "pais": nombre,
            "monto_original": monto,
            "anio_inicial": anio_ini,
            "anio_final": anio_fin,
            "monto_equivalente": round(equivalente, 2),
            "inflacion_acumulada_pct": round(inflacion_acumulada, 2),
            "perdida_poder_adquisitivo_pct": round(perdida, 2),
            "interpretacion": (
                f"Lo que costaba {monto} en {anio_ini} cuesta aproximadamente "
                f"{equivalente:.2f} en {anio_fin}, en moneda local de {nombre}."
            ),
            "fuente": "Banco Mundial - Indice de precios al consumidor (FP.CPI.TOTL)"
        }

    # 13) Graficar la evolucion de un indicador para uno o varios paises
    def graficar(self, paises: str, indicador: str = "crecimiento", anios: int = 10):
        print(
            f"Herramienta graficar llamada con "
            f"paises: {paises}, indicador: {indicador}, anios: {anios}"
        )

        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            return "ERROR: falta instalar matplotlib. En la terminal: pip install matplotlib"

        if not paises or not paises.strip():
            return "Error: se requiere al menos un país."

        lista = [p.strip() for p in paises.split(",") if p.strip()]

        if len(lista) > 8:
            return "Error: se pueden graficar como máximo 8 países a la vez."

        catalogo = self._catalogo_indicadores()
        indicador = indicador.lower()

        if indicador not in catalogo:
            return f"Error: usa uno de estos indicadores: {', '.join(catalogo.keys())}"

        anios = int(anios)

        if anios < 2 or anios > 50:
            return "Error: el número de años debe estar entre 2 y 50."

        codigo_ind, nombre_ind, _ = catalogo[indicador]

        # Colores fijos por orden, pensados para distinguirse con daltonismo
        colores = [
            "#2a78d6", "#eb6834", "#1baf7a", "#eda100",
            "#e87ba4", "#008300", "#4a3aa7", "#e34948"
        ]

        series = []
        sin_datos = []

        for p in lista:
            codigo, nombre = self._buscar_codigo_pais(p)

            if not codigo:
                sin_datos.append(f"{p} (país no encontrado)")
                continue

            serie = self._serie_wb(codigo, codigo_ind, {"mrv": anios, "per_page": 100})

            if serie:
                series.append((nombre, codigo, serie))
            else:
                sin_datos.append(f"{nombre} (sin datos)")

        if not series:
            return f"No se encontraron datos de {nombre_ind} para graficar."

        # Formato de numeros: grandes en millones o miles de millones
        todos = [v for _, _, s in series for _, v in s]
        mayor = max(abs(v) for v in todos)

        def formato(v):
            if mayor >= 1e9:
                return f"{v / 1e9:,.1f} mil M"
            if mayor >= 1e6:
                return f"{v / 1e6:,.1f} M"
            return f"{v:,.1f}"

        fig, ax = plt.subplots(figsize=(10, 5.5), dpi=120)
        fig.patch.set_facecolor("#fcfcfb")
        ax.set_facecolor("#fcfcfb")

        for i, (nombre, codigo, serie) in enumerate(series):
            x = [a for a, _ in serie]
            y = [v for _, v in serie]
            color = colores[i]
            ax.plot(x, y, color=color, linewidth=2, marker="o", markersize=4, label=nombre)
            # Etiqueta directa al final de cada linea (solo si son 4 o menos)
            if len(series) <= 4:
                ax.annotate(
                    f"{nombre} {formato(y[-1])}",
                    xy=(x[-1], y[-1]),
                    xytext=(6, 0),
                    textcoords="offset points",
                    va="center",
                    fontsize=9,
                    color="#0b0b0b"
                )

        # Linea de cero si el indicador cruza a negativo
        if min(todos) < 0 < max(todos):
            ax.axhline(0, color="#52514e", linewidth=1)

        titulo = nombre_ind if len(series) >= 2 else f"{series[0][0]}: {nombre_ind}"
        ax.set_title(titulo, fontsize=13, color="#0b0b0b", loc="left", pad=12)
        fig.text(
            0.01, 0.01, "Fuente: Banco Mundial - World Development Indicators",
            fontsize=8, color="#52514e"
        )
        ax.grid(axis="y", color="#e4e3df", linewidth=0.8)
        ax.set_axisbelow(True)
        for lado in ("top", "right", "left"):
            ax.spines[lado].set_visible(False)
        ax.spines["bottom"].set_color("#b5b4ae")
        ax.tick_params(colors="#52514e", labelsize=9, length=0)
        ax.xaxis.get_major_locator().set_params(integer=True)
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda v, _: formato(v))
        )
        if len(series) >= 2:
            ax.legend(
                frameon=False, fontsize=9, loc="upper center",
                bbox_to_anchor=(0.5, -0.08), ncol=min(len(series), 4)
            )
        ax.margins(x=0.15 if len(series) <= 4 else 0.03)
        fig.tight_layout(rect=(0, 0.03, 1, 1))

        carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graficas")
        os.makedirs(carpeta, exist_ok=True)
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        codigos = "_".join(c for _, c, _ in series)
        ruta = os.path.join(carpeta, f"{indicador}_{codigos}_{marca}.png")
        fig.savefig(ruta, facecolor=fig.get_facecolor())
        plt.close(fig)


        # Guardar los datos en JSON para la grafica interactiva (Plotly)
        datos_json = {
            "titulo": titulo,
            "indicador": nombre_ind,
            "fuente": "Banco Mundial - World Development Indicators",
            "series": {
                nombre: {
                    "anios": [a for a, _ in serie],
                    "valores": [v for _, v in serie]
                }
                for nombre, _, serie in series
            }
        }
        ruta_json = os.path.splitext(ruta)[0] + ".json"
        with open(ruta_json, "w", encoding="utf-8") as archivo:
            json.dump(datos_json, archivo, ensure_ascii=False)

        # Abrir la imagen 
        try:
            if getattr(self, "abrir_grafica", True) and os.name == "nt":
                os.startfile(ruta)
        except Exception:
            pass

        return {
            "grafica_guardada_en": ruta,
            "indicador": nombre_ind,
            "datos_graficados": {
                nombre: {str(a): round(v, 2) for a, v in serie}
                for nombre, _, serie in series
            },
            "sin_datos": sin_datos,
            "fuente": "Banco Mundial - World Development Indicators"
        }
