# src/dashboard/pages/scenarios.py
from dash import register_page, html, dcc
import dash_bootstrap_components as dbc

from dashboard.components.scenarios.controls import make_scenario_controls # Korrekt
# NEU: Passe diesen Import an, da die Grafik jetzt in scenarios/graphs liegt
from dashboard.components.scenarios.graphs.per_appliance_comparison_graph import per_appliance_comparison_graph_component 

from data_loader.lastprofile import list_appliances # Korrekt

register_page(
    __name__,
    path="/scenarios",
    title="Szenario-Simulation | PowerE",
    name="Szenario-Simulation"
)

layout = dbc.Container(
    [
        html.H1("Lastverschiebung: Szenario-Simulation", className="my-4"),
        html.Hr(),
        html.Div(
            id="scenario-controls-container",
            children=[
                make_scenario_controls(list_appliances(2024)) # Korrekt
            ]
        ),
        html.Hr(className="my-4"),
        html.Div(
            id="scenario-results-container",
            children=[
                per_appliance_comparison_graph_component(), # Korrekt
            ]
        ),
    ],
    fluid=True
)