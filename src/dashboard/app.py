# src/dashboard/app.py

from dash import Dash, dcc, html
import dash_bootstrap_components as dbc

# Callbacks importieren, damit alle @app.callback-Definitionen registriert werden
from . import callbacks

# 1) Dash-App initialisieren
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP]
)
# 2) Flask-Server exportieren für Hosting (z. B. Gunicorn, FastAPI)
server = app.server

# 3) Layout definieren
app.layout = dbc.Container([
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
                    {"label": "Tages-Ansicht",   "value": "daily"},
                    {"label": "Wochen-Ansicht",  "value": "weekly"},
                    {"label": "Monats-Ansicht",  "value": "monthly"},
                    {"label": "Jahres-Ansicht",  "value": "yearly"},
                ],
                value="monthly",
                labelStyle={"display": "block"}
            ),
            html.Br(),

            html.Label("Jahr"),
            dcc.Dropdown(
                id="year-selector",
                options=[{"label": y, "value": y} for y in [2015, 2024, 2035, 2050]],
                value=2024,
                clearable=False
            ),
            html.Br(),

            html.Label("Geräte / Metriken"),
            dcc.Dropdown(
                id="appliance-selector",
                multi=True,
                placeholder="Wähle Geräte oder Metriken"
            ),
            html.Br(),

            # Datumsauswahl: nur bei daily/weekly/monthly
            html.Div(
                dcc.DatePickerRange(
                    id="date-range",
                    display_format="DD.MM.YYYY"
                ),
                id="date-picker-container"
            ),
            html.Br(),

            # Platzhalter für Survey-Filter (Alter, Einkommensklasse etc.)
            html.Div(id="survey-filters")
        ], width=3),

        # Hauptbereich
        dbc.Col([
            dcc.Loading(
                dcc.Graph(id="main-graph"),
                type="circle"
            ),
            html.Div(id="summary-stats", style={"marginTop": "1rem"})
        ], width=9)
    ])
], fluid=True)

# 4) App starten, wenn direkt aufgerufen
if __name__ == "__main__":
    # Debug-Modus in dev-Umgebung; Host/Port könntest du auch aus settings.py lesen
    app.run_server(debug=True, host="127.0.0.1", port=8050)