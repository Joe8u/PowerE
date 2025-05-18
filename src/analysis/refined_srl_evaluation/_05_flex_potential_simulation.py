# PowerE/src/analysis/refined_srl_evaluation/_05_flex_potential_simulation.py
"""
Simuliert das umfragebasierte Flexibilitätspotenzial für Geschirrspüler
an ausgewählten Top-DR-Tagen. Berücksichtigt detaillierte SRL-Preise,
JASM-Lastprofile (in MW) und spezifische DR-Programmregeln.
"""
import pandas as pd
import datetime
from pathlib import Path
import sys
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
# --- BEGINN: Überarbeitetes Pfad-Setup ---
try:
    CURRENT_SCRIPT_PATH = Path(__file__).resolve()
    PROJECT_ROOT = CURRENT_SCRIPT_PATH.parent.parent.parent.parent
except NameError:
    PROJECT_ROOT = Path.cwd()
    print(f"[WARNUNG] __file__ nicht definiert. PROJECT_ROOT als aktuelles Arbeitsverzeichnis angenommen: {PROJECT_ROOT}")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    print(f"[Path Setup] Projekt-Root '{PROJECT_ROOT}' zum sys.path hinzugefügt.")
# --- ENDE: Überarbeitetes Pfad-Setup ---

# --- BEGINN: Überarbeitete Importe (alle von src ausgehend) ---
try:
    from src.analysis.refined_srl_evaluation._01_srl_peak_price_finder import find_top_srl_price_periods
    from src.analysis.refined_srl_evaluation._02_jasm_dishwasher_80pct_energy_window_finder import find_shortest_80pct_energy_window
    from src.analysis.refined_srl_evaluation._03_dr_day_identifier import identify_dr_candidate_days
    from src.analysis.refined_srl_evaluation._04_dr_day_ranker import calculate_ranking_metrics_for_days
    from src.data_loader.tertiary_regulation_loader import load_regulation_range
    from src.data_loader.lastprofile import load_appliances as load_jasm_year_profile
    from src.logic.respondent_level_model.flexibility_potential.a_survey_data_preparer import prepare_survey_flexibility_data
    from src.logic.respondent_level_model.flexibility_potential.b_participation_calculator import calculate_participation_metrics
except ImportError as e:
    print(f"FEHLER beim Importieren der Projektmodule: {e}")
    print("Stellen Sie sicher, dass alle __init__.py Dateien in den entsprechenden src Unterordnern vorhanden sind.")
    print(f"Aktueller sys.path: {sys.path}")
    sys.exit(1)
# --- ENDE: Überarbeitete Importe ---

def get_data_for_specific_window(
    df_timeseries: pd.DataFrame,
    start_utc: pd.Timestamp,
    end_utc: pd.Timestamp,
    value_column: str
) -> pd.Series:
    """Extrahiert Daten für ein spezifisches Zeitfenster aus einer Zeitreihe."""
    if df_timeseries is None or df_timeseries.empty:
        return pd.Series(dtype=float)
    mask = (df_timeseries.index >= start_utc) & (df_timeseries.index <= end_utc)
    return df_timeseries.loc[mask, value_column]

