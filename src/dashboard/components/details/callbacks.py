# src/dashboard/components/details/callbacks.py

from dash import callback, Input, Output
import datetime

from data_loader.lastprofile                 import load_appliances, list_appliances
from data_loader.tertiary_regulation_loader  import load_regulation_range
from data_loader.spot_price_loader           import load_spot_price_range

from dashboard.components.details.controls            import ALL
from dashboard.components.details.graphs.lastprofile_graphs import make_load_figure
from dashboard.components.details.graphs.market_graphs     import make_regulation_figure
from dashboard.components.details.graphs.cost_graphs       import cost_graph, make_cost_info
from dashboard.components.details.graphs.cost2_graphs     import cost2_graph, make_cost2_figure

@callback(
    Output("time-series-graph", "figure"),
    Output("regulation-graph",   "figure"),
    Output("spot-cost-total",    "children"),
    Output("reg-cost-total",     "children"),
    Output("cost2-graph",        "figure"),
    Input("appliance-dropdown",  "value"),
    Input("cumulative-checkbox", "value"),
    Input("date-picker",         "start_date"),
    Input("date-picker",         "end_date"),
)
def update_graph(selected_values, cumulative_flag, start, end):
    # 1) Start‐ und End‐Datum parsen
    start_dt = datetime.datetime.fromisoformat(start)
    end_dt   = datetime.datetime.fromisoformat(end)

    # 2) Appliance‐Auswahl normalisieren
    if not selected_values or ALL in selected_values:
        appliances = list_appliances(2024)
    else:
        appliances = selected_values

    # 3) Lastprofil laden und Linie(n) zeichnen
    df_load = load_appliances(
        appliances=appliances,
        start=start_dt,
        end=end_dt,
        year=2024
    )
    fig_load = make_load_figure(
        df_load,
        appliances,
        start,
        end,
        cumulative=("cumulative" in cumulative_flag)
    )

    # 4) tertiäre Regelleistung laden
    df_reg  = load_regulation_range(start_dt, end_dt)

    # 5) Spot‐Preise laden
    df_spot = load_spot_price_range(start_dt, end_dt)

    # 6) Volumen + Preise auf einem gemeinsamen Zeitbereich plotten
    fig_reg = make_regulation_figure(
        df_reg,
        df_spot,
        fig_load.layout.xaxis.range,  # gemeinsame X‐Achse
        start,
        end
    )

    # 7) Kosten-Info (Spot- und Regelkosten)
    cost_info = make_cost_info(df_load, df_spot, df_reg)

    # 8) Alternative Kosten‐Grafik (kumulierte Kosten + Prozentanteile)
    fig_cost2 = make_cost2_figure(
        df_load,
        appliances,
        df_spot,
        df_reg,
        fig_load.layout.xaxis.range,  # geteilte Zeitachse
        start,
        end
    )

    return fig_load, fig_reg, cost_info["spot"], cost_info["reg"], fig_cost2