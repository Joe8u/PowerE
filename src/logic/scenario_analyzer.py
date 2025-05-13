# src/logic/scenario_analyzer.py
import pandas as pd
import numpy as np
import datetime # Für pd.Timedelta und Typ-Annotationen

# Importiere deine bereits erstellten Logik-Bausteine
from .load_shifting_simulation import run_load_shifting_simulation
from .cost.spot_market_costs import calculate_spot_market_costs
from .cost.dr_incentive_costs import calculate_dr_incentive_costs
from .cost.ancillary_service_costs import calculate_mfrr_savings_opportunity # Korrekter Funktionsname

def _calculate_interval_duration_h(time_index: pd.DatetimeIndex) -> float:
    """Hilfsfunktion zur robusten Bestimmung der Intervalldauer in Stunden."""
    if time_index is None or not isinstance(time_index, pd.DatetimeIndex) or len(time_index) < 2:
        print("[WARNUNG] _calculate_interval_duration_h: Ungültiger Zeitindex oder weniger als 2 Punkte. Nehme 0.25h an.")
        return 0.25 # Annahme: 15 Minuten
    
    diffs_seconds = pd.Series(time_index).diff().dropna().dt.total_seconds()
    if not diffs_seconds.empty:
        median_diff_seconds = diffs_seconds.median()
        if median_diff_seconds > 0:
            return median_diff_seconds / 3600.0
    
    print("[WARNUNG] _calculate_interval_duration_h: Konnte Intervalldauer nicht aus Index ableiten, nehme 0.25h an.")
    return 0.25

def _derive_average_incentive_payout_rate_eur_per_kwh(
    shifted_energy_per_device_kwh: dict,
    df_load_profiles_for_monthly_avg: pd.DataFrame,
    interval_duration_h: float,
    offered_incentive_for_event_pct: float,
    avg_household_electricity_price_eur_kwh: float,
    assumed_dr_events_per_month: int
) -> float:
    """
    Berechnet den durchschnittlichen Auszahlungsbetrag (Kosten für DR-Programm) pro kWh
    für das aktuelle DR-Event.
    """
    if not shifted_energy_per_device_kwh or sum(shifted_energy_per_device_kwh.values()) <= 0:
        return 0.0

    total_monetary_rebate_for_event_eur = 0.0
    total_energy_shifted_in_event_kwh = sum(shifted_energy_per_device_kwh.values())
    
    num_days_in_profile = 1.0
    if not df_load_profiles_for_monthly_avg.empty and isinstance(df_load_profiles_for_monthly_avg.index, pd.DatetimeIndex) and len(df_load_profiles_for_monthly_avg.index) > 1:
        duration_of_profile_td = (df_load_profiles_for_monthly_avg.index.max() - df_load_profiles_for_monthly_avg.index.min())
        num_days_in_profile = max(1.0, duration_of_profile_td.total_seconds() / (24 * 3600.0))
    elif not df_load_profiles_for_monthly_avg.empty: # Nur ein Datenpunkt im Profil
        print("[WARNUNG] _derive_average_incentive_payout_rate: df_load_profiles_for_monthly_avg hat nur einen Datenpunkt. Monatsverbrauchsschätzung ist ungenau.")
        # num_days_in_profile bleibt 1.0 (oder eine andere Annahme treffen)

    for device, energy_shifted_this_event_dev in shifted_energy_per_device_kwh.items():
        if energy_shifted_this_event_dev <= 0:
            continue

        if device not in df_load_profiles_for_monthly_avg.columns:
            print(f"[WARNUNG] _derive_average_incentive_payout_rate: Gerät {device} nicht in Lastprofilen für Monatsdurchschnitt gefunden.")
            continue
            
        total_energy_dev_in_profile_kwh = df_load_profiles_for_monthly_avg[device].sum() * interval_duration_h
        avg_daily_energy_dev_kwh = total_energy_dev_in_profile_kwh / num_days_in_profile
        monthly_energy_dev_kwh = avg_daily_energy_dev_kwh * 30.4375

        monthly_device_cost_eur = monthly_energy_dev_kwh * avg_household_electricity_price_eur_kwh
        device_monthly_rebate_eur = monthly_device_cost_eur * offered_incentive_for_event_pct
        device_rebate_per_event_eur = device_monthly_rebate_eur / assumed_dr_events_per_month
        
        total_monetary_rebate_for_event_eur += device_rebate_per_event_eur

    if total_energy_shifted_in_event_kwh > 0:
        avg_payout_rate_eur_per_kwh = total_monetary_rebate_for_event_eur / total_energy_shifted_in_event_kwh
        print(f"[INFO] _derive_average_incentive_payout_rate: Berechneter Anreizkostensatz = {avg_payout_rate_eur_per_kwh:.4f} EUR/kWh")
        return avg_payout_rate_eur_per_kwh
    else:
        return 0.0

