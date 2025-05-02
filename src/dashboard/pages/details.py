# src/dashboard/pages/details.py
from dash import register_page, html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import datetime

from data_loader.lastprofile import load_appliances, list_appliances

# 1) Register the page
register_page(__name__, path="/details", title="Details")

# 2) (Optionally) preload a short period, or leave df=None until callback
# We'll leave it out and load inside the callback to keep memory small.

# 3) Module‐level layout only
#    Notice: no function named "layout"!
APPLIANCES = list_appliances(2024)

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
          end_date="2024-01-07",
          display_format="YYYY-MM-DD"
        ),
      ], width=5),
    ], className="mb-4"),
    dcc.Graph(id="time-series-graph")
])

# 4) Callback: loads *only* the requested appliance & date span
@callback(
    Output("time-series-graph", "figure"),
    Input("appliance-dropdown", "value"),
    Input("date-picker", "start_date"),
    Input("date-picker", "end_date"),
)
def update_graph(appliance, start, end):
    # parse strings to datetimes
    start_dt = datetime.datetime.fromisoformat(start)
    end_dt   = datetime.datetime.fromisoformat(end)

    # load only what’s needed
    df = load_appliances(
        appliances=[appliance],
        start=start_dt,
        end=end_dt,
        year=2024
    )

    # assume load_appliances returns a DataFrame indexed by timestamp
    fig = px.line(
        df,
        x=df.index,
        y=appliance,
        title=f"{appliance} Verbrauch {start} bis {end}",
        labels={"x": "Zeit", appliance: "Leistung (kW)"}
    )
    fig.update_layout(transition_duration=300)
    return fig