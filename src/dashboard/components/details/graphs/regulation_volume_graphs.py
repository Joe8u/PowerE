# src/dashboard/components/details/graphs/regulation_volume_graphs.py

from dash import html
import dash_bootstrap_components as dbc
import pandas as pd

def regulation_volume_graph():
    """
    Container für die Gesamt-Regelleistungs-Menge.
    """
    return dbc.Row(
        dbc.Col(html.Div(id="total-regulation-volume"), width=12),
        className="mb-4"
    )

def make_regulation_volume_info(df_reg: pd.DataFrame) -> dbc.Card:
    """
    Berechnet das Gesamt-Volumen der abgerufenen Regelenergie (MWh)
    und gibt eine Dash-Card mit der Kennzahl zurück.
    """
    # Zeitdifferenz in Stunden (Median-Intervall)
    dt_h = 0.25
    # Summe von MW * Stunden = MWh
    total_mwh = (df_reg["total_called_mw"] * dt_h).sum()

    return dbc.Card(
        [
            dbc.CardHeader("Total Regelenergie"),
            dbc.CardBody(html.H4(f"{total_mwh:,.2f} MWh"))
        ],
        color="warning",
        inverse=False
    )