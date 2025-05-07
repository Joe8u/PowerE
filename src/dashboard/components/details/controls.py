# src/dashboard/components/details/controls.py
from dash import html, dcc
import dash_bootstrap_components as dbc

ALL = "ALL"

def make_controls(appliances):
    return dbc.Row([
        dbc.Col([
            html.Label("Appliances auswählen"),
            dcc.Dropdown(
                id="appliance-dropdown",
                options=[
                    {"label": "Alle Geräte", "value": ALL},
                    *[{"label": a, "value": a} for a in appliances]
                ],
                value=[ALL],
                multi=True,
                clearable=False
            ),
            dbc.Checklist(
                id="cumulative-checkbox",
                options=[{"label": "Kumulierten Verbrauch anzeigen", "value": "cumulative"}],
                value=[],
                inline=True,
                className="mt-2"
            ),  # <- Komma hier!

            # NEU: Auswahl, welche Graphen angezeigt werden sollen
            html.Div([
                html.Label("Anzuzeigende Grafiken"),
                dbc.Checklist(
                    id="graph-selector",
                    options=[
                        {"label": "Verbrauch",        "value": "show_load"},
                        {"label": "Marktübersicht",   "value": "show_market"},
                        {"label": "Spotkosten", "value": "show_cost2"},
                    ],
                    value=["show_load", "show_market", "show_cost2"],  # Default: alles an
                    inline=True,
                    className="mt-2"
                ),
            ], className="mt-3"),
        ], width=4),
        dbc.Col([
            html.Label("Zeitbereich wählen"),
            dcc.DatePickerRange(
                id="date-picker",
                start_date="2024-01-01",
                end_date="2024-01-02",
                display_format="YYYY-MM-DD"
            ),
        ], width=5),
    ], className="mb-4")