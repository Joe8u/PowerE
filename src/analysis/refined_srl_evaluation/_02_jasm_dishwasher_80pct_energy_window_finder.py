# PowerE/src/analysis/refined_srl_evaluation/_02_jasm_dishwasher_80pct_energy_window_finder.py
"""
Identifiziert für spezifische Tage das kürzeste kontinuierliche Zeitfenster,
in dem 80% des täglichen Geschirrspüler-Energieverbrauchs (basierend auf JASM-Daten) stattfinden.
"""
import pandas as pd
import numpy as np
import datetime
from pathlib import Path
import sys
from typing import List, Dict, Tuple, Optional

# Füge den Projekt-Root und src zum sys.path hinzu
try:
    SCRIPT_DIR_J80 = Path(__file__).resolve().parent
    PROJECT_ROOT_J80 = SCRIPT_DIR_J80.parent.parent.parent 
    SRC_DIR_J80 = PROJECT_ROOT_J80 / "src"
    if str(PROJECT_ROOT_J80) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT_J80))
    if str(SRC_DIR_J80) not in sys.path:
        sys.path.insert(0, str(SRC_DIR_J80))
    from analysis.refined_srl_evaluation._01_srl_peak_price_finder import find_top_srl_price_periods # Für Testblock
except NameError: 
    PROJECT_ROOT_J80 = Path.cwd()
    SRC_DIR_J80 = PROJECT_ROOT_J80 / "src"
    if str(SRC_DIR_J80) not in sys.path:
         sys.path.insert(0, str(SRC_DIR_J80))
    if str(PROJECT_ROOT_J80) not in sys.path: 
         sys.path.insert(0, str(PROJECT_ROOT_J80))
    from analysis.refined_srl_evaluation._01_srl_peak_price_finder import find_top_srl_price_periods # Für Testblock

from data_loader.lastprofile import load_appliances as load_jasm_profiles

def find_shortest_80pct_energy_window(
    target_year_jasm: int,
    appliance_name: str,
    specific_dates: List[datetime.date],
    energy_threshold_pct: float = 80.0, # Standardwert bleibt 80%
    time_resolution_minutes: int = 15
) -> Dict[datetime.date, Optional[Tuple[datetime.time, datetime.time, float, float]]]:
    """
    Findet für jeden Tag das kürzeste kontinuierliche Zeitfenster, das mindestens
    energy_threshold_pct des täglichen Energieverbrauchs des Geräts abdeckt.

    Returns:
        Dict[datetime.date, Optional[Tuple[datetime.time, datetime.time, float, float]]]:
            Schlüssel: Datum.
            Wert: Tupel (Startzeit, Endzeit, Dauer_Stunden, Energie_im_Fenster_MWh) oder None.
    """
    print(f"Identifiziere kürzestes kontinuierliches Fenster für {energy_threshold_pct}% Energie ({appliance_name}) für {len(specific_dates)} Tage im Jahr {target_year_jasm}...")
    
    daily_shortest_window: Dict[datetime.date, Optional[Tuple[datetime.time, datetime.time, float, float]]] = {}
    interval_duration_h = time_resolution_minutes / 60.0

    # Lade JASM-Daten für den gesamten relevanten Zeitraum einmalig
    all_dates_jasm_df = pd.DataFrame()
    if specific_dates:
        min_date = min(specific_dates)
        max_date = max(specific_dates)
        start_dt_load = datetime.datetime.combine(min_date, datetime.time.min)
        end_dt_load = datetime.datetime.combine(max_date, datetime.time.max)
        try:
            all_dates_jasm_df = load_jasm_profiles(
                appliances=[appliance_name], start=start_dt_load, end=end_dt_load,
                year=target_year_jasm, group=True
            )
            if all_dates_jasm_df.empty or appliance_name not in all_dates_jasm_df.columns:
                print(f"FEHLER: Keine JASM-Daten für '{appliance_name}' im Zeitraum {min_date} bis {max_date} geladen.")
                return {date: None for date in specific_dates}
            if not isinstance(all_dates_jasm_df.index, pd.DatetimeIndex):
                all_dates_jasm_df.index = pd.to_datetime(all_dates_jasm_df.index)
        except Exception as e:
            print(f"FEHLER beim Laden der JASM-Daten für den Zeitraum: {e}")
            return {date: None for date in specific_dates}
    else:
        print("Keine spezifischen Tage zum Analysieren übergeben.")
        return {}

    for target_date in specific_dates:
        print(f"  Analysiere Tag: {target_date.strftime('%Y-%m-%d')}")
        
        start_of_day = pd.Timestamp(target_date, tz=all_dates_jasm_df.index.tz)
        end_of_day_exclusive = start_of_day + pd.Timedelta(days=1)
        
        df_day = all_dates_jasm_df.loc[
            (all_dates_jasm_df.index >= start_of_day) &
            (all_dates_jasm_df.index < end_of_day_exclusive), 
            [appliance_name]
        ].copy()

        if df_day.empty:
            print(f"    Keine Daten für '{appliance_name}' am {target_date.strftime('%Y-%m-%d')} gefunden.")
            daily_shortest_window[target_date] = None
            continue

        df_day['energy_mwh_interval'] = df_day[appliance_name] * interval_duration_h
        total_daily_energy_mwh = df_day['energy_mwh_interval'].sum()

        if total_daily_energy_mwh == 0:
            print(f"    Kein Energieverbrauch für '{appliance_name}' am {target_date.strftime('%Y-%m-%d')}.")
            daily_shortest_window[target_date] = None
            continue
            
        target_window_energy_mwh = total_daily_energy_mwh * (energy_threshold_pct / 100.0)
        
        min_duration_intervals = len(df_day) + 1 
        best_window_info: Optional[Tuple[datetime.time, datetime.time, float, float]] = None

        for i in range(len(df_day)):
            current_window_energy_mwh = 0.0
            for j in range(i, len(df_day)):
                current_window_energy_mwh += df_day['energy_mwh_interval'].iloc[j]
                
                if current_window_energy_mwh >= target_window_energy_mwh:
                    current_duration_intervals = (j - i + 1)
                    if current_duration_intervals < min_duration_intervals:
                        min_duration_intervals = current_duration_intervals
                        window_start_dt = df_day.index[i]
                        window_end_dt = df_day.index[j] + pd.Timedelta(minutes=time_resolution_minutes) 
                        
                        best_window_info = (
                            window_start_dt.time(),
                            window_end_dt.time(),
                            min_duration_intervals * interval_duration_h, 
                            current_window_energy_mwh 
                        )
                    break 

        if best_window_info:
            daily_shortest_window[target_date] = best_window_info
            s_time, e_time, dur_h, energy_win = best_window_info
            print(f"    Kürzestes kontinuierliches Fenster für >= {energy_threshold_pct}% Energie ({target_date.strftime('%Y-%m-%d')}):")
            print(f"      Start: {s_time.strftime('%H:%M')}, Ende: {e_time.strftime('%H:%M')}, Dauer: {dur_h:.2f}h, Energie: {energy_win:.3f} MWh")
        else:
            print(f"    Konnte kein kontinuierliches Fenster für {energy_threshold_pct}% Energie am {target_date.strftime('%Y-%m-%d')} finden.")
            daily_shortest_window[target_date] = None
            
    return daily_shortest_window

