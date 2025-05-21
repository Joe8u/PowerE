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






# --- Simulation für EIN spezifisches Event-Szenario ---
event_date_obj = datetime.date(2024, 12, 30)
# Aus _04_ wissen wir, dass der 2024-12-30 eine hohe Priorität hat
# Nehmen wir an, der relevante SRL-Peak ist um 16:45 UTC an diesem Tag
reference_peak_ts_utc = pd.Timestamp(f"{event_date_obj.strftime('%Y-%m-%d')} 16:45:00", tz='UTC')

# Wähle ein spezifisches Szenario für pre_offset und duration
test_pre_offset_h = 1.0
test_event_total_duration_h = 1.5

print(f"\n--- Starte iterative Simulation für EIN Event ---")
print(f"Tag: {event_date_obj.strftime('%Y-%m-%d')}, Ref-Peak: {reference_peak_ts_utc.strftime('%H:%M')} UTC")
print(f"Szenario: Pre-Offset: {test_pre_offset_h}h, Event-Dauer: {test_event_total_duration_h}h")

# 1. Event-Fenster definieren
event_start_utc = reference_peak_ts_utc - datetime.timedelta(hours=test_pre_offset_h)
# Das Ende des letzten Intervalls ist start + duration - resolution.
# Das Fenster geht also von event_start_utc bis (event_start_utc + duration)
event_end_exclusive_utc = event_start_utc + datetime.timedelta(hours=test_event_total_duration_h)

# 2. Relevante JASM-Last und SRL-Preise für dieses Fenster extrahieren
# (Die get_data_for_specific_window Funktion muss angepasst werden, um bis < event_end_exclusive_utc zu gehen)
# Für die Simulation nehmen wir an, der letzte Timestamp im Fenster ist event_end_exclusive_utc - 15min

# Anpassung für get_data_for_specific_window oder direkte Filterung:
# Maske, um Daten bis zum Beginn des letzten Intervalls zu bekommen
jasm_mask = (df_jasm_15min_mwh.index >= event_start_utc) & \
            (df_jasm_15min_mwh.index < event_end_exclusive_utc) # < statt <=
srl_mask = (df_srl_all_year.index >= event_start_utc) & \
           (df_srl_all_year.index < event_end_exclusive_utc)

jasm_load_in_event_mwh_series = df_jasm_15min_mwh.loc[jasm_mask, f'{APPLIANCE_NAME}_mwh_interval']
srl_prices_in_event_chf_kwh_series = df_srl_all_year.loc[srl_mask, 'srl_price_chf_kwh']

if jasm_load_in_event_mwh_series.empty or \
   srl_prices_in_event_chf_kwh_series.empty or \
   len(jasm_load_in_event_mwh_series) != len(srl_prices_in_event_chf_kwh_series):
    print(f"FEHLER: Ungültige oder nicht übereinstimmende JASM/SRL-Daten für das Event-Fenster.")
    # Hier würde man im Hauptskript zum nächsten Szenario springen
    # sys.exit() # Nur für diesen Testfall

# Potenzielle nationale Gesamtlast im Event-Fenster (wenn Teilnahme 100%)
potenzielle_gesamte_jasm_last_event_mwh = jasm_load_in_event_mwh_series.sum()
if potenzielle_gesamte_jasm_last_event_mwh <= 1e-9:
    print(f"INFO: Keine JASM-Last für '{APPLIANCE_NAME}' im definierten Event-Fenster. Simulation für dieses Event nicht sinnvoll.")
    # Hier würde man im Hauptskript zum nächsten Szenario springen

# 3. Iterationsvariablen initialisieren
aktueller_komp_prozentsatz = 0.0  # Start mit 0%
vorheriger_komp_prozentsatz = -1.0
iterations_zaehler = 0
MAX_ITERATIONS = 50
KONVERGENZ_SCHWELLE_PROZENT = 0.01 # Prozentpunkte
DAEMPFUNGSFAKTOR = 0.5 # Optional

