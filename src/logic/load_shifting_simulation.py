# src/logic/load_shifting_simulation.py
import pandas as pd
import numpy as np
from scipy.stats import lognorm

def run_load_shifting_simulation(
    df_load_profiles: pd.DataFrame,
    shift_metrics: dict,
    df_participation_curve_q10: pd.DataFrame,
    event_parameters: dict,
    simulation_assumptions: dict,
    debug_device_name: str = None
) -> dict:
    """
    Simuliert das Lastverschiebungspotenzial (Reduktion) und den Payback-Effekt
    PRO GERÄT basierend auf Lastprofilen, Umfragedaten und Event-Parametern.
    """
    print("\n===================================================================")
    print("---- run_load_shifting_simulation GESTARTET (pro Gerät) ----")
    print("===================================================================")

    print(f"[INPUT] Event Parameter: {event_parameters}")
    print(f"[INPUT] Simulationsannahmen: {simulation_assumptions}")
    # ... (Restliche INPUT Prints wie in deinem Code) ...
    if df_load_profiles is not None and not df_load_profiles.empty:
        print(f"[INPUT] df_load_profiles: {df_load_profiles.shape[0]} Zeilen, {df_load_profiles.shape[1]} Geräte. Index von {df_load_profiles.index.min()} bis {df_load_profiles.index.max()}")
        print(f"[INPUT] Geräte in df_load_profiles: {df_load_profiles.columns.tolist()}")
    else:
        print("[INPUT] df_load_profiles ist leer oder None.")
    print(f"[INPUT] Geräte in shift_metrics (Q9): {list(shift_metrics.keys())}")
    print(f"[INPUT] Geräte in df_participation_curve_q10 (Q10): {df_participation_curve_q10['device'].unique().tolist()}")


    event_start_time = event_parameters.get('start_time')
    event_end_time = event_parameters.get('end_time')
    required_duration_hours = event_parameters.get('required_duration_hours', 0)
    incentive_for_lookup = event_parameters.get('incentive_percentage', 0) * 100
    reality_discount_factor = simulation_assumptions.get('reality_discount_factor', 1.0)
    payback_model_config = simulation_assumptions.get('payback_model', {})

    if df_load_profiles is None or df_load_profiles.empty:
        print("FEHLER: Leere Lastprofile übergeben. Simulation wird abgebrochen.")
        cols = list(shift_metrics.keys()) if shift_metrics else []
        return {
            "df_shiftable_per_appliance": pd.DataFrame(columns=cols, dtype=float),
            "df_payback_per_appliance": pd.DataFrame(columns=cols, dtype=float),
            "total_shifted_energy_kwh": 0.0,
            "shifted_energy_per_device_kwh": {}
        }
    
    df_shiftable_per_appliance = pd.DataFrame(0.0, index=df_load_profiles.index, columns=df_load_profiles.columns, dtype=float)
    df_payback_per_appliance = pd.DataFrame(0.0, index=df_load_profiles.index, columns=df_load_profiles.columns, dtype=float)
    
    try:
        event_timestamps_mask = (df_load_profiles.index >= event_start_time) & (df_load_profiles.index < event_end_time)
        event_timestamps = df_load_profiles[event_timestamps_mask].index
    except Exception as e:
        print(f"FEHLER beim Filtern der Event-Zeitstempel: {e}.")
        return {
            "df_shiftable_per_appliance": df_shiftable_per_appliance,
            "df_payback_per_appliance": df_payback_per_appliance,
            "total_shifted_energy_kwh": 0.0,
            "shifted_energy_per_device_kwh": {}
        }
        
    if event_timestamps.empty:
        print("WARNUNG: Keine Zeitstempel im Event-Fenster gefunden.")
        return {
            "df_shiftable_per_appliance": df_shiftable_per_appliance,
            "df_payback_per_appliance": df_payback_per_appliance,
            "total_shifted_energy_kwh": 0.0,
            "shifted_energy_per_device_kwh": {}
        }

    print(f"\n[REDUKTION] Simuliere für {len(event_timestamps)} Zeitstempel im Event-Fenster von {event_start_time} bis {event_end_time}...")

    for dev in df_load_profiles.columns:
        verbose_print = (debug_device_name is None and len(df_load_profiles.columns) < 4) or (dev == debug_device_name)
        if verbose_print: print(f"\n  --- Gerät: {dev} ---")

        if dev not in shift_metrics or dev not in df_participation_curve_q10['device'].unique():
            if verbose_print: print(f"    WARNUNG: Fehlende Daten für Gerät '{dev}'. Überspringe.")
            continue
        
        # ... (Logik für p_participate_incentive, p_duration_ok, p_effective_real wie in deinem Code) ...
        device_q10_data = df_participation_curve_q10[df_participation_curve_q10['device'] == dev].sort_values(by='comp_pct')
        p_participate_incentive = 0.0
        if not device_q10_data.empty:
            participation_at_incentive = np.interp(incentive_for_lookup, device_q10_data['comp_pct'], device_q10_data['participation_pct'])
            p_participate_incentive = participation_at_incentive / 100.0
        if verbose_print: print(f"    p_participate_incentive (Q10, für {incentive_for_lookup:.0f}% Anreiz): {p_participate_incentive:.4f}")

        dev_shift_metrics = shift_metrics[dev]
        lognorm_s, lognorm_scale_val = dev_shift_metrics.get('lognorm_shape'), dev_shift_metrics.get('lognorm_scale')
        p_duration_ok = 0.0
        if not (pd.isna(lognorm_s) or pd.isna(lognorm_scale_val) or required_duration_hours <= 0):
            try:
                p_duration_ok = 1 - lognorm.cdf(required_duration_hours, s=lognorm_s, loc=0, scale=lognorm_scale_val)
            except Exception as e:
                if verbose_print: print(f"    Fehler bei lognorm.cdf: {e}")
                p_duration_ok = 0.0
        if verbose_print: print(f"    p_duration_ok (Q9, für {required_duration_hours}h Dauer): {p_duration_ok:.4f}")

        p_combined = p_participate_incentive * p_duration_ok
        p_effective_real = p_combined * reality_discount_factor
        if verbose_print: print(f"    p_combined: {p_combined:.4f}, p_effective_real (mit Discount {reality_discount_factor:.2f}): {p_effective_real:.4f}")

        if p_effective_real <= 0:
            if verbose_print: print(f"    Keine effektive Teilnahme für {dev}, p_effective_real ist <= 0.")
            continue

        device_total_shifted_kw_sum_for_print = 0 # Nur für Print-Zwecke
        for t in event_timestamps:
            current_load_dev_t = df_load_profiles.loc[t, dev]
            if current_load_dev_t > 0:
                shiftable_load_dev_t = current_load_dev_t * p_effective_real
                df_shiftable_per_appliance.loc[t, dev] = shiftable_load_dev_t
                device_total_shifted_kw_sum_for_print += shiftable_load_dev_t
        
        if verbose_print: print(f"    Summe der verschiebbaren Leistungswerte für {dev} im Event: {device_total_shifted_kw_sum_for_print:.2f} kW (über {len(event_timestamps)} Intervalle)")


    print(f"\n[REDUKTION] Zusammenfassung df_shiftable_per_appliance (Summe kW-Werte pro Gerät über Event-Dauer):")
    print(df_shiftable_per_appliance.loc[event_timestamps].sum())
    print(f"[REDUKTION] Gesamtsumme verschiebbarer Leistungswerte über alle Geräte und Event-Dauer: {df_shiftable_per_appliance.loc[event_timestamps].sum().sum():.2f} kW")


    # --- PAYBACK BERECHNEN UND MODELLIEREN PRO GERÄT ---
    print("\n[PAYBACK] Starte Payback-Berechnung...")
    dt_h = 0 # Muss hier neu initialisiert und berechnet werden
    if len(df_load_profiles.index) > 1 and isinstance(df_load_profiles.index, pd.DatetimeIndex):
        dt_h = (df_load_profiles.index[1] - df_load_profiles.index[0]).total_seconds() / 3600
    elif len(df_load_profiles.index) == 1:
         dt_h = 1.0 # Oder eine andere Annahme für Einzelpunkt-Profile
    
    print(f"  Intervalldauer für Energieberechnung (dt_h): {dt_h:.4f} Stunden")

    # Die shifted_energy_kwh_dev Berechnung muss NACH dem Befüllen von df_shiftable_per_appliance
    # und NACH der Berechnung von dt_h erfolgen.
    # Dieser Block wird weiter unten platziert, vor dem return.

    if dt_h > 0:
        for dev in df_load_profiles.columns:
            # ... (Rest der Payback-Logik wie in deinem Code, das ist korrekt platziert) ...
            verbose_print = (debug_device_name is None and len(df_load_profiles.columns) < 4) or (dev == debug_device_name)
            if verbose_print and dev in df_shiftable_per_appliance.columns: print(f"  --- Payback für Gerät: {dev} ---")

            if dev not in df_shiftable_per_appliance.columns: continue # Sicherstellen

            # WICHTIG: shifted_energy_kwh_dev wird hier für jedes Gerät *innerhalb* der Payback-Schleife berechnet
            current_device_shifted_power_sum = df_shiftable_per_appliance[dev].loc[event_timestamps].sum() # Nur Summe über Event-Zeitstempel
            shifted_energy_kwh_dev = current_device_shifted_power_sum * dt_h
            if verbose_print: print(f"    Verschobene Energie für {dev}: {shifted_energy_kwh_dev:.2f} kWh")

            if shifted_energy_kwh_dev <= 0:
                if verbose_print: print(f"    Keine Energie für {dev} verschoben, kein Payback.")
                continue

            payback_type = payback_model_config.get('type', 'none')
            payback_duration_hours_config = payback_model_config.get('duration_hours', required_duration_hours)
            if isinstance(payback_duration_hours_config, pd.Timedelta):
                 payback_duration_hours = payback_duration_hours_config.total_seconds() / 3600
            else:
                 payback_duration_hours = float(payback_duration_hours_config)

            payback_delay_hours = payback_model_config.get('delay_hours', 0)
            if verbose_print: print(f"    Payback Modell: Typ={payback_type}, Dauer={payback_duration_hours:.2f}h, Delay={payback_delay_hours:.2f}h")

            if payback_type == 'uniform_after_event' and payback_duration_hours > 0:
                payback_start_time = event_end_time + pd.Timedelta(hours=payback_delay_hours)
                payback_end_time_exclusive = payback_start_time + pd.Timedelta(hours=payback_duration_hours)
                if verbose_print: print(f"    Payback-Fenster: {payback_start_time} bis {payback_end_time_exclusive}")
                
                payback_power_kw_dev = shifted_energy_kwh_dev / payback_duration_hours
                if verbose_print: print(f"    Payback-Leistung für {dev}: {payback_power_kw_dev:.2f} kW")

                payback_timestamps_mask = (df_payback_per_appliance.index >= payback_start_time) & \
                                          (df_payback_per_appliance.index < payback_end_time_exclusive)

                if payback_timestamps_mask.any():
                    df_payback_per_appliance.loc[payback_timestamps_mask, dev] += payback_power_kw_dev
                    if verbose_print: print(f"    Payback für {dev} erfolgreich in Zeitfenster eingetragen.")
                else:
                    if verbose_print: print(f"    WARNUNG: Payback-Zeitfenster für Gerät {dev} liegt außerhalb des Datenbereichs oder ist leer.")
            elif payback_type == 'none':
                if verbose_print: print(f"    Kein Payback ('none') für {dev} angewendet.")
            else:
                if verbose_print: print(f"    WARNUNG: Unbekannter Payback-Modell-Typ für Gerät {dev}: {payback_type}")
    else:
        print("WARNUNG: Intervalldauer dt_h ist 0 oder Index nicht bestimmbar, Payback kann nicht berechnet werden.")
    
    print(f"\n[PAYBACK] Zusammenfassung df_payback_per_appliance (Summe kW-Werte pro Gerät über Payback-Dauer):")
    print(df_payback_per_appliance.sum()) 
    print(f"[PAYBACK] Gesamtsumme Payback-Leistungswerte über alle Geräte und Payback-Dauer: {df_payback_per_appliance.sum().sum():.2f} kW")

    # --- BERECHNUNG DER GESAMTEN VERSCHOBENEN ENERGIE UND PRO GERÄT (JETZT AN DER RICHTIGEN STELLE) ---
    shifted_energy_per_device_kwh = {}
    total_shifted_energy_all_devices_kwh = 0.0
    if dt_h > 0 and not df_shiftable_per_appliance.empty:
        # Summiere nur über die Spalten (Geräte), die auch in df_load_profiles und somit in df_shiftable_per_appliance sind
        for dev_calc in df_shiftable_per_appliance.columns: 
            # Wichtig: .sum() hier summiert alle Leistungswerte im Event-Zeitfenster für das Gerät
            energy_dev = df_shiftable_per_appliance[dev_calc].loc[event_timestamps].sum() * dt_h
            shifted_energy_per_device_kwh[dev_calc] = energy_dev
            total_shifted_energy_all_devices_kwh += energy_dev
    # Diese Print-Ausgabe ist jetzt genauer, da sie nach allen Berechnungen erfolgt.
    print(f"\n[INFO] Gesamte verschobene Energie über alle Geräte (final): {total_shifted_energy_all_devices_kwh:.2f} kWh")

    print("\n===================================================================")
    print("---- run_load_shifting_simulation (pro Gerät) ABGESCHLOSSEN ----")
    print("===================================================================")
    return {
        "df_shiftable_per_appliance": df_shiftable_per_appliance,
        "df_payback_per_appliance": df_payback_per_appliance,
        "total_shifted_energy_kwh": total_shifted_energy_all_devices_kwh,
        "shifted_energy_per_device_kwh": shifted_energy_per_device_kwh
    }