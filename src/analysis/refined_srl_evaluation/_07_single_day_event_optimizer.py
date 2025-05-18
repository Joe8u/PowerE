# PowerE/src/analysis/refined_srl_evaluation/_07_single_day_event_optimizer.py
"""
Optimiert DR-Event-Parameter (Start-Offset und Dauer) für einen einzelnen,
spezifischen Hochpreistag, um den wirtschaftlichen Nutzen oder andere
Zielgrößen zu maximieren. Verwendet Event-Dauern basierend auf q9-Mapping
und eine feinere Iteration der Kompensationsprozentsätze.
"""
import pandas as pd
import datetime
from pathlib import Path
import sys
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# --- Pfad-Setup ---
try:
    CURRENT_SCRIPT_PATH = Path(__file__).resolve()
    PROJECT_ROOT = CURRENT_SCRIPT_PATH.parent.parent.parent.parent
except NameError:
    PROJECT_ROOT = Path.cwd()
    print(f"[WARNUNG] _07_ __file__ nicht definiert. PROJECT_ROOT: {PROJECT_ROOT}")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    print(f"[Path Setup _07_] Projekt-Root '{PROJECT_ROOT}' zum sys.path hinzugefügt.")

REPORTS_DIR_07 = PROJECT_ROOT / "reports" / "figures" / "step_07_daily_optimization"
REPORTS_DIR_07.mkdir(parents=True, exist_ok=True)

# --- Importe aus dem Projekt ---
try:
    from src.data_loader.tertiary_regulation_loader import load_regulation_range
    from src.data_loader.lastprofile import load_appliances as load_jasm_year_profile
    from src.logic.respondent_level_model.flexibility_potential.a_survey_data_preparer import prepare_survey_flexibility_data
    from src.logic.respondent_level_model.flexibility_potential.b_participation_calculator import calculate_participation_metrics
    from src.analysis.refined_srl_evaluation._05_flex_potential_simulation import get_data_for_specific_window # Wiederverwendung
except ImportError as e:
    print(f"FEHLER beim Importieren der Projektmodule in _07_: {e}")
    sys.exit(1)

