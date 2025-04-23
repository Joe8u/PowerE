# src/dashboard/callbacks.py

from dash import Input, Output
from src.dashboard.app import app           # dein Dash-App-Objekt
from src.loaders.jasm.yearly import load_jasm_yearly
# (ggf. später weitere Loader für market, tertiary, survey)

@app.callback(
    Output("appliance-selector", "options"),
    Input("source-tabs",    "value"),
    Input("year-selector",  "value"),
    Input("granularity",    "value"),
)
def update_appliances(source, year, grit):
    if source == "jasm" and grit == "yearly":
        df = load_jasm_yearly(year)
        return [{"label": c, "value": c} for c in df.columns]
    return []