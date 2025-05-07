# src/dashboard/components/details/graphs/cost2_graphs.py

from dash import dcc
import pandas as pd
import plotly.graph_objects as go


def cost2_graph():
    """
    DCC-Graph-Component für die Appliance-Kosten (Spot vs. Regel) pro Intervall mit prozentualer Aufteilung.
    """
    return dcc.Graph(id="cost2-graph")


def make_cost2_figure(
    df_load: pd.DataFrame,
    df_spot: pd.DataFrame,
    df_reg: pd.DataFrame,
    xaxis_range,
    start: str,
    end: str
) -> go.Figure:
    """
    Erzeugt:
      1) Eine Kosten-Linie (Spot+Regel) je Intervall
      2) Gestapelte Balken der Prozent-Anteile (Spot vs. Regel) auf Sekundärachse
    """
    # 1) Gesamtkonsum pro Intervall (kW als Proxy für kWh)
    cons = df_load.sum(axis=1)

    # 2) Preise auf denselben Zeitindex abbilden
    spot_prices = df_spot['price_eur_mwh'].reindex(cons.index, fill_value=0)
    reg_prices  = df_reg['avg_price_eur_mwh'].reindex(cons.index, fill_value=0)

    # 3) Kosten-Beiträge pro Intervall
    spot_cost = cons * spot_prices
    reg_cost  = cons * reg_prices
    total_cost = spot_cost + reg_cost

    # 4) Prozentanteile berechnen (vermeide Division durch Null)
    pct_base = total_cost.replace(0, 1)
    spot_pct = (spot_cost / pct_base) * 100
    reg_pct  = (reg_cost  / pct_base) * 100

    # 5) Figure aufbauen
    fig = go.Figure()
    # Linie: Kosten pro Intervall
    fig.add_trace(go.Scatter(
        x=total_cost.index,
        y=total_cost,
        name="Kosten pro Intervall (EUR)",
        mode="lines",
        yaxis="y1"
    ))
    # Gestapelte Balken: Prozent-Anteile
    fig.add_trace(go.Bar(
        x=spot_pct.index,
        y=spot_pct,
        name="Spot (%)",
        marker_opacity=0.5,
        yaxis="y2"
    ))
    fig.add_trace(go.Bar(
        x=reg_pct.index,
        y=reg_pct,
        name="Regel (%)",
        marker_opacity=0.5,
        yaxis="y2"
    ))

    # 6) Layout konfigurieren
    fig.update_layout(
        title_text=f"Variable Kosten & Anteile {start} bis {end} (pro Intervall)",
        xaxis=dict(range=xaxis_range, title="Zeit"),
        yaxis=dict(title="Kosten per Intervall (EUR)"),
        yaxis2=dict(
            title="Anteil (%)",
            overlaying="y",
            side="right",
            range=[0, 100]
        ),
        barmode="stack",
        legend=dict(traceorder="normal"),
        transition_duration=300
    )
    return fig