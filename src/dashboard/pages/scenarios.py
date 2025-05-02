#!/usr/bin/env python3
# src/dashboard/pages/scenarios.py

from dash import register_page, html, dcc, callback, Input, Output
import plotly.express as px

# 1) Seite registrieren
register_page(__name__, path="/scenarios", title="Scenarios")

# 2) Modul-level layout
layout = html.Div([
    html.H1("Szenarioanalyse"),
    html.P("Interaktive Analyse von Lastverschiebungsszenarien."),
    dcc.Graph(id="scenario-plot"),
    dcc.Slider(
        id="compensation-slider",
        min=0,
        max=50,
        step=5,
        value=10,
        marks={i: f"{i}%" for i in range(0, 51, 10)},
        tooltip={"placement": "bottom", "always_visible": True},
    ),
])

# 3) Callback mit Pages-API
@callback(
    Output("scenario-plot", "figure"),
    Input("compensation-slider", "value")
)
def update_scenario_plot(compensation_value):
    # Dummy-Plot als Platzhalter
    fig = px.line(
        x=[1, 2, 3],
        y=[compensation_value, compensation_value * 2, compensation_value * 3],
        labels={"x": "Szenario", "y": "Netto-Mehrwert"},
        title=f"Netto-Mehrwert bei {compensation_value}% Rabatt"
    )
    return fig