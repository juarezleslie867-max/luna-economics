# Configuracion del Semaforo macroeconomico de Luna Economics
# Cada rango es (minimo, maximo, estado). None significa "sin limite".
# El minimo se incluye y el maximo no: (0, 3) significa 0 <= valor < 3

COLORES_ESTADO = {
    "Favorable": "#2D9B83",
    "Precaución": "#D6A345",
    "Crítico": "#C75C62",
    "Sin evaluación": "#376C89",
}

ANIOS_MAXIMOS_DE_ANTIGUEDAD = 3

INDICADORES = [
    {
        "clave": "crecimiento", "bloque": "Actividad",
        "nombre": "Crecimiento del PIB real", "unidad": "%",
        "fuente": "wb", "codigo": "NY.GDP.MKTP.KD.ZG",
        "rangos": [(3, None, "Favorable"), (0, 3, "Precaución"), (None, 0, "Crítico")],
        "nota": "Referencia: crecimiento tendencial de economías emergentes (~3-4 %).",
    },
    {
        "clave": "inversion", "bloque": "Actividad",
        "nombre": "Inversión (FBKF, % PIB)", "unidad": "% PIB",
        "fuente": "wb", "codigo": "NE.GDI.FTOT.ZS",
        "rangos": [(25, None, "Favorable"), (18, 25, "Precaución"), (None, 18, "Crítico")],
        "nota": "Referencia: ~25 % del PIB en economías de crecimiento alto y sostenido (Comisión sobre Crecimiento, 2008).",
    },
    {
        "clave": "desempleo", "bloque": "Actividad",
        "nombre": "Desempleo", "unidad": "%",
        "fuente": "wb", "codigo": "SL.UEM.TOTL.ZS",
        "rangos": [(None, 5, "Favorable"), (5, 8, "Precaución"), (8, None, "Crítico")],
        "nota": "Con alta informalidad, un desempleo bajo no implica un buen mercado laboral.",
    },
    {
        "clave": "inflacion", "bloque": "Precios",
        "nombre": "Inflación (IPC)", "unidad": "%",
        "fuente": "imf", "codigo": "PCPIPCH",
        "rangos": [(2, 5, "Favorable"), (0, 2, "Precaución"), (5, 10, "Precaución"),
                   (None, 0, "Crítico"), (10, None, "Crítico")],
        "nota": "Referencia: metas de inflación de bancos centrales de la región (Banguat: 4 % ± 1).",
    },
    {
        "clave": "cuenta_corriente", "bloque": "Sector externo",
        "nombre": "Cuenta corriente (% PIB)", "unidad": "% PIB",
        "fuente": "wb", "codigo": "BN.CAB.XOKA.GD.ZS",
        "rangos": [(-3, None, "Favorable"), (-5, -3, "Precaución"), (None, -5, "Crítico")],
        "nota": "Déficits mayores al 5 % del PIB se asocian con vulnerabilidad externa.",
    },
    {
        "clave": "reservas", "bloque": "Sector externo",
        "nombre": "Reservas internacionales", "unidad": "meses de importación",
        "fuente": "wb", "codigo": "FI.RES.TOTL.MO",
        "rangos": [(4, None, "Favorable"), (3, 4, "Precaución"), (None, 3, "Crítico")],
        "nota": "Regla clásica: al menos 3 meses de importaciones.",
    },
    {
        "clave": "deuda", "bloque": "Fiscal",
        "nombre": "Deuda pública (% PIB)", "unidad": "% PIB",
        "fuente": "imf", "codigo": "GGXWDG_NGDP",
        "rangos": [(None, 50, "Favorable"), (50, 70, "Precaución"), (70, None, "Crítico")],
        "nota": "Referencia del FMI para economías emergentes (~70 % del PIB).",
    },
    {
        "clave": "balance_fiscal", "bloque": "Fiscal",
        "nombre": "Balance fiscal (% PIB)", "unidad": "% PIB",
        "fuente": "imf", "codigo": "GGXCNL_NGDP",
        "rangos": [(-3, None, "Favorable"), (-5, -3, "Precaución"), (None, -5, "Crítico")],
        "nota": "Referencia tipo Maastricht: déficit no mayor al 3 % del PIB.",
    },
]

CONTEXTO = [
    {"clave": "pib_pc", "nombre": "PIB per cápita", "unidad": "USD",
     "fuente": "wb", "codigo": "NY.GDP.PCAP.CD"},
    {"clave": "remesas", "nombre": "Remesas (% PIB)", "unidad": "% PIB",
     "fuente": "wb", "codigo": "BX.TRF.PWKR.DT.GD.ZS"},
]


def evaluar(valor, rangos, anio=None, anio_actual=None):
    """Devuelve el estado del semaforo para un valor."""
    if valor is None:
        return "Sin evaluación"
    if anio is not None and anio_actual is not None:
        if anio_actual - int(anio) > ANIOS_MAXIMOS_DE_ANTIGUEDAD:
            return "Sin evaluación"
    for minimo, maximo, estado in rangos:
        if (minimo is None or valor >= minimo) and (maximo is None or valor < maximo):
            return estado
    return "Sin evaluación"


if __name__ == "__main__":
    reglas = {i["clave"]: i["rangos"] for i in INDICADORES}
    print("Inflacion 4.0  ->", evaluar(4.0, reglas["inflacion"]))
    print("Inflacion 12.0 ->", evaluar(12.0, reglas["inflacion"]))
    print("Inflacion -1.0 ->", evaluar(-1.0, reglas["inflacion"]))
    print("Deuda 60       ->", evaluar(60, reglas["deuda"]))
    print("Inversion 15   ->", evaluar(15, reglas["inversion"]))
    print("Dato de 2019   ->", evaluar(3.5, reglas["crecimiento"], 2019, 2026))
    print("Sin dato       ->", evaluar(None, reglas["crecimiento"]))