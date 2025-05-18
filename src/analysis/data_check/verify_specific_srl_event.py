# PowerE/src/analysis/data_check/verify_specific_srl_event.py
"""
Überprüft eine spezifische Rohdatendatei der Tertiärregelleistung für einen
exakten Zeitstempel, um die Details der dortigen Angebote, insbesondere
aktivierte Events und deren Preise, anzuzeigen.
Zeigt auch den Original-Status aus den Rohdaten an.
"""
import pandas as pd
from pathlib import Path
import numpy as np
import os
import sys

# --- Konfiguration für die Überprüfung ---
TARGET_YEAR = 2024
TARGET_MONTH_STR = "01" # Januar
TARGET_DAY_STR = "19"   # 19.
TARGET_TIME_STR = "08:00" # Von-Zeit des zu prüfenden Intervalls

RAW_FILENAME_TEMPLATE = "{year}-{month}-TRE-Ergebnis.csv"
# Dieser Zeitstempel wird verwendet, um die 'timestamp'-Spalte zu erstellen und zu filtern
TIMESTAMP_TO_VERIFY_STR = f"{TARGET_YEAR}-{TARGET_MONTH_STR}-{TARGET_DAY_STR} {TARGET_TIME_STR}:00"

# --- Pfad-Setup ---
try:
    CURRENT_SCRIPT_PATH = Path(__file__).resolve().parent
    PROJECT_ROOT = CURRENT_SCRIPT_PATH.parent.parent.parent 
except NameError:
    PROJECT_ROOT = Path(os.getcwd()).resolve()
    print(f"[WARNUNG] __file__ nicht definiert. PROJECT_ROOT als CWD angenommen: {PROJECT_ROOT}")
    if PROJECT_ROOT.name != "PowerE": 
        if (PROJECT_ROOT / "PowerE").exists():
            PROJECT_ROOT = PROJECT_ROOT / "PowerE"
        else:
            print(f"FEHLER: CWD ({PROJECT_ROOT}) ist nicht das erwartete Projekt-Root 'PowerE'. Bitte vom PowerE-Ordner ausführen.")
            sys.exit(1)
print(f"[Path Setup] PROJECT_ROOT: {PROJECT_ROOT}")