print(f"  Potenzielle JASM-Last im Fenster: {potenzielle_gesamte_jasm_last_event_mwh:.3f} MWh")
print(f"  Durchschnittlicher SRL Preis im Fenster: {srl_prices_in_event_chf_kwh_series.mean():.4f} CHF/kWh")
print(f"  Starte Iteration (max. {MAX_ITERATIONS}, Schwelle: {KONVERGENZ_SCHWELLE_PROZENT}%):")

konvergierte_ergebnisse = {}

while abs(aktueller_komp_prozentsatz - vorheriger_komp_prozentsatz) > KONVERGENZ_SCHWELLE_PROZENT \
      and iterations_zaehler < MAX_ITERATIONS:

    vorheriger_komp_prozentsatz = aktueller_komp_prozentsatz
    iterations_zaehler += 1

    # a. Teilnahmequote berechnen
    teilnahme_details = calculate_participation_metrics(
        df_survey_flex_input=df_survey_prepared,
        target_appliance=APPLIANCE_NAME,
        event_duration_h=test_event_total_duration_h,
        offered_incentive_pct=aktueller_komp_prozentsatz
    )
    aktuelle_teilnahmequote = min(teilnahme_details['raw_participation_rate'], MAX_PARTICIPATION_CAP)

    # b. National verschobene Energie berechnen
    # jasm_load_in_event_mwh_series ist die *potenzielle* Last pro Intervall, wenn alle teilnehmen
    national_verschobene_energie_pro_intervall_mwh = jasm_load_in_event_mwh_series * aktuelle_teilnahmequote
    gesamte_national_verschobene_energie_event_mwh = national_verschobene_energie_pro_intervall_mwh.sum()

    if gesamte_national_verschobene_energie_event_mwh <= 1e-9: # Nahezu Null
        # Wenn keine Energie verschoben wird, kann auch kein Wert generiert werden.
        # Der Kompensationsprozentsatz sollte dann idealerweise 0% sein.
        naechster_komp_prozentsatz = 0.0
        # print(f"    Iter. {iterations_zaehler}: Keine Energie verschoben bei {aktueller_komp_prozentsatz:.2f}%. Nächster Versuch mit 0%.")
    else:
        # c. Wert der national verschobenen Energie am SRL-Markt berechnen
        gesamter_srl_wert_event_chf = (national_verschobene_energie_pro_intervall_mwh * 1000 * srl_prices_in_event_chf_kwh_series).sum()

        # d. Neuen Kompensationslevel ableiten
        # Auszahlung pro verschobener kWh, wenn der gesamte SRL-Wert weitergegeben wird
        auszahlung_pro_verschobener_kwh_chf = gesamter_srl_wert_event_chf / (gesamte_national_verschobene_energie_event_mwh * 1000)
        
        naechster_komp_prozentsatz = (auszahlung_pro_verschobener_kwh_chf / BASE_PRICE_CHF_KWH_COMPENSATION) * 100
    
    # e. Konvergenzprüfung und Dämpfung
    naechster_komp_prozentsatz = max(0.0, min(naechster_komp_prozentsatz, 150.0)) # Begrenzung, z.B. max 150%

    # Dämpfung zur Stabilisierung
    aktueller_komp_prozentsatz = (DAEMPFUNGSFAKTOR * vorheriger_komp_prozentsatz) + \
                                 ((1 - DAEMPFUNGSFAKTOR) * naechster_komp_prozentsatz)
    
    print(f"    Iter. {iterations_zaehler:02d}: "
          f"Geboten={vorheriger_komp_prozentsatz:6.2f}% -> "
          f"Teiln.={aktuelle_teilnahmequote:6.2%} -> "
          f"Versch.Energie={gesamte_national_verschobene_energie_event_mwh:8.3f} MWh -> "
          f"SRL-Wert={gesamter_srl_wert_event_chf:10.2f} CHF -> "
          f"CHF/kWh={auszahlung_pro_verschobener_kwh_chf if gesamte_national_verschobene_energie_event_mwh > 1e-9 else 0.0:6.4f} -> "
          f"Nächstes Gebot={naechster_komp_prozentsatz:6.2f}% -> "
          f"Gedämpft={aktueller_komp_prozentsatz:6.2f}%")

