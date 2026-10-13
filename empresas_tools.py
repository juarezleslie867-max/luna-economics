#######################################
# Luna Economics                      #
# Herramientas de analisis de empresas #
#######################################
# Fuentes sin clave:
#   - Yahoo Finance (via yfinance): precios, rendimiento, riesgo, valuacion.
#   - SEC EDGAR (gobierno de EE. UU.): estados financieros oficiales (10-K).

import json
import math
import os
import re
from datetime import datetime

import requests

SEC_HEADERS = {
    "User-Agent": os.environ.get(
        "SEC_USER_AGENT", "LunaEconomics/1.0 (proyecto academico; contacto@lunaeconomics.app)"
    )
}
FUENTE_YAHOO = "Yahoo Finance (vía yfinance)"
FUENTE_SEC = "SEC EDGAR · Estados financieros oficiales (10-K)"
INDICE_REFERENCIA = ("^GSPC", "S&P 500")


def _num(valor, decimales=2):
    """Redondea y convierte NaN/None en None."""
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return None
    if math.isnan(valor) or math.isinf(valor):
        return None
    return round(valor, decimales)


def _pct(valor):
    """Fraccion (0.25) -> porcentaje (25.0)."""
    v = _num(valor, 6)
    return None if v is None else round(v * 100, 2)


