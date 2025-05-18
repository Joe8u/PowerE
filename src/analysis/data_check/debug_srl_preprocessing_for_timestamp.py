# PowerE/src/analysis/data_check/debug_srl_preprocessing_for_timestamp.py
"""
Analysiert eine einzelne Rohdatendatei der Tertiärregelleistung für einen
spezifischen Zeitstempel, um die Berechnung des gewichteten Durchschnittspreises
Schritt für Schritt nachzuvollziehen und mögliche Fehlerquellen zu identifizieren.
"""
import pandas as pd
from pathlib import Path
import numpy as np
import os
import sys

# --- Konfiguration für das Debugging ---
# Passe diese Werte an, um eine spezifische Datei und einen Zeitstempel zu untersuchen
DEBUG_YEAR = 2024
DEBUG_MONTH_STR = "01" # Als String, z.B. "01" für Januar
DEBUG_RAW_FILENAME_TEMPLATE = "{year}-{month}-TRE-Ergebnis.csv" # Vorlage für den Dateinamen
DEBUG_TIMESTAMP_TO_CHECK_STR = "2024-01-19 08:00:00" # Der problematische Zeitstempel

# --- Pfad-Setup ---
try:
    CURRENT_SCRIPT_PATH = Path(__file__).resolve().parent
    # Korrektur: Drei .parent Aufrufe, um zum PowerE-Ordner (Projekt-Root) zu gelangen,
    # wenn das Skript in PowerE/src/analysis/data_check/ liegt.
    PROJECT_ROOT = CURRENT_SCRIPT_PATH.parent.parent.parent.parent 
    # Überprüfung, ob der Pfad plausibel aussieht (sollte auf 'PowerE' enden)
    if PROJECT_ROOT.name != "PowerE" and Path(os.getcwd()).name == "PowerE":
        print(f"[WARNUNG] PROJECT_ROOT ({PROJECT_ROOT}) scheint nicht korrekt zu sein. Versuche CWD als Projekt-Root.")
        PROJECT_ROOT = Path(os.getcwd()).resolve()
    elif PROJECT_ROOT.name != "PowerE": # Fallback, falls __file__ nicht wie erwartet ist
         PROJECT_ROOT = Path(os.getcwd()).resolve() # Nimmt das aktuelle Arbeitsverzeichnis
         print(f"[WARNUNG] __file__ basiert PROJECT_ROOT ({PROJECT_ROOT}) scheint nicht korrekt. Versuche CWD.")
         if PROJECT_ROOT.name != "PowerE": # Wenn CWD auch nicht passt, gib eine klarere Fehlermeldung
             print(f"FEHLER: Konnte den Projekt-Root 'PowerE' nicht zuverlässig bestimmen. Aktuell: {PROJECT_ROOT}")
             sys.exit(1)

except NameError: # Fallback, falls __file__ nicht definiert ist
    PROJECT_ROOT = Path(os.getcwd()).resolve()
    print(f"[WARNUNG] __file__ nicht definiert. PROJECT_ROOT als CWD angenommen: {PROJECT_ROOT}")
    if PROJECT_ROOT.name != "PowerE":
        print(f"FEHLER: CWD ({PROJECT_ROOT}) ist nicht das erwartete Projekt-Root 'PowerE'.")
        sys.exit(1)

print(f"[Path Setup] PROJECT_ROOT: {PROJECT_ROOT}")

