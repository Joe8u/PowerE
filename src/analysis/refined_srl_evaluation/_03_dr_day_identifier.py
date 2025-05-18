# Angenommen, dies ist ein neues Skript _03_dr_day_identifier.py
# oder wird in den __main__-Block von _02_...py integriert.

import pandas as pd
import datetime
from pathlib import Path
import sys
from typing import List, Dict, Tuple, Optional

# --- Pfad-Setup (ähnlich wie in deinen Skripten) ---
# Notwendig, damit die Imports der anderen Skripte funktionieren
try:
    SCRIPT_DIR_STEP3 = Path(__file__).resolve().parent
    # Direkter Import, wenn im gleichen Verzeichnis oder PYTHONPATH korrekt ist
    # Passe die Imports an deine tatsächliche Ordnerstruktur an, falls _01 und _02 nicht direkt hier liegen
    # z.B. from ._01_srl_peak_price_finder import find_top_srl_price_periods
    from _01_srl_peak_price_finder import find_top_srl_price_periods
    from _02_jasm_dishwasher_80pct_energy_window_finder import find_shortest_80pct_energy_window
except NameError: # Fallback für interaktive Umgebungen
    PROJECT_ROOT_STEP3 = Path.cwd()
    # Annahme: src-Ordner ist relativ zum Projekt-Root
    SRC_DIR_STEP3 = PROJECT_ROOT_STEP3 / "src"
    if str(SRC_DIR_STEP3) not in sys.path:
         sys.path.insert(0, str(SRC_DIR_STEP3))
    # Annahme: Die Analyse-Skripte liegen im Unterordner analysis/refined_srl_evaluation/
    # Dieser Teil hängt stark von deiner genauen Struktur ab, wenn du interaktiv arbeitest.
    # Für einen robusten Import wäre es besser, das Projekt als Paket zu behandeln.
    if str(PROJECT_ROOT_STEP3) not in sys.path:
         sys.path.insert(0, str(PROJECT_ROOT_STEP3))
    from analysis.refined_srl_evaluation._01_srl_peak_price_finder import find_top_srl_price_periods
    from analysis.refined_srl_evaluation._02_jasm_dishwasher_80pct_energy_window_finder import find_shortest_80pct_energy_window
except ImportError as e:
    print(f"FEHLER beim Importieren der Module _01 oder _02: {e}")
    print("Stelle sicher, dass die Skripte im korrekten Pfad liegen und sys.path entsprechend angepasst ist,")
    print("oder dass du dieses Skript aus dem korrekten Verzeichnis heraus ausführst.")
    sys.exit(1)


def identify_dr_candidate_days(
    srl_peak_data: pd.DataFrame,
    appliance_windows: Dict[datetime.date, Optional[Tuple[datetime.time, datetime.time, float, float]]]
) -> List[datetime.date]:
    """
    Identifiziert Tage, an denen SRL-Preisspitzen in das Energieverbrauchsfenster des Geräts fallen.
    Gibt eine sortierte Liste der Daten (Tage) zurück.
    """
    candidate_days_list: List[datetime.date] = []
    if srl_peak_data is None or srl_peak_data.empty or not appliance_windows:
        return candidate_days_list # Gibt leere Liste zurück

    if not isinstance(srl_peak_data.index, pd.DatetimeIndex):
        # Versuche Konvertierung, gib aber keine print-Meldung innerhalb der Funktion aus,
        # außer es ist ein kritischer Fehler. Die aufrufende Instanz kann das Logging übernehmen.
        try:
            srl_peak_data.index = pd.to_datetime(srl_peak_data.index)
        except Exception:
            # print("FEHLER (intern): Index von srl_peak_data konnte nicht in DatetimeIndex umgewandelt werden.")
            return candidate_days_list # Leere Liste bei Fehler

    for peak_date_key, window_info in appliance_windows.items():
        if window_info is None:
            continue # Kein Fenster für diesen Tag in den JASM-Daten

        appliance_start_time, appliance_end_time, _, _ = window_info
        # Filtere SRL-Spitzen für das aktuelle Datum (peak_date_key ist datetime.date)
        srl_peaks_on_this_day = srl_peak_data[srl_peak_data.index.normalize().date == peak_date_key]


        if srl_peaks_on_this_day.empty:
            continue # Keine SRL-Spitzen für diesen Tag in den übergebenen Daten
        
        for timestamp, _ in srl_peaks_on_this_day.iterrows():
            srl_peak_time = timestamp.time()
            overlap = False
            # Standardfall: Fenster beginnt und endet am selben Tag (nicht über Mitternacht oder genau 00:00)
            if appliance_start_time < appliance_end_time:
                if appliance_start_time <= srl_peak_time < appliance_end_time:
                    overlap = True
            # Fall: Fenster geht bis Mitternacht (Endzeit ist 00:00)
            elif appliance_end_time == datetime.time(0,0) and appliance_start_time != datetime.time(0,0):
                if srl_peak_time >= appliance_start_time:
                    overlap = True
            # Fall: Fenster ist (theoretisch) 24 Stunden (Start und Ende sind 00:00)
            elif appliance_start_time == datetime.time(0,0) and appliance_end_time == datetime.time(0,0):
                overlap = True
            # Andere Fälle (z.B. Startzeit > Endzeit, was ein über Mitternacht gehendes Fenster wäre,
            # wird von Skript 2 so nicht direkt erzeugt, da es tagesbasiert ist)
            
            if overlap:
                if peak_date_key not in candidate_days_list: # Füge den Tag nur einmal hinzu
                    candidate_days_list.append(peak_date_key)
                break # Eine passende Spitze reicht, um diesen Tag zu qualifizieren
    
    return sorted(candidate_days_list)


