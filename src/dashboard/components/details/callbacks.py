# src/dashboard/components/details/callbacks.py

from dash import callback, Input, Output
import datetime

from data_loader.lastprofile                 import load_appliances, list_appliances
from data_loader.tertiary_regulation_loader  import load_regulation_range
from data_loader.spot_price_loader           import load_spot_price_range

from dashboard.components.details.controls            import ALL
from dashboard.components.details.graphs.lastprofile_graphs import make_load_figure
from dashboard.components.details.graphs.market_graphs     import make_regulation_figure
from dashboard.components.details.graphs.cost_graphs       import make_cost_info
from dashboard.components.details.graphs.cost2_graphs      import cost2_graph, make_cost2_figure
from dashboard.components.details.graphs.consumption_graphs import make_consumption_info
from dashboard.components.details.graphs.regulation_volume_graphs import make_regulation_volume_info

from dashboard.components.details.survey_graphs.participation_graphs import make_participation_curve
from dashboard.components.details.survey_graphs.shift_duration_all import make_all_shift_distributions


@callback(
    # 1–6: Figures & Cards
    Output("time-series-graph",      "figure"),
    Output("regulation-graph",        "figure"),
    Output("spot-cost-total",         "children"),
    Output("reg-cost-total",          "children"),
    Output("total-consumption",       "children"),
    Output("total-regulation-volume", "children"),
    Output("cost2-graph",             "figure"),
    Output("participation-curve",     "figure"),
    Output("shift-all-graph",         "figure"),

    # 7–11: Styles
    Output("load-container",          "style"),
    Output("market-container",        "style"),
    Output("cost2-graph-container",   "style"),
    Output("consumption-container",   "style"),
    Output("regulation-volume-container","style"),

    # 12–16: Inputs
    Input("appliance-dropdown",       "value"),
    Input("cumulative-checkbox",      "value"),
    Input("date-picker",              "start_date"),
    Input("date-picker",              "end_date"),
    Input("graph-selector",           "value"),
)
def update_graph(selected_values, cumulative_flag, start, end, selected_graphs):
    # Sichtbarkeit pro Grafik
    style_load          = {} if "show_load"            in selected_graphs else {"display":"none"}
    style_market        = {} if "show_market"          in selected_graphs else {"display":"none"}
    style_cost2         = {} if "show_cost2"           in selected_graphs else {"display":"none"}
    style_consumption   = {} if "show_consumption"     in selected_graphs else {"display":"none"}
    style_regulation_vol= {} if "show_regulation_volume" in selected_graphs else {"display":"none"}

    # 1) Start‐ und End‐Datum parsen
    start_dt = datetime.datetime.fromisoformat(start)
    end_dt   = datetime.datetime.fromisoformat(end)

    # 2) Appliance‐Auswahl normalisieren
    all_appliances = list_appliances(2024)
    if not selected_values or ALL in selected_values:
        appliances = all_appliances
    else:
        appliances = selected_values

    # 3) Gefiltertes Lastprofil laden und Linie(n) zeichnen
    df_load_filt = load_appliances(
        appliances=appliances,
        start=start_dt,
        end=end_dt,
        year=2024
    )
    fig_load = make_load_figure(
        df_load_filt,
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

    # 7a) Spot-Kosten aus gefilterten Daten
    cost_filt = make_cost_info(df_load_filt, df_spot, df_reg)

    # 7b) Gesamter Verbrauch (für neue Komponente)
    cons_card      = make_consumption_info(df_load_filt)
    reg_vol_card   = make_regulation_volume_info(df_reg)

    # 7c) Regel-Kosten aus **allen** Geräten (unabhängig vom Filter)
    df_load_all = load_appliances(
        appliances=all_appliances,
        start=start_dt,
        end=end_dt,
        year=2024
    )
    cost_all = make_cost_info(df_load_all, df_spot, df_reg)

    # 8) Alternative Kosten‐Grafik (kumulierte Kosten + Prozentanteile)
    fig_cost2 = make_cost2_figure(
        df_load_filt,
        appliances,
        df_spot,
        df_reg,
        fig_load.layout.xaxis.range,  # geteilte Zeitachse
        start,
        end
    )

    # 9) Teilnahme-Curve und Shift-Dauer
    fig_part = make_participation_curve()
    fig_shift = make_all_shift_distributions()

    return (
        # 1–6: Figures & Cards
        fig_load,
        fig_reg,
        cost_filt["spot"],
        cost_all["reg"],
        cons_card,
        reg_vol_card,
        fig_cost2,
        fig_part,
        fig_shift,

        # 7–11: Styles
        style_load,
        style_market,
        style_cost2,
        style_consumption,
        style_regulation_vol,
    )
