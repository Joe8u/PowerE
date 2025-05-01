#!/usr/bin/env python3
# src/dashboard/pages/summary.py

import pandas as pd
from dash import register_page, html, dcc, callback, Input, Output
import plotly.express as px

# Seite registrieren
register_page("summary", path="/", title="Executive Summary")

# Dummy-Daten
DF_DUMMY = pd.DataFrame({
    "Kategorie": ["Spot Einsparung", "Kompensation"],
    "Wert": [1000, 300]
})

# Modul-level Layout
layout = html.Div([
    html.H2("Executive Summary"),
    # Intervall, um die beiden Callbacks einmal zu triggern
    dcc.Interval(id="summary-interval", interval=1, n_intervals=0, max_intervals=1),

    html.Div([
        html.H4("Netto-Mehrwert (CHF)"),
        html.Div(id="summary-net-value")
    ], className="card", style={"marginBottom": "20px"}),

    dcc.Graph(id="summary-kpi-graph")
])

# Callback 1: Netto-Wert ausrechnen
@callback(
    Output("summary-net-value", "children"),
    Input("summary-interval", "n_intervals")
)
def update_net_value(_):
    total = (
        DF_DUMMY.loc[DF_DUMMY["Kategorie"] == "Spot Einsparung", "Wert"].sum()
        - DF_DUMMY.loc[DF_DUMMY["Kategorie"] == "Kompensation", "Wert"].sum()
    )
    return f"{total} CHF"

# Callback 2: Balkendiagramm zeichnen
@callback(
    Output("summary-kpi-graph", "figure"),
    Input("summary-interval", "n_intervals")
)
def update_kpi_graph(_):
    fig = px.bar(
        DF_DUMMY,
        x="Kategorie",
        y="Wert",
        title="Kosten vs. Kompensation",
        labels={"Wert": "CHF", "Kategorie": ""}
    )
    fig.update_layout(margin={"t":40, "b":20, "l":20, "r":20})
    return fig