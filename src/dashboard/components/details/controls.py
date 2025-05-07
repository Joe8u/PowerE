# src/dashboard/components/details/controls.py
from dash import html, dcc
import dash_bootstrap_components as dbc

ALL = "ALL"

def make_controls(appliances):
    return dbc.Row([
      dbc.Col([
        html.Label("Appliances auswählen"),
        dcc.Dropdown(
          id="appliance-dropdown",
          options=[
            {"label": "Alle Geräte", "value": ALL},
            *[{"label": a, "value": a} for a in appliances]
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
    ], className="mb-4")