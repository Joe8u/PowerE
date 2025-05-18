# PowerE/src/analysis/evaluate_srl_dishwasher_potential.py
"""
Skript zur Bewertung des Potenzials von Geschirrspülern als virtuelles Kraftwerk
für Tertiärregelleistung (SRL), basierend auf spezifischen Spitzenmarktpreis-Zeitfenstern.
"""
import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
import datetime
import matplotlib.pyplot as plt
import seaborn as sns

# --- Pfad-Setup für Modul-Importe ---
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent 
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path: 
     sys.path.insert(0, str(PROJECT_ROOT / "src"))

try:
    from data_loader.tertiary_regulation_loader import load_regulation_range
    from data_loader.lastprofile import load_appliances as load_jasm_profiles
    from logic.respondent_level_model.flexibility_potential.a_survey_data_preparer import prepare_survey_flexibility_data
    print("Alle benötigten Loader-Module erfolgreich importiert.\n")
except ImportError as e:
    print(f"FEHLER beim Importieren der Loader-Module: {e}")
    sys.exit(1)

# --- Konfiguration und Annahmen ---
TARGET_YEAR_SRL = 2024 
TARGET_YEAR_JASM = 2024 
APPLIANCE_NAME = "Geschirrspüler"

N_TOP_SRL_PERIODS_TO_ANALYZE = 24 # Anzahl der teuersten SRL-Perioden, die wir genauer untersuchen

AGGREGATOR_MARGIN_PCT = 30.0  
PRICE_HOUSEHOLD_CHF_PER_KWH = 0.25 
N_SURVEY_BASE_DISHWASHER_OWNERS_VALID_ANSWERS = 300 # PLATZHALTER - BITTE ERMITTELN UND ANPASSEN!
TIME_RESOLUTION_JASM_MINUTES = 15 
JASM_POWER_UNIT_IS_MW = True    
MIN_SRL_EVENT_DURATION_H = 1.0 # Mindestdauer, die ein Teilnehmer Flexibilität anbieten muss

OUTPUT_DIR = Path("data_check_srl_evaluation_output_v2") 
os.makedirs(OUTPUT_DIR, exist_ok=True)

def convert_mwh_to_kwh_price(price_mwh):
    return price_mwh / 1000.0