def debug_single_srl_timestamp():
    """
    Führt die detaillierte Analyse für eine Rohdatei und einen Zeitstempel durch.
    """
    raw_file_name = DEBUG_RAW_FILENAME_TEMPLATE.format(year=DEBUG_YEAR, month=DEBUG_MONTH_STR)
    # Konstruiere den Pfad zum Rohdatenverzeichnis basierend auf dem korrigierten PROJECT_ROOT
    raw_file_path = PROJECT_ROOT / "data" / "raw" / "market" / "regelenergie" / "mfrR" / str(DEBUG_YEAR) / raw_file_name
    
    debug_timestamp = pd.to_datetime(DEBUG_TIMESTAMP_TO_CHECK_STR)

    print(f"=== Starte detailliertes Debugging für SRL-Preprocessing ===")
    print(f"Analysiere Datei: {raw_file_path}")
    print(f"Fokussiere auf Zeitstempel: {debug_timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")

    if not raw_file_path.exists():
        print(f"FEHLER: Rohdatendatei nicht gefunden: {raw_file_path}")
        return

    # 1. Rohdaten für den relevanten Monat laden (nur benötigte Spalten)
    try:
        df_raw_month = pd.read_csv(
            raw_file_path,
            sep=';',
            encoding='latin1',
            usecols=['Ausschreibung', 'Von', 'Abgerufene Menge', 'Preis', 'Status', 'Produkt'] # Mehr Spalten für Kontext
        )
        print(f"Rohdatei '{raw_file_path.name}' geladen. {len(df_raw_month)} Zeilen insgesamt.")
    except Exception as e:
        print(f"FEHLER beim Lesen der Rohdatei {raw_file_path.name}: {e}")
        return

    if df_raw_month.empty:
        print("Rohdatei ist leer oder enthält keine der benötigten Spalten.")
        return

    # 2. Datums-String und primären 'timestamp' (Start des Intervalls) erstellen
    try:
        df_raw_month_cleaned = df_raw_month[df_raw_month['Ausschreibung'].apply(lambda x: isinstance(x, str))].copy()
        # .loc wird verwendet, um SettingWithCopyWarning zu vermeiden
        df_raw_month_cleaned.loc[:, 'date_str'] = df_raw_month_cleaned['Ausschreibung'].str.split('_').apply(
            lambda parts: f"{DEBUG_YEAR}-{parts[2]}-{parts[3]}" if len(parts) > 3 else None
        )
        df_raw_month_cleaned.dropna(subset=['date_str'], inplace=True)
        
        df_raw_month_cleaned.loc[:, 'timestamp'] = pd.to_datetime(
            df_raw_month_cleaned['date_str'] + ' ' + df_raw_month_cleaned['Von'],
            format="%Y-%m-%d %H:%M",
            errors='coerce'
        )
        df_raw_month_cleaned.dropna(subset=['timestamp'], inplace=True)
    except Exception as e_ts:
        print(f"FEHLER bei der Zeitstempel-Erstellung: {e_ts}")
        return
        
    print(f"\nNach Zeitstempel-Erstellung: {len(df_raw_month_cleaned)} Zeilen mit validem Timestamp.")

    # 3. Filtere auf den spezifischen Debug-Zeitstempel
    df_debug_slot_raw = df_raw_month_cleaned[df_raw_month_cleaned['timestamp'] == debug_timestamp].copy()

    if df_debug_slot_raw.empty:
        print(f"\nKeine Rohdaten-Einträge für den Zeitstempel {debug_timestamp.strftime('%Y-%m-%d %H:%M:%S')} gefunden (nach initialer Zeitstempel-Erstellung).")
        return
        
    print(f"\nRohdaten-Einträge für Slot {debug_timestamp.strftime('%Y-%m-%d %H:%M:%S')} ({len(df_debug_slot_raw)} Einträge gefunden):")
    print(df_debug_slot_raw[['Ausschreibung', 'Von', 'Abgerufene Menge', 'Preis', 'Status', 'Produkt']].to_string())

    # 4. Spalten umbenennen und Typkonvertierung (wie im Preprocessing-Skript)
    df_debug_slot_renamed = df_debug_slot_raw.rename(columns={
        'Abgerufene Menge': 'called_mw',
        'Preis': 'price_eur_mwh'
    })

    if 'called_mw' in df_debug_slot_renamed.columns:
        df_debug_slot_renamed.loc[:, 'called_mw'] = df_debug_slot_renamed['called_mw'].astype(str).str.replace(',', '.', regex=False)
        df_debug_slot_renamed.loc[:, 'called_mw'] = pd.to_numeric(df_debug_slot_renamed['called_mw'], errors='coerce')
    if 'price_eur_mwh' in df_debug_slot_renamed.columns:
        df_debug_slot_renamed.loc[:, 'price_eur_mwh'] = df_debug_slot_renamed['price_eur_mwh'].astype(str).str.replace(',', '.', regex=False)
        df_debug_slot_renamed.loc[:, 'price_eur_mwh'] = pd.to_numeric(df_debug_slot_renamed['price_eur_mwh'], errors='coerce')
    
    print("\nNach Umbenennung und Typkonvertierung zu numerisch (Fehler zu NaN):")
    print(df_debug_slot_renamed[['timestamp', 'called_mw', 'price_eur_mwh', 'Status', 'Produkt']].to_string())

    # 5. Entferne Zeilen, wo Konvertierung fehlschlug
    df_debug_slot_valid_numeric = df_debug_slot_renamed.dropna(subset=['called_mw', 'price_eur_mwh']).copy()
    if df_debug_slot_valid_numeric.empty:
        print("\nKeine Einträge mit validen numerischen Werten für Menge und Preis für diesen Slot.")
        return
    print(f"\nNach Entfernung von NaN bei Menge/Preis ({len(df_debug_slot_valid_numeric)} Einträge verbleiben):")
    print(df_debug_slot_valid_numeric[['timestamp', 'called_mw', 'price_eur_mwh', 'Status', 'Produkt']].to_string())

    # 6. Filtere nur tatsächlich abgerufene Mengen (called_mw > 0)
    df_debug_slot_called_only = df_debug_slot_valid_numeric[df_debug_slot_valid_numeric['called_mw'] > 0].copy()
    if df_debug_slot_called_only.empty:
        print("\nKeine Einträge mit called_mw > 0 für diesen Slot.")
        print("Das bedeutet, für diesen Zeitstempel würde im Preprocessing kein Eintrag in 'agg' resultieren oder total_called_mw wäre 0.")
        return
    print(f"\nNach Filter auf called_mw > 0 ({len(df_debug_slot_called_only)} Einträge verbleiben):")
    print(df_debug_slot_called_only[['timestamp', 'called_mw', 'price_eur_mwh', 'Status', 'Produkt']].to_string())
    
    # 7. Berechne 'cost' für diese gefilterten Einträge
    df_debug_slot_called_only.loc[:, 'cost'] = df_debug_slot_called_only['called_mw'] * df_debug_slot_called_only['price_eur_mwh']
    print("\nMit berechneter 'cost'-Spalte (nur für called_mw > 0):")
    print(df_debug_slot_called_only[['timestamp', 'called_mw', 'price_eur_mwh', 'cost', 'Status', 'Produkt']].to_string())

    # 8. Führe die Aggregation für diesen einen Zeitstempel durch
    total_called_mw_for_slot = df_debug_slot_called_only['called_mw'].sum()
    total_cost_for_slot = df_debug_slot_called_only['cost'].sum()
    
    avg_price_eur_mwh_for_slot = 0
    if total_called_mw_for_slot != 0:
        avg_price_eur_mwh_for_slot = total_cost_for_slot / total_called_mw_for_slot
    else:
        print("WARNUNG: total_called_mw für diesen Slot ist 0, Durchschnittspreis kann nicht sinnvoll berechnet werden.")

    print("\n--- Finale Aggregation für den Zeitstempel ---")
    print(f"Zeitstempel: {debug_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Summe 'called_mw': {total_called_mw_for_slot}")
    print(f"Summe 'cost': {total_cost_for_slot}")
    print(f"Berechneter 'avg_price_eur_mwh': {avg_price_eur_mwh_for_slot:.6f}")

    print("\nVergleiche dies mit dem Wert, den du in deiner vorverarbeiteten Datei siehst.")
    # ... (Rest der Print-Anweisungen) ...

if __name__ == "__main__":
    debug_single_srl_timestamp()

