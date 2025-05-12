# src/dashboard/pages/details.py

from dash import register_page, html, dcc
import dash_bootstrap_components as dbc
from data_loader.lastprofile import list_appliances

from dashboard.components.details.controls import make_controls
from dashboard.components.details.graphs.lastprofile_graphs import time_series_graph
from dashboard.components.details.graphs.market_graphs import regulation_graph
from dashboard.components.details.graphs.cost_graphs       import cost_graph
from dashboard.components.details.graphs.cost2_graphs        import cost2_graph
from dashboard.components.details.graphs.consumption_graphs import consumption_graph
from dashboard.components.details.graphs.regulation_volume_graphs import regulation_volume_graph
from dashboard.components.details.survey_graphs.participation_graphs import make_participation_curve
from dashboard.components.details.survey_graphs.shift_duration_all import calculate_shift_potential_data

# Damit der Callback-Decorator aktiv wird
import dashboard.components.details.callbacks  # noqa: F401

# Registriere die Seite bei Dash
register_page(__name__, path="/details", title="Details")

# Layout der Seite
layout = html.Div([
    html.H2("Detail-Analyse: Lastprofil-Zeitreihen"),

    # Controls: Dropdown, DatePickerRange, Checkbox, Graph-Selector
    make_controls(list_appliances(2024)),

    # 1) Kosten‐Übersicht (Spot- und Regelkosten) immer anzeigen
    cost_graph(),

    # 2) Gesamtverbrauch und Total-Regelenergie nebeneinander
    dbc.Row([
        dbc.Col(
            consumption_graph(),
            id="consumption-container",
            width=6
        ),
        dbc.Col(
            regulation_volume_graph(),
            id="regulation-volume-container",
            width=6
        ),
    ], className="mb-4"),

    # 3) Verbrauchs-Zeitreihe (toggle-bar)
    html.Div(
        time_series_graph(),
        id="load-container"
    ),

    # 4) Regulierung / Spot-Preise (toggle-bar)
    html.Div(
        regulation_graph(),
        id="market-container"
    ),

    # 5) Kumulierte Kosten-Grafik (toggle-bar)
    html.Div(
        cost2_graph(),
        id="cost2-graph-container"
    ),

    # 6) Teilnahme-Kurve
    html.Div([
        html.H3("Incentive vs. Teilnahmequote"),
        dcc.Graph(id="participation-curve")
    ], className="mb-4"),

    # ... im layout-Block, z.B. nach dem Teilnahme-Curve-Abschnitt:
    html.Div([
        html.H3("Verschiebedauer-Verteilungen aller Geräte"),
        dcc.Graph(id="shift-all-graph")
    ], className="mb-4"),

])