# Ergebnisse nach Konvergenz
if iterations_zaehler == MAX_ITERATIONS and \
   abs(aktueller_komp_prozentsatz - vorheriger_komp_prozentsatz) > KONVERGENZ_SCHWELLE_PROZENT:
    print(f"\n  Iteration NICHT konvergiert nach {MAX_ITERATIONS} Schritten.")
else:
    print(f"\n  Iteration konvergiert nach {iterations_zaehler} Schritten.")

konvergierter_prozentsatz = aktueller_komp_prozentsatz
# Finale Werte mit dem konvergierten Prozentsatz berechnen
final_teilnahme_details = calculate_participation_metrics(
    df_survey_flex_input=df_survey_prepared, target_appliance=APPLIANCE_NAME,
    event_duration_h=test_event_total_duration_h, offered_incentive_pct=konvergierter_prozentsatz
)
final_teilnahmequote = min(final_teilnahme_details['raw_participation_rate'], MAX_PARTICIPATION_CAP)
final_national_verschobene_energie_mwh_series = jasm_load_in_event_mwh_series * final_teilnahmequote
final_gesamte_national_verschobene_energie_event_mwh = final_national_verschobene_energie_mwh_series.sum()
final_gesamter_srl_wert_event_chf = (final_national_verschobene_energie_mwh_series * 1000 * srl_prices_in_event_chf_kwh_series).sum()

# Zur Interpretation: Was bedeutet dieser Prozentsatz für einen Haushalt?
# Annahme eines typischen Energieverbrauchs pro HH-Event (DIESEN WERT REALISTISCH WÄHLEN!)
typischer_energieverbrauch_pro_hh_event_kwh = 1.0 # Beispiel: 1 kWh pro Geschirrspül-Shift
kompensation_pro_haushalt_chf = (konvergierter_prozentsatz / 100) * \
                                (typischer_energieverbrauch_pro_hh_event_kwh * BASE_PRICE_CHF_KWH_COMPENSATION)

print(f"\n  --- Konvergiertes Ergebnis für das Event ---")
print(f"  Konvergierter Kompensationsprozentsatz: {konvergierter_prozentsatz:.2f}%")
print(f"  Resultierende Teilnahmequote (max. {MAX_PARTICIPATION_CAP*100:.1f}%): {final_teilnahmequote:.2%}")
print(f"  Gesamte national verschobene Energie: {final_gesamte_national_verschobene_energie_event_mwh:.3f} MWh")
print(f"  Erzielter SRL-Wert / Gesamte Kompensation: {final_gesamter_srl_wert_event_chf:.2f} CHF")
if final_gesamte_national_verschobene_energie_event_mwh > 1e-9:
    print(f"  Dies entspricht einer Auszahlung von {final_gesamter_srl_wert_event_chf / (final_gesamte_national_verschobene_energie_event_mwh * 1000):.4f} CHF/kWh (verschoben)")
print(f"  Kompensation pro teilnehmendem Haushalt (Annahme {typischer_energieverbrauch_pro_hh_event_kwh} kWh/Event): {kompensation_pro_haushalt_chf:.4f} CHF")

konvergierte_ergebnisse = {
    "event_date": event_date_obj.strftime('%Y-%m-%d'),
    "event_start_utc": event_start_utc.strftime('%Y-%m-%d %H:%M'),
    "event_duration_h": test_event_total_duration_h,
    "pre_peak_offset_h": test_pre_offset_h,
    "konvergierter_komp_prozentsatz": konvergierter_prozentsatz,
    "finale_teilnahmequote": final_teilnahmequote,
    "total_verschobene_energie_mwh": final_gesamte_national_verschobene_energie_event_mwh,
    "total_srl_wert_chf": final_gesamter_srl_wert_event_chf,
    # ... weitere relevante Metriken
}
print(f"  Gespeicherte Ergebnisse: {konvergierte_ergebnisse}")
print("--- Iterative Simulation für EIN Event beendet ---")

# Im Hauptskript _05_... würden Sie diese Logik in die Schleifen über
# days_to_simulate_in_detail, PRE_PEAK_START_OFFSETS_H und DR_EVENT_TOTAL_DURATIONS_H einbetten.
# Und die Ergebnisse in all_simulation_scenario_results sammeln.