def evaluate_dr_scenario(
    df_load_to_simulate: pd.DataFrame,          # Disaggregierte Lastprofile NUR der zu simulierenden Geräte
    shift_metrics: dict,                        # Ergebnisse aus Q9
    df_participation_curve_q10: pd.DataFrame,   # Ergebnisse aus Q10
    event_parameters: dict,                     # Von der UI: start_time, end_time, required_duration_hours, incentive_percentage
    simulation_assumptions: dict,               # reality_discount_factor, payback_model
    df_spot_prices_eur_mwh: pd.Series,          # Spotpreise (Series mit Zeitindex)
    df_reg_original_data: pd.DataFrame,         # Regelenergiedaten (DataFrame mit Zeitindex)
    cost_model_assumptions: dict                # z.B. avg_household_price_eur_kwh, assumed_dr_events_per_month, as_displacement_factor
) -> dict:
    """
    Orchestriert die physische Simulation und die ökonomische Bewertung eines DR-Szenarios.
    """
    print(f"\n[SCENARIO_ANALYZER] Starte evaluate_dr_scenario für Event: {event_parameters.get('start_time')} - {event_parameters.get('end_time')}")

    if df_load_to_simulate.empty:
        print("[SCENARIO_ANALYZER] df_load_to_simulate ist leer. Breche Analyse ab.")
        # Sinnvolle leere/Null-Werte für alle erwarteten Rückgabeschlüssel zurückgeben
        return {
            "value_added_eur": 0.0, "baseline_spot_costs_eur": 0.0, "scenario_spot_costs_eur": 0.0,
            "dr_program_costs_eur": 0.0, "ancillary_service_savings_eur": 0.0,
            "original_aggregated_load_kw": pd.Series(dtype=float),
            "final_shifted_aggregated_load_kw": pd.Series(dtype=float),
            "df_shiftable_per_appliance": pd.DataFrame(columns=df_load_to_simulate.columns, dtype=float),
            "df_payback_per_appliance": pd.DataFrame(columns=df_load_to_simulate.columns, dtype=float),
            "total_shifted_energy_kwh_event": 0.0,
            "shifted_energy_per_device_kwh_event": {},
            "average_payout_rate_eur_per_kwh_event": 0.0
        }

    # 0. Intervalldauer bestimmen
    interval_duration_h = _calculate_interval_duration_h(df_load_to_simulate.index)
    if interval_duration_h <= 0:
        print("[FEHLER] Intervalldauer konnte nicht bestimmt werden oder ist ungültig.")
        # TODO: Fehlerbehandlung verbessern, evtl. Exception werfen oder spezifischeres Fehlerobjekt zurückgeben
        return {"error": "Invalid interval duration"} 

    # 1. Physische Simulation durchführen
    sim_output = run_load_shifting_simulation(
        df_load_profiles=df_load_to_simulate, # Bereits gefiltert auf relevante Geräte
        shift_metrics=shift_metrics,
        df_participation_curve_q10=df_participation_curve_q10,
        event_parameters=event_parameters,
        simulation_assumptions=simulation_assumptions
    )
    
    # Sicherstellen, dass die Ergebnis-DataFrames den vollen Index von df_load_to_simulate haben
    # und die korrekten Spalten, falls die Simulation leere Ergebnisse für manche Geräte liefert.
    base_index_cols_for_empty = (df_load_to_simulate.index, df_load_to_simulate.columns)
    
    df_shiftable_per_appliance = sim_output.get("df_shiftable_per_appliance", 
                                             pd.DataFrame(0.0, index=base_index_cols_for_empty[0], columns=base_index_cols_for_empty[1]))
    df_payback_per_appliance = sim_output.get("df_payback_per_appliance", 
                                           pd.DataFrame(0.0, index=base_index_cols_for_empty[0], columns=base_index_cols_for_empty[1]))
    total_shifted_energy_kwh_event = sim_output.get("total_shifted_energy_kwh", 0.0)
    shifted_energy_per_device_kwh_event = sim_output.get("shifted_energy_per_device_kwh", {})

    # 2. Aggregierte Lastprofile erstellen
    original_aggregated_load_kw = df_load_to_simulate.sum(axis=1)
    
    # Sicherstellen, dass die Shift- und Payback-DataFrames mit original_aggregated_load_kw ausgerichtet sind
    # 1. Zuerst über die Geräte (axis=1) summieren, um eine Series zu erhalten
    shift_sum_kw_series = df_shiftable_per_appliance.sum(axis=1)
    # 2. Dann diese Series an den Index von original_aggregated_load_kw anpassen
    shift_sum_kw = shift_sum_kw_series.reindex_like(original_aggregated_load_kw).fillna(0.0)
    
    payback_sum_kw_series = df_payback_per_appliance.sum(axis=1)
    payback_sum_kw = payback_sum_kw_series.reindex_like(original_aggregated_load_kw).fillna(0.0)
    
    final_shifted_aggregated_load_kw = original_aggregated_load_kw - shift_sum_kw + payback_sum_kw


    # 3. Kosten berechnen
    # 3a. Spotmarktkosten
    baseline_spot_costs_eur = calculate_spot_market_costs(
        original_aggregated_load_kw,
        df_spot_prices_eur_mwh # df_spot_prices_eur_mwh ist bereits eine Series
    )
    scenario_spot_costs_eur = calculate_spot_market_costs(
        final_shifted_aggregated_load_kw,
        df_spot_prices_eur_mwh
    )
    spot_market_savings_eur = baseline_spot_costs_eur - scenario_spot_costs_eur

    # 3b. DR-Anreizkosten
    avg_payout_rate_eur_kwh = _derive_average_incentive_payout_rate_eur_per_kwh(
        shifted_energy_per_device_kwh_event,
        df_load_to_simulate, # Profile, die zur Simulation verwendet wurden für Monatsdurchschnitt
        interval_duration_h,
        event_parameters['incentive_percentage'],
        cost_model_assumptions['avg_household_electricity_price_eur_kwh'],
        cost_model_assumptions['assumed_dr_events_per_month']
    )
    dr_program_costs_eur = calculate_dr_incentive_costs(
        total_shifted_energy_kwh_event,
        avg_payout_rate_eur_kwh
    )

    # 3c. Regelenergiekosten/-einsparungen
    # Aggregierte Reduktion für Regelenergie-Einsparungsberechnung
    P_shiftable_total_kw_series = df_shiftable_per_appliance.sum(axis=1).reindex_like(original_aggregated_load_kw).fillna(0.0)
    as_savings_eur = calculate_mfrr_savings_opportunity( # Korrekter Funktionsname
        df_reg_original_data,
        P_shiftable_total_kw_series, 
        interval_duration_h,
        cost_model_assumptions.get('as_displacement_factor', 0.1)
    )

    # 4. "Value Added" berechnen
    value_added_eur = spot_market_savings_eur + as_savings_eur - dr_program_costs_eur
    
    # Print-Ausgaben für Debugging (wie im vorherigen Entwurf)
    print(f"[SCENARIO_ANALYZER] Baseline Spot Kosten: {baseline_spot_costs_eur:.2f} EUR")
    # ... (weitere Prints) ...
    print(f"[SCENARIO_ANALYZER] Value Added: {value_added_eur:.2f} EUR")

    return {
        "value_added_eur": value_added_eur,
        "baseline_spot_costs_eur": baseline_spot_costs_eur,
        "scenario_spot_costs_eur": scenario_spot_costs_eur,
        "dr_program_costs_eur": dr_program_costs_eur,
        "ancillary_service_savings_eur": as_savings_eur,
        "original_aggregated_load_kw": original_aggregated_load_kw,
        "final_shifted_aggregated_load_kw": final_shifted_aggregated_load_kw,
        "df_shiftable_per_appliance": df_shiftable_per_appliance,
        "df_payback_per_appliance": df_payback_per_appliance,
        "total_shifted_energy_kwh_event": total_shifted_energy_kwh_event,
        "shifted_energy_per_device_kwh_event": shifted_energy_per_device_kwh_event,
        "average_payout_rate_eur_per_kwh_event": avg_payout_rate_eur_kwh
    }