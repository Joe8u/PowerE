# src/dashboard/components/details/graphs/cost2_graphs.py

from dash import dcc
import pandas as pd
import plotly.graph_objects as go
from typing import List

def cost2_graph():
    """
    DCC-Graph-Component für die Appliance-Kosten (Spot vs. Regel) pro Intervall mit Kennzahl.
    """
    return dcc.Graph(id="cost2-graph")


def make_cost2_figure(
    df_load: pd.DataFrame,
    appliances: List[str],
    df_spot: pd.DataFrame,
    df_reg: pd.DataFrame,
    xaxis_range,
    start: str,
    end: str
) -> go.Figure:
    """
    Zeigt die reinen Spotkosten pro Intervall als Linie und gibt oben rechts
    eine Kennzahl zur gesamten abgefragten Regelenergie (in MWh).

    Parameter:
    - df_load: DataFrame mit Lastprofilen, Index=timestamp, Spalten je Appliance
    - appliances: Liste ausgewählter Appliances
    - df_spot: DataFrame mit Spot-Preisen, Index=timestamp, Spalte 'price_eur_mwh'
    - df_reg: DataFrame mit Regelenergie, Index=timestamp, Spalte 'total_called_mw'
    - xaxis_range: Bereich für X-Achse
    - start, end: Strings für Titel
    """
    # 1) Verbrauch der ausgewählten Appliances
    cons = df_load[appliances].sum(axis=1)

    # 2) Spotpreise auf den gleichen Zeitindex abbilden
    spot_prices = df_spot['price_eur_mwh'].reindex(cons.index, fill_value=0)

    # 3) Spot-Kosten pro Intervall berechnen (kW * EUR/MWh)
    spot_cost = cons * spot_prices

    # 4) Gesamt-Regelenergie (MWh) berechnen (Integral: MW * Stunden)
    # Zeitdifferenz in Stunden
    dt = df_reg.index.to_series().diff().dropna().dt.total_seconds().median() / 3600
    total_reg_mwh = (df_reg['total_called_mw'] * dt).sum()

    # 5) Figure aufbauen
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=spot_cost.index,
        y=spot_cost,
        name="Spotkosten (EUR)",
        mode="lines"
    ))

    # 6) Annotation für Gesamt-Regelenergie
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.99, y=0.95,
        text=f"Total Regelenergie: {total_reg_mwh:.2f} MWh",
        showarrow=False,
        align="right"
    )

    # 7) Layout konfigurieren
    fig.update_layout(
        title_text=f"Spotkosten und Gesamt-Regelenergie {start} bis {end}",
        xaxis=dict(range=xaxis_range, title="Zeit"),
        yaxis=dict(title="Spotkosten per Intervall (EUR)"),
        transition_duration=300
    )
    return fig
