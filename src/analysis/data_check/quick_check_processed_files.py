# PowerE/src/analysis/data_check/quick_check_processed_files.py
"""
Skript zur schnellen Überprüfung der ersten Zeilen aller vorverarbeiteten Umfragedateien.

Dieses Skript liest jede der 15 vorverarbeiteten CSV-Dateien ein und gibt
die Kopfzeile sowie die ersten beiden Datenzeilen aus, um zu überprüfen,
ob die Artefakt-Zeile (z.B. mit "Response"-Einträgen) erfolgreich
durch die Anpassung der Preprocessing-Skripte entfernt wurde.
"""
import os
import pandas as pd
from pathlib import Path # Für modernere Pfad-Konstruktion

# --- Konfiguration ---
# Annahme: Dieses Skript liegt in PowerE/src/analysis/data_check/
# Das Verzeichnis mit den vorverarbeiteten Umfragedaten ist dann:
# PowerE/data/processed/survey/

# Ermittle das absolute Verzeichnis, in dem dieses Skript liegt
SCRIPT_DIR = Path(__file__).resolve().parent

# Definiere den Pfad zum Verzeichnis mit den vorverarbeiteten Dateien
# relativ zum Speicherort dieses Skripts.
# SCRIPT_DIR ist .../PowerE/src/analysis/data_check/
# Wir müssen also drei Ebenen hoch (data_check -> analysis -> src -> PowerE)
# und dann in data/processed/survey/
PROCESSED_DIR = SCRIPT_DIR.parent.parent.parent / "data" / "processed" / "survey"

# Liste aller 15 vorverarbeiteten Dateinamen
PROCESSED_FILES_TO_CHECK = [
    'question_1_age.csv',
    'question_2_gender.csv',
    'question_3_household_size.csv',
    'question_4_accommodation.csv',
    'question_5_electricity.csv',
    'question_6_challenges.csv',
    'question_7_consequence.csv',
    'question_8_importance_wide.csv',
    'question_9_nonuse_wide.csv',
    'question_10_incentive_wide.csv',
    'question_11_notification.csv',
    'question_12_smartplug.csv',
    'question_13_income.csv',
    'question_14_education.csv',
    'question_15_party.csv'
]

print(f"=== Schnelle Überprüfung der ersten Zeilen der vorverarbeiteten Dateien ===")
print(f"Daten werden aus '{PROCESSED_DIR}' geladen.\n")

all_files_look_clean = True

for filename in PROCESSED_FILES_TO_CHECK:
    file_path = PROCESSED_DIR / filename
    print(f"\n--- Datei: {filename} ---")

    if not file_path.exists():
        print(f"FEHLER: Datei '{file_path}' nicht gefunden. Überspringe.")
        all_files_look_clean = False
        continue

    try:
        # Lese die Datei ein. Wir erwarten, dass der Header die erste Zeile ist
        # und die zweite Zeile der Original-Rohdatei (Artefakt-Zeile) nicht mehr existiert.
        # nrows=3 liest Header + die ersten 2 Datenzeilen, wenn die Datei sauber ist.
        # Wenn die Artefakt-Zeile noch da wäre, würde es Header + Artefakt + 1. Datenzeile lesen.
        # Sicherer ist es, die ganze Datei zu laden und dann .head() zu verwenden.
        df = pd.read_csv(file_path, encoding='utf-8') 
        
        if df.empty:
            print("Datei ist leer oder enthält nur einen Header.")
            # Überprüfe, ob es nur ein Header ist oder wirklich leer
            try:
                # Versuche, nur den Header zu lesen, um zu sehen, ob die Datei existiert, aber keine Daten hat
                header_df = pd.read_csv(file_path, encoding='utf-8', nrows=0)
                if not header_df.columns.empty:
                    print("Datei enthält einen Header, aber keine Datenzeilen.")
                else:
                    print("Datei ist komplett leer.")
            except pd.errors.EmptyDataError:
                 print("Datei ist komplett leer (konnte nicht einmal Header lesen).")
            all_files_look_clean = False # Eine leere Datei ist hier auch ein Problem
            
        else:
            print("Kopfzeile und die ersten 2 Datenzeilen:")
            # .to_string() wird verwendet, um sicherzustellen, dass alle Spalten angezeigt werden
            # und die Ausgabe nicht von Pandas' Standard-Terminalbreite abgeschnitten wird.
            print(df.head(2).to_string())
            
            # Optionale Prüfung: Enthält die erste Datenzeile (Index 0) noch "Response" oder Spaltennamen?
            # Dies ist eine Heuristik.
            if 'respondent_id' in df.columns and pd.isna(df.iloc[0]['respondent_id']):
                print("WARNUNG: Die erste Datenzeile scheint einen fehlenden 'respondent_id' zu haben. Könnte die Artefakt-Zeile sein.")
                all_files_look_clean = False
            elif df.shape[0] > 0 and any(str(val).lower() == 'response' for val in df.iloc[0].values):
                 print("WARNUNG: Die erste Datenzeile enthält den Wert 'Response'. Könnte die Artefakt-Zeile sein.")
                 all_files_look_clean = False


    except pd.errors.EmptyDataError:
        print(f"FEHLER: Datei '{file_path}' ist leer und konnte nicht gelesen werden.")
        all_files_look_clean = False
    except Exception as e:
        print(f"FEHLER beim Lesen oder Anzeigen der Datei '{file_path}': {e}")
        all_files_look_clean = False
    
    print("-" * 70) # Trennlinie

print("\n\n=== Überprüfung abgeschlossen ===")
if all_files_look_clean:
    print("Alle überprüften Dateien scheinen die Artefakt-Zeile nicht mehr als erste Datenzeile zu enthalten. Gut gemacht!")
else:
    print("Mindestens eine Datei scheint noch Probleme zu haben oder konnte nicht korrekt gelesen werden. Bitte überprüfe die WARNUNGEN/FEHLER oben.")