if __name__ == '__main__':
    print("Testlauf für _02_jasm_dishwasher_80pct_energy_window_finder.py (verwendet Output von _01_ für Tage)")
    
    TEST_TARGET_YEAR_SRL = 2024
    TEST_N_TOP_SRL_PERIODS = 5 
    TEST_TARGET_YEAR_JASM = 2024
    TEST_APPLIANCE_NAME = "Geschirrspüler"
    TEST_ENERGY_THRESHOLD_PCT = 70.0 # *** GEÄNDERT auf 70.0 für den Testlauf ***
    TEST_TIME_RESOLUTION_MINUTES = 15

    print(f"\nRufe _01_srl_peak_price_finder auf, um relevante Tage zu erhalten...")
    df_top_srl_periods_for_test = find_top_srl_price_periods(
        target_year_srl=TEST_TARGET_YEAR_SRL,
        n_top_periods=TEST_N_TOP_SRL_PERIODS
    )

    if df_top_srl_periods_for_test is None or df_top_srl_periods_for_test.empty:
        print("Konnte keine Top-SRL-Perioden von _01_ laden. Test für _02_ abgebrochen.")
    else:
        relevant_dates_for_jasm_analysis = sorted(list(set(df_top_srl_periods_for_test.index.normalize().date)))
        print(f"{len(relevant_dates_for_jasm_analysis)} einzigartige Tage aus Top-SRL-Perioden für JASM-Analyse extrahiert: {relevant_dates_for_jasm_analysis}")
        
        if not relevant_dates_for_jasm_analysis:
            print("Keine relevanten Daten für JASM-Analyse extrahiert. Test für _02_ abgebrochen.")
        else:
            peak_energy_windows = find_shortest_80pct_energy_window( # Funktionsname behält "80pct" für Klarheit des ursprünglichen Ziels, aber Parameter steuert es
                target_year_jasm=TEST_TARGET_YEAR_JASM,
                appliance_name=TEST_APPLIANCE_NAME,
                specific_dates=relevant_dates_for_jasm_analysis,
                energy_threshold_pct=TEST_ENERGY_THRESHOLD_PCT, # Hier wird 70.0 übergeben
                time_resolution_minutes=TEST_TIME_RESOLUTION_MINUTES
            )
            
            if peak_energy_windows:
                print(f"\nZusammenfassung der gefundenen kürzesten kontinuierlichen {TEST_ENERGY_THRESHOLD_PCT}%-Energie-Fenster:")
                for date, window_info in peak_energy_windows.items():
                    if window_info:
                        s, e, dur, nrg = window_info
                        print(f"  Tag: {date.strftime('%Y-%m-%d')} -> Fenster: {s.strftime('%H:%M')} - {e.strftime('%H:%M')} ({dur:.2f}h, {nrg:.3f} MWh)")
                    else:
                        print(f"  Tag: {date.strftime('%Y-%m-%d')} - Kein valides Fenster gefunden.")
            else:
                print(f"Keine {TEST_ENERGY_THRESHOLD_PCT}%-Energie-Fenster für die angegebenen Tage gefunden.")
            
    print("\n--- Testlauf für _02_jasm_dishwasher_80pct_energy_window_finder.py beendet ---")