if __name__ == '__main__':
    print("--- Step 5: Simulation des umfragebasierten Flexibilitätspotenzials ---")

    # --- Globale Parameter ---
    TARGET_YEAR = 2024
    N_TOP_SRL_FOR_PIPELINE = 150
    APPLIANCE_NAME = "Geschirrspüler"
    ENERGY_THRESHOLD_JASM_WINDOW = 70.0
    TIME_RESOLUTION_JASM_WINDOW = 15
    INTERVAL_DURATION_HOURS = TIME_RESOLUTION_JASM_WINDOW / 60.0

    ENERGY_PER_DISHWASHER_EVENT_KWH = 8
    BASE_PRICE_CHF_KWH_COMPENSATION = 0.29
    MAX_PARTICIPATION_CAP = 0.629

    PRE_PEAK_START_OFFSETS_H = [2.0, 1.0, 0.0]
    DR_EVENT_TOTAL_DURATIONS_H = [1.5, 30]
    COMPENSATION_PERCENTAGES_TO_SIMULATE = [0.0, 1, 2, 3, 4, 5, 6] # Anpassung auf floats
    NUM_TOP_DAYS_TO_SIMULATE_FROM_STEP4 = 3

    srl_year_start_utc = datetime.datetime(TARGET_YEAR, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    srl_year_end_utc = datetime.datetime(TARGET_YEAR, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)

    print("\n[Phase 0/5] Lade Jahres-Zeitreihendaten...")
    print("  Lade komplette SRL-Preisdaten...")
    df_srl_all_year_raw = pd.DataFrame()
    try:
        print("  Versuch 1: Lade SRL-Daten mit naiven Start/End-Zeiten...")
        srl_year_start_naive = datetime.datetime(TARGET_YEAR, 1, 1, 0, 0, 0)
        srl_year_end_naive = datetime.datetime(TARGET_YEAR, 12, 31, 23, 59, 59)
        df_srl_all_year_raw = load_regulation_range(start=srl_year_start_naive, end=srl_year_end_naive)
    except TypeError:
        print("  WARNUNG: TypeError bei Versuch mit naiven Start/End-Zeiten für SRL-Daten.")
        print("  Versuch 2: Lade SRL-Daten mit UTC-awaren Start/End-Zeiten (Fallback)...")
        try:
            df_srl_all_year_raw = load_regulation_range(start=srl_year_start_utc, end=srl_year_end_utc)
        except Exception as e_utc_attempt:
            import traceback
            sys.exit(f"FEHLER: Beide Ladeversuche für SRL-Daten fehlgeschlagen. Fehler bei UTC-Versuch: {e_utc_attempt}\n{traceback.format_exc()}")
    except Exception as e_initial_load:
        import traceback
        sys.exit(f"ALLGEMEINER FEHLER beim initialen Laden der SRL-Daten: {e_initial_load}\n{traceback.format_exc()}")

    if df_srl_all_year_raw.empty or 'avg_price_eur_mwh' not in df_srl_all_year_raw.columns:
        sys.exit("FEHLER: SRL-Daten konnten nicht geladen werden oder Preisspalte fehlt.")
    df_srl_all_year = df_srl_all_year_raw[['avg_price_eur_mwh']].copy()
    df_srl_all_year['srl_price_chf_kwh'] = df_srl_all_year['avg_price_eur_mwh'] / 1000.0
    df_srl_all_year.index = pd.to_datetime(df_srl_all_year.index)
    if df_srl_all_year.index.tz is None:
        try:
            df_srl_all_year.index = df_srl_all_year.index.tz_localize('Europe/Zurich', ambiguous='infer', nonexistent='shift_forward').tz_convert('UTC')
        except Exception:
            df_srl_all_year.index = df_srl_all_year.index.tz_localize('UTC', ambiguous='infer', nonexistent='shift_forward')
    else:
        df_srl_all_year.index = df_srl_all_year.index.tz_convert('UTC')
    if df_srl_all_year.empty: sys.exit("FEHLER: SRL-Daten nach TZ-Konvertierung leer.")
    print(f"  SRL-Daten erfolgreich zu UTC konvertiert. Index-Beispiel: {df_srl_all_year.index[0] if not df_srl_all_year.empty else 'N/A'}")

    print(f"  Lade komplette JASM-Daten (ursprünglich stündlich in MW) für '{APPLIANCE_NAME}'...")
    df_jasm_hourly_mw_raw = pd.DataFrame() # Initialisieren
    try:
        # Ladeversuche (wie im letzten Vorschlag, um df_jasm_hourly_mw_raw zu füllen)
        print("  Versuch 1: Lade JASM-Daten mit naiven Start/End-Zeiten...")
        srl_year_start_naive = datetime.datetime(TARGET_YEAR, 1, 1, 0, 0, 0)
        srl_year_end_naive = datetime.datetime(TARGET_YEAR, 12, 31, 23, 59, 59)
        df_jasm_hourly_mw_raw = load_jasm_year_profile(
            appliances=[APPLIANCE_NAME], start=srl_year_start_naive, end=srl_year_end_naive,
            year=TARGET_YEAR, group=True # group=True, falls APPLIANCE_NAME eine Gruppe ist
        )
    except TypeError:
        print("  WARNUNG: TypeError bei JASM-Ladeversuch mit naiven Zeiten.")
        print("  Versuch 2: Lade JASM-Daten mit UTC-awaren Start/End-Zeiten (Fallback)...")
        try:
            df_jasm_all_year_mw = load_jasm_year_profile(
                appliances=[APPLIANCE_NAME], start=srl_year_start_utc, end=srl_year_end_utc,
                year=TARGET_YEAR, group=True
            )
        except Exception as e_jasm_utc:
            import traceback
            sys.exit(f"FEHLER: Beide Ladeversuche für JASM-Daten fehlgeschlagen. Fehler bei UTC-Versuch: {e_jasm_utc}\n{traceback.format_exc()}")
    except Exception as e_jasm_initial_load: # Generische Exception für Ladefehler
        import traceback
        sys.exit(f"ALLGEMEINER FEHLER beim Laden der JASM-Rohdaten: {e_jasm_initial_load}\n{traceback.format_exc()}")

    if df_jasm_hourly_mw_raw.empty or APPLIANCE_NAME not in df_jasm_hourly_mw_raw.columns:
        sys.exit(f"FEHLER: JASM-Rohdaten für '{APPLIANCE_NAME}' konnten nicht geladen werden oder Spalte fehlt.")
    
    # Nur die relevante Spalte und Index zu Datetime konvertieren
    df_jasm_hourly_mw = df_jasm_hourly_mw_raw[[APPLIANCE_NAME]].copy()
    df_jasm_hourly_mw.index = pd.to_datetime(df_jasm_hourly_mw.index)

    # Zeitzonenbehandlung für den stündlichen DataFrame
    if df_jasm_hourly_mw.index.tz is None:
        print("  JASM-Stunden-Datenindex (MW) ist tz-naiv. Annahme: Repräsentiert 'Europe/Zurich'. Lokalisiere und konvertiere zu UTC...")
        try:
            df_jasm_hourly_mw.index = df_jasm_hourly_mw.index.tz_localize('Europe/Zurich', ambiguous='infer', nonexistent='shift_forward').tz_convert('UTC')
        except Exception as e_tz_jasm:
            print(f"    Fehler beim Lokalisieren des JASM-Stunden-Index mit 'Europe/Zurich': {e_tz_jasm}. Versuche Lokalisierung als UTC...")
            df_jasm_hourly_mw.index = df_jasm_hourly_mw.index.tz_localize('UTC', ambiguous='infer', nonexistent='shift_forward')
    else:
        print(f"  JASM-Stunden-Datenindex (MW) hat bereits Zeitzone: {df_jasm_hourly_mw.index.tz}. Konvertiere zu UTC...")
        df_jasm_hourly_mw.index = df_jasm_hourly_mw.index.tz_convert('UTC')
    
    if df_jasm_hourly_mw.empty:
        sys.exit("FEHLER: JASM-Stunden-Daten (MW) nach TZ-Konvertierung leer.")
    print(f"  JASM-Stunden-Daten (MW) erfolgreich zu UTC konvertiert. Index-Beispiel: {df_jasm_hourly_mw.index[0] if not df_jasm_hourly_mw.empty else 'N/A'}")

    # RESAMPLE JASM-DATEN VON STÜNDLICH AUF 15-MINUTEN-FREQUENZ (FORWARD FILL)
    print(f"  Resample JASM-Daten (MW) von stündlich auf 15-Minuten-Frequenz (ffill)...")
    df_jasm_15min_mw = df_jasm_hourly_mw.resample('15min').ffill()
    # Sicherstellen, dass die Zeitzoneninformation beim Resampling erhalten bleibt oder korrekt gesetzt wird
    if df_jasm_15min_mw.index.tz is None and df_jasm_hourly_mw.index.tz is not None:
         df_jasm_15min_mw.index = df_jasm_15min_mw.index.tz_localize(df_jasm_hourly_mw.index.tz)
    elif df_jasm_15min_mw.index.tz != df_jasm_hourly_mw.index.tz and df_jasm_hourly_mw.index.tz is not None:
         df_jasm_15min_mw.index = df_jasm_15min_mw.index.tz_convert(df_jasm_hourly_mw.index.tz)
    print(f"  JASM-Daten (MW) auf 15-Minuten-Frequenz resampelt. Index-Beispiel: {df_jasm_15min_mw.index[0] if not df_jasm_15min_mw.empty else 'N/A'}")

    # Berechne Energie pro 15-Minuten-Intervall in MWh
    # INTERVAL_DURATION_HOURS ist global als 0.25 (15/60) definiert
    df_jasm_15min_mwh = df_jasm_15min_mw.copy()
    df_jasm_15min_mwh[f'{APPLIANCE_NAME}_mwh_interval'] = df_jasm_15min_mwh[APPLIANCE_NAME] * INTERVAL_DURATION_HOURS # MW * 0.25h = MWh
    
    print("\n[Phase 1/5] Lade aufbereitete Umfragedaten...")
    df_survey_prepared = prepare_survey_flexibility_data()
    if df_survey_prepared.empty: sys.exit("FEHLER: Keine Umfragedaten geladen.")

    print("\n[Phase 2/5] Führe Analyse-Pipeline (Steps 1-4) durch...")
    df_srl_peaks_for_pipeline = find_top_srl_price_periods(TARGET_YEAR, N_TOP_SRL_FOR_PIPELINE)
    if df_srl_peaks_for_pipeline is None or df_srl_peaks_for_pipeline.empty: sys.exit("FEHLER: Pipeline Step 1.")
    df_srl_peaks_for_pipeline.index = pd.to_datetime(df_srl_peaks_for_pipeline.index)
    if df_srl_peaks_for_pipeline.index.tz is None:
        df_srl_peaks_for_pipeline.index = df_srl_peaks_for_pipeline.index.tz_localize('UTC', ambiguous='infer', nonexistent='shift_forward')
    else:
        df_srl_peaks_for_pipeline.index = df_srl_peaks_for_pipeline.index.tz_convert('UTC')

    srl_peak_dates_for_jasm_window_id = sorted(list(set(df_srl_peaks_for_pipeline.index.normalize().date)))
    if not srl_peak_dates_for_jasm_window_id: sys.exit("FEHLER: Pipeline Step 2a.")
    appliance_windows_for_pipeline = find_shortest_80pct_energy_window(TARGET_YEAR, APPLIANCE_NAME, srl_peak_dates_for_jasm_window_id, ENERGY_THRESHOLD_JASM_WINDOW, TIME_RESOLUTION_JASM_WINDOW)
    
    candidate_days_step3 = identify_dr_candidate_days(df_srl_peaks_for_pipeline, appliance_windows_for_pipeline)
    if not candidate_days_step3:
        print("INFO: Pipeline Step 3 - Keine Kandidatentage gefunden.") # Weniger aggressiv bei leerem Ergebnis
        
    ranked_days_step4_output = calculate_ranking_metrics_for_days(candidate_days_step3, df_srl_peaks_for_pipeline, appliance_windows_for_pipeline)
    if not ranked_days_step4_output:
        print("INFO: Pipeline Step 4 - Keine gerankten Tage.")

    days_to_simulate_in_detail = []
    if ranked_days_step4_output: # Nur fortfahren, wenn es gerankte Tage gibt
        for day_rank_info in ranked_days_step4_output[:NUM_TOP_DAYS_TO_SIMULATE_FROM_STEP4]:
            day_date_obj = day_rank_info['date']
            peaks_on_that_day_in_window = df_srl_peaks_for_pipeline[
                (df_srl_peaks_for_pipeline.index.normalize().date == day_date_obj) &
                (np.isclose(df_srl_peaks_for_pipeline['price_chf_kwh'], day_rank_info['max_srl_price_in_window']))
            ]
            if not peaks_on_that_day_in_window.empty:
                reference_peak_ts_utc = pd.to_datetime(peaks_on_that_day_in_window.index[0], utc=True)
                days_to_simulate_in_detail.append({
                    "date_obj": day_date_obj,
                    "rank_step4": ranked_days_step4_output.index(day_rank_info) + 1,
                    "reference_peak_utc_timestamp": reference_peak_ts_utc,
                })
            else:
                 print(f"WARNUNG: Konnte Referenz-Peak-Timestamp für {day_date_obj} nicht exakt bestimmen.")
    
    if not days_to_simulate_in_detail:
        print(f"Keine Tage für detaillierte Simulation vorbereitet. Überprüfe Pipeline-Ergebnisse oder Auswahlkriterien.")
        # sys.exit() # Nicht unbedingt abbrechen, die Simulation wird dann einfach keine Ergebnisse liefern

    print(f"\n[Phase 3/5] Starte detaillierte Simulation für {len(days_to_simulate_in_detail)} Top-Tag(e)...")
    all_simulation_scenario_results = []

    for day_scenario_info in days_to_simulate_in_detail:
        event_date = day_scenario_info["date_obj"]
        reference_peak_ts = day_scenario_info["reference_peak_utc_timestamp"]
        print(f"  Simuliere für Tag: {event_date.strftime('%Y-%m-%d')} (Referenz-Peak um {reference_peak_ts.strftime('%H:%M')} UTC)")

        for pre_offset_h in PRE_PEAK_START_OFFSETS_H:
            for event_total_duration_h in DR_EVENT_TOTAL_DURATIONS_H:
                event_start_utc = reference_peak_ts - datetime.timedelta(hours=pre_offset_h)
                event_end_utc = event_start_utc + datetime.timedelta(hours=event_total_duration_h) - datetime.timedelta(minutes=TIME_RESOLUTION_JASM_WINDOW)
                
                jasm_load_in_event_window_mwh_series = get_data_for_specific_window(
                    df_jasm_15min_mwh, event_start_utc, event_end_utc, f'{APPLIANCE_NAME}_mwh_interval' # KORRIGIERT
                )
                srl_prices_in_event_window_chf_kwh_series = get_data_for_specific_window(
                    df_srl_all_year, event_start_utc, event_end_utc, 'srl_price_chf_kwh'
                )

                if jasm_load_in_event_window_mwh_series.empty or \
                   srl_prices_in_event_window_chf_kwh_series.empty or \
                   len(jasm_load_in_event_window_mwh_series) != len(srl_prices_in_event_window_chf_kwh_series):
                    continue
                
                total_jasm_load_in_event_mwh = jasm_load_in_event_window_mwh_series.sum() # Jetzt MWh
                if total_jasm_load_in_event_mwh <= 0:
                    continue

                for offered_comp_pct in COMPENSATION_PERCENTAGES_TO_SIMULATE:
                    participation_details = calculate_participation_metrics(
                        df_survey_flex_input=df_survey_prepared,
                        target_appliance=APPLIANCE_NAME,
                        event_duration_h=event_total_duration_h,
                        offered_incentive_pct=offered_comp_pct
                    )
                    raw_rate = participation_details['raw_participation_rate']
                    final_rate = min(raw_rate, MAX_PARTICIPATION_CAP)

                    aligned_jasm_mwh, aligned_srl_chf_kwh = jasm_load_in_event_window_mwh_series.align(srl_prices_in_event_window_chf_kwh_series, join='inner')
                    
                    dispatched_energy_per_interval_mwh = aligned_jasm_mwh * final_rate
                    total_dispatched_energy_mwh = dispatched_energy_per_interval_mwh.sum() # Jetzt MWh
                    
                    # Umrechnung von MWh in kWh für Kostenberechnung mit CHF/kWh Preisen
                    avoided_costs_chf = (dispatched_energy_per_interval_mwh * 1000 * aligned_srl_chf_kwh).sum() # Korrigierte Berechnung

                    compensation_chf_per_hh_event = 0.0
                    if ENERGY_PER_DISHWASHER_EVENT_KWH is not None:
                         monthly_base_cost = ENERGY_PER_DISHWASHER_EVENT_KWH * BASE_PRICE_CHF_KWH_COMPENSATION
                         compensation_chf_per_hh_event = monthly_base_cost * (offered_comp_pct / 100.0)
                    
                    num_survey_participants_final = int(round(final_rate * participation_details['base_population']))
                    
                    # ANNAHME für aggregierten Netto-Nutzen (benötigt Schätzung für Gesamtzahl der Haushalte)
                    TOTAL_HOUSEHOLDS_WITH_APPLIANCE_CH = 2400000 # Beispiel! Muss validiert werden.
                    num_participating_households_total_ch = final_rate * TOTAL_HOUSEHOLDS_WITH_APPLIANCE_CH
                    total_compensation_costs_ch = num_participating_households_total_ch * compensation_chf_per_hh_event
                    net_benefit_chf_total_ch = avoided_costs_chf - total_compensation_costs_ch
                    
                    # Durchschnittliche verschobene Leistung im Event in MW (für 1MW Regel)
                    avg_dispatched_power_mw = 0
                    if event_total_duration_h > 0:
                        avg_dispatched_power_mw = total_dispatched_energy_mwh / event_total_duration_h


                    all_simulation_scenario_results.append({
                        "date": event_date,
                        "rank_step4": day_scenario_info["rank_step4"],
                        "event_start_utc": event_start_utc.strftime('%Y-%m-%d %H:%M'),
                        "event_duration_h": event_total_duration_h,
                        "pre_peak_offset_h": pre_offset_h,
                        "offered_compensation_pct": offered_comp_pct,
                        "final_participation_rate_pct": final_rate * 100,
                        "total_jasm_load_in_event_mwh": total_jasm_load_in_event_mwh, # MWh
                        "total_dispatched_energy_mwh": total_dispatched_energy_mwh, # MWh
                        "avg_dispatched_power_mw": avg_dispatched_power_mw, # MW
                        "avg_srl_price_in_event_chf_kwh": aligned_srl_chf_kwh.mean() if not aligned_srl_chf_kwh.empty else 0,
                        "avoided_srl_costs_chf": avoided_costs_chf,
                        "compensation_chf_per_hh_simulated": compensation_chf_per_hh_event,
                        "total_compensation_ch_estimate": total_compensation_costs_ch, # Für die Schweiz geschätzt
                        "net_benefit_chf_total_ch_estimate": net_benefit_chf_total_ch # Für die Schweiz geschätzt
                    })

    print("\n[Phase 4/5] Verarbeite und zeige Simulationsergebnisse...")
    if all_simulation_scenario_results:
        df_sim_results = pd.DataFrame(all_simulation_scenario_results)
        df_sim_results = df_sim_results.sort_values(by=[
            "rank_step4", "date", "pre_peak_offset_h", "event_duration_h", "offered_compensation_pct"
        ])
        
        print("\n\n--- Detaillierte Simulationsergebnisse ---")
        pd.set_option('display.max_rows', None)
        pd.set_option('display.width', 300) # Breite erhöht
        
        for (event_date_str_key, offset, duration), group in df_sim_results.groupby(['event_start_utc', 'pre_peak_offset_h', 'event_duration_h']):
            event_d_obj = pd.to_datetime(event_date_str_key).date()
            rank = group['rank_step4'].iloc[0]
            print(f"\nTag: {event_d_obj.strftime('%Y-%m-%d')} (Rank {rank}), Event Start UTC: {event_date_str_key}, Offset: {offset}h, Dauer: {duration}h")
            print(f"  JASM Last im Event: {group['total_jasm_load_in_event_mwh'].iloc[0]:.3f} MWh, Ø SRL Preis: {group['avg_srl_price_in_event_chf_kwh'].iloc[0]:.4f} CHF/kWh")
            print(f"  {'Anreiz(%)':<10} | {'Teiln.(%)':<10} | {'Versch.MWh':<11} | {'Versch.MW(Ø)':<13} | {'Verm.Kosten':<12} | {'Komp./HH':<9} | {'NettoNutzen CH':<15}")
            print("  " + "-" * 115) # Länge angepasst
            for _, row in group.iterrows():
                print(f"  {row['offered_compensation_pct']:<10.1f} | "
                      f"{row['final_participation_rate_pct']:<10.1f} | "
                      f"{row['total_dispatched_energy_mwh']:<11.3f} | "
                      f"{row['avg_dispatched_power_mw']:<13.3f} | "
                      f"{row['avoided_srl_costs_chf']:<12.2f} | "
                      f"{row['compensation_chf_per_hh_simulated']:<9.2f} | "
                      f"{row['net_benefit_chf_total_ch_estimate']:<15.2f}")
        
        try:
            if 'SCRIPT_DIR_STEP5' not in locals() and '__file__' in locals(): SCRIPT_DIR_STEP5 = Path(__file__).resolve().parent
            elif 'SCRIPT_DIR_STEP5' not in locals(): SCRIPT_DIR_STEP5 = Path.cwd()
            results_path = SCRIPT_DIR_STEP5 / "_05_simulation_results_MWh_NetBenefitCH.csv"
            df_sim_results.to_csv(results_path, index=False, sep=';', decimal='.')
            print(f"\nSimulationsergebnisse gespeichert unter: {results_path}")
        except Exception as e_save:
            print(f"\nFehler beim Speichern der Ergebnisse: {e_save}")
    else:
        print("\nKeine Simulationsergebnisse erzeugt.")

    print("\n--- Simulation (Step 5) beendet. ---")