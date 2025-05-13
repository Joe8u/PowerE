# src/dashboard/components/scenarios/controls.py
from dash import html, dcc
import dash_bootstrap_components as dbc

# Du könntest ALL hier definieren oder aus details.controls importieren, wenn es dort bleibt
ALL = "ALL"

def make_scenario_controls(appliances_list): # Nimmt die Liste der verfügbaren Geräte entgegen
    """
    Erstellt die Steuerelemente für die Szenario-Simulationsseite.
    """
    return dbc.Card( # Umhülle die Controls mit einer Card für bessere Optik
        dbc.CardBody([
            html.H4("Simulationsparameter", className="card-title mb-3"),
            dbc.Row([
                # Spalte 1: Geräte- und Datumsauswahl
                dbc.Col([
                    html.Label("Appliances auswählen", className="form-label"),
                    dcc.Dropdown(
                        id="scenario-appliance-dropdown", # Eindeutige ID für diese Seite
                        options=[
                            {"label": "Alle analysierten Geräte", "value": ALL},
                            *[{"label": a, "value": a} for a in appliances_list]
                        ],
                        value=appliances_list, # Standard: Alle vorauswählen
                        multi=True,
                        clearable=False
                    ),
                    html.Br(),
                    html.Label("Zeitbereich für Lastprofile wählen", className="form-label"),
                    dcc.DatePickerRange(
                        id="scenario-date-picker", # Eindeutige ID
                        start_date="2024-01-01",   # Standardwerte
                        end_date="2024-01-02",
                        display_format="YYYY-MM-DD",
                        className="mb-2"
                    ),
                ], md=4), # md=4 bedeutet, auf mittleren Schirmen nimmt es 4 von 12 Spalten ein

                # Spalte 2: DR-Event Parameter
                dbc.Col([
                    html.Label("Parameter für DR-Event", className="form-label fw-bold"),
                    dbc.Row([
                        dbc.Col([
                            html.Div("Startstunde (0-23 Uhr am ersten gewählten Tag)", className="small mb-1"),
                            dcc.Input(
                                id="scenario-dr-start-hour", # Eindeutige ID
                                type="number",
                                value=14, # Standardwert
                                min=0,
                                max=23,
                                step=1,
                                className="form-control form-control-sm"
                            ),
                        ], width=12, lg=4, className="mb-2 mb-lg-0"), # lg für größere Schirme
                        dbc.Col([
                            html.Div("Dauer (Stunden)", className="small mb-1"),
                            dcc.Input(
                                id="scenario-dr-duration-hours", # Eindeutige ID
                                type="number",
                                value=2.0, # Standardwert
                                min=0.25,  # z.B. Viertelstunden
                                step=0.25,
                                className="form-control form-control-sm"
                            ),
                        ], width=12, lg=4, className="mb-2 mb-lg-0"),
                        dbc.Col([
                            html.Div("Anreiz (%)", className="small mb-1"),
                            dcc.Input(
                                id="scenario-dr-incentive-pct", # Eindeutige ID
                                type="number",
                                value=15, # Standardwert
                                min=0,
                                max=100,
                                step=1,
                                className="form-control form-control-sm"
                            ),
                        ], width=12, lg=4),
                    ]),
                ], md=5),

                # Spalte 3: Simulations-Button
                dbc.Col([
                    html.Div(style={"height": "25px"}), # Kleiner Platzhalter für bessere Ausrichtung mit Labels
                    html.Button(
                        "Simulation starten / aktualisieren",
                        id="scenario-run-button", # Eindeutige ID
                        n_clicks=0,
                        className="btn btn-primary w-100" # Bootstrap Button, volle Breite der Spalte
                    )
                ], md=3, className="d-flex align-items-center") # Vertikal zentrieren
            ])
        ]),
        className="mb-4" # Abstand nach unten für die ganze Card
    )