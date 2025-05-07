# src/dashboard/components/details/graphs/market_graphs.py

from dash import dcc
from plotly.subplots import make_subplots
import plotly.graph_objects as go

def regulation_graph():
    """
    DCC-Graph-Component für die tertiäre Regelleistung / Spotpreise.
    """
    return dcc.Graph(
       id="regulation-graph",
       config={
           # Fügt in der Modebar den Autoscale-Button hinzu
           "modeBarButtonsToAdd": ["resetScale2d"],
           "displaylogo": False
       }
   )


def make_regulation_figure(
    df_reg,        # tertiäre Regelleistung
    df_spot,       # Spot-Preise
    xaxis_range,   # geteilte Zeitachse
    start, end
):
    """
    Kombiniert Abruf-Volumen (Bar) und Preise (Linien) auf zwei Y-Achsen.
    """
    dfrr = df_reg.reset_index()
    dfsp = df_spot.reset_index()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1) Volumen als Balken (primäre Y)
    fig.add_trace(
        go.Bar(
            x=dfrr["timestamp"],
            y=dfrr["total_called_mw"],
            name="Abruf (MW)",
            marker_color="#d35400",   # dunkleres Orange für Volumen
            opacity=0.6
        ),
        secondary_y=False
    )

    # 2) Regelpreis als Linie (sekundäre Y)
    fig.add_trace(
        go.Scatter(
            x=dfrr["timestamp"],
            y=dfrr["avg_price_eur_mwh"],
            name="Regelpreis (EUR/MWh)",
            mode="lines",
            line=dict(color="#ff7f0e", width=2)  # Orange
        ),
        secondary_y=True
    )

    # 3) Spotpreis als gepunktete Linie (sekundäre Y)
    fig.add_trace(
        go.Scatter(
            x=dfsp["timestamp"],
            y=dfsp["price_eur_mwh"],
            name="Spot-Preis (EUR/MWh)",
            mode="lines",
            line=dict(color="#1f77b4", dash="dot", width=2)  # Blau
        ),
        secondary_y=True
    )

    # Achsenbeschriftungen & -bereich
    fig.update_xaxes(title_text="Zeit", range=xaxis_range)
    fig.update_yaxes(title_text="Abruf (MW)", secondary_y=False)
    fig.update_yaxes(title_text="Preis (EUR/MWh)", secondary_y=True)

    #automatische Neuskalierung bei Ein/Ausblenden
    fig.update_layout(
        title_text="Marktübersicht",
        transition_duration=300,
        legend=dict(
            itemclick="toggle",    # beim Klick die Achsen neu autorangen
            itemdoubleclick="toggleothers"
        ),
        yaxis=dict(autorange=True),
        yaxis2=dict(autorange=True)
    )
    return fig