if __name__ == '__main__':
    print("--- Step 7: Optimierung der DR-Event-Parameter für einen einzelnen Tag ---")

    # --- KONFIGURATION DER SIMULATION FÜR DIESEN TAG ---
    TARGET_YEAR_07 = 2024
    APPLIANCE_NAME_07 = "Geschirrspüler"
    
    TARGET_DAY_TO_OPTIMIZE = datetime.date(2024, 12, 30) 
    REFERENCE_PEAK_TS_FOR_TARGET_DAY_UTC = pd.Timestamp("2024-12-30 16:45:00", tz='UTC')

    POSSIBLE_OFFSETS_H_07 = np.arange(-2.0, 2.5, 0.5) 

    q9_duration_mapping_for_sim = {
        "Nein, auf keinen Fall": 0.0,
        "Ja, aber maximal für 3 Stunden": 1.5,
        "Ja, für 3 bis 6 Stunden": 4.5,
        "Ja, für 6 bis 12 Stunden": 9.0,
        "Ja, für maximal 24 Stunden": 24.0,
        "Ja, für mehr als 24 Stunden": 30.0
    }
    POSSIBLE_DURATIONS_H_07 = sorted([val for val in q9_duration_mapping_for_sim.values() if val > 0])
    if not POSSIBLE_DURATIONS_H_07:
        print("WARNUNG: Keine sinnvollen Dauern aus q9_duration_mapping extrahiert. Verwende Standarddauern [1.0, 2.0, 3.0, 4.0].")
        POSSIBLE_DURATIONS_H_07 = [1.0, 2.0, 3.0, 4.0]
    print(f"Simulierte Event-Dauern (Stunden): {POSSIBLE_DURATIONS_H_07}")

    # --- ANPASSUNG FÜR KOMPENSATIONSPROZENTSÄTZE ---
    start_comp_pct = 0.0
    end_comp_pct = 10.0  # Beispiel: bis 10.0%
    step_comp_pct = 0.1  # 0.1%-Schritte
    num_comp_points = int(round((end_comp_pct - start_comp_pct) / step_comp_pct)) + 1
    COMPENSATION_PCTS_FOR_OPTIMIZATION = np.linspace(start_comp_pct, end_comp_pct, num_comp_points).tolist()
    # Runden Sie die Werte, um potenzielle Float-Ungenauigkeiten von linspace zu minimieren, wenn gewünscht
    COMPENSATION_PCTS_FOR_OPTIMIZATION = [round(val, 2) for val in COMPENSATION_PCTS_FOR_OPTIMIZATION]
    print(f"Simulierte Kompensationsprozentsätze: {COMPENSATION_PCTS_FOR_OPTIMIZATION[:5]} ... bis {COMPENSATION_PCTS_FOR_OPTIMIZATION[-1]} ({len(COMPENSATION_PCTS_FOR_OPTIMIZATION)} Stufen)")
    # --- ENDE ANPASSUNG KOMPENSATIONSPROZENTSÄTZE ---

    TIME_RESOLUTION_MINUTES_07 = 15
    INTERVAL_DURATION_HOURS_07 = TIME_RESOLUTION_MINUTES_07 / 60.0
    ENERGY_PER_DISHWASHER_EVENT_KWH_07 = 8.0
    BASE_PRICE_CHF_KWH_COMPENSATION_07 = 0.29
    MAX_PARTICIPATION_CAP_07 = 0.629
    TOTAL_HOUSEHOLDS_WITH_APPLIANCE_CH_07 = 2400000 # Ihre validierte Zahl

    print(f"\n[Phase 0/2] Lade benötigte Daten für das Jahr {TARGET_YEAR_07}...")
    srl_year_start_utc = datetime.datetime(TARGET_YEAR_07, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    srl_year_end_utc = datetime.datetime(TARGET_YEAR_07, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)
    srl_year_start_naive = datetime.datetime(TARGET_YEAR_07, 1, 1, 0, 0, 0)
    srl_year_end_naive = datetime.datetime(TARGET_YEAR_07, 12, 31, 23, 59, 59)

    df_srl_all_year_raw = pd.DataFrame()
    try:
        # print("  Versuch 1: Lade SRL-Daten mit naiven Start/End-Zeiten...")
        df_srl_all_year_raw = load_regulation_range(start=srl_year_start_naive, end=srl_year_end_naive)
    except TypeError:
        # print("  WARNUNG: TypeError bei Versuch mit naiven Start/End-Zeiten für SRL-Daten.")
        # print("  Versuch 2: Lade SRL-Daten mit UTC-awaren Start/End-Zeiten (Fallback)...")
        try:
            df_srl_all_year_raw = load_regulation_range(start=srl_year_start_utc, end=srl_year_end_utc)
        except Exception as e_utc_attempt:
            sys.exit(f"FEHLER: Beide Ladeversuche für SRL-Daten fehlgeschlagen: {e_utc_attempt}")
    if df_srl_all_year_raw.empty or 'avg_price_eur_mwh' not in df_srl_all_year_raw.columns:
        sys.exit("FEHLER: SRL-Daten nicht geladen.")
    df_srl_all_year = df_srl_all_year_raw[['avg_price_eur_mwh']].copy()
    df_srl_all_year['srl_price_chf_kwh'] = df_srl_all_year['avg_price_eur_mwh'] / 1000.0
    df_srl_all_year.index = pd.to_datetime(df_srl_all_year.index)
    if df_srl_all_year.index.tz is None:
        try: df_srl_all_year.index = df_srl_all_year.index.tz_localize('Europe/Zurich', ambiguous='infer', nonexistent='shift_forward').tz_convert('UTC')
        except: df_srl_all_year.index = df_srl_all_year.index.tz_localize('UTC', ambiguous='infer', nonexistent='shift_forward')
    else: df_srl_all_year.index = df_srl_all_year.index.tz_convert('UTC')
    print(f"  SRL-Jahresdaten (UTC) geladen. Shape: {df_srl_all_year.shape}")

    df_jasm_hourly_mw_raw = pd.DataFrame()
    try:
        # print("  Versuch 1: Lade JASM-Daten mit naiven Start/End-Zeiten...")
        df_jasm_hourly_mw_raw = load_jasm_year_profile(appliances=[APPLIANCE_NAME_07], start=srl_year_start_naive, end=srl_year_end_naive, year=TARGET_YEAR_07, group=True)
    except TypeError:
        # print("  WARNUNG: TypeError bei JASM-Ladeversuch mit naiven Zeiten.")
        # print("  Versuch 2: Lade JASM-Daten mit UTC-awaren Start/End-Zeiten (Fallback)...")
        try:
            df_jasm_hourly_mw_raw = load_jasm_year_profile(appliances=[APPLIANCE_NAME_07], start=srl_year_start_utc, end=srl_year_end_utc, year=TARGET_YEAR_07, group=True)
        except Exception as e_jasm_utc:
            sys.exit(f"FEHLER: Beide Ladeversuche für JASM-Daten fehlgeschlagen: {e_jasm_utc}")
    if df_jasm_hourly_mw_raw.empty or APPLIANCE_NAME_07 not in df_jasm_hourly_mw_raw.columns:
        sys.exit(f"FEHLER: JASM-Daten für '{APPLIANCE_NAME_07}' nicht geladen.")
    df_jasm_hourly_mw = df_jasm_hourly_mw_raw[[APPLIANCE_NAME_07]].copy()
    df_jasm_hourly_mw.index = pd.to_datetime(df_jasm_hourly_mw.index)
    if df_jasm_hourly_mw.index.tz is None:
        try: df_jasm_hourly_mw.index = df_jasm_hourly_mw.index.tz_localize('Europe/Zurich', ambiguous='infer', nonexistent='shift_forward').tz_convert('UTC')
        except: df_jasm_hourly_mw.index = df_jasm_hourly_mw.index.tz_localize('UTC', ambiguous='infer', nonexistent='shift_forward')
    else: df_jasm_hourly_mw.index = df_jasm_hourly_mw.index.tz_convert('UTC')
    df_jasm_15min_mw = df_jasm_hourly_mw.resample('15min').ffill()
    if df_jasm_15min_mw.index.tz is None and df_jasm_hourly_mw.index.tz is not None :
         df_jasm_15min_mw.index = df_jasm_15min_mw.index.tz_localize(df_jasm_hourly_mw.index.tz)
    elif df_jasm_15min_mw.index.tz != df_jasm_hourly_mw.index.tz and df_jasm_hourly_mw.index.tz is not None :
         df_jasm_15min_mw.index = df_jasm_15min_mw.index.tz_convert(df_jasm_hourly_mw.index.tz)
    df_jasm_15min_mwh_interval_data = df_jasm_15min_mw.copy()
    df_jasm_15min_mwh_interval_data[f'{APPLIANCE_NAME_07}_mwh_interval'] = df_jasm_15min_mwh_interval_data[APPLIANCE_NAME_07] * INTERVAL_DURATION_HOURS_07
    print(f"  JASM Jahresdaten für '{APPLIANCE_NAME_07}' (15min, MWh/Intervall, UTC) geladen. Shape: {df_jasm_15min_mwh_interval_data.shape}")

    df_survey_prepared = prepare_survey_flexibility_data() # Gibt bereits Infos aus
    if df_survey_prepared.empty: sys.exit("FEHLER: Keine Umfragedaten geladen.")
    # print(f"  Umfragedaten geladen. Shape: {df_survey_prepared.shape}") # Redundanter Print

    print(f"\n[Phase 1/2] Starte Simulationen für Tag {TARGET_DAY_TO_OPTIMIZE.strftime('%Y-%m-%d')}...")
    daily_optimization_results = []

    for offset_h in POSSIBLE_OFFSETS_H_07:
        for duration_h in POSSIBLE_DURATIONS_H_07:
            event_start_utc = REFERENCE_PEAK_TS_FOR_TARGET_DAY_UTC - datetime.timedelta(hours=offset_h)
            event_end_utc = event_start_utc + datetime.timedelta(hours=duration_h) - datetime.timedelta(minutes=TIME_RESOLUTION_MINUTES_07)
            
            jasm_load_series = get_data_for_specific_window(
                df_jasm_15min_mwh_interval_data, event_start_utc, event_end_utc, f'{APPLIANCE_NAME_07}_mwh_interval'
            )
            srl_price_series = get_data_for_specific_window(
                df_srl_all_year, event_start_utc, event_end_utc, 'srl_price_chf_kwh'
            )

            if jasm_load_series.empty or srl_price_series.empty or len(jasm_load_series) != len(srl_price_series):
                continue
            total_jasm_load_in_event_mwh = jasm_load_series.sum()
            if total_jasm_load_in_event_mwh <= 0:
                continue

            for offered_comp_pct in COMPENSATION_PCTS_FOR_OPTIMIZATION: # Verwendet die neue, feinere Liste
                participation_details = calculate_participation_metrics(
                    df_survey_flex_input=df_survey_prepared,
                    target_appliance=APPLIANCE_NAME_07,
                    event_duration_h=duration_h,
                    offered_incentive_pct=offered_comp_pct
                )
                raw_rate = participation_details['raw_participation_rate']
                final_rate = min(raw_rate, MAX_PARTICIPATION_CAP_07)

                aligned_jasm_mwh, aligned_srl_chf_kwh = jasm_load_series.align(srl_price_series, join='inner')
                if aligned_jasm_mwh.empty or aligned_srl_chf_kwh.empty: continue

                dispatched_energy_per_interval_mwh = aligned_jasm_mwh * final_rate
                total_dispatched_energy_mwh = dispatched_energy_per_interval_mwh.sum()
                avoided_costs_chf = (dispatched_energy_per_interval_mwh * 1000 * aligned_srl_chf_kwh).sum()

                device_event_base_cost_chf = ENERGY_PER_DISHWASHER_EVENT_KWH_07 * BASE_PRICE_CHF_KWH_COMPENSATION_07
                compensation_chf_per_hh_event = device_event_base_cost_chf * (offered_comp_pct / 100.0)
                
                num_participating_households_total_ch = final_rate * TOTAL_HOUSEHOLDS_WITH_APPLIANCE_CH_07
                total_compensation_costs_ch = num_participating_households_total_ch * compensation_chf_per_hh_event
                net_benefit_chf_total = avoided_costs_chf - total_compensation_costs_ch
                
                avg_dispatched_power_mw = (total_dispatched_energy_mwh / duration_h) if duration_h > 0 else 0

                daily_optimization_results.append({
                    "date": TARGET_DAY_TO_OPTIMIZE, "offset_h": offset_h, "duration_h": duration_h,
                    "offered_compensation_pct": offered_comp_pct,
                    "final_participation_rate_pct": final_rate * 100,
                    "total_jasm_load_in_event_mwh": total_jasm_load_in_event_mwh,
                    "total_dispatched_energy_mwh": total_dispatched_energy_mwh,
                    "avg_dispatched_power_mw": avg_dispatched_power_mw,
                    "avg_srl_price_in_event_chf_kwh": aligned_srl_chf_kwh.mean() if not aligned_srl_chf_kwh.empty else 0,
                    "avoided_srl_costs_chf": avoided_costs_chf,
                    "compensation_chf_per_hh": compensation_chf_per_hh_event,
                    "total_compensation_ch": total_compensation_costs_ch,
                    "net_benefit_chf_total": net_benefit_chf_total
                })
    
    print(f"\n[Phase 2/2] Analysiere Ergebnisse für Tag {TARGET_DAY_TO_OPTIMIZE.strftime('%Y-%m-%d')}...")
    if not daily_optimization_results:
        print("Keine Simulationsergebnisse für die Optimierung erzeugt.")
        sys.exit()

    df_results_day = pd.DataFrame(daily_optimization_results)
    df_results_day = df_results_day.sort_values(by="net_benefit_chf_total", ascending=False)

    current_timestamp_str_07 = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_output_dir_07 = REPORTS_DIR_07 / f"optimize_{TARGET_DAY_TO_OPTIMIZE.strftime('%Y%m%d')}_{current_timestamp_str_07}"
    run_output_dir_07.mkdir(parents=True, exist_ok=True)
    print(f"Optimierungs-Ausgaben werden gespeichert in: {run_output_dir_07}")

    print("\nTop 10 Szenarien nach höchstem Netto-Nutzen für diesen Tag:")
    print(df_results_day.head(10))
    try:
        file_name_part = f"optimization_results_{TARGET_DAY_TO_OPTIMIZE.strftime('%Y%m%d')}.csv"
        full_results_path = run_output_dir_07 / file_name_part
        df_results_day.to_csv(full_results_path, index=False, sep=';', decimal='.')
        print(f"Detaillierte Tagesergebnisse gespeichert: {full_results_path}")
    except Exception as e_save: print(f"  Fehler beim Speichern der Tagesergebnisse: {e_save}")

    for comp_pct_val in df_results_day['offered_compensation_pct'].unique(): # Iteriere über tatsächlich vorhandene Werte
        df_subset = df_results_day[df_results_day['offered_compensation_pct'] == comp_pct_val]
        if df_subset.empty: continue
        
        # Überprüfen, ob genügend Daten für eine sinnvolle Pivot-Tabelle vorhanden sind
        if df_subset['duration_h'].nunique() < 2 or df_subset['offset_h'].nunique() < 2 :
            print(f"  Nicht genügend variierende Daten für Heatmap bei {comp_pct_val}% Anreiz. Überspringe Heatmap.")
            continue
            
        try:
            pivot_table = df_subset.pivot_table(index='duration_h', columns='offset_h', values='net_benefit_chf_total')
            plt.figure(figsize=(12, 8))
            sns.heatmap(pivot_table, annot=True, fmt=".0f", cmap="viridis")
            plt.title(f"Netto-Nutzen (CHF) für {TARGET_DAY_TO_OPTIMIZE.strftime('%Y-%m-%d')} bei {comp_pct_val:.2f}% Anreiz\nOffset zum Peak (h) vs. Event-Dauer (h)")
            plt.xlabel("Start-Offset zum Peak (Stunden, negativ=nach Peak, positiv=vor Peak)")
            plt.ylabel("Event-Dauer (Stunden)")
            plt.tight_layout()
            heatmap_filename = f"heatmap_net_benefit_comp{str(comp_pct_val).replace('.', '_')}.png"
            heatmap_path = run_output_dir_07 / heatmap_filename
            plt.savefig(heatmap_path)
            plt.close()
            print(f"Heatmap gespeichert: {heatmap_path}")
        except Exception as e_plot: print(f"  Fehler beim Erstellen der Heatmap für {comp_pct_val}% Anreiz: {e_plot}")
            
    print("\n--- Optimierungsanalyse für einzelnen Tag (Step 7) abgeschlossen. ---")