import json
import plotly.graph_objects as go

# Colores de las lineas (uno por pais, en orden fijo)
COLORES = {
    "claro": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
              "#e87ba4", "#008300", "#6250d6", "#e34948"],
    "oscuro": ["#3987e5", "#d95926", "#199e70", "#c98500",
               "#d55181", "#008300", "#9085e9", "#e66767"],
}

# Colores del fondo, textos y rejilla segun la paleta Luna
TEMA = {
    "claro": {"fondo": "#FFFFFF", "texto": "#142F40", "suave": "#376C89",
              "rejilla": "#E3ECF0", "eje": "#A6C9D8"},
    "oscuro": {"fondo": "#0C1E29", "texto": "#F7F8F9", "suave": "#A6C9D8",
               "rejilla": "#20475D", "eje": "#376C89"},
}


def figura_desde_json(ruta_json, modo="claro"):
    """Lee el archivo JSON de una grafica y la dibuja."""
    with open(ruta_json, encoding="utf-8") as archivo:
        return figura_desde_datos(json.load(archivo), modo)


def figura_desde_datos(datos, modo="claro"):
    """Dibuja la grafica a partir de los datos (del JSON o de Supabase)."""
    colores = COLORES[modo]
    tema = TEMA[modo]
    series = datos["series"]

    # Escala: numeros grandes en millones o miles de millones
    todos = [v for s in series.values() for v in s["valores"]]
    mayor = max(abs(v) for v in todos)
    if mayor >= 1e9:
        divisor, sufijo = 1e9, " mil M"
    elif mayor >= 1e6:
        divisor, sufijo = 1e6, " M"
    else:
        divisor, sufijo = 1, ""

    fig = go.Figure()

    for i, (pais, s) in enumerate(series.items()):
        x = [int(a) for a in s["anios"]]
        y = [v / divisor for v in s["valores"]]
        color = colores[i]

        fig.add_trace(go.Scatter(
            x=x, y=y, name=pais, mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=8, color=color,
                        line=dict(color=tema["fondo"], width=2)),
            hovertemplate=f"{pais}: %{{y:,.1f}}{sufijo}<extra></extra>",
        ))

        # Etiqueta al final de cada linea (solo si son 4 paises o menos)
        if len(series) <= 4:
            fig.add_annotation(
                x=x[-1], y=y[-1], text=f"{pais} {y[-1]:,.1f}{sufijo}",
                showarrow=False, xanchor="left", xshift=10,
                font=dict(color=tema["texto"], size=12),
            )

    # Linea de cero si hay valores negativos y positivos
    if min(todos) < 0 < max(todos):
        fig.add_hline(y=0, line=dict(color=tema["suave"], width=1))

    fig.add_annotation(
        text=f"Fuente: {datos['fuente']}", xref="paper", yref="paper",
        x=0, y=-0.3, xanchor="left", showarrow=False,
        font=dict(size=10, color=tema["suave"]),
    )

    fig.update_layout(
        title=dict(text=datos["titulo"], x=0, xanchor="left",
                   font=dict(family="Vidaloka, serif", size=20,
                             color=tema["texto"])),
        font=dict(family="Montserrat, sans-serif", size=12,
                  color=tema["suave"]),
        paper_bgcolor=tema["fondo"],
        plot_bgcolor=tema["fondo"],
        hovermode="x unified",
        hoverlabel=dict(bgcolor=tema["fondo"],
                        font=dict(color=tema["texto"])),
        showlegend=len(series) >= 2,
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.15,
                    font=dict(color=tema["texto"])),
        margin=dict(l=10, r=150 if len(series) <= 4 else 20, t=60, b=90),
        height=460,
    )
    todos_anios = [int(a) for s in series.values() for a in s["anios"]]
    fig.update_xaxes(showgrid=False, linecolor=tema["eje"], tickformat="d",
                     range=[min(todos_anios) - 0.5, max(todos_anios) + 0.5])
    fig.update_yaxes(gridcolor=tema["rejilla"], zeroline=False,
                     tickformat=",.1~f", ticksuffix=sufijo)

    return fig


def mini_grafica(serie, promedio, modo="claro"):
    tema = TEMA[modo]
    color = "#376C89" if modo == "claro" else "#A6C9D8"
    x = [a for a, _ in serie]
    y = [v for _, v in serie]

    fig = go.Figure(go.Scatter(
        x=x, y=y, mode="lines+markers",
        line=dict(color=color, width=2),
        marker=dict(size=5, color=color),
        hovertemplate="%{x}: %{y:,.1f}<extra></extra>",
    ))
    if promedio is not None:
        fig.add_hline(y=promedio, line=dict(color=tema["suave"], width=1, dash="dot"))

    fig.update_layout(
        height=90, margin=dict(l=0, r=0, t=4, b=0), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor=tema["fondo"], font=dict(color=tema["texto"])),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig