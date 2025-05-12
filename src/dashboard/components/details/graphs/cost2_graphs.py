# src/dashboard/components/details/graphs/cost2_graphs.py

from dash import dcc
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots # Wichtig für sekundäre Y-Achse
from typing import List, Optional # Optional für den neuen Parameter

def cost2_graph(): # Diese Funktion bleibt unverändert
    return dcc.Graph(id="cost2-graph")

def make_cost2_figure(
    df_load: pd.DataFrame,
    appliances: List[str],
    df_spot: pd.DataFrame,
    df_reg: pd.DataFrame, 
    xaxis_range,
    start: str,
    end: str,
    shiftable_power_series: Optional[pd.Series] = None # <<< HIER IST DER 8. PARAMETER
) -> go.Figure:
    """
    Zeigt die reinen Spotkosten pro Intervall als Linie und optional
    das verschiebbare Lastpotenzial auf einer zweiten Y-Achse.
    """
    # 1) Verbrauch der ausgewählten Appliances
    cons = df_load[appliances].sum(axis=1)

    # 2) Spotpreise auf den gleichen Zeitindex abbilden
    spot_prices = df_spot['price_eur_mwh'].reindex(cons.index, method='ffill')

    # 3) Spot-Kosten pro Intervall berechnen
    dt_h_load = 0
    if not df_load.empty and isinstance(df_load.index, pd.DatetimeIndex) and len(df_load.index) > 1:
        dt_h_load = (df_load.index[1] - df_load.index[0]).total_seconds() / 3600
    elif not df_load.empty and len(df_load.index) == 1: # Fall mit nur einem Datenpunkt
         dt_h_load = 1 # Annahme 1h oder eine andere sinnvolle Dauer

    energy_kwh_interval = cons * dt_h_load
    spot_cost_eur_interval = energy_kwh_interval * spot_prices / 1000

    # Figure aufbauen mit sekundärer Y-Achse
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Spotkosten-Kurve
    fig.add_trace(go.Scatter(
        x=spot_cost_eur_interval.index,
        y=spot_cost_eur_interval,
        name="Spotkosten (EUR)",
        mode="lines"
    ), secondary_y=False)

    # Kurve für verschiebbare Last, falls Daten vorhanden
    if shiftable_power_series is not None and not shiftable_power_series.empty:
        fig.add_trace(go.Scatter(
            x=shiftable_power_series.index,
            y=shiftable_power_series,
            name="Verschiebbares Potenzial (kW)",
            mode="lines",
            line=dict(dash='dot', color='rgba(255,127,14,0.7)')
        ), secondary_y=True)

    # Layout konfigurieren
    fig.update_layout(
        title_text=f"Spotkosten & Verschiebe-Potenzial ({start} bis {end})",
        xaxis=dict(range=xaxis_range, title="Zeit"),
        transition_duration=300
    )
    fig.update_yaxes(title_text="Spotkosten pro Intervall (EUR)", secondary_y=False)
    if shiftable_power_series is not None and not shiftable_power_series.empty:
        fig.update_yaxes(title_text="Verschiebbares Potenzial (kW)", secondary_y=True, showgrid=False)

    return fig