# src/dashboard/components/scenarios/callbacks.py
from dash import callback, Input, Output, State, no_update, go # go importieren für leere Figur
import pandas as pd
import datetime

# Datenlader
from data_loader.lastprofile import load_appliances # list_appliances hier nicht direkt im Callback nötig

# Umfragedaten-Verarbeitung
from dashboard.components.details.survey_graphs.participation_graphs import get_participation_df
from dashboard.components.details.survey_graphs.shift_duration_all import calculate_shift_potential_data

# Die Simulationsfunktion aus dem logic-Ordner
from logic.load_shifting_simulation import run_load_shifting_simulation # <<< An den Anfang verschieben

# Die Grafikfunktion für den per-Appliance-Vergleich (aus dem neuen scenarios/graphs Ordner)
from .graphs.per_appliance_comparison_graph import make_per_appliance_comparison_figure
# Der Import von orchestrate_simulation_processing wird hier nicht mehr benötigt,
# da wir die Logik direkt in diesem Callback implementieren, um die dynamischen UI-Inputs zu verwenden.


@callback(
    Output("per-appliance-comparison-graph", "figure"),
    Input("scenario-run-button", "n_clicks"),
    State("scenario-appliance-dropdown", "value"),
    State("scenario-date-picker", "start_date"),
    State("scenario-date-picker", "end_date"),
    State("scenario-dr-start-hour", "value"),
    State("scenario-dr-duration-hours", "value"),
    State("scenario-dr-incentive-pct", "value"),
)
def update_scenario_simulation_graph(
    n_clicks,
    selected_appliances,
    start_date_str,
    end_date_str,
    dr_start_hour,
    dr_duration_hours,
    dr_incentive_pct
):
    if n_clicks == 0 or n_clicks is None:
        return no_update

    # --- 1. Eingaben parsen und vorbereiten ---
    start_dt = datetime.datetime.fromisoformat(start_date_str)
    end_dt = datetime.datetime.fromisoformat(end_date_str)
    
    if not selected_appliances:
        print("Keine Geräte für Simulation ausgewählt.")
        # go.Figure() hier direkt importieren oder plotly.graph_objects als go
        # Alternativ: Am Anfang der Datei 'import plotly.graph_objects as go'
        # Für den Moment, da 'go' nicht importiert ist, nutze 'no_update' oder eine leere dict für figure
        return {"data": [], "layout": {}} # Leere Figur

    df_load_filt = load_appliances(
        appliances=selected_appliances, start=start_dt, end=end_dt, year=2024
    )
    if df_load_filt.empty:
        print("Keine Lastdaten für ausgewählten Zeitraum/Geräte gefunden.")
        return {"data": [], "layout": {}} # Leere Figur


    # --- 3. Umfragedaten für Simulation laden ---
    shift_data_results = calculate_shift_potential_data()
    shift_metrics = shift_data_results["metrics"]
    df_participation_curve_q10 = get_participation_df()

    # --- 4. Event-Parameter und Simulationsannahmen erstellen ---
    try:
        dr_start_hour_int = int(dr_start_hour) if dr_start_hour is not None else 14 # Fallback
        dr_duration_float = float(dr_duration_hours) if dr_duration_hours is not None else 2.0 # Fallback
        dr_incentive_float = float(dr_incentive_pct) if dr_incentive_pct is not None else 15.0 # Fallback

        event_start_actual_dt = pd.Timestamp(f"{start_date_str} {dr_start_hour_int:02d}:00:00")
        event_end_actual_dt = event_start_actual_dt + pd.Timedelta(hours=dr_duration_float)
    except Exception as e:
        print(f"Fehler beim Erstellen der Event-Zeiten: {e}")
        event_start_actual_dt = start_dt + pd.Timedelta(hours=14)
        event_end_actual_dt = event_start_actual_dt + pd.Timedelta(hours=2.0)

    event_parameters = {
        'start_time': event_start_actual_dt,
        'end_time': event_end_actual_dt,
        'required_duration_hours': dr_duration_float,
        'incentive_percentage': dr_incentive_float / 100.0
    }
    simulation_assumptions = {
        'reality_discount_factor': 0.7,
        'payback_model': {'type': 'uniform_after_event', 'duration_hours': dr_duration_float, 'delay_hours': 0.25}
    }

    # Vorbereitung für run_load_shifting_simulation
    sim_appliances = [a for a in selected_appliances if a in shift_metrics and a in df_load_filt.columns]
    df_load_for_simulation = df_load_filt[sim_appliances].copy() if sim_appliances else pd.DataFrame()

    # Initialisiere Ergebnis-DataFrames
    base_index = df_load_filt.index if not df_load_filt.empty else None
    # Stelle sicher, dass sim_appliances nicht leer ist für die Spalten, oder verwende df_load_for_simulation.columns
    cols_for_template = df_load_for_simulation.columns if not df_load_for_simulation.empty else []
    empty_df_template = pd.DataFrame(index=base_index, columns=cols_for_template, dtype=float).fillna(0.0)
    
    df_shiftable_per_appliance_res = empty_df_template.copy()
    df_payback_per_appliance_res = empty_df_template.copy()

    if not df_load_for_simulation.empty:
        simulation_output = run_load_shifting_simulation(
            df_load_profiles=df_load_for_simulation,
            shift_metrics=shift_metrics,
            df_participation_curve_q10=df_participation_curve_q10,
            event_parameters=event_parameters,
            simulation_assumptions=simulation_assumptions
        )
        temp_shiftable = simulation_output.get("df_shiftable_per_appliance")
        if temp_shiftable is not None:
            df_shiftable_per_appliance_res = temp_shiftable.reindex_like(empty_df_template).fillna(0.0)

        temp_payback = simulation_output.get("df_payback_per_appliance")
        if temp_payback is not None:
            df_payback_per_appliance_res = temp_payback.reindex_like(empty_df_template).fillna(0.0)

    # --- 5. Ergebnis-Grafik erstellen ---
    fig = make_per_appliance_comparison_figure(
        df_load_original_disaggregated=df_load_filt,
        df_shiftable_per_appliance=df_shiftable_per_appliance_res,
        df_payback_per_appliance=df_payback_per_appliance_res,
        appliances_to_plot=sim_appliances # Nur die tatsächlich simulierten und im Lastprofil vorhandenen Geräte plotten
    )

    return fig