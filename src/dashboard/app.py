# src/dashboard/app.py
from dash import Dash, html
from dashboard.pages.scenarios import layout as scenarios_layout, register_callbacks as register_scenarios

# Initialisiere die Dash-App
app = Dash(__name__, title="PowerE-Dash")

# Definiere das Hauptlayout (vorläufig nur mit der Scenarios-Seite)
app.layout = html.Div([
    html.H1("PowerE-Dash: Haushaltslastverschiebung"),
    scenarios_layout  # Integriere das Layout der Scenarios-Seite
])

# Registriere Callbacks für die Scenarios-Seite
register_scenarios(app)

if __name__ == "__main__":
    app.run_server(debug=True)