#######################
# Agente Económico    #
# Herramientas        #
#######################

import requests
from urllib.parse import quote


class BasicTools:

    def consultar_tipo_cambio(self, moneda: str = ""):
        print(f"Herramienta consultar_tipo_cambio llamada con {moneda}")

        if not moneda:
            return "Error: se requiere el código de la moneda."

        if moneda.upper() == "USD":
            return "El tipo de cambio es 7.80 quetzales por dólar"

        return f"No tengo información para la moneda {moneda}"

    def consultar_tipo_cambio_api(self, moneda: str = ""):
        return self.consultar_tipo_cambio(moneda)

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

    def diversificar_inversion(
        self,
        monto: float,
        perfil: str = "moderado"
    ):
        print(
            f"Herramienta diversificar_inversion llamada con "
            f"monto: {monto}, perfil: {perfil}"
        )

        perfil = perfil.lower()

        repartos = {
            "conservador": {
                "renta_fija": 0.70,
                "acciones": 0.20,
                "efectivo": 0.10
            },
            "moderado": {
                "renta_fija": 0.50,
                "acciones": 0.40,
                "efectivo": 0.10
            },
            "agresivo": {
                "renta_fija": 0.30,
                "acciones": 0.60,
                "efectivo": 0.10
            }
        }

        if perfil not in repartos:
            return (
                "Error: el perfil debe ser conservador, "
                "moderado o agresivo."
            )

        reparto = repartos[perfil]

        return {
            "perfil": perfil,
            "monto_total": monto,
            "renta_fija": round(
                monto * reparto["renta_fija"], 2
            ),
            "acciones": round(
                monto * reparto["acciones"], 2
            ),
            "efectivo": round(
                monto * reparto["efectivo"], 2
            )
        }

    def interes_compuesto(
        self,
        capital: float,
        tasa_anual: float,
        anios: int
    ):
        print(
            f"Herramienta interes_compuesto llamada con "
            f"capital: {capital}, tasa_anual: {tasa_anual}, "
            f"anios: {anios}"
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

    def datos_pais(self, pais: str):
        print(f"Herramienta datos_pais llamada con pais: {pais}")

        if not pais or not pais.strip():
            return "Error: se requiere el nombre del país."

        pais = pais.strip()
        url = f"https://restcountries.com/v3.1/name/{quote(pais)}"
        params = {
            "fields": "name,region,population,currencies,cca2"
        }

        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code != 200:
                return f"No se encontró información para el país {pais}"

            datos = response.json()

            if not isinstance(datos, list) or len(datos) == 0:
                return f"No se encontró información para el país {pais}"

            info = datos[0]

            nombre = info.get("name", {}).get("common", pais)
            region = info.get("region", "Desconocida")
            poblacion = info.get("population", 0)
            codigo = info.get("cca2", "")
            monedas = info.get("currencies", {})
            moneda = ", ".join(monedas.keys()) if monedas else "Desconocida"

            return {
                "pais": nombre,
                "codigo": codigo,
                "region": region,
                "poblacion": poblacion,
                "moneda": moneda
            }

        except Exception as error:
            print(f"Error al procesar datos_pais: {error}")
            return f"ERROR: No se pudo obtener información del país {pais}"

    def indicadores_economicos(self, pais: str):
        print(
            f"Herramienta indicadores_economicos llamada con pais: {pais}"
        )

        if not pais or not pais.strip():
            return "Error: se requiere el nombre del país."

        pais = pais.strip()

        url_pais = (
            f"https://restcountries.com/v3.1/name/{quote(pais)}"
        )
        params_pais = {"fields": "name,cca2"}

        try:
            resp_pais = requests.get(
                url_pais,
                params=params_pais,
                timeout=30
            )

            if resp_pais.status_code != 200:
                return f"No se encontró el país {pais}"

            datos_pais = resp_pais.json()

            if not isinstance(datos_pais, list) or len(datos_pais) == 0:
                return f"No se encontró el país {pais}"

            codigo = datos_pais[0].get("cca2", "")
            nombre = datos_pais[0].get(
                "name",
                {}
            ).get("common", pais)

            if not codigo:
                return (
                    f"No se pudo determinar el código del país {pais}"
                )

        except Exception as error:
            print(f"Error al obtener codigo de pais: {error}")
            return f"ERROR: No se pudo obtener el país {pais}"

        indicadores = {
            "PIB (USD actuales)": "NY.GDP.MKTP.CD",
            "PIB per capita (USD)": "NY.GDP.PCAP.CD",
            "Crecimiento del PIB (%)": "NY.GDP.MKTP.KD.ZG",
            "Inflacion (%)": "FP.CPI.TOTL.ZG",
            "Desempleo (%)": "SL.UEM.TOTL.ZS",
            "Deuda publica (% del PIB)": "GC.DOD.TOTL.GD.ZS",
            "Exportaciones (% del PIB)": "NE.EXP.GNFS.ZS"
        }

        resultado = {
            "pais": nombre,
            "codigo": codigo,
            "indicadores": {}
        }

        for nombre_ind, codigo_ind in indicadores.items():
            url_wb = (
                f"https://api.worldbank.org/v2/country/{codigo}/"
                f"indicator/{codigo_ind}"
            )
            params_wb = {
                "format": "json",
                "per_page": 1,
                "mrnev": 1
            }

            try:
                resp = requests.get(
                    url_wb,
                    params=params_wb,
                    timeout=30
                )
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
                    resultado["indicadores"][nombre_ind] = (
                        "Sin datos disponibles"
                    )

            except Exception as error:
                print(f"Error al obtener {nombre_ind}: {error}")
                resultado["indicadores"][nombre_ind] = (
                    "Error al consultar"
                )

        return resultado