def analyze_srl_potential_with_peak_focus():
    print("=== Starte Analyse: Geschirrspüler als VKW für SRL (Fokus auf spezifische Spitzenpreis-Zeitfenster) ===")

    # 1. Lade SRL-Preisdaten für ein ganzes Jahr
    print(f"\nLade SRL-Preisdaten für {TARGET_YEAR_SRL}...")
    srl_start_date = datetime.datetime(TARGET_YEAR_SRL, 1, 1)
    srl_end_date = datetime.datetime(TARGET_YEAR_SRL, 12, 31, 23, 59, 59)
    try:
        df_srl = load_regulation_range(start=srl_start_date, end=srl_end_date) 
        if df_srl.empty:
            print(f"FEHLER: Keine SRL-Daten für {TARGET_YEAR_SRL} geladen.")
            return
        if 'avg_price_eur_mwh' in df_srl.columns:
            df_srl['price_chf_kwh'] = convert_mwh_to_kwh_price(df_srl['avg_price_eur_mwh']) 
            print("SRL-Preise geladen und zu CHF/kWh konvertiert (Annahme EUR=CHF).")
        else:
            print("FEHLER: Spalte 'avg_price_eur_mwh' nicht in SRL-Daten gefunden.")
            return
    except Exception as e:
        print(f"FEHLER beim Laden oder Verarbeiten der SRL-Daten: {e}")
        import traceback
        traceback.print_exc() 
        return

    # 2. Identifiziere die N teuersten SRL-Perioden und deren Zeitpunkte
    if df_srl.empty or 'price_chf_kwh' not in df_srl.columns:
        print("Keine gültigen SRL-Preisdaten für die Identifikation von Spitzenpreisen.")
        return
        
    df_top_srl_periods = df_srl.nlargest(N_TOP_SRL_PERIODS_TO_ANALYZE, 'price_chf_kwh').copy() # .copy() um SettingWithCopyWarning zu vermeiden
    if df_top_srl_periods.empty:
        print(f"FEHLER: Konnte keine Top {N_TOP_SRL_PERIODS_TO_ANALYZE} Spitzenpreisperioden identifizieren.")
        return
        
    print(f"\nDie {N_TOP_SRL_PERIODS_TO_ANALYZE} teuersten SRL-Perioden im Jahr {TARGET_YEAR_SRL}:")
    df_top_srl_periods['weekday'] = df_top_srl_periods.index.day_name()
    df_top_srl_periods['hour'] = df_top_srl_periods.index.hour
    print(df_top_srl_periods[['price_chf_kwh', 'weekday', 'hour']].to_string())
    
    avg_price_of_these_top_periods_chf_kwh = df_top_srl_periods['price_chf_kwh'].mean()
    print(f"Durchschnittlicher Arbeitspreis in diesen Top-{N_TOP_SRL_PERIODS_TO_ANALYZE} Perioden: {avg_price_of_these_top_periods_chf_kwh:.4f} CHF/kWh")

    # 3. Bestimme maximal bietbaren Anreiz (basierend auf dem Durchschnitt der Top-Preise)
    max_offerable_incentive_chf_kwh = avg_price_of_these_top_periods_chf_kwh * (1 - AGGREGATOR_MARGIN_PCT / 100)
    print(f"Maximal bietbarer Anreiz für Teilnehmer (basierend auf ø Top-Preise, nach {AGGREGATOR_MARGIN_PCT}% Marge): {max_offerable_incentive_chf_kwh:.4f} CHF/kWh")

    # 4. Lade und verarbeite Umfragedaten (Flexibilitätspotenzial)
    print("\nLade aufbereitete Umfragedaten (Q9 und Q10)...")
    try:
        df_survey_flex = prepare_survey_flexibility_data() 
        if df_survey_flex.empty:
            print("FEHLER: Aufbereitete Umfragedaten sind leer.")
            return
    except Exception as e:
        print(f"FEHLER beim Laden der aufbereiteten Umfragedaten: {e}")
        return

    df_dishwasher_flex = df_survey_flex[df_survey_flex['device'] == APPLIANCE_NAME].copy()
    if df_dishwasher_flex.empty:
        print(f"Keine Umfragedaten für das Gerät '{APPLIANCE_NAME}' gefunden.")
        return

    df_dishwasher_flex['survey_incentive_pct_required'] = pd.to_numeric(df_dishwasher_flex['survey_incentive_pct_required'], errors='coerce')
    df_dishwasher_flex['survey_max_duration_h'] = pd.to_numeric(df_dishwasher_flex['survey_max_duration_h'], errors='coerce')

    # 5. Ermittle Teilnehmerbasis basierend auf dem Anreiz
    participating_respondents = []
    for _, row in df_dishwasher_flex.iterrows():
        choice = row['survey_incentive_choice']
        required_pct = row['survey_incentive_pct_required']
        max_duration = row['survey_max_duration_h']

        if pd.isna(max_duration) or max_duration < MIN_SRL_EVENT_DURATION_H:
            continue 

        participant_accepts_incentive = False
        if choice == 'yes_fixed': 
            participant_accepts_incentive = True
        elif choice == 'yes_conditional':
            if not pd.isna(required_pct):
                required_incentive_chf_kwh = (required_pct / 100) * PRICE_HOUSEHOLD_CHF_PER_KWH
                if max_offerable_incentive_chf_kwh >= required_incentive_chf_kwh:
                    participant_accepts_incentive = True
        
        if participant_accepts_incentive:
            participating_respondents.append(row['respondent_id'])

    N_market_driven_participants = len(set(participating_respondents))
    
    if N_SURVEY_BASE_DISHWASHER_OWNERS_VALID_ANSWERS == 0:
        R_participation_peak = 0.0
        print("WARNUNG: N_SURVEY_BASE_DISHWASHER_OWNERS_VALID_ANSWERS ist 0. Teilnahmequote kann nicht berechnet werden.")
    else:
        R_participation_peak = N_market_driven_participants / N_SURVEY_BASE_DISHWASHER_OWNERS_VALID_ANSWERS
    
    print(f"\nAnzahl Teilnehmer aus Umfrage, die für den Anreiz teilnehmen und Mindestdauer erfüllen: {N_market_driven_participants}")
    print(f"(Bezogen auf N_survey_base_dishwasher_owners_valid_answers = {N_SURVEY_BASE_DISHWASHER_OWNERS_VALID_ANSWERS})")
    print(f"Entspricht einer Teilnahmequote (R_participation_peak): {R_participation_peak:.2%}")

    # 6. Lade JASM-Daten für das gesamte JASM-Zieljahr
    print(f"\nLade JASM-Lastprofildaten für '{APPLIANCE_NAME}' für das Jahr {TARGET_YEAR_JASM}...")
    jasm_start_date = datetime.datetime(TARGET_YEAR_JASM, 1, 1)
    jasm_end_date = datetime.datetime(TARGET_YEAR_JASM, 12, 31, 23, 59, 59)
    try:
        df_jasm_all_year = load_jasm_profiles(
            appliances=[APPLIANCE_NAME], 
            start=jasm_start_date,
            end=jasm_end_date,
            year=TARGET_YEAR_JASM,
            group=True
        )
        if df_jasm_all_year.empty or APPLIANCE_NAME not in df_jasm_all_year.columns:
            print(f"FEHLER: Keine JASM-Daten für '{APPLIANCE_NAME}' im Jahr {TARGET_YEAR_JASM} geladen.")
            return
        P_JASM_total_CH_dishwasher_mw_series = df_jasm_all_year[APPLIANCE_NAME]
        print(f"JASM-Daten für {APPLIANCE_NAME} ({TARGET_YEAR_JASM}) geladen. Durchschnittliche Last: {P_JASM_total_CH_dishwasher_mw_series.mean():.2f} MW")
    except Exception as e:
        print(f"FEHLER beim Laden der JASM-Jahresdaten: {e}")
        return

    # 7. Quantifiziere VPP-Flexibilität WÄHREND DER SPEZIFISCHEN TOP-SRL-PERIODEN
    # Normalisiere die Zeitstempel der Top-SRL-Perioden auf das JASM-Jahr
    if not isinstance(df_top_srl_periods.index, pd.DatetimeIndex):
        df_top_srl_periods.index = pd.to_datetime(df_top_srl_periods.index)
    if not isinstance(P_JASM_total_CH_dishwasher_mw_series.index, pd.DatetimeIndex):
        P_JASM_total_CH_dishwasher_mw_series.index = pd.to_datetime(P_JASM_total_CH_dishwasher_mw_series.index)

    df_top_srl_periods_timestamps_normalized = df_top_srl_periods.index.map(
        lambda ts: ts.replace(year=TARGET_YEAR_JASM) 
    )
    
    # Hole die JASM-Last und die SRL-Preise für diese exakten normalisierten Zeitpunkte
    jasm_load_at_srl_peaks_mw = P_JASM_total_CH_dishwasher_mw_series.reindex(df_top_srl_periods_timestamps_normalized, method='nearest', tolerance=pd.Timedelta(f'{TIME_RESOLUTION_JASM_MINUTES}min'))
    srl_prices_at_peaks_chf_kwh = df_top_srl_periods['price_chf_kwh'].values # Behalte die originalen Preise für die Erlösrechnung

    # Kombiniere für die Analyse
    df_analysis_peaks = pd.DataFrame({
        'srl_original_timestamp': df_top_srl_periods.index,
        'srl_price_chf_kwh': srl_prices_at_peaks_chf_kwh,
        'jasm_normalized_timestamp': df_top_srl_periods_timestamps_normalized,
        'jasm_load_mw': jasm_load_at_srl_peaks_mw.values # .values um Index-Mismatch zu vermeiden
    })
    df_analysis_peaks.dropna(subset=['jasm_load_mw'], inplace=True) # Entferne, falls keine JASM-Daten gefunden wurden

    if df_analysis_peaks.empty:
        print("WARNUNG: Konnte keine übereinstimmenden JASM-Lastdaten für die Top-SRL-Perioden finden.")
    else:
        df_analysis_peaks['vpp_flex_kw'] = df_analysis_peaks['jasm_load_mw'] * 1000 * R_participation_peak
        
        print(f"\nAnalyse der {len(df_analysis_peaks)} Top-SRL-Perioden mit zugehöriger JASM-Last und VPP-Flexibilität:")
        print(df_analysis_peaks[['srl_original_timestamp', 'srl_price_chf_kwh', 'jasm_load_mw', 'vpp_flex_kw']].head().to_string())
        
        avg_vpp_flex_at_peaks_kw = df_analysis_peaks['vpp_flex_kw'].mean()
        print(f"Durchschnittliche VPP-Flexibilität während dieser {len(df_analysis_peaks)} Spitzenperioden: {avg_vpp_flex_at_peaks_kw:.2f} kW")

        # 8. Verfeinerte Wirtschaftlichkeitsbetrachtung für diese Spitzenperioden
        # Energie pro 15-Minuten-Intervall
        df_analysis_peaks['energy_shifted_kwh_per_interval'] = df_analysis_peaks['vpp_flex_kw'] * (TIME_RESOLUTION_JASM_MINUTES / 60.0)
        
        # Erlöse und Kosten pro Intervall
        df_analysis_peaks['revenue_chf_per_interval'] = df_analysis_peaks['energy_shifted_kwh_per_interval'] * df_analysis_peaks['srl_price_chf_kwh']
        df_analysis_peaks['incentive_cost_chf_per_interval'] = df_analysis_peaks['energy_shifted_kwh_per_interval'] * max_offerable_incentive_chf_kwh
        df_analysis_peaks['net_value_aggregator_per_interval'] = df_analysis_peaks['revenue_chf_per_interval'] - df_analysis_peaks['incentive_cost_chf_per_interval']

        # Summen über alle analysierten Spitzenperioden
        total_energy_shifted_kwh = df_analysis_peaks['energy_shifted_kwh_per_interval'].sum()
        total_potential_revenue_chf = df_analysis_peaks['revenue_chf_per_interval'].sum()
        total_incentive_costs_chf = df_analysis_peaks['incentive_cost_chf_per_interval'].sum()
        total_net_value_aggregator_chf = df_analysis_peaks['net_value_aggregator_per_interval'].sum()

        print("\n--- Verfeinerte Wirtschaftlichkeitsbetrachtung (für die ausgewählten Top-SRL-Perioden) ---")
        print(f"Anzahl analysierter Spitzen-Perioden (je {TIME_RESOLUTION_JASM_MINUTES} min): {len(df_analysis_peaks)}")
        print(f"Gesamte potenziell verschobene Energie in diesen Perioden: {total_energy_shifted_kwh:.2f} kWh")
        print(f"Potenzielle Bruttoerlöse (Aggregator) aus Arbeitspreis: {total_potential_revenue_chf:.2f} CHF")
        print(f"Geschätzte Anreizkosten für Teilnehmer: {total_incentive_costs_chf:.2f} CHF")
        print(f"Netto-Mehrwert für Aggregator (vor Tech-/Ops-Kosten): {total_net_value_aggregator_chf:.2f} CHF")
    
    print("\n\n=== Analyse abgeschlossen ===")

if __name__ == "__main__":
    analyze_srl_potential_with_peak_focus() # Geänderter Funktionsname
