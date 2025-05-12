# src/dashboard/components/details/callbacks.py

from dash import callback, Input, Output
import datetime
import pandas as pd # Importiert

# Deine bestehenden Imports für Datenlader
from data_loader.lastprofile                 import load_appliances, list_appliances
from data_loader.tertiary_regulation_loader  import load_regulation_range
from data_loader.spot_price_loader           import load_spot_price_range

# Deine bestehenden Imports für UI-Komponenten und Basis-Grafikfunktionen
from dashboard.components.details.controls            import ALL
from dashboard.components.details.graphs.lastprofile_graphs import make_load_figure
from dashboard.components.details.graphs.market_graphs     import make_regulation_figure
from dashboard.components.details.graphs.cost_graphs       import make_cost_info
from dashboard.components.details.graphs.cost2_graphs      import make_cost2_figure
from dashboard.components.details.graphs.consumption_graphs import make_consumption_info
from dashboard.components.details.graphs.regulation_volume_graphs import make_regulation_volume_info

# Imports für Umfrage-Grafiken und Datenbeschaffung
from dashboard.components.details.survey_graphs.participation_graphs import make_participation_curve, get_participation_df
from dashboard.components.details.survey_graphs.shift_duration_all import calculate_shift_potential_data

# NEU: Import für die per-appliance Vergleichsgrafik
from dashboard.components.details.graphs.per_appliance_comparison_graph import make_per_appliance_comparison_figure

# NEU: Import der ausgelagerten Orchestrierungsfunktion
# Stelle sicher, dass der Pfad korrekt ist. Wenn callback_helpers.py im selben Ordner "details" liegt:
# from .callback_helpers import orchestrate_simulation_processing
# Wenn es in src/dashboard/components/details/callback_helpers.py liegt:
from dashboard.components.details.callback_helpers import orchestrate_simulation_processing


@callback(
    # Outputs: Füge das Output für die neue Grafik hinzu
    Output("time-series-graph",      "figure"),
    Output("regulation-graph",        "figure"),
    Output("spot-cost-total",         "children"),
    Output("reg-cost-total",          "children"),
    Output("total-consumption",       "children"),
    Output("total-regulation-volume", "children"),
    Output("cost2-graph",             "figure"),
    Output("participation-curve",     "figure"),
    Output("shift-all-graph",         "figure"),
    Output("per-appliance-comparison-graph", "figure"), # <<< NEUES OUTPUT

    # Styles (bleiben gleich)
    Output("load-container",          "style"),
    Output("market-container",        "style"),
    Output("cost2-graph-container",   "style"),
    Output("consumption-container",   "style"),
    Output("regulation-volume-container","style"),

    # Inputs (bleiben vorerst gleich, DR-Event Parameter kommen später hinzu)
    Input("appliance-dropdown",       "value"),
    Input("cumulative-checkbox",      "value"),
    Input("date-picker",              "start_date"),
    Input("date-picker",              "end_date"),
    Input("graph-selector",           "value"),
)
def update_graph(selected_values, cumulative_flag, start, end, selected_graphs,):
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
    all_appliances_list = list_appliances(2024) # Umbenannt für Klarheit
    if not selected_values or ALL in selected_values:
        appliances_selected = all_appliances_list
    else:
        appliances_selected = selected_values

    # --- BASIS-DATEN LADEN ---
    df_load_filt = load_appliances(
        appliances=appliances_selected, start=start_dt, end=end_dt, year=2024
    )
    df_reg  = load_regulation_range(start_dt, end_dt)
    df_spot = load_spot_price_range(start_dt, end_dt)

    # --- KARTEN (KPIs) ERSTELLEN ---
    cost_filt = make_cost_info(df_load_filt, df_spot, df_reg)
    cons_card = make_consumption_info(df_load_filt)
    reg_vol_card = make_regulation_volume_info(df_reg)
    df_load_all_for_costs = load_appliances( # Eigene Variable für Klarheit
        appliances=all_appliances_list, start=start_dt, end=end_dt, year=2024
    )
    cost_all = make_cost_info(df_load_all_for_costs, df_spot, df_reg)

    # --- UMFRAGEDATEN FÜR SIMULATION UND GRAFIKEN LADEN ---
    shift_data_results = calculate_shift_potential_data()
    shift_metrics = shift_data_results["metrics"]
    fig_shift = shift_data_results["figure"]

    df_participation_curve_q10 = get_participation_df()
    # make_participation_curve ruft get_participation_df intern auf, daher kein Argument nötig
    fig_part = make_participation_curve()


    # --- SIMULATIONS-ORCHESTRIERUNG AUFRUFEN ---
    # Später hier die echten UI-Inputs für DR-Parameter übergeben anstatt `start`
    sim_processing_results = orchestrate_simulation_processing(
        df_load_filt,
        appliances_selected, # Die aktuell vom Nutzer ausgewählten Geräte
        shift_metrics,
        df_participation_curve_q10,
        start_date_str_for_event=start # 'start' ist der String vom DatePicker für Test-Event
        # Zukünftige DR-Event UI Input Werte hier übergeben
    )

    # Ergebnisse aus der Orchestrierungsfunktion extrahieren
    df_shiftable_per_appliance = sim_processing_results["df_shiftable_per_appliance"]
    df_payback_per_appliance = sim_processing_results["df_payback_per_appliance"]
    original_aggregated_load_kw = sim_processing_results["original_aggregated_load_kw"]
    shifted_total_load_kw = sim_processing_results["shifted_total_load_kw"]
    P_shiftable_total_series_for_cost2 = sim_processing_results["P_shiftable_total_series_for_cost2"]
    sim_appliances_used_in_sim = sim_processing_results["sim_appliances_actually_used"]


    # --- FINALE GRAFIKEN ERSTELLEN ---
    # Haupt-Lastprofil-Grafik (kann jetzt Original und simuliertes Gesamtprofil anzeigen)
    fig_load = make_load_figure(
        df_load_filt, # Das ist das df_load, das deine Funktion erwartet
        appliances_selected,
        start,
        end,
        ("cumulative" in cumulative_flag) # cumulative als Boolean übergeben
    )
    
    # Markt-Grafik (benötigt fig_load für Achsenbereich)
    fig_reg = make_regulation_figure(
        df_reg, df_spot, fig_load.layout.xaxis.range, start, end
    )

    # Alternative Kosten‐Grafik
    fig_cost2 = make_cost2_figure(
        df_load_filt, appliances_selected, df_spot, df_reg,
        fig_load.layout.xaxis.range, start, end,
        P_shiftable_total_series_for_cost2 # Aggregiertes Reduktionspotenzial
    )

    # NEU: Grafik für per-appliance Vergleich erstellen
    fig_per_appliance_comparison = make_per_appliance_comparison_figure(
        df_load_original_disaggregated=df_load_filt, # Die gefilterten Originalprofile
        df_shiftable_per_appliance=df_shiftable_per_appliance,
        df_payback_per_appliance=df_payback_per_appliance,
        appliances_to_plot=sim_appliances_used_in_sim # Nur die Geräte, die auch simuliert wurden
    )

    

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
        fig_per_appliance_comparison, 
        style_load,
        style_market,
        style_cost2,
        style_consumption,
        style_regulation_vol,
    )