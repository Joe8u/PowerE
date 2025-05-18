# PowerE/src/analysis/refined_srl_evaluation/_04_dr_day_ranker.py
"""
Nimmt die in Step 3 identifizierten DR-Kandidatentage und bewertet/rankt sie
basierend auf Kriterien wie der Höhe der Preisspitzen im Überlapp,
der Anzahl der Überlapp-Perioden etc.
"""
import pandas as pd
import datetime
from pathlib import Path
import sys
from typing import List, Dict, Tuple, Optional, Any

# --- Pfad-Setup (konsistent mit den anderen Skripten halten) ---
try:
    SCRIPT_DIR_STEP4 = Path(__file__).resolve().parent
    # Annahme: Die anderen Analyse-Skripte befinden sich im selben Verzeichnis
    # Falls nicht, Pfade zum Projekt-Root/src-Verzeichnis entsprechend anpassen
    # Beispiel für Import aus übergeordnetem src, wenn die Skripte in einem Unterordner von src liegen:
    # PROJECT_ROOT_STEP4 = SCRIPT_DIR_STEP4.parent.parent.parent # Annahme: _04 ist in src/analysis/refined_srl_evaluation
    # SRC_DIR_STEP4 = PROJECT_ROOT_STEP4 / "src"
    # if str(SRC_DIR_STEP4) not in sys.path:
    # sys.path.insert(0, str(SRC_DIR_STEP4))

    from _01_srl_peak_price_finder import find_top_srl_price_periods
    from _02_jasm_dishwasher_80pct_energy_window_finder import find_shortest_80pct_energy_window
    # Die Funktion aus _03_dr_day_identifier.py, die die Liste der Tage liefert
    from _03_dr_day_identifier import identify_dr_candidate_days
except NameError: # Fallback für interaktive Umgebungen (z.B. Jupyter)
    PROJECT_ROOT_STEP4 = Path.cwd() # Annahme: Aktuelles Verzeichnis ist der Projekt-Root
    SRC_DIR_STEP4 = PROJECT_ROOT_STEP4 / "src"
    if str(SRC_DIR_STEP4) not in sys.path:
         sys.path.insert(0, str(SRC_DIR_STEP4))
    # Die folgenden Pfade müssen eventuell angepasst werden, je nachdem wo die Skripte wirklich liegen
    # relativ zum Projekt-Root, wenn interaktiv gearbeitet wird.
    if str(PROJECT_ROOT_STEP4) not in sys.path: # Für den Fall, dass _01, _02 im Root liegen
         sys.path.insert(0, str(PROJECT_ROOT_STEP4))
    from analysis.refined_srl_evaluation._01_srl_peak_price_finder import find_top_srl_price_periods
    from analysis.refined_srl_evaluation._02_jasm_dishwasher_80pct_energy_window_finder import find_shortest_80pct_energy_window
    from analysis.refined_srl_evaluation._03_dr_day_identifier import identify_dr_candidate_days
except ImportError as e:
    print(f"FEHLER beim Importieren der Module _01, _02 oder _03: {e}")
    print("Stelle sicher, dass die Skripte im korrekten Pfad liegen und sys.path entsprechend angepasst ist.")
    sys.exit(1)

