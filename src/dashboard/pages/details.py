#!/usr/bin/env python3
# src/dashboard/pages/details.py

from dash import register_page, html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd

register_page("details", path="/details", title="Details")

# 1) Daten einmal laden
df = pd.concat([
    pd.read_csv(f"data/processed/lastprofile/2024/2024-{m:02d}.csv",
                parse_dates=["timestamp"])
    for m in range(1, 13)
])

# 2) Strip timezone info → naive datetime64[ns]
df["timestamp"] = (
    pd.to_datetime(df["timestamp"], utc=True)
      .dt.tz_convert("Europe/Zurich")
      .dt.tz_localize(None)
)

# 3) Liste aller Appliances
APPLIANCES = [c for c in df.columns if c != "timestamp"]

# 4) Define the page layout
layout = html.Div([
    html.H2("Detail-Analyse: Lastprofil-Zeitreihen"),
    dbc.Row([
        dbc.Col([
            html.Label("Appliance auswählen"),
            dcc.Dropdown(
                id="appliance-dropdown",
                options=[{"label": a, "value": a} for a in APPLIANCES],
                value=APPLIANCES[0],
                clearable=False
            ),
        ], width=4),
        dbc.Col([
            html.Label("Zeitbereich wählen"),
            dcc.DatePickerRange(
                id="date-picker",
                start_date="2024-01-01",
                end_date="2024-12-31",
                display_format="YYYY-MM-DD"
            ),
        ], width=5),
    ], className="mb-4"),
    dcc.Graph(id="time-series-graph")
])

# 5) Wire up the callback with the Pages API’s decorator
@callback(
    Output("time-series-graph", "figure"),
    Input("appliance-dropdown", "value"),
    Input("date-picker", "start_date"),
    Input("date-picker", "end_date"),
)
def update_graph(appliance, start_date, end_date):
    # Filter data
    dff = df[
        (df["timestamp"] >= start_date) & 
        (df["timestamp"] <= end_date)
    ]
    # Build figure
    fig = px.line(
        dff, x="timestamp", y=appliance,
        title=f"{appliance} Verbrauch von {start_date} bis {end_date}",
        labels={"timestamp": "Zeit", appliance: "Leistung (kW)"}
    )
    fig.update_layout(transition_duration=300)
    return fig