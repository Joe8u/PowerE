# src/dashboard/components/details/graphs/cost_graphs.py

from dash import dcc
import plotly.express as px
import pandas as pd

def cost_graph():
    """
    DCC‐Graph‐Component für die Appliance‐Kosten (Spot vs. Regel).
    """
    return dcc.Graph(id="cost-graph")

def make_cost_figure(
    df_load: pd.DataFrame,
    df_spot: pd.DataFrame,
    df_reg: pd.DataFrame,
    start: str,
    end: str
):
    """
    Berechnet gestapelte Spot‐ vs. Regel‐Kosten für die Summe aller Appliances.
    x-Achse: Zeit
    y-Achse: EUR
    """
    # 1) Gesamtkonsum pro Intervall (kW als Proxy für kWh)
    cons = df_load.sum(axis=1)

    # 2) Spot‐ und Regel‐Preise auf exact denselben Index bringen
    spot_prices = df_spot["price_eur_mwh"].reindex(cons.index, fill_value=0)
    reg_prices  = df_reg["avg_price_eur_mwh"].reindex(cons.index, fill_value=0)

    # 3) Kosten‐Beiträge
    spot_cost = cons * spot_prices
    reg_cost  = cons * reg_prices

    # 4) DataFrame zusammenpacken
    dfc = pd.DataFrame({
        "timestamp":     cons.index,
        "Spot-Kosten":   spot_cost,
        "Regel-Kosten":  reg_cost,
    })

    # 5) In langes Format transformieren
    dfm = dfc.melt(
        id_vars="timestamp",
        value_vars=["Spot-Kosten", "Regel-Kosten"],
        var_name="Kostenart",
        value_name="EUR"
    )

    # 6) Gestapeltes Balkendiagramm
    fig = px.bar(
        dfm,
        x="timestamp",
        y="EUR",
        color="Kostenart",
        title=f"Variable Kosten {start} bis {end}",
        labels={
            "timestamp": "Zeit",
            "EUR":       "Kosten (EUR)",
            "Kostenart":"Beitrag"
        }
    )
    fig.update_layout(
        barmode="stack",
        transition_duration=300,
    )
    return fig