def calculate_ranking_metrics_for_days(
    candidate_days: List[datetime.date],
    srl_peak_data: pd.DataFrame,
    appliance_windows: Dict[datetime.date, Optional[Tuple[datetime.time, datetime.time, float, float]]]
) -> List[Dict[str, Any]]:
    """
    Berechnet Ranking-Metriken für die gegebenen Kandidatentage.
    (Implementierung wie im vorherigen Beispiel)
    """
    ranked_days_info: List[Dict[str, Any]] = []

    if not candidate_days or srl_peak_data is None or srl_peak_data.empty or not appliance_windows:
        return ranked_days_info

    if not isinstance(srl_peak_data.index, pd.DatetimeIndex):
        try:
            srl_peak_data.index = pd.to_datetime(srl_peak_data.index)
        except Exception:
            print("FEHLER (intern in ranker): Index von srl_peak_data konnte nicht in DatetimeIndex umgewandelt werden.")
            return ranked_days_info

    for day_to_rank in candidate_days:
        window_info = appliance_windows.get(day_to_rank)
        if window_info is None:
            continue # Sollte nicht passieren, wenn candidate_days korrekt aus Step 3 kommt

        appliance_start_time, appliance_end_time, window_duration_h, window_energy_mwh = window_info
        srl_peaks_on_this_day = srl_peak_data[srl_peak_data.index.normalize().date == day_to_rank]

        if srl_peaks_on_this_day.empty:
            continue # Sollte nicht passieren
        
        day_max_overlap_price = 0.0
        day_avg_overlap_price_components = []
        day_count_overlap_periods = 0
        day_sum_overlap_prices = 0.0
        
        for timestamp, srl_row in srl_peaks_on_this_day.iterrows():
            srl_peak_time = timestamp.time()
            current_srl_price = srl_row['price_chf_kwh']
            overlap = False

            if appliance_start_time < appliance_end_time: # Normalfall
                if appliance_start_time <= srl_peak_time < appliance_end_time: overlap = True
            elif appliance_end_time == datetime.time(0,0) and appliance_start_time != datetime.time(0,0): # Fenster endet Mitternacht
                if srl_peak_time >= appliance_start_time: overlap = True
            elif appliance_start_time == datetime.time(0,0) and appliance_end_time == datetime.time(0,0): # 24h Fenster
                overlap = True
            
            if overlap:
                day_count_overlap_periods += 1
                day_sum_overlap_prices += current_srl_price
                day_avg_overlap_price_components.append(current_srl_price)
                if current_srl_price > day_max_overlap_price:
                    day_max_overlap_price = current_srl_price
        
        if day_count_overlap_periods > 0:
            day_avg_overlap_price = sum(day_avg_overlap_price_components) / len(day_avg_overlap_price_components) if day_avg_overlap_price_components else 0.0
            
            ranked_days_info.append({
                "date": day_to_rank,
                "max_srl_price_in_window": day_max_overlap_price,
                "avg_srl_price_in_window": day_avg_overlap_price,
                "count_srl_peaks_in_window": day_count_overlap_periods,
                "sum_srl_prices_in_window": day_sum_overlap_prices,
                "appliance_window_duration_h": window_duration_h, # Kontext
                "appliance_window_energy_mwh": window_energy_mwh  # Kontext
            })

    # Ranken der Liste, z.B. primär nach max Preis, sekundär nach Anzahl Perioden
    ranked_days_info.sort(
        key=lambda x: (x["max_srl_price_in_window"], x["count_srl_peaks_in_window"]),
        reverse=True # Höchste Werte zuerst
    )
    
    return ranked_days_info


