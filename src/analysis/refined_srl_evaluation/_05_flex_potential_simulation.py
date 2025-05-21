# PowerE/src/analysis/refined_srl_evaluation/_05_flex_potential_simulation.py
"""
Simuliert das umfragebasierte Flexibilitätspotenzial für Geschirrspüler
an ausgewählten Top-DR-Tagen. Berücksichtigt detaillierte SRL-Preise,
JASM-Lastprofile (in MW) und spezifische DR-Programmregeln.
Erfasst und zeigt nun auch die rohe Teilnahmequote vor Anwendung des Caps,
die potenzielle JASM-Last im Fenster und den durchschnittlichen SRL-Preis im Fenster.
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
    mask = (df_timeseries.index >= start_utc) & (df_timeseries.index < end_utc)
    return df_timeseries.loc[mask, value_column]

if __name__ == '__main__':
    print("--- Step 5: Simulation des umfragebasierten Flexibilitätspotenzials (mit erweiterter Ausgabe) ---")

    # --- Globale Parameter ---
    TARGET_YEAR = 2024
    N_TOP_SRL_FOR_PIPELINE = 150
    APPLIANCE_NAME = "Geschirrspüler"
    ENERGY_THRESHOLD_JASM_WINDOW = 70.0
    TIME_RESOLUTION_JASM_WINDOW = 15
    INTERVAL_DURATION_HOURS = TIME_RESOLUTION_JASM_WINDOW / 60.0

    DISHWASHER_MONTHLY_ENERGY_PER_HOUSEHOLD_KWH = 8.0
    BASE_PRICE_CHF_KWH_COMPENSATION = 0.29
    MAX_PARTICIPATION_CAP = 0.629

    PRE_PEAK_START_OFFSETS_H = [2.0, 1.0, 0.0]
    DR_EVENT_TOTAL_DURATIONS_H = [1.5, 3.0, 4.5]

    NUM_TOP_DAYS_TO_SIMULATE_FROM_STEP4 = 3

    # ... (Datenladephase und Pipeline-Phasen 0-2 bleiben unverändert wie im letzten funktionierenden Stand) ...
    srl_year_start_utc = datetime.datetime(TARGET_YEAR, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    srl_year_end_utc = datetime.datetime(TARGET_YEAR, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)

    print("\n[Phase 0/5] Lade Jahres-Zeitreihendaten...")
    print("  Lade komplette SRL-Preisdaten...")
    df_srl_all_year_raw = pd.DataFrame()
    try:
        srl_year_start_naive = datetime.datetime(TARGET_YEAR, 1, 1, 0, 0, 0)
        srl_year_end_naive = datetime.datetime(TARGET_YEAR, 12, 31, 23, 59, 59)
        df_srl_all_year_raw = load_regulation_range(start=srl_year_start_naive, end=srl_year_end_naive)
    except TypeError:
        print("  WARNUNG: TypeError bei Versuch mit naiven Start/End-Zeiten für SRL-Daten.")
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
    print(f"  SRL-Daten erfolgreich zu UTC konvertiert.")

    print(f"  Lade komplette JASM-Daten für '{APPLIANCE_NAME}'...")
    df_jasm_hourly_mw_raw = pd.DataFrame()
    try:
        srl_year_start_naive = datetime.datetime(TARGET_YEAR, 1, 1, 0, 0, 0)
        srl_year_end_naive = datetime.datetime(TARGET_YEAR, 12, 31, 23, 59, 59)
        df_jasm_hourly_mw_raw = load_jasm_year_profile(
            appliances=[APPLIANCE_NAME], start=srl_year_start_naive, end=srl_year_end_naive,
            year=TARGET_YEAR, group=True
        )
    except TypeError:
        print("  WARNUNG: TypeError bei JASM-Ladeversuch mit naiven Zeiten.")
        try:
            df_jasm_hourly_mw_raw = load_jasm_year_profile(
                appliances=[APPLIANCE_NAME], start=srl_year_start_utc, end=srl_year_end_utc,
                year=TARGET_YEAR, group=True
            )
        except Exception as e_jasm_utc:
            import traceback
            sys.exit(f"FEHLER: Beide Ladeversuche für JASM-Daten fehlgeschlagen. Fehler bei UTC-Versuch: {e_jasm_utc}\n{traceback.format_exc()}")
    except Exception as e_jasm_initial_load:
        import traceback
        sys.exit(f"ALLGEMEINER FEHLER beim Laden der JASM-Rohdaten: {e_jasm_initial_load}\n{traceback.format_exc()}")

    if df_jasm_hourly_mw_raw.empty or APPLIANCE_NAME not in df_jasm_hourly_mw_raw.columns:
        sys.exit(f"FEHLER: JASM-Rohdaten für '{APPLIANCE_NAME}' konnten nicht geladen werden oder Spalte fehlt.")

    df_jasm_hourly_mw = df_jasm_hourly_mw_raw[[APPLIANCE_NAME]].copy()
    df_jasm_hourly_mw.index = pd.to_datetime(df_jasm_hourly_mw.index)

    if df_jasm_hourly_mw.index.tz is None:
        try:
            df_jasm_hourly_mw.index = df_jasm_hourly_mw.index.tz_localize('Europe/Zurich', ambiguous='infer', nonexistent='shift_forward').tz_convert('UTC')
        except Exception as e_tz_jasm:
            print(f"    Fehler beim Lokalisieren des JASM-Stunden-Index mit 'Europe/Zurich': {e_tz_jasm}. Versuche Lokalisierung als UTC...")
            df_jasm_hourly_mw.index = df_jasm_hourly_mw.index.tz_localize('UTC', ambiguous='infer', nonexistent='shift_forward')
    else:
        df_jasm_hourly_mw.index = df_jasm_hourly_mw.index.tz_convert('UTC')

    if df_jasm_hourly_mw.empty:
        sys.exit("FEHLER: JASM-Stunden-Daten (MW) nach TZ-Konvertierung leer.")
    print(f"  JASM-Stunden-Daten (MW) erfolgreich zu UTC konvertiert.")

    print(f"  Resample JASM-Daten (MW) von stündlich auf 15-Minuten-Frequenz (ffill)...")
    df_jasm_15min_mw = df_jasm_hourly_mw.resample('15min').ffill()
    if df_jasm_15min_mw.index.tz is None and df_jasm_hourly_mw.index.tz is not None:
         df_jasm_15min_mw.index = df_jasm_15min_mw.index.tz_localize(df_jasm_hourly_mw.index.tz)
    elif df_jasm_15min_mw.index.tz != df_jasm_hourly_mw.index.tz and df_jasm_hourly_mw.index.tz is not None:
         df_jasm_15min_mw.index = df_jasm_15min_mw.index.tz_convert(df_jasm_hourly_mw.index.tz)
    print(f"  JASM-Daten (MW) auf 15-Minuten-Frequenz resampelt.")

    df_jasm_15min_mwh = df_jasm_15min_mw.copy()
    df_jasm_15min_mwh[f'{APPLIANCE_NAME}_mwh_interval'] = df_jasm_15min_mwh[APPLIANCE_NAME] * INTERVAL_DURATION_HOURS

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
    if not srl_peak_dates_for_jasm_window_id: sys.exit("FEHLER: Pipeline Step 2a (Keine Peak-Tage für JASM-Analyse).")

    appliance_windows_for_pipeline = find_shortest_80pct_energy_window(
        target_year_jasm=TARGET_YEAR,
        appliance_name=APPLIANCE_NAME,
        specific_dates=srl_peak_dates_for_jasm_window_id,
        energy_threshold_pct=ENERGY_THRESHOLD_JASM_WINDOW,
        time_resolution_minutes=TIME_RESOLUTION_JASM_WINDOW
    )

    candidate_days_step3 = identify_dr_candidate_days(df_srl_peaks_for_pipeline, appliance_windows_for_pipeline)
    if not candidate_days_step3:
        print("INFO: Pipeline Step 3 - Keine Kandidatentage gefunden.")

    ranked_days_step4_output = calculate_ranking_metrics_for_days(candidate_days_step3, df_srl_peaks_for_pipeline, appliance_windows_for_pipeline)
    if not ranked_days_step4_output:
        print("INFO: Pipeline Step 4 - Keine gerankten Tage.")

    days_to_simulate_in_detail = []
    if ranked_days_step4_output:
        for rank_idx, day_rank_info in enumerate(ranked_days_step4_output[:NUM_TOP_DAYS_TO_SIMULATE_FROM_STEP4]):
            day_date_obj = day_rank_info['date']
            srl_peaks_on_ranked_day = df_srl_peaks_for_pipeline[
                (df_srl_peaks_for_pipeline.index.normalize().date == day_date_obj)
            ]
            potential_peak_timestamps = srl_peaks_on_ranked_day[
                np.isclose(srl_peaks_on_ranked_day['price_chf_kwh'], day_rank_info['max_srl_price_in_window'])
            ]
            if not potential_peak_timestamps.empty:
                reference_peak_ts_utc = pd.to_datetime(potential_peak_timestamps.index[0], utc=True)
                days_to_simulate_in_detail.append({
                    "date_obj": day_date_obj,
                    "rank_step4": rank_idx + 1,
                    "reference_peak_utc_timestamp": reference_peak_ts_utc,
                    "max_srl_price_in_window_at_peak_rank": day_rank_info['max_srl_price_in_window']
                })
            else:
                 print(f"WARNUNG: Konnte Referenz-Peak-Timestamp für {day_date_obj} mit Preis {day_rank_info['max_srl_price_in_window']} nicht exakt bestimmen.")

    if not days_to_simulate_in_detail:
        print(f"Keine Tage für detaillierte Simulation vorbereitet. Überprüfe Pipeline-Ergebnisse oder Auswahlkriterien.")

    all_simulation_scenario_results = []

    print(f"\n[Phase 3/5] Starte detaillierte Simulation für {len(days_to_simulate_in_detail)} Tag(e), {len(PRE_PEAK_START_OFFSETS_H)} Offset(s), {len(DR_EVENT_TOTAL_DURATIONS_H)} Dauer(en)...")
    for day_info in days_to_simulate_in_detail:
        event_date_obj = day_info["date_obj"]
        reference_peak_ts_utc = day_info["reference_peak_utc_timestamp"]
        print(f"\n--- Starte Simulation für Tag: {event_date_obj.strftime('%Y-%m-%d')} (Rank {day_info['rank_step4']}) ---")
        print(f"  Referenz-SRL-Peak (UTC): {reference_peak_ts_utc.strftime('%Y-%m-%d %H:%M')} mit Preis {day_info['max_srl_price_in_window_at_peak_rank']:.4f} CHF/kWh")

        for pre_offset_h_scenario in PRE_PEAK_START_OFFSETS_H:
            for event_total_duration_h_scenario in DR_EVENT_TOTAL_DURATIONS_H:
                print(f"\n  Szenario: Pre-Peak-Offset: {pre_offset_h_scenario}h, DR-Event-Dauer: {event_total_duration_h_scenario}h")

                event_start_utc = reference_peak_ts_utc - datetime.timedelta(hours=pre_offset_h_scenario)
                event_end_exclusive_utc = event_start_utc + datetime.timedelta(hours=event_total_duration_h_scenario)

                jasm_load_in_event_mwh_series = get_data_for_specific_window(
                    df_jasm_15min_mwh, event_start_utc, event_end_exclusive_utc, f'{APPLIANCE_NAME}_mwh_interval'
                )
                srl_prices_in_event_chf_kwh_series = get_data_for_specific_window(
                    df_srl_all_year, event_start_utc, event_end_exclusive_utc, 'srl_price_chf_kwh'
                )

                # Variable für potenzielle JASM-Last im Fenster berechnen und speichern
                potenzielle_gesamte_jasm_last_event_mwh = jasm_load_in_event_mwh_series.sum() if not jasm_load_in_event_mwh_series.empty else 0.0

                if jasm_load_in_event_mwh_series.empty or \
                   srl_prices_in_event_chf_kwh_series.empty or \
                   len(jasm_load_in_event_mwh_series) != len(srl_prices_in_event_chf_kwh_series):
                    print(f"    FEHLER: Ungültige oder nicht übereinstimmende JASM/SRL-Daten für das Event-Fenster. Überspringe Szenario.")
                    all_simulation_scenario_results.append({
                        "event_date": event_date_obj.strftime('%Y-%m-%d'), "rank_step4": day_info["rank_step4"],
                        "reference_peak_utc": reference_peak_ts_utc.strftime('%Y-%m-%d %H:%M'),
                        "event_start_utc": event_start_utc.strftime('%Y-%m-%d %H:%M'),
                        "event_duration_h": event_total_duration_h_scenario, "pre_peak_offset_h": pre_offset_h_scenario,
                        "potenzielle_jasm_last_im_fenster_mwh": potenzielle_gesamte_jasm_last_event_mwh, # Auch bei Fehler loggen
                        "avg_srl_price_in_window_chf_kwh": srl_prices_in_event_chf_kwh_series.mean() if not srl_prices_in_event_chf_kwh_series.empty else np.nan, # Auch bei Fehler loggen
                        "error_message": "JASM/SRL data mismatch or empty for window"
                    })
                    continue

                # potenzielle_gesamte_jasm_last_event_mwh ist bereits oben berechnet
                if potenzielle_gesamte_jasm_last_event_mwh <= 1e-9: # Prüfen nach der Berechnung
                    print(f"    INFO: Keine JASM-Last ({potenzielle_gesamte_jasm_last_event_mwh:.6f} MWh) für '{APPLIANCE_NAME}' im definierten Event-Fenster. Simulation für dieses Szenario nicht sinnvoll.")
                    all_simulation_scenario_results.append({
                        "event_date": event_date_obj.strftime('%Y-%m-%d'), "rank_step4": day_info["rank_step4"],
                        "reference_peak_utc": reference_peak_ts_utc.strftime('%Y-%m-%d %H:%M'),
                        "event_start_utc": event_start_utc.strftime('%Y-%m-%d %H:%M'),
                        "event_duration_h": event_total_duration_h_scenario, "pre_peak_offset_h": pre_offset_h_scenario,
                        "potenzielle_jasm_last_im_fenster_mwh": potenzielle_gesamte_jasm_last_event_mwh,
                        "avg_srl_price_in_window_chf_kwh": srl_prices_in_event_chf_kwh_series.mean(),
                        "error_message": "No JASM load in event window"
                    })
                    continue

                avg_srl_price_in_window = srl_prices_in_event_chf_kwh_series.mean()
                if pd.isna(avg_srl_price_in_window) or avg_srl_price_in_window < 0 :
                    print(f"    INFO: Durchschnittlicher SRL Preis im Fenster ({avg_srl_price_in_window:.4f} CHF/kWh) ist ungültig oder negativ. Überspringe Szenario.")
                    all_simulation_scenario_results.append({
                        "event_date": event_date_obj.strftime('%Y-%m-%d'), "rank_step4": day_info["rank_step4"],
                        "reference_peak_utc": reference_peak_ts_utc.strftime('%Y-%m-%d %H:%M'),
                        "event_start_utc": event_start_utc.strftime('%Y-%m-%d %H:%M'),
                        "event_duration_h": event_total_duration_h_scenario, "pre_peak_offset_h": pre_offset_h_scenario,
                        "potenzielle_jasm_last_im_fenster_mwh": potenzielle_gesamte_jasm_last_event_mwh,
                        "avg_srl_price_in_window_chf_kwh": avg_srl_price_in_window,
                        "error_message": f"Invalid or negative avg SRL price: {avg_srl_price_in_window:.4f}"
                    })
                    continue

                aktueller_komp_prozentsatz = 0.0
                vorheriger_komp_prozentsatz = -1.0
                iterations_zaehler = 0
                MAX_ITERATIONS = 50
                KONVERGENZ_SCHWELLE_PROZENT = 0.01
                DAEMPFUNGSFAKTOR = 0.5

                print(f"    Potenzielle JASM-Last im Fenster: {potenzielle_gesamte_jasm_last_event_mwh:.3f} MWh") # Bereits geloggt
                print(f"    Durchschnittlicher SRL Preis im Fenster: {avg_srl_price_in_window:.4f} CHF/kWh") # Bereits geloggt
                print(f"    Starte Iteration (max. {MAX_ITERATIONS}, Schwelle: {KONVERGENZ_SCHWELLE_PROZENT}%):")

                _rohe_teilnahme_iter = 0.0
                _gedeckelte_teilnahme_iter = 0.0
                _versch_energie_iter = 0.0
                _srl_wert_iter = 0.0
                _chf_kwh_iter = 0.0
                _naechstes_gebot_iter = 0.0

                while abs(aktueller_komp_prozentsatz - vorheriger_komp_prozentsatz) > KONVERGENZ_SCHWELLE_PROZENT \
                      and iterations_zaehler < MAX_ITERATIONS:
                    vorheriger_komp_prozentsatz = aktueller_komp_prozentsatz
                    iterations_zaehler += 1
                    teilnahme_details = calculate_participation_metrics(
                        df_survey_flex_input=df_survey_prepared,
                        target_appliance=APPLIANCE_NAME,
                        event_duration_h=event_total_duration_h_scenario,
                        offered_incentive_pct=aktueller_komp_prozentsatz
                    )
                    _rohe_teilnahme_iter = teilnahme_details['raw_participation_rate']
                    _gedeckelte_teilnahme_iter = min(_rohe_teilnahme_iter, MAX_PARTICIPATION_CAP)
                    national_verschobene_energie_pro_intervall_mwh = jasm_load_in_event_mwh_series * _gedeckelte_teilnahme_iter
                    _versch_energie_iter = national_verschobene_energie_pro_intervall_mwh.sum()
                    if _versch_energie_iter <= 1e-9:
                        _naechstes_gebot_iter = 0.0
                        _srl_wert_iter = 0.0
                        _chf_kwh_iter = 0.0
                    else:
                        _srl_wert_iter = (national_verschobene_energie_pro_intervall_mwh * 1000 * srl_prices_in_event_chf_kwh_series).sum()
                        basis_kosten_fuer_verschobene_energie_chf = (_versch_energie_iter * 1000) * BASE_PRICE_CHF_KWH_COMPENSATION
                        if basis_kosten_fuer_verschobene_energie_chf <= 1e-9 :
                             if _srl_wert_iter > 1e-9: _naechstes_gebot_iter = 150.0
                             else: _naechstes_gebot_iter = 0.0
                        else:
                             _naechstes_gebot_iter = (_srl_wert_iter / basis_kosten_fuer_verschobene_energie_chf) * 100
                        _chf_kwh_iter = _srl_wert_iter / (_versch_energie_iter * 1000)
                    _naechstes_gebot_iter = max(0.0, min(_naechstes_gebot_iter, 150.0))
                    aktueller_komp_prozentsatz = (DAEMPFUNGSFAKTOR * vorheriger_komp_prozentsatz) + \
                                                 ((1 - DAEMPFUNGSFAKTOR) * _naechstes_gebot_iter)
                    print(f"      Iter. {iterations_zaehler:02d}: Geboten={vorheriger_komp_prozentsatz:6.2f}% -> RohTQ={_rohe_teilnahme_iter:6.2%} -> GedTQ={_gedeckelte_teilnahme_iter:6.2%} -> VersEn={_versch_energie_iter:8.3f}MWh -> SRLWert={_srl_wert_iter:10.2f}CHF -> CHF/kWh={_chf_kwh_iter:6.4f} -> NächstGebot={_naechstes_gebot_iter:6.2f}% -> Gedämpft={aktueller_komp_prozentsatz:6.2f}%")

                konvergiert = iterations_zaehler < MAX_ITERATIONS or \
                              abs(aktueller_komp_prozentsatz - vorheriger_komp_prozentsatz) <= KONVERGENZ_SCHWELLE_PROZENT
                if not konvergiert:
                    print(f"    Iteration NICHT konvergiert nach {MAX_ITERATIONS} Schritten.")
                else:
                    print(f"    Iteration konvergiert nach {iterations_zaehler} Schritten.")

                konvergierter_prozentsatz = aktueller_komp_prozentsatz
                final_teilnahme_details = calculate_participation_metrics(
                    df_survey_flex_input=df_survey_prepared, target_appliance=APPLIANCE_NAME,
                    event_duration_h=event_total_duration_h_scenario, offered_incentive_pct=konvergierter_prozentsatz
                )
                final_rohe_teilnahmequote_vor_cap = final_teilnahme_details['raw_participation_rate']
                final_teilnahmequote = min(final_rohe_teilnahmequote_vor_cap, MAX_PARTICIPATION_CAP)
                final_national_verschobene_energie_mwh_series = jasm_load_in_event_mwh_series * final_teilnahmequote
                final_gesamte_national_verschobene_energie_event_mwh = final_national_verschobene_energie_mwh_series.sum()
                if final_gesamte_national_verschobene_energie_event_mwh <= 1e-9:
                    final_gesamter_srl_wert_event_chf = 0.0
                    final_auszahlung_pro_kwh_chf = 0.0
                else:
                    final_gesamter_srl_wert_event_chf = (final_national_verschobene_energie_mwh_series * 1000 * srl_prices_in_event_chf_kwh_series).sum()
                    final_auszahlung_pro_kwh_chf = final_gesamter_srl_wert_event_chf / (final_gesamte_national_verschobene_energie_event_mwh * 1000)
                monatliche_kostenbasis_pro_haushalt_chf = DISHWASHER_MONTHLY_ENERGY_PER_HOUSEHOLD_KWH * BASE_PRICE_CHF_KWH_COMPENSATION
                kompensation_pro_haushalt_chf = (konvergierter_prozentsatz / 100.0) * monatliche_kostenbasis_pro_haushalt_chf

                print(f"\n    --- Konvergiertes Ergebnis für Szenario ---")
                print(f"    Konvergierter Kompensationsprozentsatz: {konvergierter_prozentsatz:.2f}%")
                print(f"    Rohe Teilnahmequote (vor Cap): {final_rohe_teilnahmequote_vor_cap:.2%}")
                print(f"    Finale Teilnahmequote (max. {MAX_PARTICIPATION_CAP*100:.1f}%): {final_teilnahmequote:.2%}")
                print(f"    Potenzielle JASM-Last im Fenster (100% Teilnahme): {potenzielle_gesamte_jasm_last_event_mwh:.3f} MWh") # << NEUE AUSGABE
                print(f"    Gesamte national verschobene Energie: {final_gesamte_national_verschobene_energie_event_mwh:.3f} MWh")
                print(f"    Durchschnittlicher SRL-Preis im Fenster: {avg_srl_price_in_window:.4f} CHF/kWh") # << NEUE AUSGABE
                print(f"    Erzielter SRL-Wert / Gesamte Kompensation: {final_gesamter_srl_wert_event_chf:.2f} CHF")
                print(f"    Dies entspricht einer Auszahlung von {final_auszahlung_pro_kwh_chf:.4f} CHF/kWh (verschoben)")
                print(f"    Kompensation pro teilnehmendem Haushalt (Basis: {DISHWASHER_MONTHLY_ENERGY_PER_HOUSEHOLD_KWH} kWh @ {BASE_PRICE_CHF_KWH_COMPENSATION} CHF/kWh): {kompensation_pro_haushalt_chf:.4f} CHF")

                szenario_ergebnis = {
                    "event_date": event_date_obj.strftime('%Y-%m-%d'),
                    "rank_step4": day_info["rank_step4"],
                    "reference_peak_utc": reference_peak_ts_utc.strftime('%Y-%m-%d %H:%M'),
                    "event_start_utc": event_start_utc.strftime('%Y-%m-%d %H:%M'),
                    "event_duration_h": event_total_duration_h_scenario,
                    "pre_peak_offset_h": pre_offset_h_scenario,
                    "konvergierter_komp_prozentsatz": konvergierter_prozentsatz,
                    "rohe_teilnahmequote_vor_cap": final_rohe_teilnahmequote_vor_cap,
                    "finale_teilnahmequote": final_teilnahmequote,
                    "potenzielle_jasm_last_im_fenster_mwh": potenzielle_gesamte_jasm_last_event_mwh, # << HIER GESPEICHERT
                    "total_verschobene_energie_mwh": final_gesamte_national_verschobene_energie_event_mwh,
                    "avg_srl_price_in_window_chf_kwh": avg_srl_price_in_window, # Bereits gespeichert
                    "total_srl_wert_chf": final_gesamter_srl_wert_event_chf,
                    "auszahlung_pro_kwh_verschoben_chf": final_auszahlung_pro_kwh_chf,
                    "kompensation_pro_haushalt_chf": kompensation_pro_haushalt_chf,
                    "kompensations_basis_energie_kwh": DISHWASHER_MONTHLY_ENERGY_PER_HOUSEHOLD_KWH,
                    "iterations_to_converge": iterations_zaehler,
                    "converged": konvergiert,
                    "error_message": None # Setze None, wenn kein Fehler
                }
                all_simulation_scenario_results.append(szenario_ergebnis)

    print("\n--- Alle Simulationsszenarien abgeschlossen ---")
    if all_simulation_scenario_results:
        df_results = pd.DataFrame(all_simulation_scenario_results)
        print("\nZusammenfassung der Simulationsergebnisse:")
        columns_to_show = [
            "event_date", "rank_step4", "event_duration_h", "pre_peak_offset_h",
            "potenzielle_jasm_last_im_fenster_mwh", # << NEUE SPALTE
            "avg_srl_price_in_window_chf_kwh", # << NEUE SPALTE
            "konvergierter_komp_prozentsatz",
            "rohe_teilnahmequote_vor_cap",
            "finale_teilnahmequote",
            "total_verschobene_energie_mwh", "total_srl_wert_chf",
            "kompensation_pro_haushalt_chf", "converged", "error_message"
        ]
        columns_to_show_existing = [col for col in columns_to_show if col in df_results.columns]
        formatters = {}
        if 'rohe_teilnahmequote_vor_cap' in df_results.columns: formatters['rohe_teilnahmequote_vor_cap'] = "{:.2%}".format
        if 'finale_teilnahmequote' in df_results.columns: formatters['finale_teilnahmequote'] = "{:.2%}".format
        if 'konvergierter_komp_prozentsatz' in df_results.columns: formatters['konvergierter_komp_prozentsatz'] = "{:.2f}%".format
        if 'potenzielle_jasm_last_im_fenster_mwh' in df_results.columns: formatters['potenzielle_jasm_last_im_fenster_mwh'] = "{:.3f}".format
        if 'avg_srl_price_in_window_chf_kwh' in df_results.columns: formatters['avg_srl_price_in_window_chf_kwh'] = "{:.4f}".format
        if 'total_verschobene_energie_mwh' in df_results.columns: formatters['total_verschobene_energie_mwh'] = "{:.3f}".format
        if 'total_srl_wert_chf' in df_results.columns: formatters['total_srl_wert_chf'] = "{:.2f}".format
        if 'kompensation_pro_haushalt_chf' in df_results.columns: formatters['kompensation_pro_haushalt_chf'] = "{:.4f}".format

        print(df_results[columns_to_show_existing].to_string(index=False, formatters=formatters))

        results_filename = f"simulation_results_{APPLIANCE_NAME}_{TARGET_YEAR}_erweitert.csv" # Dateinamen angepasst
        results_path_dir = PROJECT_ROOT / "data" / "results"
        results_path_dir.mkdir(parents=True, exist_ok=True)
        results_path_file = results_path_dir / results_filename
        try:
            df_results.to_csv(results_path_file, index=False, sep=';', decimal='.')
            print(f"\nSimulationsergebnisse gespeichert unter: {results_path_file}")
        except Exception as e_save:
            print(f"\nFEHLER beim Speichern der Ergebnisse: {e_save}")
    else:
        print("Keine Simulationsergebnisse zum Anzeigen oder Speichern vorhanden.")

    print("\n--- Simulation des Flexibilitätspotenzials beendet. ---")