class EmpresasTools:
    _tickers_sec = None  # cache compartido de la lista de empresas de la SEC

    # ---------------------------------------------------------
    # Ayudantes
    # ---------------------------------------------------------
    def _resolver_ticker(self, empresa):
        """Acepta un ticker (AAPL) o un nombre (Apple) y devuelve el ticker."""
        import yfinance as yf

        texto = (empresa or "").strip()
        if not texto:
            return None
        if " " not in texto and texto.upper() == texto and len(texto) <= 10:
            return texto
        try:
            resultados = yf.Search(texto, max_results=8).quotes
            for r in resultados:
                if r.get("quoteType") == "EQUITY":
                    return r["symbol"]
            if resultados:
                return resultados[0]["symbol"]
        except Exception as error:
            print(f"No se pudo buscar el ticker de {texto}: {error}")
        return texto.upper()

    def _historia(self, ticker, anios):
        import yfinance as yf

        inicio = f"{datetime.now().year - int(anios)}-01-01"
        hist = yf.Ticker(ticker).history(start=inicio, auto_adjust=True)
        if hist is None or hist.empty:
            return None
        cierre = hist["Close"].dropna()
        return cierre if len(cierre) >= 30 else None

    def _metricas(self, cierre):
        """Rendimiento y riesgo a partir de los precios de cierre diarios."""
        rend_total = cierre.iloc[-1] / cierre.iloc[0] - 1
        anios = (cierre.index[-1] - cierre.index[0]).days / 365.25
        cagr = (1 + rend_total) ** (1 / anios) - 1 if anios > 0 else None
        diarios = cierre.pct_change().dropna()
        volatilidad = diarios.std() * math.sqrt(252)
        caida_maxima = (cierre / cierre.cummax() - 1).min()
        rend_1a = cierre.iloc[-1] / cierre.iloc[-253] - 1 if len(cierre) > 253 else None

        por_anio = cierre.groupby(cierre.index.year).last()
        anuales = {}
        anterior = cierre.iloc[0]
        for anio, valor in por_anio.items():
            anuales[str(anio)] = _pct(valor / anterior - 1)
            anterior = valor

        return {
            "rendimiento_total_pct": _pct(rend_total),
            "rendimiento_anual_promedio_pct": _pct(cagr),
            "rendimiento_ultimo_anio_pct": _pct(rend_1a),
            "volatilidad_anual_pct": _pct(volatilidad),
            "caida_maxima_pct": _pct(caida_maxima),
            "rendimiento_por_riesgo": _num(cagr / volatilidad if cagr is not None and volatilidad else None),
            "rendimiento_por_anio_calendario_pct": anuales,
        }

    def _serie_base_100(self, cierre):
        """Valor de 100 invertidos al cierre del año previo al inicio, y al cierre de cada año."""
        base = cierre.iloc[0]
        por_anio = cierre.groupby(cierre.index.year).last()
        anios = [int(cierre.index[0].year) - 1] + [int(a) for a in por_anio.index]
        valores = [100.0] + [round(float(v / base * 100), 2) for v in por_anio.values]
        return anios, valores

    def _guardar_grafica(self, series, titulo, nombre_archivo):
        """Guarda PNG (para el informe) y JSON (para Plotly en el chat)."""
        carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graficas")
        os.makedirs(carpeta, exist_ok=True)
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = os.path.join(carpeta, f"{nombre_archivo}_{marca}")

        datos_json = {
            "titulo": titulo,
            "indicador": "Valor de 100 invertidos",
            "fuente": FUENTE_YAHOO,
            "series": {n: {"anios": a, "valores": v} for n, (a, v) in series.items()},
        }
        with open(base + ".json", "w", encoding="utf-8") as archivo:
            json.dump(datos_json, archivo, ensure_ascii=False)

        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            colores = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
                       "#e87ba4", "#008300", "#6250d6", "#e34948"]
            fig, ax = plt.subplots(figsize=(10, 5.5), dpi=120)
            fig.patch.set_facecolor("#fcfcfb")
            ax.set_facecolor("#fcfcfb")
            for i, (nombre, (a, v)) in enumerate(series.items()):
                estilo = "--" if nombre == INDICE_REFERENCIA[1] else "-"
                ax.plot(a, v, estilo, color=colores[i % 8], linewidth=2, marker="o",
                        markersize=4, label=nombre)
                ax.annotate(f"{nombre} {v[-1]:,.0f}", xy=(a[-1], v[-1]), xytext=(6, 0),
                            textcoords="offset points", va="center", fontsize=9)
            ax.axhline(100, color="#52514e", linewidth=1)
            ax.set_title(titulo, fontsize=13, loc="left", pad=12)
            fig.text(0.01, 0.01, f"Fuente: {FUENTE_YAHOO}", fontsize=8, color="#52514e")
            ax.grid(axis="y", color="#e4e3df", linewidth=0.8)
            for lado in ("top", "right", "left"):
                ax.spines[lado].set_visible(False)
            ax.xaxis.get_major_locator().set_params(integer=True)
            ax.legend(frameon=False, fontsize=9, loc="upper center",
                      bbox_to_anchor=(0.5, -0.08), ncol=min(len(series), 4))
            ax.margins(x=0.15)
            fig.tight_layout(rect=(0, 0.03, 1, 1))
            fig.savefig(base + ".png", facecolor=fig.get_facecolor())
            plt.close(fig)
        except Exception as error:
            print(f"No se pudo dibujar la gráfica PNG: {error}")

        return base + ".png"

    # ---------------------------------------------------------
    # Herramienta 1: analisis de una empresa
    # ---------------------------------------------------------
    def analizar_empresa(self, empresa: str, anios: int = 5):
        print(f"Herramienta analizar_empresa llamada con empresa: {empresa}, anios: {anios}")
        try:
            import yfinance as yf
        except ImportError:
            return {"error": "Falta instalar yfinance. En la terminal: pip install yfinance"}

        anios = max(1, min(int(anios or 5), 20))
        ticker = self._resolver_ticker(empresa)
        if not ticker:
            return {"error": "Indica el nombre o el ticker de la empresa."}

        try:
            cierre = self._historia(ticker, anios)
        except Exception as error:
            return {"error": f"Yahoo Finance no respondió para {ticker}: {error}"}
        if cierre is None:
            return {"error": f"No encontré precios para '{empresa}' (ticker probado: {ticker})."}

        try:
            info = yf.Ticker(ticker).info or {}
        except Exception:
            info = {}

        resultado = {
            "empresa": info.get("longName") or info.get("shortName") or ticker,
            "ticker": ticker,
            "sector": info.get("sector"),
            "industria": info.get("industry"),
            "pais": info.get("country"),
            "moneda": info.get("currency"),
            "fecha_ultimo_precio": cierre.index[-1].strftime("%Y-%m-%d"),
            "precio_actual": _num(cierre.iloc[-1]),
            "minimo_52_semanas": _num(info.get("fiftyTwoWeekLow")),
            "maximo_52_semanas": _num(info.get("fiftyTwoWeekHigh")),
            "capitalizacion_miles_de_millones": _num((info.get("marketCap") or 0) / 1e9) or None,
            "periodo_analizado_anios": anios,
            "rendimiento_y_riesgo": self._metricas(cierre),
            "valuacion": {
                "per_ultimos_12_meses": _num(info.get("trailingPE")),
                "per_estimado": _num(info.get("forwardPE")),
                "precio_valor_libro": _num(info.get("priceToBook")),
                "rendimiento_dividendo_pct": _pct(info.get("trailingAnnualDividendYield")),
                "beta": _num(info.get("beta")),
            },
            "salud_financiera": {
                "margen_neto_pct": _pct(info.get("profitMargins")),
                "rentabilidad_patrimonio_roe_pct": _pct(info.get("returnOnEquity")),
                "crecimiento_ingresos_pct": _pct(info.get("revenueGrowth")),
                "deuda_sobre_patrimonio_pct": _num(info.get("debtToEquity")),
            },
        }

        # Comparacion con el mercado (S&P 500) y grafica base 100
        series = {resultado["empresa"]: self._serie_base_100(cierre)}
        try:
            cierre_ref = self._historia(INDICE_REFERENCIA[0], anios)
            if cierre_ref is not None:
                ref = self._metricas(cierre_ref)
                resultado["referencia_mercado"] = {
                    "indice": INDICE_REFERENCIA[1],
                    "rendimiento_anual_promedio_pct": ref["rendimiento_anual_promedio_pct"],
                    "volatilidad_anual_pct": ref["volatilidad_anual_pct"],
                    "caida_maxima_pct": ref["caida_maxima_pct"],
                }
                series[INDICE_REFERENCIA[1]] = self._serie_base_100(cierre_ref)
        except Exception as error:
            print(f"No se pudo obtener el S&P 500: {error}")

        resultado["grafica_guardada_en"] = self._guardar_grafica(
            series, f"{resultado['empresa']}: valor de 100 invertidos",
            f"empresa_{re.sub(r'[^A-Za-z0-9]', '', ticker)}",
        )
        resultado["fuente"] = FUENTE_YAHOO
        resultado["advertencia"] = (
            "Datos de mercado de Yahoo Finance (fuente no oficial). Rendimientos pasados no "
            "garantizan rendimientos futuros. Verificar en fuentes oficiales antes de invertir."
        )
        return resultado

    # ---------------------------------------------------------
    # Herramienta 2: comparar empresas
    # ---------------------------------------------------------
    def comparar_empresas(self, empresas: str, anios: int = 5):
        print(f"Herramienta comparar_empresas llamada con empresas: {empresas}, anios: {anios}")
        try:
            import yfinance as yf
        except ImportError:
            return {"error": "Falta instalar yfinance. En la terminal: pip install yfinance"}

        lista = [e.strip() for e in (empresas or "").split(",") if e.strip()]
        if len(lista) < 2 or len(lista) > 6:
            return {"error": "Indica entre 2 y 6 empresas separadas por coma."}
        anios = max(1, min(int(anios or 5), 20))

        tabla, series, sin_datos = [], {}, []
        for e in lista:
            ticker = self._resolver_ticker(e)
            try:
                cierre = self._historia(ticker, anios)
            except Exception:
                cierre = None
            if cierre is None:
                sin_datos.append(f"{e} ({ticker})")
                continue
            try:
                info = yf.Ticker(ticker).info or {}
            except Exception:
                info = {}
            nombre = info.get("shortName") or ticker
            m = self._metricas(cierre)
            tabla.append({
                "empresa": nombre,
                "ticker": ticker,
                "sector": info.get("sector"),
                "rendimiento_anual_promedio_pct": m["rendimiento_anual_promedio_pct"],
                "volatilidad_anual_pct": m["volatilidad_anual_pct"],
                "caida_maxima_pct": m["caida_maxima_pct"],
                "rendimiento_por_riesgo": m["rendimiento_por_riesgo"],
                "per_ultimos_12_meses": _num(info.get("trailingPE")),
                "margen_neto_pct": _pct(info.get("profitMargins")),
                "rendimiento_dividendo_pct": _pct(info.get("trailingAnnualDividendYield")),
            })
            series[nombre] = self._serie_base_100(cierre)

        if not tabla:
            return {"error": "No se encontraron datos de ninguna de las empresas.", "sin_datos": sin_datos}

        try:
            cierre_ref = self._historia(INDICE_REFERENCIA[0], anios)
            if cierre_ref is not None:
                series[INDICE_REFERENCIA[1]] = self._serie_base_100(cierre_ref)
        except Exception:
            pass

        ranking = sorted(
            tabla, key=lambda f: (f["rendimiento_por_riesgo"] is None, -(f["rendimiento_por_riesgo"] or 0))
        )
        return {
            "periodo_analizado_anios": anios,
            "comparacion": ranking,
            "criterio_del_orden": "rendimiento_por_riesgo (rendimiento anual promedio / volatilidad)",
            "sin_datos": sin_datos,
            "grafica_guardada_en": self._guardar_grafica(
                series, "Valor de 100 invertidos", "comparacion_empresas"
            ),
            "fuente": FUENTE_YAHOO,
            "advertencia": "Rendimientos pasados no garantizan rendimientos futuros.",
        }

    # ---------------------------------------------------------
    # Herramienta 3: estados financieros oficiales (SEC)
    # ---------------------------------------------------------
    def _buscar_cik(self, ticker):
        if EmpresasTools._tickers_sec is None:
            r = requests.get("https://www.sec.gov/files/company_tickers.json",
                             headers=SEC_HEADERS, timeout=30)
            r.raise_for_status()
            EmpresasTools._tickers_sec = {
                v["ticker"].upper(): (int(v["cik_str"]), v["title"]) for v in r.json().values()
            }
        return EmpresasTools._tickers_sec.get(ticker.upper().replace(".", "-"))

    @staticmethod
    def _serie_sec(hechos, conceptos, instantaneo):
        """Valores anuales de un concepto contable; usa el concepto con datos mas recientes."""
        patron = re.compile(r"^CY\d{4}Q4I$" if instantaneo else r"^CY\d{4}$")
        mejor = {}
        for concepto in conceptos:
            unidades = hechos.get(concepto, {}).get("units", {}).get("USD", [])
            serie = {}
            for h in unidades:
                marco = h.get("frame", "")
                if patron.match(marco):
                    serie[int(marco[2:6])] = h["val"]
            if serie and (not mejor or max(serie) > max(mejor)):
                mejor = serie
        return mejor

    def estados_financieros(self, empresa: str):
        print(f"Herramienta estados_financieros llamada con empresa: {empresa}")
        ticker = self._resolver_ticker(empresa)
        try:
            encontrado = self._buscar_cik(ticker)
        except Exception as error:
            return {"error": f"No se pudo consultar la SEC: {error}"}
        if not encontrado:
            return {"error": f"'{empresa}' ({ticker}) no aparece en la SEC. Esta herramienta solo "
                             "cubre empresas que reportan en EE. UU."}
        cik, nombre = encontrado

        try:
            r = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json",
                             headers=SEC_HEADERS, timeout=40)
            r.raise_for_status()
            hechos = r.json().get("facts", {}).get("us-gaap", {})
        except Exception as error:
            return {"error": f"No se pudieron descargar los estados financieros de la SEC: {error}"}

        cuentas = {
            "ingresos": (["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                          "SalesRevenueNet"], False),
            "utilidad_neta": (["NetIncomeLoss"], False),
            "activos_totales": (["Assets"], True),
            "pasivos_totales": (["Liabilities"], True),
            "patrimonio": (["StockholdersEquity"], True),
            "efectivo": (["CashAndCashEquivalentsAtCarryingValue"], True),
        }
        series = {k: self._serie_sec(hechos, c, inst) for k, (c, inst) in cuentas.items()}
        anios = sorted({a for s in series.values() for a in s})[-5:]
        if not anios:
            return {"error": f"La SEC no tiene datos anuales estandarizados para {nombre}."}

        tabla = {}
        for a in anios:
            fila = {k: _num(s[a] / 1e6) if a in s else None for k, s in series.items()}
            ing, util = series["ingresos"].get(a), series["utilidad_neta"].get(a)
            act, pas, pat = (series["activos_totales"].get(a), series["pasivos_totales"].get(a),
                             series["patrimonio"].get(a))
            fila["margen_neto_pct"] = _pct(util / ing) if ing and util is not None else None
            fila["roe_pct"] = _pct(util / pat) if pat and util is not None else None
            fila["pasivos_sobre_activos_pct"] = _pct(pas / act) if act and pas is not None else None
            anterior = series["ingresos"].get(a - 1)
            fila["crecimiento_ingresos_pct"] = _pct(ing / anterior - 1) if ing and anterior else None
            tabla[str(a)] = fila

        return {
            "empresa": nombre,
            "ticker": ticker,
            "unidad": "millones de USD (ratios en %)",
            "estados_por_anio": tabla,
            "fuente": FUENTE_SEC,
            "nota": "Cifras anuales reportadas oficialmente por la empresa a la SEC (formulario 10-K).",
        }