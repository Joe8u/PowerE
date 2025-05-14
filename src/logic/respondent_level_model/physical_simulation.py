# PowerE/src/logic/respondent_level_model/physical_simulation.py
import pandas as pd
import numpy as np
import datetime # Für pd.Timedelta, falls benötigt

# Helferfunktion zur Bestimmung der Intervalldauer (könnte auch globaler verfügbar gemacht werden)
def _calculate_interval_duration_h_for_physical_sim(time_index: pd.DatetimeIndex) -> float:
    if time_index is None or not isinstance(time_index, pd.DatetimeIndex) or len(time_index) < 2:
        print("[WARNUNG] physical_simulation._calculate_interval_duration_h: Ungültiger Zeitindex. Nehme 0.25h an.")
        return 0.25
    diffs_seconds = pd.Series(time_index).diff().dropna().dt.total_seconds()
    if not diffs_seconds.empty:
        median_diff_seconds = diffs_seconds.median()
        if median_diff_seconds > 0:
            return median_diff_seconds / 3600.0
    print("[WARNUNG] physical_simulation._calculate_interval_duration_h: Konnte Intervalldauer nicht ableiten, nehme 0.25h an.")
    return 0.25

def calculate_respondent_level_shift(
    df_respondent_flexibility: pd.DataFrame, # Der Output von create_respondent_flexibility_df()
    df_average_load_profiles: pd.DataFrame,  # Disaggregierte Durchschnitts-Lastprofile pro Gerät (kW)
    event_parameters: dict,                  # Enthält start_time, end_time, required_duration_hours, incentive_percentage
    simulation_assumptions: dict,            # Enthält reality_discount_factor, payback_model
    debug_device_name: str = None
) -> dict:
    """
    Simuliert das physische Lastverschiebungspotenzial (Reduktion und Payback) pro Gerät,
    basierend auf individuellen Respondentendaten und durchschnittlichen Lastprofilen.
    """
    print("\n===================================================================")
    print("---- calculate_respondent_level_shift GESTARTET ----")
    print("===================================================================")
    print(f"[INPUT] df_respondent_flexibility Shape: {df_respondent_flexibility.shape}")
    print(f"[INPUT] df_average_load_profiles Shape: {df_average_load_profiles.shape}, "
          f"Index: {df_average_load_profiles.index.min()} bis {df_average_load_profiles.index.max()}")
    print(f"[INPUT] Event Parameter: {event_parameters}")
    print(f"[INPUT] Simulationsannahmen: {simulation_assumptions}")

    # Parameter extrahieren
    event_start_time = event_parameters.get('start_time')
    event_end_time = event_parameters.get('end_time')
    required_duration_hours = event_parameters.get('required_duration_hours', 0)
    # incentive_percentage ist 0-1, für Vergleich mit q10_pct_required (0-100) * 100 nehmen
    offered_incentive_pct_event = event_parameters.get('incentive_percentage', 0) * 100 
    
    reality_discount_factor = simulation_assumptions.get('reality_discount_factor', 1.0)
    payback_model_config = simulation_assumptions.get('payback_model', {})

    # Initialisiere Ergebnis-DataFrames
    # Spalten sind die Geräte aus den Durchschnitts-Lastprofilen
    output_columns = df_average_load_profiles.columns.tolist()
    df_shiftable_per_appliance = pd.DataFrame(0.0, index=df_average_load_profiles.index, columns=output_columns, dtype=float)
    df_payback_per_appliance = pd.DataFrame(0.0, index=df_average_load_profiles.index, columns=output_columns, dtype=float)
    
    detailed_participation_for_costing = [] # Liste von Tupeln (respondent_id, device, pct_required_for_participation)

    if df_average_load_profiles.empty:
        print("FEHLER: df_average_load_profiles ist leer. Simulation wird abgebrochen.")
        return {
            "df_shiftable_per_appliance": df_shiftable_per_appliance,
            "df_payback_per_appliance": df_payback_per_appliance,
            "total_shifted_energy_kwh": 0.0,
            "shifted_energy_per_device_kwh": {},
            "detailed_participation_for_costing": detailed_participation_for_costing
        }

    # Zeitfenster für das Event filtern (basierend auf dem Index der Durchschnittsprofile)
    try:
        event_timestamps_mask = (df_average_load_profiles.index >= event_start_time) & (df_average_load_profiles.index < event_end_time)
        event_timestamps = df_average_load_profiles[event_timestamps_mask].index
    except Exception as e:
        print(f"FEHLER beim Filtern der Event-Zeitstempel für Durchschnittsprofile: {e}.")
        # ... (Rückgabe der initialisierten DFs etc.)
        return {
            "df_shiftable_per_appliance": df_shiftable_per_appliance,
            "df_payback_per_appliance": df_payback_per_appliance,
            "total_shifted_energy_kwh": 0.0,
            "shifted_energy_per_device_kwh": {},
            "detailed_participation_for_costing": detailed_participation_for_costing
        }
        
    if event_timestamps.empty:
        print("WARNUNG: Keine Zeitstempel im Event-Fenster für Durchschnittsprofile gefunden.")
        # ... (Rückgabe der initialisierten DFs etc.)
        return {
            "df_shiftable_per_appliance": df_shiftable_per_appliance,
            "df_payback_per_appliance": df_payback_per_appliance,
            "total_shifted_energy_kwh": 0.0,
            "shifted_energy_per_device_kwh": {},
            "detailed_participation_for_costing": detailed_participation_for_costing
        }

    print(f"\n[REDUKTION] Simuliere für {len(event_timestamps)} Zeitstempel im Event-Fenster von {event_start_time} bis {event_end_time}...")

    # --- A. Identifiziere "Effektive Shifter" basierend auf df_respondent_flexibility ---
    effective_shifters_by_device = {dev: [] for dev in output_columns} # Speichert respondent_ids
    # Auch die Kompensationsanforderung der tatsächlichen Shifter speichern
    actual_compensation_for_shifters = [] # Liste von (respondent_id, device, pct_required)

    for index, row in df_respondent_flexibility.iterrows():
        dev = row['device']
        if dev not in output_columns: # Nur Geräte betrachten, für die wir Durchschnittsprofile haben
            continue

        participates = False
        pct_required_for_this_participation = np.nan

        if row['incentive_choice'] == 'yes_fixed':
            participates = True
            pct_required_for_this_participation = 0.0 # Nehmen an, 0% ist die Anforderung
        elif row['incentive_choice'] == 'yes_conditional':
            if not pd.isna(row['incentive_pct_required']) and row['incentive_pct_required'] <= offered_incentive_pct_event:
                participates = True
                pct_required_for_this_participation = row['incentive_pct_required']
        
        can_meet_duration = (not pd.isna(row['max_duration_hours'])) and \
                            (row['max_duration_hours'] >= required_duration_hours)

        if participates and can_meet_duration:
            effective_shifters_by_device[dev].append(row['respondent_id'])
            actual_compensation_for_shifters.append(
                (row['respondent_id'], dev, pct_required_for_this_participation)
            )
    
    detailed_participation_for_costing = actual_compensation_for_shifters # Für spätere Kostenberechnung

    # --- B. Aggregiere das Verschiebungspotenzial pro Gerät ---
    for dev_type in output_columns:
        verbose_print = (debug_device_name is None and len(output_columns) < 4) or (dev_type == debug_device_name)
        if verbose_print: print(f"\n  --- Verarbeite Gerät: {dev_type} ---")

        num_effective_shifters_dev = len(set(effective_shifters_by_device.get(dev_type, [])))
        
        # Basispopulation für dieses Gerät aus der Umfrage
        # (Anzahl der eindeutigen Respondenten, die für dieses Gerät in df_respondent_flexibility Daten geliefert haben)
        # Dies berücksichtigt, dass nicht jeder Respondent jedes Gerät in der Umfrage hatte/beantwortet hat.
        num_survey_base_for_dev = df_respondent_flexibility[df_respondent_flexibility['device'] == dev_type]['respondent_id'].nunique()

        if verbose_print: print(f"    Anzahl effektiver Shifter für {dev_type}: {num_effective_shifters_dev}")
        if verbose_print: print(f"    Basispopulation aus Umfrage für {dev_type}: {num_survey_base_for_dev}")

        if num_survey_base_for_dev == 0:
            if verbose_print: print(f"    Keine Basispopulation für {dev_type} in Umfragedaten. Rate = 0.")
            effective_rate_dev = 0.0
        else:
            effective_rate_dev = num_effective_shifters_dev / num_survey_base_for_dev
        
        final_rate_dev_with_discount = effective_rate_dev * reality_discount_factor
        if verbose_print: 
            print(f"    Effektive Rate für {dev_type} (Umfrage): {effective_rate_dev:.4f}")
            print(f"    Finale Rate für {dev_type} (mit Discount {reality_discount_factor:.2f}): {final_rate_dev_with_discount:.4f}")

        if final_rate_dev_with_discount <= 0:
            if verbose_print: print(f"    Kein finales Shift-Potenzial für {dev_type}.")
            continue

        # Anwenden auf das Durchschnitts-Lastprofil
        for t in event_timestamps:
            current_avg_load_dev_t = df_average_load_profiles.loc[t, dev_type]
            if current_avg_load_dev_t > 0:
                shiftable_load_dev_t = current_avg_load_dev_t * final_rate_dev_with_discount
                df_shiftable_per_appliance.loc[t, dev_type] = shiftable_load_dev_t

    print(f"\n[REDUKTION] Zusammenfassung df_shiftable_per_appliance (Summe kW-Werte pro Gerät über Event-Dauer):")
    print(df_shiftable_per_appliance.loc[event_timestamps].sum())
    print(f"[REDUKTION] Gesamtsumme verschiebbarer Leistungswerte: {df_shiftable_per_appliance.loc[event_timestamps].sum().sum():.2f} kW")

    # --- C. Berechne verschobene Energien ---
    dt_h = _calculate_interval_duration_h_for_physical_sim(df_average_load_profiles.index)
    shifted_energy_per_device_kwh = {}
    total_shifted_energy_all_devices_kwh = 0.0

    if dt_h > 0 and not df_shiftable_per_appliance.empty:
        for dev_calc in df_shiftable_per_appliance.columns:
            # Summiere nur über die Event-Zeitstempel für die verschobene Energie
            energy_dev = df_shiftable_per_appliance[dev_calc].loc[event_timestamps].sum() * dt_h
            shifted_energy_per_device_kwh[dev_calc] = energy_dev
            total_shifted_energy_all_devices_kwh += energy_dev
    print(f"\n[ENERGIE] Gesamte verschobene Energie über alle Geräte (final): {total_shifted_energy_all_devices_kwh:.2f} kWh")
    if debug_device_name and debug_device_name in shifted_energy_per_device_kwh:
        print(f"  Verschobene Energie für {debug_device_name}: {shifted_energy_per_device_kwh[debug_device_name]:.2f} kWh")


    # --- D. PAYBACK BERECHNEN UND MODELLIEREN PRO GERÄT ---
    print("\n[PAYBACK] Starte Payback-Berechnung...")
    print(f"  Intervalldauer für Energieberechnung (dt_h): {dt_h:.4f} Stunden")

    if dt_h > 0:
        for dev in output_columns: # Iteriere über die Geräte aus den Durchschnittsprofilen
            verbose_print = (debug_device_name is None and len(output_columns) < 4) or (dev == debug_device_name)
            if verbose_print: print(f"  --- Payback für Gerät: {dev} ---")

            energy_to_payback_dev = shifted_energy_per_device_kwh.get(dev, 0.0)
            if verbose_print: print(f"    Energie zum Zurückzahlen für {dev}: {energy_to_payback_dev:.2f} kWh")

            if energy_to_payback_dev <= 0:
                if verbose_print: print(f"    Keine Energie für {dev} verschoben, kein Payback.")
                continue

            payback_type = payback_model_config.get('type', 'none')
            payback_duration_hours_config = payback_model_config.get('duration_hours', required_duration_hours)
            if isinstance(payback_duration_hours_config, pd.Timedelta):
                 payback_duration_hours = payback_duration_hours_config.total_seconds() / 3600.0
            else:
                 payback_duration_hours = float(payback_duration_hours_config)
            
            payback_delay_hours = payback_model_config.get('delay_hours', 0)
            if verbose_print: print(f"    Payback Modell: Typ={payback_type}, Dauer={payback_duration_hours:.2f}h, Delay={payback_delay_hours:.2f}h")

            if payback_type == 'uniform_after_event' and payback_duration_hours > 0:
                payback_start_time = event_end_time + pd.Timedelta(hours=payback_delay_hours)
                payback_end_time_exclusive = payback_start_time + pd.Timedelta(hours=payback_duration_hours)
                if verbose_print: print(f"    Payback-Fenster: {payback_start_time} bis {payback_end_time_exclusive}")
                
                payback_power_kw_dev = energy_to_payback_dev / payback_duration_hours
                if verbose_print: print(f"    Payback-Leistung für {dev}: {payback_power_kw_dev:.2f} kW")

                payback_timestamps_mask = (df_payback_per_appliance.index >= payback_start_time) & \
                                          (df_payback_per_appliance.index < payback_end_time_exclusive)

                if payback_timestamps_mask.any():
                    df_payback_per_appliance.loc[payback_timestamps_mask, dev] += payback_power_kw_dev # += falls es schon was gab
                    if verbose_print: print(f"    Payback für {dev} ({payback_power_kw_dev:.2f} kW) erfolgreich in {payback_timestamps_mask.sum()} Zeitintervalle eingetragen.")
                else:
                    if verbose_print: print(f"    WARNUNG: Payback-Zeitfenster für Gerät {dev} liegt außerhalb des Datenbereichs oder ist leer.")
            # ... (andere payback types) ...
    else:
        print("WARNUNG: Intervalldauer dt_h ist 0, Payback kann nicht berechnet werden.")
    
    print(f"\n[PAYBACK] Zusammenfassung df_payback_per_appliance (Summe kW-Werte pro Gerät):")
    print(df_payback_per_appliance.sum())
    print(f"[PAYBACK] Gesamtsumme Payback-Leistungswerte: {df_payback_per_appliance.sum().sum():.2f} kW")

    print("\n===================================================================")
    print("---- calculate_respondent_level_shift ABGESCHLOSSEN ----")
    print("===================================================================")
    return {
        "df_shiftable_per_appliance": df_shiftable_per_appliance,
        "df_payback_per_appliance": df_payback_per_appliance,
        "total_shifted_energy_kwh": total_shifted_energy_all_devices_kwh,
        "shifted_energy_per_device_kwh": shifted_energy_per_device_kwh,
        "detailed_participation_for_costing": detailed_participation_for_costing # NEU
    }