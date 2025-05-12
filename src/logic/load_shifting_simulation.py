# src/logic/load_shifting_simulation.py
import pandas as pd
import numpy as np
from scipy.stats import lognorm

def run_load_shifting_simulation(
    df_load_profiles: pd.DataFrame,     # Index=Timestamp, Spalten=Geräte (kW)
    shift_metrics: dict,                # Ergebnisse aus Q9 (calculate_shift_potential_data)
    df_participation_curve_q10: pd.DataFrame, # Ergebnisse aus Q10 (get_participation_df)
    event_parameters: dict,             # z.B. start_time, end_time, required_duration_hours, incentive_percentage
    simulation_assumptions: dict        # z.B. reality_discount_factor, payback_model
) -> dict:
    """
    Simuliert das Lastverschiebungspotenzial (Reduktion) und den Payback-Effekt
    PRO GERÄT basierend auf Lastprofilen, Umfragedaten und Event-Parametern.
    """
    print("---- run_load_shifting_simulation gestartet (pro Gerät) ----")

    # Eingabeparameter extrahieren
    event_start_time = event_parameters.get('start_time')
    event_end_time = event_parameters.get('end_time')
    required_duration_hours = event_parameters.get('required_duration_hours', 0)
    incentive_for_lookup = event_parameters.get('incentive_percentage', 0) * 100
    reality_discount_factor = simulation_assumptions.get('reality_discount_factor', 1.0)
    payback_model_config = simulation_assumptions.get('payback_model', {})

    # Initialisiere die Ergebnis-DataFrames mit Nullen und dem Index/Spalten der Lastprofile
    if df_load_profiles is not None and not df_load_profiles.empty:
        df_shiftable_per_appliance = pd.DataFrame(0.0, index=df_load_profiles.index, columns=df_load_profiles.columns, dtype=float)
        df_payback_per_appliance = pd.DataFrame(0.0, index=df_load_profiles.index, columns=df_load_profiles.columns, dtype=float)
    else:
        print("Leere Lastprofile übergeben. Simulation wird nicht durchgeführt.")
        # Leere DataFrames mit den erwarteten Spaltennamen (falls bekannt) oder einfach leer zurückgeben
        cols = shift_metrics.keys() if shift_metrics else [] # Versuche Spalten aus shift_metrics zu bekommen
        return {
            "df_shiftable_per_appliance": pd.DataFrame(columns=cols, dtype=float),
            "df_payback_per_appliance": pd.DataFrame(columns=cols, dtype=float)
        }

    # Zeitfenster für das Event filtern
    try:
        # Wichtig: .loc[start:end] ist inklusiv für beide Grenzen, wenn der Index sortiert ist.
        # Um sicherzustellen, dass wir nur bis *vor* event_end_time gehen für eine exakte Dauer:
        event_timestamps_mask = (df_load_profiles.index >= event_start_time) & (df_load_profiles.index < event_end_time)
        event_timestamps = df_load_profiles[event_timestamps_mask].index
    except Exception as e: # Breitere Exception für diverse Index-Probleme
        print(f"Fehler beim Filtern der Event-Zeitstempel: {e}. Möglicherweise liegen Start/Ende außerhalb der Daten oder Index ist nicht sortiert/DatetimeIndex.")
        return {
            "df_shiftable_per_appliance": df_shiftable_per_appliance, # Gibt die initialisierten (leeren/Nullen) DFs zurück
            "df_payback_per_appliance": df_payback_per_appliance
        }
        
    if event_timestamps.empty:
        print("Keine Zeitstempel im Event-Fenster gefunden. Liegt das Event innerhalb des Datenbereichs und ist der Index korrekt?")
        return {
            "df_shiftable_per_appliance": df_shiftable_per_appliance,
            "df_payback_per_appliance": df_payback_per_appliance
        }

    print(f"Simuliere für {len(event_timestamps)} Zeitstempel im Event-Fenster von {event_start_time} bis {event_end_time}...")

    # --- BERECHNUNG DES REDUKTIONSPOTENZIALS PRO GERÄT ---
    for dev in df_load_profiles.columns:
        if dev not in shift_metrics:
            print(f"Warnung: Keine Shift-Metriken (Q9) für Gerät '{dev}' gefunden. Überspringe Reduktion.")
            continue
        if dev not in df_participation_curve_q10['device'].unique():
            print(f"Warnung: Keine Partizipationskurve (Q10) für Gerät '{dev}' gefunden. Überspringe Reduktion.")
            continue

        # a. Teilnahme-Wahrscheinlichkeit durch Anreiz (Q10)
        device_q10_data = df_participation_curve_q10[df_participation_curve_q10['device'] == dev].sort_values(by='comp_pct')
        p_participate_incentive = 0.0
        if not device_q10_data.empty:
            participation_at_incentive = np.interp(
                incentive_for_lookup,
                device_q10_data['comp_pct'],
                device_q10_data['participation_pct']
            )
            p_participate_incentive = participation_at_incentive / 100.0

        # b. Fähigkeits-Wahrscheinlichkeit für Dauer (Q9)
        dev_shift_metrics = shift_metrics[dev]
        lognorm_s, lognorm_scale_val = dev_shift_metrics.get('lognorm_shape'), dev_shift_metrics.get('lognorm_scale')
        p_duration_ok = 0.0
        if not (pd.isna(lognorm_s) or pd.isna(lognorm_scale_val) or required_duration_hours <= 0):
            try:
                p_duration_ok = 1 - lognorm.cdf(required_duration_hours, s=lognorm_s, loc=0, scale=lognorm_scale_val)
            except Exception as e:
                print(f"Fehler bei lognorm.cdf für {dev}: s={lognorm_s}, scale={lognorm_scale_val}, dur={required_duration_hours}. Fehler: {e}")
                p_duration_ok = 0.0

        # c. Kombinierte & reale Wahrscheinlichkeit
        p_combined = p_participate_incentive * p_duration_ok
        p_effective_real = p_combined * reality_discount_factor

        if p_effective_real <= 0:
            continue # Keine Verschiebung für dieses Gerät

        # d. Verschiebbare Last pro Zeitschritt im Event für dieses Gerät berechnen
        for t in event_timestamps:
            current_load_dev_t = df_load_profiles.loc[t, dev]
            if current_load_dev_t > 0:
                shiftable_load_dev_t = current_load_dev_t * p_effective_real
                df_shiftable_per_appliance.loc[t, dev] = shiftable_load_dev_t # Speichere pro Gerät

    # --- ENDE REDUKTIONSPOTENZIAL ---


    # --- PAYBACK BERECHNEN UND MODELLIEREN PRO GERÄT ---
    # Intervalldauer in Stunden (aus dem Index der Lastprofile ableiten)
    dt_h = 0
    if len(df_load_profiles.index) > 1:
        # Sicherstellen, dass der Index ein DatetimeIndex ist, um total_seconds verwenden zu können
        if isinstance(df_load_profiles.index, pd.DatetimeIndex):
            dt_h = (df_load_profiles.index[1] - df_load_profiles.index[0]).total_seconds() / 3600
        else:
            print("Warnung: Index von df_load_profiles ist kein DatetimeIndex. dt_h kann nicht zuverlässig bestimmt werden.")
    elif len(df_load_profiles.index) == 1:
         dt_h = 1.0 # Annahme für einen einzelnen Datenpunkt
    
    if dt_h > 0:
        for dev in df_load_profiles.columns:
            if dev not in df_shiftable_per_appliance.columns: # Sollte nicht passieren
                continue

            # Gesamte verschobene Energie für DIESES Gerät in kWh
            shifted_energy_kwh_dev = df_shiftable_per_appliance[dev].sum() * dt_h

            if shifted_energy_kwh_dev <= 0:
                continue # Kein Payback, wenn nichts verschoben wurde

            payback_type = payback_model_config.get('type', 'none')
            # Standard-Paybackdauer: Gleich der Eventdauer, falls nicht anders spezifiziert
            payback_duration_hours = payback_model_config.get('duration_hours', event_end_time - event_start_time)
            if isinstance(payback_duration_hours, pd.Timedelta): # Umwandeln, falls es ein Timedelta ist
                 payback_duration_hours = payback_duration_hours.total_seconds() / 3600
            
            payback_delay_hours = payback_model_config.get('delay_hours', 0)

            if payback_type == 'uniform_after_event' and payback_duration_hours > 0:
                payback_start_time = event_end_time + pd.Timedelta(hours=payback_delay_hours)
                payback_end_time_exclusive = payback_start_time + pd.Timedelta(hours=payback_duration_hours)
                
                payback_power_kw_dev = shifted_energy_kwh_dev / payback_duration_hours

                # Payback-Leistung in df_payback_per_appliance eintragen
                # Maske für den Payback-Zeitraum erstellen
                payback_timestamps_mask = (df_payback_per_appliance.index >= payback_start_time) & \
                                          (df_payback_per_appliance.index < payback_end_time_exclusive)

                if payback_timestamps_mask.any():
                    df_payback_per_appliance.loc[payback_timestamps_mask, dev] += payback_power_kw_dev
                else:
                    print(f"Warnung: Payback-Zeitfenster für Gerät {dev} ({payback_start_time} bis {payback_end_time_exclusive}) liegt außerhalb des Datenbereichs oder ist leer.")
            
            elif payback_type == 'none':
                # Kein Payback für dieses Gerät oder global
                pass # explizit nichts tun
            else:
                print(f"Warnung: Unbekannter Payback-Modell-Typ für Gerät {dev}: {payback_type}")
    else:
        print("Warnung: Intervalldauer dt_h ist 0 oder Index nicht bestimmbar, Payback kann nicht berechnet werden.")
    # --- ENDE PAYBACK ---

    print("---- run_load_shifting_simulation (pro Gerät) abgeschlossen ----")
    return {
        "df_shiftable_per_appliance": df_shiftable_per_appliance,
        "df_payback_per_appliance": df_payback_per_appliance
    }