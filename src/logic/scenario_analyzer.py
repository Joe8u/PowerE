# src/logic/scenario_analyzer.py
import pandas as pd
import numpy as np
import datetime # Für pd.Timedelta und Typ-Annotationen

# Importiere deine Logik-Bausteine
# NEU: Importiere die respondenten-basierte Simulation aus der überarbeiteten load_shifting_simulation.py
from .load_shifting_simulation import simulate_respondent_level_load_shift 
from .cost.spot_market_costs import calculate_spot_market_costs
from .cost.dr_incentive_costs import calculate_dr_incentive_costs
from .cost.ancillary_service_costs import calculate_mfrr_savings_opportunity

def _calculate_interval_duration_h(time_index: pd.DatetimeIndex) -> float:
    """Hilfsfunktion zur robusten Bestimmung der Intervalldauer eines Zeitindex in Stunden."""
    if time_index is None or not isinstance(time_index, pd.DatetimeIndex) or len(time_index) < 2:
        print("[WARNUNG] scenario_analyzer._calculate_interval_duration_h: Ungültiger Zeitindex oder weniger als 2 Punkte. Nehme 0.25h an.")
        return 0.25 # Annahme: 15 Minuten
    
    diffs_seconds = pd.Series(time_index).diff().dropna().dt.total_seconds()
    if not diffs_seconds.empty:
        median_diff_seconds = diffs_seconds.median()
        if median_diff_seconds > 0:
            return median_diff_seconds / 3600.0
    
    print("[WARNUNG] scenario_analyzer._calculate_interval_duration_h: Konnte Intervalldauer nicht aus Index ableiten, nehme 0.25h an.")
    return 0.25

def _derive_average_incentive_payout_rate_eur_per_kwh(
    shifted_energy_per_device_kwh: dict,
    df_average_device_load_profiles_kwh: pd.DataFrame, 
    interval_duration_h: float,
    offered_incentive_for_event_pct: float, # Dies ist event_parameters['incentive_percentage'] (0-1)
    avg_household_electricity_price_eur_kwh: float,
    assumed_dr_events_per_month: int
) -> float:
    """
    Berechnet den durchschnittlichen Auszahlungsbetrag (Kosten für DR-Programm) pro kWh
    für das aktuelle DR-Event, basierend auf der angebotenen Incentive-Rate und
    geschätzten monatlichen Gerätenutzungskosten.
    """
    if not shifted_energy_per_device_kwh or sum(shifted_energy_per_device_kwh.values()) <= 0:
        return 0.0

    total_monetary_rebate_for_event_eur = 0.0
    total_energy_shifted_in_event_kwh = sum(shifted_energy_per_device_kwh.values())
    
    num_days_in_profile = 1.0
    if not df_average_device_load_profiles_kwh.empty and \
       isinstance(df_average_device_load_profiles_kwh.index, pd.DatetimeIndex) and \
       len(df_average_device_load_profiles_kwh.index) > 1:
        num_unique_days = df_average_device_load_profiles_kwh.index.normalize().nunique()
        num_days_in_profile = max(1.0, float(num_unique_days))
        
    elif not df_average_device_load_profiles_kwh.empty:
        print("[WARNUNG] _derive_average_incentive_payout_rate: df_average_device_load_profiles_kwh hat nur wenige Datenpunkte. Monatsverbrauchsschätzung könnte ungenau sein.")

    for device, energy_shifted_this_event_dev in shifted_energy_per_device_kwh.items():
        if energy_shifted_this_event_dev <= 0:
            continue

        if device not in df_average_device_load_profiles_kwh.columns:
            print(f"[WARNUNG] _derive_average_incentive_payout_rate: Gerät {device} nicht in Lastprofilen für Monatsdurchschnitt gefunden ({df_average_device_load_profiles_kwh.columns.tolist()}).")
            continue
            
        total_energy_dev_in_profile_kwh = df_average_device_load_profiles_kwh[device].sum() * interval_duration_h
        avg_daily_energy_dev_kwh = total_energy_dev_in_profile_kwh / num_days_in_profile
        monthly_energy_dev_kwh = avg_daily_energy_dev_kwh * 30.4375 

        monthly_device_cost_eur = monthly_energy_dev_kwh * avg_household_electricity_price_eur_kwh
        device_monthly_rebate_eur = monthly_device_cost_eur * offered_incentive_for_event_pct
        device_rebate_per_event_eur = device_monthly_rebate_eur / assumed_dr_events_per_month
        
        total_monetary_rebate_for_event_eur += device_rebate_per_event_eur

    if total_energy_shifted_in_event_kwh > 0:
        avg_payout_rate_eur_per_kwh = total_monetary_rebate_for_event_eur / total_energy_shifted_in_event_kwh
        print(f"[INFO] _derive_average_incentive_payout_rate: Berechneter Anreizkostensatz = {avg_payout_rate_eur_per_kwh:.4f} EUR/kWh "
              f"(Gesamtanreiz für Event: {total_monetary_rebate_for_event_eur:.2f} EUR / "
              f"Gesamt verschobene Energie: {total_energy_shifted_in_event_kwh:.2f} kWh)")
        return avg_payout_rate_eur_per_kwh
    else:
        return 0.0

