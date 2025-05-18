# PowerE/src/analysis/refined_srl_evaluation/_02_jasm_load_provider.py
"""
Lädt die aggregierten JASM-Lastprofildaten für den spezifizierten Appliance-Namen
für die Tage, an denen SRL-Spitzenpreise aufgetreten sind.
"""
import pandas as pd
import datetime
from pathlib import Path
import sys
from typing import List, Dict, Optional

# Füge den Projekt-Root und src zum sys.path hinzu
try:
    SCRIPT_DIR_JLP = Path(__file__).resolve().parent
    PROJECT_ROOT_JLP = SCRIPT_DIR_JLP.parent.parent.parent 
    SRC_DIR_JLP = PROJECT_ROOT_JLP / "src"
    if str(PROJECT_ROOT_JLP) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT_JLP))
    if str(SRC_DIR_JLP) not in sys.path:
        sys.path.insert(0, str(SRC_DIR_JLP))
    from analysis.refined_srl_evaluation._01_srl_peak_price_finder import find_top_srl_price_periods # Für Testblock
except NameError: 
    PROJECT_ROOT_JLP = Path.cwd()
    SRC_DIR_JLP = PROJECT_ROOT_JLP / "src"
    if str(SRC_DIR_JLP) not in sys.path:
         sys.path.insert(0, str(SRC_DIR_JLP))
    if str(PROJECT_ROOT_JLP) not in sys.path: 
         sys.path.insert(0, str(PROJECT_ROOT_JLP))
    from analysis.refined_srl_evaluation._01_srl_peak_price_finder import find_top_srl_price_periods # Für Testblock


from data_loader.lastprofile import load_appliances as load_jasm_profiles

def get_jasm_load_for_specific_dates(
    target_year_jasm: int,
    appliance_name: str,
    specific_dates: List[datetime.date]
) -> Optional[pd.DataFrame]:
    """
    Lädt JASM-Lastprofildaten für den appliance_name für die übergebenen specific_dates.

    Args:
        target_year_jasm (int): Das Jahr, für das die JASM-Daten geladen werden.
        appliance_name (str): Der Name des Geräts (z.B. "Geschirrspüler").
        specific_dates (List[datetime.date]): Eine Liste von Tagen, für die Daten geladen werden sollen.

    Returns:
        Optional[pd.DataFrame]: Ein DataFrame mit dem Zeitstempel-Index und einer Spalte
                                 für den appliance_name mit den Lastwerten (in MW oder kW,
                                 je nach JASM-Daten). Gibt None zurück bei Fehlern.
    """
    if not specific_dates:
        print("INFO (JASM Load Provider): Keine spezifischen Tage für das Laden von JASM-Daten übergeben.")
        return pd.DataFrame() # Leerer DataFrame, wenn keine Daten angefordert

    print(f"Lade JASM-Lastprofildaten für '{appliance_name}' für {len(specific_dates)} spezifische Tage im Jahr {target_year_jasm}...")
    
    # Lade Daten für den minimal und maximal benötigten Zeitraum, um wiederholtes Laden zu vermeiden
    min_date = min(specific_dates)
    max_date = max(specific_dates)
    start_dt_load = datetime.datetime.combine(min_date, datetime.time.min)
    # Lade bis zum Ende des letzten benötigten Tages
    end_dt_load = datetime.datetime.combine(max_date, datetime.time.max) 
    
    try:
        df_jasm_data = load_jasm_profiles(
            appliances=[appliance_name],
            start=start_dt_load,
            end=end_dt_load,
            year=target_year_jasm, 
            group=True 
        )
        if df_jasm_data.empty or appliance_name not in df_jasm_data.columns:
            print(f"FEHLER: Keine JASM-Daten für '{appliance_name}' im Zeitraum {min_date} bis {max_date} geladen oder Spalte fehlt.")
            return None
        if not isinstance(df_jasm_data.index, pd.DatetimeIndex):
            df_jasm_data.index = pd.to_datetime(df_jasm_data.index)
        
        # Filtere den DataFrame, um nur die exakten 'specific_dates' zu behalten
        # Erstelle einen booleschen Index
        date_condition = df_jasm_data.index.normalize().isin([pd.Timestamp(d) for d in specific_dates])
        df_jasm_filtered_by_date = df_jasm_data[date_condition]

        if df_jasm_filtered_by_date.empty:
            print(f"WARNUNG: Obwohl Daten für den Zeitraum geladen wurden, keine Daten für die spezifischen Tage {specific_dates} gefunden.")
            return pd.DataFrame(columns=[appliance_name])


        print(f"JASM-Daten für '{appliance_name}' für die relevanten Tage geladen. Shape: {df_jasm_filtered_by_date.shape}")
        return df_jasm_filtered_by_date[[appliance_name]] # Nur die relevante Spalte zurückgeben

    except Exception as e:
        print(f"FEHLER beim Laden der JASM-Daten für den Zeitraum {min_date}-{max_date}: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    print("Testlauf für _02_jasm_load_provider.py (verwendet Output von _01_ für Tage)")
    
    TEST_TARGET_YEAR_SRL = 2024
    TEST_N_TOP_SRL_PERIODS = 5 # Weniger Perioden für einen schnelleren Test
    TEST_TARGET_YEAR_JASM = 2024
    TEST_APPLIANCE_NAME = "Geschirrspüler"

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
            jasm_load_df = get_jasm_load_for_specific_dates(
                target_year_jasm=TEST_TARGET_YEAR_JASM,
                appliance_name=TEST_APPLIANCE_NAME,
                specific_dates=relevant_dates_for_jasm_analysis
            )
            
            if jasm_load_df is not None and not jasm_load_df.empty:
                print(f"\nJASM Lastprofil für '{TEST_APPLIANCE_NAME}' für die relevanten Tage (erste 10 Zeilen):")
                print(jasm_load_df.head(10).to_string())
                print(f"Shape des geladenen JASM-DataFrames: {jasm_load_df.shape}")
            elif jasm_load_df is not None and jasm_load_df.empty:
                 print("JASM Lastprofil für die relevanten Tage ist leer.")
            else:
                print("Fehler beim Laden des JASM Lastprofils für die relevanten Tage.")
            
    print("\n--- Testlauf für _02_jasm_load_provider.py beendet ---")
