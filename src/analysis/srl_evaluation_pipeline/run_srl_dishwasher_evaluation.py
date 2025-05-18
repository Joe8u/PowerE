# PowerE/src/analysis/run_srl_dishwasher_evaluation.py
"""
Hauptskript zur Orchestrierung der Bewertung des Potenzials von Geschirrspülern
als virtuelles Kraftwerk für Tertiärregelleistung (SRL).
"""
import os
import sys
import pandas as pd
from pathlib import Path
import datetime

# --- Pfad-Setup für Modul-Importe ---
# Annahme: Dieses Skript liegt in PowerE/src/analysis/
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent # PowerE/ Ordner
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
     sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Importiere Funktionen aus den Komponenten-Modulen
# Annahme: Die Komponenten liegen in src/analysis/srl_evaluation_pipeline/
try:
    from analysis.srl_evaluation_pipeline._01_srl_price_analyzer import analyze_srl_prices
    from analysis.srl_evaluation_pipeline._02_incentive_calculator import calculate_max_offerable_incentive
    from analysis.srl_evaluation_pipeline._03_survey_participant_selector import determine_participating_households
    from analysis.srl_evaluation_pipeline._04_vpp_flex_quantifier import quantify_vpp_flexibility_at_peaks
    from analysis.srl_evaluation_pipeline._05_economic_evaluator import evaluate_economics_for_peaks
    print("Alle Komponenten-Module erfolgreich importiert.\n")
except ImportError as e:
    print(f"FEHLER beim Importieren der Komponenten-Module: {e}")
    print(f"Aktueller sys.path: {sys.path}")
    print(f"PROJECT_ROOT wurde gesetzt auf: {PROJECT_ROOT}")
    print("Stelle sicher, dass die Pfade korrekt sind und __init__.py Dateien in den Unterordnern existieren (z.B. in srl_evaluation_pipeline).")
    sys.exit(1)

# --- Globale Konfiguration und Annahmen (zentral hier definiert) ---
TARGET_YEAR_SRL = 2024 
TARGET_YEAR_JASM = 2024 
APPLIANCE_NAME = "Geschirrspüler"
N_TOP_SRL_PERIODS_TO_ANALYZE = 24 
AGGREGATOR_MARGIN_PCT = 30.0  
PRICE_HOUSEHOLD_CHF_PER_KWH = 0.29 
N_SURVEY_BASE_DISHWASHER_OWNERS_VALID_ANSWERS = 334 # Dein ermittelter Wert
TIME_RESOLUTION_JASM_MINUTES = 15 
JASM_POWER_UNIT_IS_MW = True    
MIN_SRL_EVENT_DURATION_H = 1.0 

# Definiere den Output-Ordner relativ zum PROJECT_ROOT für Konsistenz
OUTPUT_DIR_BASE = PROJECT_ROOT / "data_check_srl_evaluation_orchestrated"
os.makedirs(OUTPUT_DIR_BASE, exist_ok=True)

