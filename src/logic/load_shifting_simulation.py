# src/logic/load_shifting_simulation.py
# Diese Datei enthält die Logik zur Simulation von Lastverschiebungen,
# basierend auf einem respondenten-level Ansatz.
# Die Kernlogik wurde aus dem vorherigen Modul 
# src/logic/respondent_level_model/physical_simulation.py hierher verschoben und integriert.

import pandas as pd
import numpy as np
import datetime # Für pd.Timedelta und Typ-Annotationen

def _calculate_interval_duration_h(time_index: pd.DatetimeIndex) -> float:
    """
    Hilfsfunktion zur robusten Bestimmung der Intervalldauer eines Zeitindex in Stunden.
    """
    if time_index is None or not isinstance(time_index, pd.DatetimeIndex) or len(time_index) < 2:
        print("[WARNUNG] load_shifting_simulation._calculate_interval_duration_h: Ungültiger Zeitindex oder weniger als 2 Punkte. Nehme 0.25h an.")
        return 0.25  # Annahme: 15 Minuten
    
    # Median der Zeitdifferenzen verwenden, um robuster gegenüber Ausreißern oder unregelmäßigen Schritten zu sein
    diffs_seconds = pd.Series(time_index).diff().dropna().dt.total_seconds()
    if not diffs_seconds.empty:
        median_diff_seconds = diffs_seconds.median()
        if median_diff_seconds > 0:
            return median_diff_seconds / 3600.0
    
    print("[WARNUNG] load_shifting_simulation._calculate_interval_duration_h: Konnte Intervalldauer nicht aus Index ableiten, nehme 0.25h an.")
    return 0.25

