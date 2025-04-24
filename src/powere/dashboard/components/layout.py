# src/dashboard/components/layout.py
from dash import html, dcc
import dash_bootstrap_components as dbc


def create_layout():
    """
    Return the Dash application layout: sidebar controls + main graph.
    """
    return dbc.Container([
        html.H1("PowerE Dashboard"),

        dbc.Row([
            # Sidebar
            dbc.Col([
                html.Label("Datenquelle"),
                dcc.Tabs(
                    id="source-tabs",
                    value="jasm",
                    children=[
                        dcc.Tab(label="JASM", value="jasm"),
                        dcc.Tab(label="Market", value="market"),
                        dcc.Tab(label="Tertiary", value="tertiary"),
                        dcc.Tab(label="Survey", value="survey"),
                    ]
                ),
                html.Br(),

                html.Label("Zeitraum-Granularität"),
                dcc.RadioItems(
                    id="granularity",
                    options=[
                        {"label": "Tages-Ansicht",  "value": "daily"},
                        {"label": "Wochen-Ansicht", "value": "weekly"},
                        {"label": "Monats-Ansicht", "value": "monthly"},
                        {"label": "Jahres-Ansicht", "value": "yearly"},
                    ],
                    value="monthly",
                    labelStyle={"display": "block"}
                ),
                html.Br(),

                html.Label("Jahr"),
                dcc.Dropdown(
                    id="year-selector",
                    options=[{"label": y, "value": y} for y in [2015, 2024, 2035, 2050]],
                    value=2024
                ),
                html.Br(),

                html.Label("Geräte / Metriken"),
                dcc.Dropdown(
                    id="appliance-selector",
                    multi=True,
                ),
                html.Br(),

                # Platzhalter für Umfrage-Filter
                html.Div(id="survey-filters"),

            ], width=3),

            # Main Panel
            dbc.Col([
                dcc.Loading(
                    id="loading-graph",
                    children=[dcc.Graph(id="main-graph")]
                ),
                html.Div(id="summary-stats")
            ], width=9)
        ])

    ], fluid=True)
