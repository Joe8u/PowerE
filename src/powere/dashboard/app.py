# src/dashboard/app.py

import dash_bootstrap_components as dbc
from dash import Dash, dcc, html


def create_dash_app() -> Dash:
    """
    Erzeugt die Dash-Instanz, legt Layout fest
    und registriert alle Callbacks.
    """
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

    # === Layout ===
    app.layout = dbc.Container(
        [
            html.H1("PowerE Dashboard"),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Datenquelle"),
                            dcc.Tabs(
                                id="source-tabs",
                                value="jasm",
                                children=[
                                    dcc.Tab(label="JASM", value="jasm"),
                                    dcc.Tab(label="Market", value="market"),
                                    dcc.Tab(label="Tertiary", value="tertiary"),
                                    dcc.Tab(label="Survey", value="survey"),
                                ],
                            ),
                            html.Br(),
                            html.Label("Zeitraum-Granularität"),
                            dcc.RadioItems(
                                id="granularity",
                                options=[
                                    {"label": "Tages-Ansicht", "value": "daily"},
                                    {"label": "Wochen-Ansicht", "value": "weekly"},
                                    {"label": "Monats-Ansicht", "value": "monthly"},
                                    {"label": "Jahres-Ansicht", "value": "yearly"},
                                ],
                                value="monthly",
                                labelStyle={"display": "block"},
                            ),
                            html.Br(),
                            html.Label("Jahr"),
                            dcc.Dropdown(
                                id="year-selector",
                                options=[
                                    {"label": y, "value": y}
                                    for y in [2015, 2024, 2035, 2050]
                                ],
                                value=2024,
                            ),
                            html.Br(),
                            html.Label("Geräte / Metriken"),
                            dcc.Dropdown(id="appliance-selector", multi=True),
                            html.Br(),
                            html.Label("Zeitraum (nur daily/weekly/monthly)"),
                            dcc.DatePickerRange(
                                id="date-range",
                                display_format="DD.MM.YYYY",
                                start_date_placeholder_text="Startdatum",
                                end_date_placeholder_text="Enddatum",
                            ),
                            html.Br(),
                            # nur für Survey-Tab
                            html.Div(id="survey-filters"),
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            dcc.Loading(dcc.Graph(id="main-graph"), type="circle"),
                            html.Div(id="summary-stats"),
                        ],
                        width=9,
                    ),
                ]
            ),
        ],
        fluid=True,
    )

    # === Callbacks registrieren ===
    from src.dashboard.callbacks import register_callbacks

    register_callbacks(app)

    return app


# globale App-Instanz für WSGI/uvicorn
app = create_dash_app()

if __name__ == "__main__":
    # Ab Dash v2: app.run statt run_server
    app.run(debug=True, host="127.0.0.1", port=8050)
