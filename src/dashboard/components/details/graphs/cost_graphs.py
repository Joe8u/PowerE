# src/dashboard/components/details/graphs/cost_graphs.py

from dash import html
import dash_bootstrap_components as dbc
import pandas as pd

def cost_graph():
    """
    Statt Graph: eine Row mit zwei Cards,
    in denen die Gesamtkosten stehen.
    """
    return dbc.Row(
        [
            dbc.Col(html.Div(id="spot-cost-total"), width=6),
            dbc.Col(html.Div(id="reg-cost-total"),  width=6),
        ],
        className="mb-4"
    )

def make_cost_info(
    df_load: pd.DataFrame,
    df_spot: pd.DataFrame,
    df_reg: pd.DataFrame,
):
    """
    Berechnet:
      - spot_cost_total: Summe(consumption * spot_price)
      - reg_cost_total:  Summe(consumption * reg_price)
    und gibt zwei Dash-HTML-Elemente zurück.
    """
    # 1) Verbrauch pro Intervall (kW als Proxy für kWh)
    cons = df_load.sum(axis=1)

    # 2) Preise auf denselben Index
    spot_prices = df_spot["price_eur_mwh"].reindex(cons.index, fill_value=0)
    reg_prices  = df_reg["avg_price_eur_mwh"].reindex(cons.index, fill_value=0)

    # 3) Kosten aggregieren
    spot_cost_total = (cons * spot_prices).sum()
    reg_cost_total  = (cons * reg_prices ).sum()

    # 4) Zwei Cards basteln
    spot_card = dbc.Card(
        [
            dbc.CardHeader("Gesamtkosten Spot-Preis"),
            dbc.CardBody(html.H4(f"{spot_cost_total:,.2f} €"))
        ],
        color="primary", inverse=True
    )
    reg_card = dbc.Card(
        [
            dbc.CardHeader("Gesamtkosten Regelenergie"),
            dbc.CardBody(html.H4(f"{reg_cost_total:,.2f} €"))
        ],
        color="warning", inverse=True
    )

    # 5) Gib die beiden Cards als Dict für den Callback zurück
    return {
        "spot": spot_card,
        "reg":  reg_card
    }