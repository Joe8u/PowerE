# src/dashboard/components/details/callbacks.py

from dash import callback, Input, Output
import datetime
import pandas as pd # Bleibt für pd.Timestamp etc.

# Datenlader (bleiben)
from data_loader.lastprofile                 import load_appliances, list_appliances
from data_loader.tertiary_regulation_loader  import load_regulation_range
from data_loader.spot_price_loader           import load_spot_price_range

# UI-Komponenten und Basis-Grafikfunktionen (bleiben)
from dashboard.components.details.controls            import ALL
from dashboard.components.details.graphs.lastprofile_graphs import make_load_figure
from dashboard.components.details.graphs.market_graphs     import make_regulation_figure
from dashboard.components.details.graphs.cost_graphs       import make_cost_info
from dashboard.components.details.graphs.cost2_graphs      import make_cost2_figure # Beachte die Argumente beim Aufruf!
from dashboard.components.details.graphs.consumption_graphs import make_consumption_info
from dashboard.components.details.graphs.regulation_volume_graphs import make_regulation_volume_info

# Umfrage-Grafiken und Datenbeschaffung (bleiben für die Detail-Seite)
from dashboard.components.details.survey_graphs.participation_graphs import make_participation_curve, get_participation_df
from dashboard.components.details.survey_graphs.shift_duration_all import calculate_shift_potential_data

# --- GELÖSCHTE IMPORTS ---
# from dashboard.components.details.graphs.per_appliance_comparison_graph import make_per_appliance_comparison_figure
# from dashboard.components.details.callback_helpers import orchestrate_simulation_processing
# from logic.load_shifting_simulation import run_load_shifting_simulation


@callback(
    # Outputs: "per-appliance-comparison-graph" wurde entfernt
    Output("time-series-graph",      "figure"),
    Output("regulation-graph",        "figure"),
    Output("spot-cost-total",         "children"),
    Output("reg-cost-total",          "children"),
    Output("total-consumption",       "children"),
    Output("total-regulation-volume", "children"),
    Output("cost2-graph",             "figure"),
    Output("participation-curve",     "figure"),
    Output("shift-all-graph",         "figure"),
    # Output("per-appliance-comparison-graph", "figure"), # <<< GELÖSCHT

    # Styles (bleiben gleich)
    Output("load-container",          "style"),
    Output("market-container",        "style"),
    Output("cost2-graph-container",   "style"),
    Output("consumption-container",   "style"),
    Output("regulation-volume-container","style"),

    # Inputs (bleiben gleich)
    Input("appliance-dropdown",       "value"),
    Input("cumulative-checkbox",      "value"),
    Input("date-picker",              "start_date"),
    Input("date-picker",              "end_date"),
    Input("graph-selector",           "value"),
)
def update_graph(selected_values, cumulative_flag, start, end, selected_graphs): # Parameterliste ohne DR-Event Inputs
    # Sichtbarkeit pro Grafik (bleibt)
    style_load          = {} if "show_load"            in selected_graphs else {"display":"none"}
    style_market        = {} if "show_market"          in selected_graphs else {"display":"none"}
    style_cost2         = {} if "show_cost2"           in selected_graphs else {"display":"none"}
    style_consumption   = {} if "show_consumption"     in selected_graphs else {"display":"none"}
    style_regulation_vol= {} if "show_regulation_volume" in selected_graphs else {"display":"none"}

    # 1) Start‐ und End‐Datum parsen (bleibt)
    start_dt = datetime.datetime.fromisoformat(start)
    end_dt   = datetime.datetime.fromisoformat(end)

    # 2) Appliance‐Auswahl normalisieren (bleibt)
    all_appliances_list = list_appliances(2024)
    if not selected_values or ALL in selected_values:
        appliances_selected = all_appliances_list
    else:
        appliances_selected = selected_values

    # --- BASIS-DATEN LADEN --- (bleibt)
    df_load_filt = load_appliances(
        appliances=appliances_selected, start=start_dt, end=end_dt, year=2024
    )
    df_reg  = load_regulation_range(start_dt, end_dt)
    df_spot = load_spot_price_range(start_dt, end_dt)

    # --- KARTEN (KPIs) ERSTELLEN --- (bleibt)
    cost_filt = make_cost_info(df_load_filt, df_spot, df_reg)
    cons_card = make_consumption_info(df_load_filt)
    reg_vol_card = make_regulation_volume_info(df_reg)
    df_load_all_for_costs = load_appliances(
        appliances=all_appliances_list, start=start_dt, end=end_dt, year=2024
    )
    cost_all = make_cost_info(df_load_all_for_costs, df_spot, df_reg)

    # --- UMFRAGEDATEN FÜR DIE DETAIL-SEITEN-GRAFIKEN LADEN --- (bleibt)
    shift_data_results = calculate_shift_potential_data()
    # shift_metrics = shift_data_results["metrics"] # Wird hier nicht mehr für Simulation benötigt
    fig_shift = shift_data_results["figure"] 

    # df_participation_curve_q10 = get_participation_df() # Wird hier nicht mehr für Simulation benötigt
    fig_part = make_participation_curve() # Ruft get_participation_df intern auf


    # --- Block für SIMULATIONS-ORCHESTRIERUNG wurde GELÖSCHT ---


    # --- FINALE GRAFIKEN ERSTELLEN (OHNE SIMULATIONS-SPEZIFISCHE ANPASSUNGEN HIER) ---
    fig_load = make_load_figure( # Aufruf mit ursprünglichen Parametern
        df_load_filt,
        appliances_selected,
        start,
        end,
        ("cumulative" in cumulative_flag)
    )
    
    fig_reg = make_regulation_figure( # Benötigt fig_load für Achsenbereich
        df_reg, df_spot, fig_load.layout.xaxis.range, start, end
    )

    # Alternative Kosten‐Grafik (ohne die verschiebbare Potenzialkurve auf dieser Seite)
    fig_cost2 = make_cost2_figure( # Aufruf mit ursprünglichen 7 Parametern
        df_load_filt, appliances_selected, df_spot, df_reg,
        fig_load.layout.xaxis.range, start, end
        # Das 8. Argument P_shiftable_total_series_for_cost2 wird hier nicht mehr übergeben
    )

    # --- Aufruf von make_per_appliance_comparison_figure wurde GELÖSCHT ---

    return (
        fig_load,
        fig_reg,
        cost_filt["spot"],
        cost_all["reg"],
        cons_card,
        reg_vol_card,
        fig_cost2,
        fig_part,
        fig_shift,
        # fig_per_appliance_comparison, # <<< GELÖSCHT
        style_load,
        style_market,
        style_cost2,
        style_consumption,
        style_regulation_vol,
    )