def main_evaluation_pipeline():
    print("=== Starte orchestrierte Analyse: Geschirrspüler als VKW für SRL (Spitzenpreise) ===")

    # Schritt 1: SRL-Preise analysieren
    print("\n--- Schritt 1: Analysiere SRL-Preise ---")
    srl_results = analyze_srl_prices(
        target_year_srl=TARGET_YEAR_SRL,
        n_top_periods=N_TOP_SRL_PERIODS_TO_ANALYZE,
        project_root_path=PROJECT_ROOT # Übergabe für Loader
    )
    if srl_results is None: return
    df_top_srl_periods = srl_results['df_top_srl_periods']
    avg_price_of_these_top_periods_chf_kwh = srl_results['avg_price_top_periods']
    print(f"Durchschnittlicher Arbeitspreis in Top-{N_TOP_SRL_PERIODS_TO_ANALYZE} Perioden: {avg_price_of_these_top_periods_chf_kwh:.4f} CHF/kWh")

    # Schritt 2: Maximal bietbaren Anreiz berechnen
    print("\n--- Schritt 2: Berechne maximal bietbaren Anreiz ---")
    max_offerable_incentive_chf_kwh = calculate_max_offerable_incentive(
        avg_peak_srl_price_chf_kwh=avg_price_of_these_top_periods_chf_kwh,
        aggregator_margin_pct=AGGREGATOR_MARGIN_PCT
    )
    print(f"Maximal bietbarer Anreiz für Teilnehmer: {max_offerable_incentive_chf_kwh:.4f} CHF/kWh")

    # Schritt 3: Teilnehmerbasis ermitteln
    print("\n--- Schritt 3: Ermittle teilnehmende Haushalte ---")
    participant_results = determine_participating_households(
        max_offerable_incentive_chf_kwh=max_offerable_incentive_chf_kwh,
        price_household_chf_per_kwh=PRICE_HOUSEHOLD_CHF_PER_KWH,
        min_srl_event_duration_h=MIN_SRL_EVENT_DURATION_H,
        appliance_name=APPLIANCE_NAME,
        n_survey_base_valid_answers=N_SURVEY_BASE_DISHWASHER_OWNERS_VALID_ANSWERS,
        project_root_path=PROJECT_ROOT # Übergabe für Loader
    )
    if participant_results is None: return
    R_participation_peak = participant_results['participation_rate']
    avg_actual_incentive_paid_chf_kwh = participant_results['avg_actual_incentive_paid']
    print(f"Teilnahmequote (R_participation_peak): {R_participation_peak:.2%}")
    print(f"Durchschnittlicher tatsächlicher Anreiz für Teilnehmer: {avg_actual_incentive_paid_chf_kwh:.4f} CHF/kWh")

    # Schritt 4: VPP-Flexibilität quantifizieren
    print("\n--- Schritt 4: Quantifiziere VPP-Flexibilität ---")
    vpp_flex_results = quantify_vpp_flexibility_at_peaks(
        df_top_srl_periods=df_top_srl_periods, # Enthält die Zeitstempel der Spitzen
        target_year_jasm=TARGET_YEAR_JASM,
        appliance_name=APPLIANCE_NAME,
        r_participation_peak=R_participation_peak,
        jasm_power_unit_is_mw=JASM_POWER_UNIT_IS_MW,
        project_root_path=PROJECT_ROOT # Übergabe für Loader
    )
    if vpp_flex_results is None: return
    df_analysis_peaks = vpp_flex_results['df_analysis_peaks'] # Enthält srl_price, jasm_load, vpp_flex_kw
    avg_vpp_flex_at_peaks_kw = vpp_flex_results['avg_vpp_flex_kw']
    print(f"Durchschnittliche VPP-Flexibilität während Spitzenperioden: {avg_vpp_flex_at_peaks_kw:.2f} kW")
    
    # Schritt 5: Wirtschaftlichkeit bewerten
    print("\n--- Schritt 5: Bewerte Wirtschaftlichkeit ---")
    if not df_analysis_peaks.empty:
        economic_results = evaluate_economics_for_peaks(
            df_analysis_peaks=df_analysis_peaks, # Enthält vpp_flex_kw und srl_price_chf_kwh pro Spitzenperiode
            avg_actual_incentive_paid_chf_kwh=avg_actual_incentive_paid_chf_kwh,
            time_resolution_jasm_minutes=TIME_RESOLUTION_JASM_MINUTES
        )
        print("\nWirtschaftlichkeitsbetrachtung (für Top-SRL-Perioden):")
        for key, value in economic_results.items():
            if isinstance(value, float):
                print(f"  {key.replace('_', ' ').capitalize()}: {value:.2f} CHF" if "chf" in key else f"  {key.replace('_', ' ').capitalize()}: {value:.2f}")
            else:
                print(f"  {key.replace('_', ' ').capitalize()}: {value}")
    else:
        print("Keine Daten für Wirtschaftlichkeitsanalyse verfügbar (df_analysis_peaks ist leer).")

    print("\n\n=== Orchestrierte Analyse abgeschlossen ===")

if __name__ == "__main__":
    main_evaluation_pipeline()
