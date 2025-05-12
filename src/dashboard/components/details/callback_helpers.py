# src/dashboard/components/details/callback_helpers.py
import pandas as pd
import datetime # Für pd.Timedelta, falls nicht schon in pd enthalten für deine Version

# Importiere die Simulationsfunktion und ggf. andere nötige Dinge
from logic.load_shifting_simulation import run_load_shifting_simulation
# from scipy.stats import lognorm # Wird in run_load_shifting_simulation verwendet, nicht direkt hier

def orchestrate_simulation_processing(
    df_load_filt: pd.DataFrame,
    appliances_selected: list,
    shift_metrics: dict,
    df_participation_curve_q10: pd.DataFrame,
    # Parameter für die Erstellung der Test-event_parameters:
    start_date_str_for_event: str, # Der 'start'-String vom DatePicker
    # Später kommen hier die eigentlichen UI-Inputs für DR-Event-Parameter hinzu
    # z.B. dr_event_start_hour_input, dr_event_duration_input, dr_event_incentive_input
) -> dict:
    """
    Orchestriert die Vorbereitung, Durchführung und erste Aufbereitung der Lastverschiebungssimulation.
    """

    # --- DR EVENT & SIMULATIONS-PARAMETER DEFINIEREN (Testwerte) ---
    # HINWEIS: Diese Werte sollten später aus UI-Inputs kommen!
    event_start_sim_str = f"{start_date_str_for_event} 14:00:00"
    event_duration_sim_hours = 2.0
    event_incentive_sim_percentage = 0.15

    try:
        # start_dt aus dem Hauptcallback ist hier nicht direkt verfügbar,
        # wir verwenden start_date_str_for_event
        current_start_dt = pd.Timestamp(start_date_str_for_event) # Sicherstellen, dass es ein Timestamp ist
        event_start_sim_dt = pd.Timestamp(event_start_sim_str)
        event_end_sim_dt = event_start_sim_dt + pd.Timedelta(hours=event_duration_sim_hours)
    except Exception:
        current_start_dt = pd.Timestamp(datetime.date.today()) # Fallback auf heute
        event_start_sim_dt = current_start_dt + pd.Timedelta(hours=14)
        event_end_sim_dt = event_start_sim_dt + pd.Timedelta(hours=event_duration_sim_hours)
    
    event_parameters = {
        'start_time': event_start_sim_dt,
        'end_time': event_end_sim_dt,
        'required_duration_hours': event_duration_sim_hours,
        'incentive_percentage': event_incentive_sim_percentage
    }
    simulation_assumptions = {
        'reality_discount_factor': 0.7,
        'payback_model': {'type': 'uniform_after_event', 'duration_hours': 2, 'delay_hours': 0.25}
    }

    # --- DATEN FÜR SIMULATIONSFUNKTION VORBEREITEN ---
    sim_appliances = [a for a in appliances_selected if a in shift_metrics and a in df_load_filt.columns]
    df_load_for_simulation = df_load_filt[sim_appliances].copy() if sim_appliances else pd.DataFrame()

    # Initialisiere Ergebnis-DataFrames
    # Verwende df_load_filt.index für die korrekte Zeitachse, falls vorhanden
    base_index = df_load_filt.index if not df_load_filt.empty else None
    empty_df_template = pd.DataFrame(index=base_index, columns=sim_appliances, dtype=float).fillna(0.0)
    
    df_shiftable_per_appliance = empty_df_template.copy()
    df_payback_per_appliance = empty_df_template.copy()

    # --- SIMULATION DURCHFÜHREN (NUR WENN SINNVOLL) ---
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
            df_shiftable_per_appliance = temp_shiftable.reindex_like(empty_df_template).fillna(0.0)

        temp_payback = simulation_output.get("df_payback_per_appliance")
        if temp_payback is not None:
            df_payback_per_appliance = temp_payback.reindex_like(empty_df_template).fillna(0.0)

    # --- ABGELEITETE AGGREGIERTE ZEITREIHEN BERECHNEN ---
    original_aggregated_load_kw = pd.Series(dtype=float)
    shifted_total_load_kw = pd.Series(dtype=float)
    P_shiftable_total_series_for_cost2 = pd.Series(dtype=float)

    if not df_load_filt.empty and sim_appliances: # Nur wenn es was zu aggregieren gibt
        original_aggregated_load_kw = df_load_filt[sim_appliances].sum(axis=1).reindex_like(df_shiftable_per_appliance).fillna(0.0)
        
        # Summiere nur über die Spalten, die auch in sim_appliances sind, um KeyErrors zu vermeiden
        # und stelle sicher, dass die Indizes übereinstimmen
        shift_sum = df_shiftable_per_appliance[sim_appliances].sum(axis=1).reindex_like(original_aggregated_load_kw).fillna(0.0)
        payback_sum = df_payback_per_appliance[sim_appliances].sum(axis=1).reindex_like(original_aggregated_load_kw).fillna(0.0)
        
        shifted_total_load_kw = original_aggregated_load_kw - shift_sum + payback_sum
        P_shiftable_total_series_for_cost2 = shift_sum
    elif not df_load_filt.empty : # Fall: df_load_filt nicht leer, aber sim_appliances leer
        original_aggregated_load_kw = pd.Series(0.0, index=df_load_filt.index)
        shifted_total_load_kw = original_aggregated_load_kw.copy()
        P_shiftable_total_series_for_cost2 = pd.Series(0.0, index=df_load_filt.index)


    return {
        "df_shiftable_per_appliance": df_shiftable_per_appliance,
        "df_payback_per_appliance": df_payback_per_appliance,
        "original_aggregated_load_kw": original_aggregated_load_kw,
        "shifted_total_load_kw": shifted_total_load_kw,
        "P_shiftable_total_series_for_cost2": P_shiftable_total_series_for_cost2,
        "sim_appliances_actually_used": sim_appliances # Wichtig für die Grafikfunktion
    }