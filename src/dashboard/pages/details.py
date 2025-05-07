# src/dashboard/pages/details.py

from dash import register_page, html
from data_loader.lastprofile import list_appliances

from dashboard.components.details.controls import make_controls
from dashboard.components.details.graphs.lastprofile_graphs import time_series_graph
from dashboard.components.details.graphs.market_graphs import regulation_graph
from dashboard.components.details.graphs.cost_graphs       import cost_graph
from dashboard.components.details.graphs.cost2_graphs        import cost2_graph

# Damit der Callback-Decorator aktiv wird
import dashboard.components.details.callbacks  # noqa: F401

# Registriere die Seite bei Dash
register_page(__name__, path="/details", title="Details")

# Layout der Seite
layout = html.Div([
    html.H2("Detail-Analyse: Lastprofil-Zeitreihen"),

    # Controls: Dropdown, DatePickerRange, Checkbox
    make_controls(list_appliances(2024)),

    # Grafiken
    # 1) Verbrauch
    time_series_graph(),

    # 2) Regulierung / Spot
    regulation_graph(),

    # 3) Kosten‐Grafik
    cost_graph(),
    cost2_graph(),
])