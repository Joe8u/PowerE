#!/usr/bin/env python3
# src/dashboard/pages/summary.py

import pandas as pd
from dash import register_page, html, dcc, callback, Input, Output
import plotly.express as px

# 1) Seite registrieren
register_page("summary", path="/", title="Executive Summary")

# Dummy-Daten
DF_DUMMY = pd.DataFrame({
    'Kategorie': ['Spot Einsparung', 'Kompensation'],
    'Wert': [1000, 300]
})

# 2) Modul-level layout
layout = html.Div([
    html.H2("Executive Summary"),
    html.Div([
        html.H4("Netto-Mehrwert (CHF)"),
        html.Div(id="summary-net-value")
    ], className="card", style={"marginBottom": "20px"}),
    dcc.Graph(id="summary-kpi-graph")
])

# 3) Callbacks mit Pages-API

@callback(
    Output("summary-net-value", "children"),
    []
)
def update_net_value():
    total = (
        DF_DUMMY.loc[DF_DUMMY['Kategorie'] == 'Spot Einsparung', 'Wert'].sum()
        - DF_DUMMY.loc[DF_DUMMY['Kategorie'] == 'Kompensation', 'Wert'].sum()
    )
    return f"{total} CHF"

@callback(
    Output("summary-kpi-graph", "figure"),
    []
)
def update_kpi_graph():
    fig = px.bar(
        DF_DUMMY,
        x="Kategorie",
        y="Wert",
        title="Kosten vs. Kompensation"
    )
    return fig