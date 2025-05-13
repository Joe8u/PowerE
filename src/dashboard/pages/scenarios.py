# src/dashboard/pages/scenarios.py
from dash import register_page, html, dcc
import dash_bootstrap_components as dbc

from dashboard.components.scenarios.controls import make_scenario_controls # Korrekt
# NEU: Passe diesen Import an, da die Grafik jetzt in scenarios/graphs liegt
from dashboard.components.scenarios.graphs.per_appliance_comparison_graph import per_appliance_comparison_graph_component 

from data_loader.lastprofile import list_appliances # Korrekt

import dashboard.components.scenarios.callbacks  # noqa: F401

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

        html.H4("Ökonomische Bewertung des Szenarios:", className="mb-3"),
        dbc.Row(
            [
                dbc.Col(dbc.Card([dbc.CardHeader("Value Added (Netto)"), 
                                dbc.CardBody(id="scenario-kpi-value-added", className="fs-4 fw-bold")]), 
                        width=12, md=6, lg=3, className="mb-3"),
                dbc.Col(dbc.Card([dbc.CardHeader("Spotmarkt-Einsparung"), 
                                dbc.CardBody(id="scenario-kpi-spot-savings", className="fs-5")]), 
                        width=12, md=6, lg=3, className="mb-3"),
                dbc.Col(dbc.Card([dbc.CardHeader("Regelenergie-Einsparung"), 
                                dbc.CardBody(id="scenario-kpi-as-savings", className="fs-5")]), 
                        width=12, md=6, lg=3, className="mb-3"),
                dbc.Col(dbc.Card([dbc.CardHeader("DR-Programmkosten (Anreize)"), 
                                dbc.CardBody(id="scenario-kpi-dr-costs", className="fs-5")]), 
                        width=12, md=6, lg=3, className="mb-3"),
            ],
            className="mb-2" # Weniger Abstand nach unten, wenn noch mehr KPIs kommen
        ),
        dbc.Row(
            [
                dbc.Col(dbc.Card([dbc.CardHeader("Verschobene Energie (Event)"),
                                dbc.CardBody(id="scenario-kpi-total-shifted-energy", className="fs-5")]), 
                        width=12, md=6, lg=3, className="mb-3"),
                dbc.Col(dbc.Card([dbc.CardHeader("Avg. Anreizkostenrate"),
                                dbc.CardBody(id="scenario-kpi-avg-payout-rate", className="fs-5")]), 
                        width=12, md=6, lg=3, className="mb-3"),
                # Hier wäre Platz für Baseline-Kosten vs. Szenario-Kosten, falls gewünscht
            ],
            className="mb-4"
        ),


    ],
    fluid=True
    
)