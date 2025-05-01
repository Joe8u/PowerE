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

# Modul-level Layout mit Interval als Trigger
layout = html.Div([
    dcc.Interval(id="summary-trigger", interval=1, max_intervals=1),
    html.H2("Executive Summary"),
    html.Div([
        html.H4("Netto-Mehrwert (CHF)"),
        html.Div(id="summary-net-value")
    ], className="card", style={"marginBottom": "20px"}),
    dcc.Graph(id="summary-kpi-graph")
])

# Callback 1 – wird einmal durch Interval ausgelöst
@callback(
    Output("summary-net-value", "children"),
    Input("summary-trigger", "n_intervals")
)
def update_net_value(_):
    total = (
        DF_DUMMY.loc[DF_DUMMY["Kategorie"]=="Spot Einsparung", "Wert"].sum()
        - DF_DUMMY.loc[DF_DUMMY["Kategorie"]=="Kompensation",   "Wert"].sum()
    )
    return f"{total} CHF"

# Callback 2 – baut das Balkendiagramm
@callback(
    Output("summary-kpi-graph", "figure"),
    Input("summary-trigger", "n_intervals")
)
def update_kpi_graph(_):
    fig = px.bar(DF_DUMMY, x="Kategorie", y="Wert", title="Kosten vs. Kompensation")
    return fig