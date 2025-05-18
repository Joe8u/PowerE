# PowerE/src/analysis/data_check/inspect_raw_srl_file.py
"""
Analysiert eine einzelne Rohdatendatei der Tertiärregelleistung (TRE-Ergebnis.csv),
um deren Struktur, Datentypen und grundlegende Verteilungen zu verstehen.
"""
import pandas as pd
from pathlib import Path
import numpy as np
import os
import sys

# --- Konfiguration für die Analyse ---
# Passe diese Werte an, um eine spezifische Rohdatei zu untersuchen
TARGET_YEAR = 2024
TARGET_MONTH_STR = "01" # Als String, z.B. "01" für Januar
RAW_FILENAME_TEMPLATE = "{year}-{month}-TRE-Ergebnis.csv"

# --- Pfad-Setup ---
try:
    CURRENT_SCRIPT_PATH = Path(__file__).resolve().parent
    # Korrektur: Drei .parent Aufrufe, um zum PowerE-Ordner (Projekt-Root) zu gelangen,
    # wenn das Skript in PowerE/src/analysis/data_check/ liegt.
    PROJECT_ROOT = CURRENT_SCRIPT_PATH.parent.parent.parent 
except NameError:
    PROJECT_ROOT = Path(os.getcwd()).resolve()
    print(f"[WARNUNG] __file__ nicht definiert. PROJECT_ROOT als CWD angenommen: {PROJECT_ROOT}")
    # Zusätzliche Prüfung, ob der CWD-Fallback wahrscheinlich korrekt ist
    if PROJECT_ROOT.name != "PowerE" and (PROJECT_ROOT / "src").exists() and (PROJECT_ROOT / "data").exists():
        print(f"           CWD ({PROJECT_ROOT}) scheint der korrekte Projekt-Root 'PowerE' zu sein.")
    elif PROJECT_ROOT.name != "PowerE":
        print(f"FEHLER: CWD ({PROJECT_ROOT}) ist wahrscheinlich nicht das erwartete Projekt-Root 'PowerE'. Bitte vom PowerE-Ordner ausführen oder Pfad anpassen.")
        sys.exit(1)
print(f"[Path Setup] PROJECT_ROOT: {PROJECT_ROOT}")

def inspect_single_raw_srl_file():
    """
    Führt die detaillierte Inspektion für eine einzelne Rohdatei durch.
    """
    raw_file_name = RAW_FILENAME_TEMPLATE.format(year=TARGET_YEAR, month=TARGET_MONTH_STR)
    # Konstruiere den Pfad zum Rohdatenverzeichnis basierend auf dem korrigierten PROJECT_ROOT
    raw_file_path = PROJECT_ROOT / "data" / "raw" / "market" / "regelenergie" / "mfrR" / str(TARGET_YEAR) / raw_file_name
    
    print(f"=== Starte Inspektion der SRL-Rohdatei ===")
    print(f"Analysiere Datei: {raw_file_path}\n")

    if not raw_file_path.exists():
        print(f"FEHLER: Rohdatendatei nicht gefunden: {raw_file_path}")
        return

    # 1. Rohdaten laden (alle Spalten, um das Format zu sehen)
    try:
        df_raw = pd.read_csv(
            raw_file_path,
            sep=';',
            encoding='latin1' 
            # Kein usecols, um alle Spalten zu sehen
        )
        print(f"Rohdatei '{raw_file_path.name}' geladen. {len(df_raw)} Zeilen und {len(df_raw.columns)} Spalten insgesamt.")
    except Exception as e:
        print(f"FEHLER beim Lesen der Rohdatei {raw_file_path.name}: {e}")
        return

    if df_raw.empty:
        print("Rohdatei ist leer.")
        return

    # 2. Allgemeine Informationen zum DataFrame
    print("\n--- Allgemeine DataFrame Informationen (df.info()) ---")
    df_raw.info()

    print("\n--- Erste 5 Zeilen der Rohdatei ---")
    print(df_raw.head().to_string())

    print("\n--- Letzte 5 Zeilen der Rohdatei ---")
    print(df_raw.tail().to_string())

    # 3. Spaltennamen und deren Datentypen (wie von Pandas initial interpretiert)
    print("\n--- Spaltennamen und initiale Datentypen ---")
    print(df_raw.dtypes)

    # 4. Überprüfung auf fehlende Werte pro Spalte
    print("\n--- Fehlende Werte pro Spalte (Anzahl) ---")
    print(df_raw.isnull().sum())

    # 5. Analyse spezifischer Spalten
    key_cols = ['Ausschreibung', 'Von', 'Bis', 'Produkt', 'Status', 'Abgerufene Menge', 'Preis']
    for col in key_cols:
        if col in df_raw.columns:
            print(f"\n--- Analyse für Spalte: '{col}' ---")
            print(f"  Datentyp: {df_raw[col].dtype}")
            print(f"  Anzahl einzigartiger Werte: {df_raw[col].nunique()}")
            
            if df_raw[col].dtype == 'object' or df_raw[col].nunique() < 20: # Zeige Value Counts für kategoriale oder Textspalten mit wenigen Uniques
                print("  Häufigkeitsverteilung (Top 10 und NaNs):")
                print(df_raw[col].value_counts(dropna=False).head(10).to_string())
            
            if col in ['Abgerufene Menge', 'Preis']:
                # Versuche, zu numerisch zu konvertieren für deskriptive Stats
                # Ersetze Komma durch Punkt für Dezimaltrennzeichen, falls europäisches Format
                temp_numeric_col = pd.to_numeric(df_raw[col].astype(str).str.replace(',', '.', regex=False), errors='coerce')
                if temp_numeric_col.notna().sum() > 0:
                    print(f"  Deskriptive Statistiken (als numerisch interpretiert, NAs ignoriert):")
                    print(temp_numeric_col.describe().to_string())
                    # Berechne Konvertierungsfehler genauer
                    original_nas = df_raw[col].isnull().sum()
                    converted_nas = temp_numeric_col.isnull().sum()
                    num_conversion_failures = converted_nas - original_nas
                    if num_conversion_failures > 0:
                        print(f"    WARNUNG: {num_conversion_failures} Werte in '{col}' konnten nicht in Zahlen konvertiert werden (zusätzlich zu ursprünglichen NaNs).")
                else:
                    print(f"    Konnte keine numerischen Werte in Spalte '{col}' für deskriptive Statistiken finden.")
        else:
            print(f"\nWARNUNG: Spalte '{col}' nicht in der Datei gefunden.")
            
    print("\n\n=== Inspektion abgeschlossen ===")

if __name__ == "__main__":
    inspect_single_raw_srl_file()