def simulate_respondent_level_load_shift( # Umbenannt für Klarheit in diesem Modul
    df_respondent_flexibility: pd.DataFrame,
    df_average_load_profiles: pd.DataFrame,
    event_parameters: dict,
    simulation_assumptions: dict,
    debug_device_name: str = None
) -> dict:
    """
    Simuliert das physische Lastverschiebungspotenzial (Reduktion und Payback) pro Gerät,
    basierend auf individuellen Respondentendaten und durchschnittlichen Lastprofilen.

    Args:
        df_respondent_flexibility (pd.DataFrame): DataFrame mit aufbereiteten Umfragedaten 
                                                  (Ausgabe von create_respondent_flexibility_df()).
                                                  Erwartete Spalten: 'respondent_id', 'device', 
                                                                    'max_duration_hours', 
                                                                    'incentive_choice', 
                                                                    'incentive_pct_required'.
        df_average_load_profiles (pd.DataFrame): Disaggregierte Durchschnitts-Lastprofile pro Gerät (in kW).
                                                 Index ist pd.DatetimeIndex, Spalten sind Gerätenamen.
        event_parameters (dict): Parameter des DR-Events. Muss enthalten:
                                 'start_time' (pd.Timestamp): Startzeit des Events.
                                 'end_time' (pd.Timestamp): Exklusive Endzeit des Events.
                                 'required_duration_hours' (float): Mindestdauer der Teilnahme.
                                 'incentive_percentage' (float): Angebotener Anreiz als 0-1 Wert (z.B. 0.15 für 15%).
        simulation_assumptions (dict): Annahmen für die Simulation. Muss enthalten:
                                      'reality_discount_factor' (float): Faktor zur Anpassung der Teilnahme (0-1).
                                      'payback_model' (dict): Konfiguration des Payback-Modells, z.B.
                                                              {'type': 'uniform_after_event', 
                                                               'duration_hours': float, 
                                                               'delay_hours': float}
        debug_device_name (str, optional): Name eines Geräts für detailliertere Print-Ausgaben.

    Returns:
        dict: Ein Dictionary mit den Simulationsergebnissen:
              "df_shiftable_per_appliance" (pd.DataFrame): Zeitreihen der verschiebbaren Last pro Gerät (kW).
              "df_payback_per_appliance" (pd.DataFrame): Zeitreihen der Payback-Last pro Gerät (kW).
              "total_shifted_energy_kwh" (float): Gesamt verschobene Energie während des Events (kWh).
              "shifted_energy_per_device_kwh" (dict): Verschobene Energie pro Gerät während des Events (kWh).
              "detailed_participation_for_costing" (list): Liste von Tupeln 
                                                            (respondent_id, device, pct_required_for_participation)
                                                            für die teilnehmenden Befragten.
    """
    print("\n===================================================================")
    print("---- simulate_respondent_level_load_shift GESTARTET ----")
    print("===================================================================")
    print(f"[INPUT] df_respondent_flexibility Shape: {df_respondent_flexibility.shape}")
    if not df_average_load_profiles.empty:
        print(f"[INPUT] df_average_load_profiles Shape: {df_average_load_profiles.shape}, "
              f"Index: {df_average_load_profiles.index.min()} bis {df_average_load_profiles.index.max()}")
    else:
        print("[INPUT] df_average_load_profiles ist leer.")
    print(f"[INPUT] Event Parameter: {event_parameters}")
    print(f"[INPUT] Simulationsannahmen: {simulation_assumptions}")

    # Standard-Rückgabeobjekt für Fehlerfälle oder leere Eingaben
    empty_output_columns = df_average_load_profiles.columns.tolist() if not df_average_load_profiles.empty else []
    empty_index = df_average_load_profiles.index if not df_average_load_profiles.empty else pd.DatetimeIndex([])
    
    default_return = {
        "df_shiftable_per_appliance": pd.DataFrame(0.0, index=empty_index, columns=empty_output_columns, dtype=float),
        "df_payback_per_appliance": pd.DataFrame(0.0, index=empty_index, columns=empty_output_columns, dtype=float),
        "total_shifted_energy_kwh": 0.0,
        "shifted_energy_per_device_kwh": {},
        "detailed_participation_for_costing": []
    }

    if df_average_load_profiles.empty:
        print("FEHLER: df_average_load_profiles ist leer. Simulation wird abgebrochen.")
        return default_return
    
    if df_respondent_flexibility.empty:
        print("WARNUNG: df_respondent_flexibility ist leer. Es kann kein Lastpotenzial verschoben werden.")
        return default_return

    output_columns = df_average_load_profiles.columns.tolist()
    df_shiftable_per_appliance = pd.DataFrame(0.0, index=df_average_load_profiles.index, columns=output_columns, dtype=float)
    df_payback_per_appliance = pd.DataFrame(0.0, index=df_average_load_profiles.index, columns=output_columns, dtype=float)
    detailed_participation_for_costing = []

    # Parameter extrahieren
    event_start_time = event_parameters.get('start_time')
    event_end_time = event_parameters.get('end_time')
    required_duration_hours = event_parameters.get('required_duration_hours', 0)
    # incentive_percentage ist 0-1, für Vergleich mit q10_pct_required (0-100) umrechnen
    offered_incentive_pct_event = event_parameters.get('incentive_percentage', 0.0) * 100.0 
    
    reality_discount_factor = simulation_assumptions.get('reality_discount_factor', 1.0)
    payback_model_config = simulation_assumptions.get('payback_model', {})

    # Zeitfenster für das Event filtern
    try:
        event_timestamps_mask = (df_average_load_profiles.index >= event_start_time) & \
                                (df_average_load_profiles.index < event_end_time)
        event_timestamps = df_average_load_profiles.index[event_timestamps_mask]
    except Exception as e:
        print(f"FEHLER beim Filtern der Event-Zeitstempel für Durchschnittsprofile: {e}.")
        return default_return
        
    if event_timestamps.empty:
        print("WARNUNG: Keine Zeitstempel im Event-Fenster für Durchschnittsprofile gefunden.")
        return default_return

    print(f"\n[REDUKTION] Simuliere für {len(event_timestamps)} Zeitstempel im Event-Fenster: {event_start_time} bis {event_end_time}...")

    # --- A. Identifiziere "Effektive Shifter" basierend auf df_respondent_flexibility ---
    effective_shifters_by_device = {dev: [] for dev in output_columns}
    
    for index, row in df_respondent_flexibility.iterrows():
        dev = row.get('device')
        if dev not in output_columns:
            continue

        participates = False
        pct_required_for_this_participation = np.nan # Prozentsatz, der zur Teilnahme führte

        # incentive_choice und pct_required prüfen
        incentive_choice = row.get('incentive_choice')
        incentive_pct_required = row.get('incentive_pct_required') # Dies ist 0-100 oder NaN

        if incentive_choice == 'yes_fixed':
            participates = True
            pct_required_for_this_participation = 0.0 
        elif incentive_choice == 'yes_conditional':
            if not pd.isna(incentive_pct_required) and incentive_pct_required <= offered_incentive_pct_event:
                participates = True
                pct_required_for_this_participation = incentive_pct_required
        
        # max_duration_hours prüfen
        max_duration = row.get('max_duration_hours')
        can_meet_duration = (not pd.isna(max_duration)) and \
                            (max_duration >= required_duration_hours)

        if participates and can_meet_duration:
            effective_shifters_by_device[dev].append(row['respondent_id'])
            detailed_participation_for_costing.append(
                (row['respondent_id'], dev, pct_required_for_this_participation)
            )
    
    # --- B. Aggregiere das Verschiebungspotenzial pro Gerät ---
    for dev_type in output_columns:
        verbose_print = (debug_device_name is None and len(output_columns) < 4) or (dev_type == debug_device_name)
        if verbose_print: print(f"\n  --- Verarbeite Gerät: {dev_type} ---")

        # Eindeutige Shifter für dieses Gerät zählen
        num_effective_shifters_dev = len(set(effective_shifters_by_device.get(dev_type, [])))
        
        # Basispopulation für dieses Gerät aus der Umfrage
        device_specific_respondents = df_respondent_flexibility[df_respondent_flexibility['device'] == dev_type]
        num_survey_base_for_dev = device_specific_respondents['respondent_id'].nunique()

        if verbose_print: 
            print(f"    Anzahl effektiver Shifter für {dev_type}: {num_effective_shifters_dev}")
            print(f"    Basispopulation (Umfrage) für {dev_type}: {num_survey_base_for_dev}")

        if num_survey_base_for_dev == 0:
            if verbose_print: print(f"    Keine Basispopulation für {dev_type} in Umfragedaten. Teilnahme-Rate = 0.")
            effective_participation_rate_dev = 0.0
        else:
            effective_participation_rate_dev = num_effective_shifters_dev / num_survey_base_for_dev
        
        final_participation_rate_dev = effective_participation_rate_dev * reality_discount_factor
        
        if verbose_print: 
            print(f"    Effektive Teilnahme-Rate für {dev_type} (Umfrage): {effective_participation_rate_dev:.4f}")
            print(f"    Finale Teilnahme-Rate für {dev_type} (mit Discount {reality_discount_factor:.2f}): {final_participation_rate_dev:.4f}")

        if final_participation_rate_dev <= 0:
            if verbose_print: print(f"    Kein finales Shift-Potenzial für {dev_type} aufgrund der Rate.")
            continue

        # Anwenden auf das Durchschnitts-Lastprofil während des Events
        for t_stamp in event_timestamps:
            current_avg_load_dev_t = df_average_load_profiles.loc[t_stamp, dev_type]
            if current_avg_load_dev_t > 0: # Nur positive Last kann verschoben werden
                shiftable_load_dev_t = current_avg_load_dev_t * final_participation_rate_dev
                df_shiftable_per_appliance.loc[t_stamp, dev_type] = shiftable_load_dev_t
    
    if not df_shiftable_per_appliance.empty:
        print(f"\n[REDUKTION] Zusammenfassung df_shiftable_per_appliance (Summe kW über Event-Dauer pro Gerät):")
        print(df_shiftable_per_appliance.loc[event_timestamps].sum())
        print(f"[REDUKTION] Gesamtsumme aller verschobenen Leistungswerte (Summe über Geräte und Zeit): {df_shiftable_per_appliance.loc[event_timestamps].values.sum():.2f} kW") # .values.sum() um über alles zu summieren

    # --- C. Berechne verschobene Energien ---
    # Verwende den Zeitindex von df_average_load_profiles, da dieser die Basis der Simulation ist
    dt_h = _calculate_interval_duration_h(df_average_load_profiles.index)
    shifted_energy_per_device_kwh = {}
    total_shifted_energy_all_devices_kwh = 0.0

    if dt_h > 0 and not df_shiftable_per_appliance.empty:
        for dev_calc in df_shiftable_per_appliance.columns:
            # Summiere die verschiebbare Leistung NUR während des Events und multipliziere mit der Intervalldauer
            energy_dev = df_shiftable_per_appliance.loc[event_timestamps, dev_calc].sum() * dt_h
            shifted_energy_per_device_kwh[dev_calc] = energy_dev
            total_shifted_energy_all_devices_kwh += energy_dev
    
    print(f"\n[ENERGIE] Intervalldauer für Energieberechnung (dt_h): {dt_h:.4f} Stunden")
    print(f"[ENERGIE] Gesamte verschobene Energie über alle Geräte (Event): {total_shifted_energy_all_devices_kwh:.2f} kWh")
    if debug_device_name and debug_device_name in shifted_energy_per_device_kwh:
        print(f"  Verschobene Energie für Debug-Gerät '{debug_device_name}': {shifted_energy_per_device_kwh[debug_device_name]:.2f} kWh")

    # --- D. PAYBACK BERECHNEN UND MODELLIEREN PRO GERÄT ---
    print("\n[PAYBACK] Starte Payback-Berechnung...")
    if dt_h > 0: # Payback nur sinnvoll, wenn Energie berechnet werden konnte
        for dev_payback in output_columns:
            verbose_print_payback = (debug_device_name is None and len(output_columns) < 4) or (dev_payback == debug_device_name)
            if verbose_print_payback: print(f"  --- Payback für Gerät: {dev_payback} ---")

            energy_to_payback_dev = shifted_energy_per_device_kwh.get(dev_payback, 0.0)
            if verbose_print_payback: print(f"    Energie zum Zurückzahlen für {dev_payback}: {energy_to_payback_dev:.2f} kWh")

            if energy_to_payback_dev <= 0:
                if verbose_print_payback: print(f"    Keine Energie für {dev_payback} verschoben, kein Payback.")
                continue

            payback_type = payback_model_config.get('type', 'none') # z.B. 'uniform_after_event'
            # Standard-Paybackdauer ist die Eventdauer, falls nicht anders spezifiziert
            payback_duration_hours_config = payback_model_config.get('duration_hours', required_duration_hours) 
            
            if isinstance(payback_duration_hours_config, datetime.timedelta): # Sicherstellen, dass es float ist
                 payback_duration_hours = payback_duration_hours_config.total_seconds() / 3600.0
            else:
                 payback_duration_hours = float(payback_duration_hours_config)
            
            payback_delay_hours = float(payback_model_config.get('delay_hours', 0.0))
            
            if verbose_print_payback: 
                print(f"    Payback Modell: Typ='{payback_type}', Dauer={payback_duration_hours:.2f}h, Delay={payback_delay_hours:.2f}h")

            if payback_type == 'uniform_after_event' and payback_duration_hours > 0:
                payback_start_time = event_end_time + datetime.timedelta(hours=payback_delay_hours)
                payback_end_time_exclusive = payback_start_time + datetime.timedelta(hours=payback_duration_hours)
                
                if verbose_print_payback: 
                    print(f"    Payback-Fenster: {payback_start_time} bis {payback_end_time_exclusive} (exkl.)")
                
                payback_power_kw_dev = energy_to_payback_dev / payback_duration_hours
                if verbose_print_payback: print(f"    Payback-Leistung für {dev_payback}: {payback_power_kw_dev:.2f} kW (gleichmäßig verteilt)")

                # Finde Zeitstempel im Payback-Fenster
                # Wichtig: Index muss für den gesamten Zeitraum (inkl. Payback) existieren
                payback_timestamps_mask = (df_payback_per_appliance.index >= payback_start_time) & \
                                          (df_payback_per_appliance.index < payback_end_time_exclusive)
                
                num_payback_intervals = payback_timestamps_mask.sum()
                if num_payback_intervals > 0:
                    # Addiere die Payback-Leistung zu diesen Zeitstempeln
                    # += falls es schon einen Wert gab (sollte hier nicht der Fall sein, aber sicher ist sicher)
                    df_payback_per_appliance.loc[payback_timestamps_mask, dev_payback] += payback_power_kw_dev 
                    if verbose_print_payback: 
                        print(f"    Payback für {dev_payback} ({payback_power_kw_dev:.2f} kW) in {num_payback_intervals} Zeitintervalle eingetragen.")
                else:
                    if verbose_print_payback: 
                        print(f"    WARNUNG: Payback-Zeitfenster für Gerät {dev_payback} liegt außerhalb des Datenbereichs der Lastprofile oder ist leer.")
            elif payback_type == 'none':
                 if verbose_print_payback: print(f"    Kein Payback ('none') für {dev_payback} angewendet.")
            else:
                if verbose_print_payback: print(f"    WARNUNG: Unbekannter Payback-Modell-Typ für Gerät {dev_payback}: '{payback_type}'")
    else:
        print("WARNUNG: Intervalldauer dt_h ist 0 oder negativ. Payback-Berechnung übersprungen.")
    
    if not df_payback_per_appliance.empty:
        print(f"\n[PAYBACK] Zusammenfassung df_payback_per_appliance (Summe kW über Payback-Dauer pro Gerät):")
        # Summiere nur über das tatsächliche Payback-Fenster, falls es definiert wurde
        # Dies ist eine Annäherung, da das Payback-Fenster pro Gerät variieren könnte, falls die Konfig komplexer wäre.
        # Hier nehmen wir an, das späteste mögliche Payback-Ende ist relevant oder einfach die Gesamtsumme im DataFrame.
        print(df_payback_per_appliance.sum()) 
        print(f"[PAYBACK] Gesamtsumme aller Payback-Leistungswerte (Summe über Geräte und Zeit): {df_payback_per_appliance.values.sum():.2f} kW")

    print("\n===================================================================")
    print("---- simulate_respondent_level_load_shift ABGESCHLOSSEN ----")
    print("===================================================================")
    return {
        "df_shiftable_per_appliance": df_shiftable_per_appliance,
        "df_payback_per_appliance": df_payback_per_appliance,
        "total_shifted_energy_kwh": total_shifted_energy_all_devices_kwh,
        "shifted_energy_per_device_kwh": shifted_energy_per_device_kwh,
        "detailed_participation_for_costing": detailed_participation_for_costing
    }