if __name__ == '__main__':
    print("--- Step 4: Ranke DR-Kandidatentage (Geschirrspüler) ---")

    # Parameter (sollten konsistent mit den vorherigen Schritten sein)
    TARGET_YEAR_MAIN = 2024
    N_TOP_SRL_PERIODS_MAIN = 150
    APPLIANCE_TO_ANALYZE = "Geschirrspüler"
    ENERGY_THRESHOLD_JASM_MAIN = 70.0
    TIME_RESOLUTION_JASM_MAIN = 15

    # --- Datenbeschaffung aus den vorherigen Schritten ---
    # 1. Lade SRL-Spitzenpreisperioden (Output von Step 1)
    # (Die Funktion find_top_srl_price_periods gibt ihre eigenen Fortschrittsmeldungen aus)
    df_srl_peaks = find_top_srl_price_periods(
        target_year_srl=TARGET_YEAR_MAIN,
        n_top_periods=N_TOP_SRL_PERIODS_MAIN
    )
    if df_srl_peaks is None or df_srl_peaks.empty:
        print("\nFEHLER: Keine SRL-Spitzenpreisdaten geladen. Ranking-Analyse wird abgebrochen.")
        sys.exit()
    if not isinstance(df_srl_peaks.index, pd.DatetimeIndex): # Sicherstellen, dass Index korrekt ist
        try: df_srl_peaks.index = pd.to_datetime(df_srl_peaks.index)
        except: sys.exit("FEHLER: SRL-Index konnte nicht in DatetimeIndex umgewandelt werden.")

    # 2. Extrahiere Tage und lade JASM-Fenster (Output von Step 2, gefiltert)
    srl_peak_dates_for_jasm = sorted(list(set(df_srl_peaks.index.normalize().date)))
    if not srl_peak_dates_for_jasm:
        print("\nFEHLER: Keine einzigartigen Tage aus SRL-Spitzen extrahiert. Ranking-Analyse wird abgebrochen.")
        sys.exit()
    
    # (Die Funktion find_shortest_80pct_energy_window gibt ihre eigenen Fortschrittsmeldungen aus)
    appliance_operation_windows = find_shortest_80pct_energy_window(
        target_year_jasm=TARGET_YEAR_MAIN,
        appliance_name=APPLIANCE_TO_ANALYZE,
        specific_dates=srl_peak_dates_for_jasm,
        energy_threshold_pct=ENERGY_THRESHOLD_JASM_MAIN,
        time_resolution_minutes=TIME_RESOLUTION_JASM_MAIN
    )
    # if not appliance_operation_windows:
        # print(f"\nWARNUNG: Keine Energieverbrauchsfenster für '{APPLIANCE_TO_ANALYZE}' gefunden.")
        # Das Ranking wird dann eine leere Liste ergeben, was ok ist.

    # 3. Identifiziere die Kandidatentage (Output von Step 3)
    # (Die Funktion identify_dr_candidate_days gibt selbst keine Fortschrittsmeldungen aus)
    candidate_days_from_step3 = identify_dr_candidate_days(
         srl_peak_data=df_srl_peaks,
         appliance_windows=appliance_operation_windows
    )
    if not candidate_days_from_step3:
        print("\nKeine DR-Kandidatentage von Step 3 erhalten. Ranking nicht möglich oder nicht nötig.")
        # Hier nicht unbedingt abbrechen, da die Ranking-Funktion eine leere Liste verarbeiten kann.
    else:
        print(f"\n{len(candidate_days_from_step3)} DR-Kandidatentage wurden von Step 3 zur Bewertung übergeben.")


    # --- Step 4: Berechne Metriken und Ranke die Kandidatentage ---
    # (Die Funktion calculate_ranking_metrics_for_days gibt selbst keine Fortschrittsmeldungen aus)
    ranked_dr_days_final = calculate_ranking_metrics_for_days(
        candidate_days=candidate_days_from_step3,
        srl_peak_data=df_srl_peaks,
        appliance_windows=appliance_operation_windows
    )

    # --- FINALE AUSGABE: GERANKTE LISTE DER TAGE ---
    if ranked_dr_days_final:
        print(f"\n--- ERGEBNIS (GERANKT) ---")
        print(f"{len(ranked_dr_days_final)} Tag(e) wurden bewertet und gerankt für '{APPLIANCE_TO_ANALYZE}'.")
        print("Ranking-Kriterien (Beispiel): 1. Max. SRL-Preis im Fenster (absteigend), 2. Anzahl SRL-Spitzen im Fenster (absteigend)")
        
        # Header-Formatierung
        header_parts = [
            f"{'Rank':<5}", f"{'Datum':<12}", f"{'Max Preis Überlapp':<20}",
            f"{'Anzahl Überlapp':<18}", f"{'Ø Preis Überlapp':<18}", f"{'Summe Preise Überlapp':<22}"
        ]
        header_line = " | ".join(header_parts)
        print(header_line)
        print("-" * len(header_line))
        
        for i, day_data in enumerate(ranked_dr_days_final):
            row_parts = [
                f"{i+1:<5}", f"{day_data['date'].strftime('%Y-%m-%d'):<12}",
                f"{day_data['max_srl_price_in_window']:<20.4f}",
                f"{day_data['count_srl_peaks_in_window']:<18}",
                f"{day_data['avg_srl_price_in_window']:<18.4f}",
                f"{day_data['sum_srl_prices_in_window']:<22.4f}"
            ]
            print(" | ".join(row_parts))
        print("-" * len(header_line))
    else:
        print(f"\n--- ERGEBNIS ---")
        print(f"Keine Tage gefunden, die gerankt werden konnten (basierend auf dem Input von Step 3).")

    print("\n--- Analyse für Step 4 (Ranking) beendet. ---")