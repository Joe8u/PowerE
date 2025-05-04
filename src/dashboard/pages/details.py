# src/dashboard/pages/details.py
from dash import register_page, html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import datetime

from data_loader.lastprofile import load_appliances, list_appliances

# 1) Register the page
register_page(__name__, path="/details", title="Details")

# 2) Konstanten und Appliance-Liste
APPLIANCES = list_appliances(2024)
ALL = "ALL"

# 3) Layout: Multi-Select + Checkbox
layout = html.Div([
    html.H2("Detail-Analyse: Lastprofil-Zeitreihen"),
    dbc.Row([
      dbc.Col([
        html.Label("Appliances auswählen"),
        dcc.Dropdown(
          id="appliance-dropdown",
          options=[
            {"label": "Alle Geräte", "value": ALL},
            *[{"label": a, "value": a} for a in APPLIANCES]
          ],
          value=[ALL],
          multi=True,
          clearable=False
        ),
        dbc.Checklist(
          id="cumulative-checkbox",
          options=[{"label": "Kumulierten Verbrauch anzeigen", "value": "cumulative"}],
          value=[],
          inline=True,
          className="mt-2"
        )
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

# 4) Callback: Multi, Kumuliert + korrekte Achsenzuweisung
@callback(
    Output("time-series-graph", "figure"),
    Input("appliance-dropdown", "value"),
    Input("cumulative-checkbox", "value"),
    Input("date-picker", "start_date"),
    Input("date-picker", "end_date"),
)
def update_graph(selected_values, cumulative_flag, start, end):
    # Datum parsen
    start_dt = datetime.datetime.fromisoformat(start)
    end_dt   = datetime.datetime.fromisoformat(end)

    # Auswahl normalisieren
    if not selected_values or ALL in selected_values:
        appliances = APPLIANCES
    else:
        appliances = selected_values

    # Daten abrufen
    df = load_appliances(
        appliances=appliances,
        start=start_dt,
        end=end_dt,
        year=2024
    )

    # Kumulierte Anzeige?
    if "cumulative" in cumulative_flag:
        total = df.sum(axis=1)
        total_df = total.reset_index()
        total_df.columns = ["timestamp", "value"]
        fig = px.line(
            total_df,
            x="timestamp",
            y="value",
            title=f"Kumulierter Verbrauch {start} bis {end}",
            labels={"timestamp": "Zeit", "value": "Leistung (kW)"}
        )
    else:
        df_reset = df.reset_index()
        fig = px.line(
            df_reset,
            x="timestamp",
            y=appliances,
            title=f"Verbrauch pro Appliance {start} bis {end}",
            labels={"timestamp": "Zeit", "value": "Leistung (kW)", "variable": "Appliance"}
        )

    fig.update_layout(transition_duration=300)
    return fig
