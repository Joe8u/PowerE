# src/dashboard/components/details/graphs/consumption_graphs.py

from dash import html
import dash_bootstrap_components as dbc
import pandas as pd

def consumption_graph():
    """
    Container für die Gesamtverbrauchs-Kennzahl.
    """
    return dbc.Row(
        dbc.Col(html.Div(id="total-consumption"), width=12),
        className="mb-4"
    )

def make_consumption_info(df_load: pd.DataFrame) -> dbc.Card:
    """
    Berechnet den Gesamtenergieverbrauch in kWh
    (kW * Stunden) und gibt eine Dash-Card zurück.
    """
    # Verbrauch pro Intervall (kW)
    cons = df_load.sum(axis=1)
    # Intervalldauer in Stunden
    dt_h = cons.index.to_series().diff().dropna().dt.total_seconds().median() / 3600
    # GesamtkWh
    total_kwh = (cons * dt_h).sum()

    return dbc.Card(
        [
            dbc.CardHeader("Gesamtverbrauch"),
            dbc.CardBody(html.H4(f"{total_kwh:,.0f} kWh"))
        ],
        color="info",
        inverse=False
    )