def evaluate_dr_scenario(
    df_respondent_flexibility: pd.DataFrame,
    df_average_load_profiles: pd.DataFrame, 
    event_parameters: dict,
    simulation_assumptions: dict,
    df_spot_prices_eur_mwh: pd.Series,
    df_reg_original_data: pd.DataFrame,
    cost_model_assumptions: dict
) -> dict:
    """
    Orchestriert die physische Simulation (basierend auf Respondentendaten aus df_respondent_flexibility
    und Anwendung auf df_average_load_profiles) und die ökonomische Bewertung eines DR-Szenarios.
    """
    print(f"\n[SCENARIO_ANALYZER] Starte evaluate_dr_scenario (respondent-basiert) für Event: {event_parameters.get('start_time')} - {event_parameters.get('end_time')}")

    # Standard-Rückgabeobjekt für den Fall, dass die Simulation nicht durchgeführt werden kann
    # (z.B. weil df_average_load_profiles leer ist)
    default_output_columns = df_average_load_profiles.columns.tolist() if not df_average_load_profiles.empty else []
    default_index = df_average_load_profiles.index if not df_average_load_profiles.empty else pd.DatetimeIndex([])
    
    error_return_structure = {
        "value_added_eur": 0.0, "baseline_spot_costs_eur": 0.0, "scenario_spot_costs_eur": 0.0,
        "dr_program_costs_eur": 0.0, "ancillary_service_savings_eur": 0.0,
        "original_aggregated_load_kw": pd.Series(dtype=float, index=default_index),
        "final_shifted_aggregated_load_kw": pd.Series(dtype=float, index=default_index),
        "df_shiftable_per_appliance": pd.DataFrame(0.0, index=default_index, columns=default_output_columns, dtype=float),
        "df_payback_per_appliance": pd.DataFrame(0.0, index=default_index, columns=default_output_columns, dtype=float),
        "total_shifted_energy_kwh_event": 0.0,
        "shifted_energy_per_device_kwh_event": {},
        "average_payout_rate_eur_per_kwh_event": 0.0,
        "detailed_participation_for_costing": []
    }

    if df_average_load_profiles.empty:
        print("[SCENARIO_ANALYZER] df_average_load_profiles ist leer. Breche Analyse ab und gebe Default-Struktur zurück.")
        return error_return_structure
    
    if df_respondent_flexibility.empty:
        print("[SCENARIO_ANALYZER] df_respondent_flexibility ist leer. Simulation ergibt kein Shift-Potenzial. Gebe Default-Struktur mit Baseline-Kosten zurück.")
        # In diesem Fall können Baseline-Kosten noch berechnet werden, aber kein Shift.
        interval_duration_h_baseline = _calculate_interval_duration_h(df_average_load_profiles.index)
        original_aggregated_load_kw_baseline = df_average_load_profiles.sum(axis=1)
        baseline_spot_costs_eur_only = calculate_spot_market_costs(
            original_aggregated_load_kw_baseline,
            df_spot_prices_eur_mwh
        )
        error_return_structure["baseline_spot_costs_eur"] = baseline_spot_costs_eur_only
        error_return_structure["scenario_spot_costs_eur"] = baseline_spot_costs_eur_only # Da kein Shift
        error_return_structure["original_aggregated_load_kw"] = original_aggregated_load_kw_baseline
        error_return_structure["final_shifted_aggregated_load_kw"] = original_aggregated_load_kw_baseline
        return error_return_structure


    # 0. Intervalldauer bestimmen
    interval_duration_h = _calculate_interval_duration_h(df_average_load_profiles.index)
    # Eine sehr kleine positive Dauer ist hier okay, _calculate_interval_duration_h gibt nie <=0 zurück.

    # 1. Physische Simulation durchführen mit dem respondenten-basierten Modell
    print("[SCENARIO_ANALYZER] Rufe simulate_respondent_level_load_shift auf...")
    sim_output = simulate_respondent_level_load_shift( # ANGEPASSTER AUFRUF
        df_respondent_flexibility=df_respondent_flexibility,
        df_average_load_profiles=df_average_load_profiles, 
        event_parameters=event_parameters,
        simulation_assumptions=simulation_assumptions
        # debug_device_name kann hier optional übergeben werden, falls es durchgereicht werden soll
    )
    
    df_shiftable_per_appliance = sim_output.get("df_shiftable_per_appliance")
    df_payback_per_appliance = sim_output.get("df_payback_per_appliance")
    total_shifted_energy_kwh_event = sim_output.get("total_shifted_energy_kwh", 0.0)
    shifted_energy_per_device_kwh_event = sim_output.get("shifted_energy_per_device_kwh", {})
    detailed_participation_for_costing = sim_output.get("detailed_participation_for_costing", [])

    # 2. Aggregierte Lastprofile erstellen
    original_aggregated_load_kw = df_average_load_profiles.sum(axis=1)
    
    shift_sum_kw_series = df_shiftable_per_appliance.sum(axis=1)
    shift_sum_kw = shift_sum_kw_series.reindex_like(original_aggregated_load_kw).fillna(0.0)
    
    payback_sum_kw_series = df_payback_per_appliance.sum(axis=1)
    payback_sum_kw = payback_sum_kw_series.reindex_like(original_aggregated_load_kw).fillna(0.0)
    
    final_shifted_aggregated_load_kw = original_aggregated_load_kw - shift_sum_kw + payback_sum_kw

    # 3. Kosten berechnen
    # 3a. Spotmarktkosten
    print("[SCENARIO_ANALYZER] Berechne Spotmarktkosten...")
    baseline_spot_costs_eur = calculate_spot_market_costs(
        original_aggregated_load_kw,
        df_spot_prices_eur_mwh 
    )
    scenario_spot_costs_eur = calculate_spot_market_costs(
        final_shifted_aggregated_load_kw,
        df_spot_prices_eur_mwh
    )
    spot_market_savings_eur = baseline_spot_costs_eur - scenario_spot_costs_eur
    print(f"  Baseline Spot Kosten: {baseline_spot_costs_eur:.2f} EUR")
    print(f"  Szenario Spot Kosten: {scenario_spot_costs_eur:.2f} EUR")
    print(f"  Spotmarkt Einsparungen: {spot_market_savings_eur:.2f} EUR")

    # 3b. DR-Anreizkosten
    print("[SCENARIO_ANALYZER] Berechne DR-Anreizkosten...")
    avg_payout_rate_eur_kwh = _derive_average_incentive_payout_rate_eur_per_kwh(
        shifted_energy_per_device_kwh=shifted_energy_per_device_kwh_event,
        df_average_device_load_profiles_kwh=df_average_load_profiles,
        interval_duration_h=interval_duration_h,
        offered_incentive_for_event_pct=event_parameters['incentive_percentage'], 
        avg_household_electricity_price_eur_kwh=cost_model_assumptions['avg_household_electricity_price_eur_kwh'],
        assumed_dr_events_per_month=cost_model_assumptions['assumed_dr_events_per_month']
    )
    dr_program_costs_eur = calculate_dr_incentive_costs(
        total_shifted_energy_kwh_event,
        avg_payout_rate_eur_kwh
    )
    print(f"  Durchschnittlicher Anreiz-Auszahlungssatz: {avg_payout_rate_eur_kwh:.4f} EUR/kWh")
    print(f"  DR Programmkosten (Anreize): {dr_program_costs_eur:.2f} EUR")

    # 3c. Regelenergiekosten/-einsparungen (Ancillary Service Savings)
    print("[SCENARIO_ANALYZER] Berechne Regelenergie-Einsparungen...")
    P_shiftable_total_kw_series = df_shiftable_per_appliance.sum(axis=1).reindex_like(original_aggregated_load_kw).fillna(0.0)
    cost_of_dr_for_as_eur_mwh = avg_payout_rate_eur_kwh * 1000.0 
    as_technical_availability = cost_model_assumptions.get('as_displacement_factor', 0.1)

    as_savings_eur = calculate_mfrr_savings_opportunity(
        df_reg_original=df_reg_original_data,
        df_shiftable_total_kw=P_shiftable_total_kw_series, 
        cost_of_dr_activation_eur_per_mwh=cost_of_dr_for_as_eur_mwh,
        interval_duration_h=interval_duration_h,
        technical_availability_factor=as_technical_availability 
    )
    print(f"  Regelenergie-Einsparungen: {as_savings_eur:.2f} EUR")

    # 4. "Value Added" berechnen
    value_added_eur = spot_market_savings_eur + as_savings_eur - dr_program_costs_eur
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
        "average_payout_rate_eur_per_kwh_event": avg_payout_rate_eur_kwh,
        "detailed_participation_for_costing": detailed_participation_for_costing
    }