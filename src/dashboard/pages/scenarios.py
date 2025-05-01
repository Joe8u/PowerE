# src/dashboard/pages/scenarios.py
from dash import register_page, html, dcc, Input, Output, callback
register_page("scenarios", path="/scenarios", title="Scenarios")
layout = html.Div([...])

# Layout für die Szenarioanalyse-Seite
layout = html.Div([
    html.H1("Szenarioanalyse"),
    html.P("Interaktive Analyse von Lastverschiebungsszenarien."),
    dcc.Graph(id="scenario-plot"),  # Platzhalter für ein Diagramm
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

# Funktion zum Registrieren von Callbacks
def register_callbacks(app):
    """
    Registriert Callbacks für die Szenarioanalyse-Seite.
    :param app: Dash-App-Instanz
    """
    from dash.dependencies import Input, Output

    @app.callback(
        Output("scenario-plot", "figure"),
        [Input("compensation-slider", "value")]
    )
    def update_scenario_plot(compensation_value):
        """
        Platzhalter-Callback: Aktualisiert das Diagramm basierend auf dem Kompensationsrabatt.
        """
        # Beispiel: Dummy-Plot (später mit echten Daten ersetzen)
        return {
            "data": [
                {"x": [1, 2, 3], "y": [compensation_value, compensation_value * 2, compensation_value * 3], "type": "line"}
            ],
            "layout": {"title": f"Netto-Mehrwert bei {compensation_value}% Rabatt"}
        }