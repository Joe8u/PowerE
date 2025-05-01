from dash import register_page, html, dcc, callback, Input, Output
import plotly.express as px
import datetime
from data_loader.lastprofile import load_appliances, list_appliances

register_page("details", path="/details", title="Details")

# Initiale Appliance-Liste (alle)
APPLIANCES = list_appliances(2024)

layout = html.Div([
    dcc.Dropdown(
        id="appliance-dropdown",
        options=[{"label": a, "value": a} for a in APPLIANCES],
        value=APPLIANCES[0], clearable=False
    ),
    dcc.DatePickerRange(
        id="date-picker",
        start_date="2024-01-01",
        end_date="2024-01-07"
    ),
    dcc.Graph(id="time-series-graph")
])

@callback(
    Output("time-series-graph","figure"),
    Input("appliance-dropdown","value"),
    Input("date-picker","start_date"),
    Input("date-picker","end_date"),
)
def update_graph(appliance, start, end):
    start_dt = datetime.datetime.fromisoformat(start)
    end_dt   = datetime.datetime.fromisoformat(end)
    # Nur diese Appliance & diesen Zeitraum laden
    df = load_appliances([appliance], start_dt, end_dt, year=2024)
    fig = px.line(df, x=df.index, y=appliance)
    return fig