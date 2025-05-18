# PowerE/src/analysis/refined_srl_evaluation/_01_srl_peak_price_finder.py
"""
Identifiziert die N teuersten SRL-Perioden (Arbeitspreis) aus den geladenen Daten
und zeigt sowohl den Preis in CHF/kWh als auch den ursprünglichen Preis in EUR/MWh an.
"""
import pandas as pd
import datetime
from pathlib import Path
import sys
import os # Importiere os für den Fallback im Pfad-Setup
import numpy as np

# Füge den Projekt-Root zum sys.path hinzu, damit data_loader gefunden wird
# Annahme: Dieses Skript liegt in src/analysis/refined_srl_evaluation/
# PROJECT_ROOT ist dann 4 Ebenen höher
try:
    SCRIPT_DIR_RPF = Path(__file__).resolve().parent
    # Korrektur: 3 Ebenen hoch zum src-Ordner, dann noch eine Ebene zum Projekt-Root
    PROJECT_ROOT_RPF = SCRIPT_DIR_RPF.parent.parent.parent 
    # Pfad zum src-Verzeichnis, wenn die Loader dort sind
    SRC_DIR_RPF = PROJECT_ROOT_RPF / "src"
    if str(PROJECT_ROOT_RPF) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT_RPF))
    if str(SRC_DIR_RPF) not in sys.path:
        sys.path.insert(0, str(SRC_DIR_RPF))
except NameError: # Fallback für interaktive Umgebungen
    PROJECT_ROOT_RPF = Path(os.getcwd()).resolve() # Annahme: Wird vom Projekt-Root ausgeführt
    SRC_DIR_RPF = PROJECT_ROOT_RPF / "src"
    if str(SRC_DIR_RPF) not in sys.path:
         sys.path.insert(0, str(SRC_DIR_RPF))
    if str(PROJECT_ROOT_RPF) not in sys.path: 
         sys.path.insert(0, str(PROJECT_ROOT_RPF))


from data_loader.tertiary_regulation_loader import load_regulation_range

def convert_mwh_to_kwh_price(price_mwh):
    if pd.isna(price_mwh):
        return np.nan
    return price_mwh / 1000.0

def find_top_srl_price_periods(
    target_year_srl: int,
    n_top_periods: int,
):
    """
    Lädt SRL-Preisdaten für ein Jahr und identifiziert die N teuersten Perioden.
    Gibt einen DataFrame mit diesen Perioden (Timestamp, Preis CHF/kWh, Preis EUR/MWh, Wochentag, Stunde) zurück.
    """
    print(f"Lade und analysiere SRL-Preisdaten für {target_year_srl}...")
    srl_start_date = datetime.datetime(target_year_srl, 1, 1)
    srl_end_date = datetime.datetime(target_year_srl, 12, 31, 23, 59, 59)
    
    df_srl = pd.DataFrame()
    try:
        df_srl = load_regulation_range(start=srl_start_date, end=srl_end_date)
        if df_srl.empty:
            print(f"FEHLER: Keine SRL-Daten für {target_year_srl} geladen.")
            return None
        
        # Stelle sicher, dass die Preisspalte existiert, bevor sie verwendet wird
        if 'avg_price_eur_mwh' not in df_srl.columns:
            print("FEHLER: Spalte 'avg_price_eur_mwh' nicht in SRL-Daten gefunden.")
            return None
        
        # Behalte die Originalspalte und erstelle die konvertierte
        df_srl['price_eur_mwh_original'] = df_srl['avg_price_eur_mwh'] # Behalte Original für Ausgabe
        df_srl['price_chf_kwh'] = df_srl['price_eur_mwh_original'].apply(convert_mwh_to_kwh_price) # Annahme EUR=CHF für Konvertierung
        print("SRL-Preise geladen. Original EUR/MWh behalten und zu CHF/kWh konvertiert (Annahme EUR=CHF).")

    except Exception as e:
        print(f"FEHLER beim Laden oder Verarbeiten der SRL-Daten: {e}")
        import traceback
        traceback.print_exc()
        return None

    if df_srl.empty or 'price_chf_kwh' not in df_srl.columns:
        print("Keine gültigen SRL-Preisdaten (CHF/kWh) für die Identifikation von Spitzenpreisen.")
        return None
        
    # Wähle die Top-Perioden basierend auf dem CHF/kWh Preis
    df_top_srl_periods = df_srl.nlargest(n_top_periods, 'price_chf_kwh').copy()
    if df_top_srl_periods.empty:
        print(f"FEHLER: Konnte keine Top {n_top_periods} Spitzenpreisperioden identifizieren.")
        return None
        
    # Füge Wochentag und Stunde hinzu für spätere Analyse
    if isinstance(df_top_srl_periods.index, pd.DatetimeIndex):
        df_top_srl_periods['weekday'] = df_top_srl_periods.index.day_name()
        df_top_srl_periods['hour'] = df_top_srl_periods.index.hour
    else:
        # Versuche, den Index zu konvertieren, falls er es nicht ist
        try:
            df_top_srl_periods.index = pd.to_datetime(df_top_srl_periods.index)
            df_top_srl_periods['weekday'] = df_top_srl_periods.index.day_name()
            df_top_srl_periods['hour'] = df_top_srl_periods.index.hour
            print("INFO: Index von df_top_srl_periods wurde zu DatetimeIndex konvertiert.")
        except Exception as e_conv:
            print(f"WARNUNG: Index von df_top_srl_periods ist kein DatetimeIndex und konnte nicht konvertiert werden. Wochentag/Stunde können nicht hinzugefügt werden. Fehler: {e_conv}")


    # Spalten für die Ausgabe auswählen
    columns_to_display = ['price_chf_kwh', 'price_eur_mwh_original', 'weekday', 'hour']
    # Sicherstellen, dass alle Anzeigespalten existieren
    columns_to_display = [col for col in columns_to_display if col in df_top_srl_periods.columns]


    print(f"\nDie {n_top_periods} teuersten SRL-Perioden im Jahr {target_year_srl} (Auszug):")
    print(df_top_srl_periods[columns_to_display].head().to_string())
    
    return df_top_srl_periods # Gibt den DataFrame mit allen Spalten zurück, inkl. price_eur_mwh_original

if __name__ == '__main__':
    print("Testlauf für _01_srl_peak_price_finder.py")
    top_periods_df = find_top_srl_price_periods(target_year_srl=2024, n_top_periods=24)
    if top_periods_df is not None and not top_periods_df.empty:
        print("\nGesamte Liste der Top-Perioden:")
        # Spalten für die Ausgabe im Testlauf auswählen
        test_columns_to_display = ['price_chf_kwh', 'price_eur_mwh_original', 'weekday', 'hour']
        test_columns_to_display = [col for col in test_columns_to_display if col in top_periods_df.columns]
        print(top_periods_df[test_columns_to_display].to_string())
        
        avg_price_chf_kwh = top_periods_df['price_chf_kwh'].mean()
        avg_price_eur_mwh = top_periods_df['price_eur_mwh_original'].mean()
        print(f"\nDurchschnittspreis dieser Top-Perioden (CHF/kWh): {avg_price_chf_kwh:.4f}")
        if pd.notna(avg_price_eur_mwh):
            print(f"Durchschnittspreis dieser Top-Perioden (EUR/MWh): {avg_price_eur_mwh:.2f}")
    else:
        print("Keine Top-Perioden gefunden oder Fehler beim Laden.")