def verify_event_in_raw_data():
    """
    Lädt eine spezifische Rohdatei und analysiert die Einträge für einen gegebenen Zeitstempel.
    """
    raw_file_name = RAW_FILENAME_TEMPLATE.format(year=TARGET_YEAR, month=TARGET_MONTH_STR)
    raw_file_path = PROJECT_ROOT / "data" / "raw" / "market" / "regelenergie" / "mfrR" / str(TARGET_YEAR) / raw_file_name
    
    target_timestamp = pd.to_datetime(TIMESTAMP_TO_VERIFY_STR)

    print(f"=== Gezielte Überprüfung der SRL-Rohdatei für einen Zeitstempel ===")
    print(f"Analysiere Datei: {raw_file_path}")
    print(f"Suche nach Events beginnend um: {target_timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")

    if not raw_file_path.exists():
        print(f"FEHLER: Rohdatendatei nicht gefunden: {raw_file_path}")
        return

    try:
        df_raw = pd.read_csv(
            raw_file_path,
            sep=';',
            encoding='latin1', # Liest die Datei mit Latin-1 Kodierung
            usecols=['Ausschreibung', 'Von', 'Bis', 'Produkt', 'Angebotene Menge', 
                     'Abgerufene Menge', 'Preis', 'Status']
        )
        print(f"Rohdatei '{raw_file_path.name}' geladen. {len(df_raw)} Zeilen insgesamt.")
    except Exception as e:
        print(f"FEHLER beim Lesen der Rohdatei {raw_file_path.name}: {e}")
        return

    if df_raw.empty:
        print("Rohdatei ist leer.")
        return

    # Erstelle 'date_str' und 'timestamp' Spalten
    try:
        df_raw_c = df_raw[df_raw['Ausschreibung'].apply(lambda x: isinstance(x, str))].copy()
        df_raw_c.loc[:, 'date_str'] = df_raw_c['Ausschreibung'].str.split('_').apply(
            lambda parts: f"{TARGET_YEAR}-{parts[2]}-{parts[3]}" if len(parts) > 3 else None
        )
        df_raw_c.dropna(subset=['date_str'], inplace=True)
        df_raw_c.loc[:, 'timestamp'] = pd.to_datetime(
            df_raw_c['date_str'] + ' ' + df_raw_c['Von'],
            format="%Y-%m-%d %H:%M",
            errors='coerce'
        )
        df_raw_c.dropna(subset=['timestamp'], inplace=True)
    except Exception as e_ts_prep:
        print(f"FEHLER bei der initialen Zeitstempel-Vorbereitung: {e_ts_prep}")
        return

    # Filtere auf den exakten Zeitstempel
    df_slot = df_raw_c[df_raw_c['timestamp'] == target_timestamp].copy()

    if df_slot.empty:
        print(f"Keine Einträge in den Rohdaten für den Zeitstempel {target_timestamp.strftime('%Y-%m-%d %H:%M:%S')} gefunden.")
        return

    # Erstelle eine explizite Kopie des Original-Status für die Ausgabe
    # df_slot['Status'] enthält den Wert, wie er von pd.read_csv(encoding='latin1') geladen wurde
    df_slot.loc[:, 'Status_original_display'] = df_slot['Status'] 

    print(f"\n--- Alle Rohdaten-Einträge für {target_timestamp.strftime('%Y-%m-%d %H:%M:%S')} ({len(df_slot)} Einträge) ---")
    # Zeige die Spalte, die den Original-Status enthält
    cols_to_print_all = ['Ausschreibung', 'Von', 'Bis', 'Produkt', 'Angebotene Menge', 
                         'Abgerufene Menge', 'Preis', 'Status_original_display'] 
    # Entferne 'Status', um Verwirrung zu vermeiden, da 'Status_original_display' der "rohe" Wert ist
    cols_to_print_all = [col for col in cols_to_print_all if col in df_slot.columns] 
    print(df_slot[cols_to_print_all].to_string())

    # Konvertiere 'Abgerufene Menge' und 'Preis' zu numerisch für die Filterung
    df_slot.loc[:, 'called_mw_num'] = pd.to_numeric(
        df_slot['Abgerufene Menge'].astype(str).str.replace(',', '.', regex=False), errors='coerce'
    )
    df_slot.loc[:, 'price_eur_mwh_num'] = pd.to_numeric(
        df_slot['Preis'].astype(str).str.replace(',', '.', regex=False), errors='coerce'
    )
    
    # Filtere nach aktivierten Events mit valider Menge und Preis
    # Die Konvertierung zu .str.lower() hier beeinflusst NICHT die 'Status'-Spalte in df_slot,
    # sondern wird nur für den Vergleich verwendet.
    df_activated_slot = df_slot[
        (df_slot['Status'].astype(str).str.lower() == 'aktiviert') & 
        (df_slot['called_mw_num'] > 0) &
        (df_slot['price_eur_mwh_num'].notna())
    ].copy()

    print(f"\n--- Aktivierte Events (>0 MW) für {target_timestamp.strftime('%Y-%m-%d %H:%M:%S')} ({len(df_activated_slot)} Einträge) ---")
    if not df_activated_slot.empty:
        cols_to_print_activated = ['Ausschreibung', 'Von', 'Bis', 'Produkt', 
                                   'called_mw_num', 'price_eur_mwh_num', 'Status_original_display']
        cols_to_print_activated = [col for col in cols_to_print_activated if col in df_activated_slot.columns]
        print(df_activated_slot[cols_to_print_activated].to_string())

        if df_activated_slot['price_eur_mwh_num'].notna().any():
            highest_price_event_in_slot = df_activated_slot.loc[df_activated_slot['price_eur_mwh_num'].idxmax()]
            print("\n--- Aktiviertes Event mit dem höchsten Preis in diesem Slot ---")
            print(f"  Ausschreibung: {highest_price_event_in_slot['Ausschreibung']}")
            print(f"  Von: {highest_price_event_in_slot['Von']}")
            print(f"  Bis: {highest_price_event_in_slot['Bis']}")
            print(f"  Produkt: {highest_price_event_in_slot['Produkt']}")
            print(f"  Abgerufene Menge: {highest_price_event_in_slot['called_mw_num']} MW")
            print(f"  Preis: {highest_price_event_in_slot['price_eur_mwh_num']} EUR/MWh")
            # Zeige nur den Original-Status, um Klarheit zu schaffen
            print(f"  Status (Original aus Rohdatei): {highest_price_event_in_slot['Status_original_display']}") 
        else:
            print("Keine aktivierten Events mit validem Preis in diesem Slot gefunden.")
    else:
        print("Keine aktivierten Events mit >0 MW in diesem Slot gefunden.")

    print("\n\n=== Überprüfung für spezifischen Zeitstempel abgeschlossen ===")

if __name__ == "__main__":
    verify_event_in_raw_data()