if __name__ == '__main__':
    print("--- Step 3: Identifiziere die Tage für DR-Events (Geschirrspüler) ---")

    # Parameter für die Analyse
    TARGET_YEAR_MAIN = 2024 # Für welches Jahr soll die Analyse durchgeführt werden?
    # Wie viele der teuersten SRL-Perioden sollen als "Preisspitzen" betrachtet werden?
    # Eine höhere Zahl erhöht die Chance, Tage mit Überlappungen zu finden.
    N_TOP_SRL_PERIODS_MAIN = 150
    APPLIANCE_TO_ANALYZE = "Geschirrspüler" # Welches Gerät aus den JASM-Daten?
    ENERGY_THRESHOLD_JASM_MAIN = 70.0      # Das Energie-Fenster in Prozent (z.B. 70% des Tagesverbrauchs)
    TIME_RESOLUTION_JASM_MAIN = 15         # Zeitauflösung der JASM-Daten in Minuten (aus Skript 2)

    # 1. Lade SRL-Spitzenpreisperioden
    # Die Funktion find_top_srl_price_periods gibt bereits print-Meldungen aus.
    df_srl_peaks = find_top_srl_price_periods(
        target_year_srl=TARGET_YEAR_MAIN,
        n_top_periods=N_TOP_SRL_PERIODS_MAIN
    )

    if df_srl_peaks is None or df_srl_peaks.empty:
        print("\nFEHLER: Keine SRL-Spitzenpreisdaten geladen. Analyse wird abgebrochen.")
        sys.exit()
    
    if not isinstance(df_srl_peaks.index, pd.DatetimeIndex):
        print("\nWARNUNG: SRL-Peak-Index ist kein DatetimeIndex. Versuche Konvertierung...")
        try:
            df_srl_peaks.index = pd.to_datetime(df_srl_peaks.index)
        except Exception as e_conv:
            print(f"FEHLER bei Konvertierung des SRL-Peak-Index zu DatetimeIndex: {e_conv}")
            sys.exit()

    # 2. Extrahiere einzigartige Tage aus SRL-Spitzen für die JASM-Analyse
    srl_peak_dates_for_jasm = sorted(list(set(df_srl_peaks.index.normalize().date)))

    if not srl_peak_dates_for_jasm:
        print("\nKeine einzigartigen Tage aus SRL-Spitzen extrahiert. Analyse wird abgebrochen.")
        sys.exit()
    # Die folgende Zeile kann auskommentiert werden, wenn weniger verbose Output gewünscht ist.
    # print(f"\n{len(srl_peak_dates_for_jasm)} einzigartige Tage mit SRL-Spitzen werden für die JASM-Analyse verwendet.")

    # 3. Lade Energieverbrauchsfenster für das Gerät an diesen spezifischen Tagen
    # Die Funktion find_shortest_80pct_energy_window gibt bereits print-Meldungen aus.
    appliance_operation_windows = find_shortest_80pct_energy_window(
        target_year_jasm=TARGET_YEAR_MAIN,
        appliance_name=APPLIANCE_TO_ANALYZE,
        specific_dates=srl_peak_dates_for_jasm,
        energy_threshold_pct=ENERGY_THRESHOLD_JASM_MAIN,
        time_resolution_minutes=TIME_RESOLUTION_JASM_MAIN
    )

    # Die folgende Zeile kann auskommentiert werden für weniger verbose Output.
    # if not appliance_operation_windows:
    # print(f"\nWARNUNG: Keine Energieverbrauchsfenster für '{APPLIANCE_TO_ANALYZE}' gefunden für die angegebenen Tage.")
        
    # 4. Identifiziere die Tage, an denen die Bedingungen erfüllt sind
    # Die Funktion identify_dr_candidate_days selbst gibt keine print-Meldungen aus.
    final_dr_candidate_days_list = identify_dr_candidate_days(
        srl_peak_data=df_srl_peaks,
        appliance_windows=appliance_operation_windows
    )

    # --- FINALE AUSGABE: NUR DIE TAGE ---
    if final_dr_candidate_days_list:
        print(f"\n--- ERGEBNIS ---")
        print(f"{len(final_dr_candidate_days_list)} Tag(e) erfüllen die DR-Bedingungen für '{APPLIANCE_TO_ANALYZE}' "
              f"(basierend auf Top {N_TOP_SRL_PERIODS_MAIN} SRL-Spitzen und {ENERGY_THRESHOLD_JASM_MAIN}% Energie-Fenster):")
        for day_date in final_dr_candidate_days_list:
            print(day_date.strftime('%Y-%m-%d'))
    else:
        print(f"\n--- ERGEBNIS ---")
        print(f"Keine Tage gefunden, an denen SRL-Preisspitzen im {ENERGY_THRESHOLD_JASM_MAIN}%-Verbrauchsfenster "
              f"von '{APPLIANCE_TO_ANALYZE}' lagen (für die Top {N_TOP_SRL_PERIODS_MAIN} SRL-Spitzen).")

    print("\n--- Analyse für Step 3 beendet. ---")