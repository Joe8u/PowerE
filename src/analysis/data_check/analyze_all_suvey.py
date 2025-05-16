# PowerE/src/analysis/data_check/analyze_all_suvey.py
"""
Generelles Skript zur Datenqualitätsprüfung für vorverarbeitete Umfragedaten.

Dieses Skript iteriert über eine Liste von vorverarbeiteten CSV-Dateien,
lädt jede Datei und führt grundlegende Datenqualitätsprüfungen durch,
wie z.B. Zählung fehlender Werte und deskriptive Statistiken/Häufigkeiten.
"""
import os
import pandas as pd
import numpy as np

# --- Konfiguration ---
# Passe diesen Pfad an den Ort an, an dem deine 15 vorverarbeiteten CSVs liegen
PROCESSED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../data/processed/survey/'))

# Liste deiner vorverarbeiteten Dateinamen (oder du liest alle CSVs aus dem Ordner ein)
# Beispielhafte Liste - BITTE AN DEINE DATEINAMEN ANPASSEN!
processed_files_info = {
    'question_1_age.csv': {'answer_col': 'age', 'type': 'numeric'},
    'question_2_gender.csv': {'answer_col': 'gender', 'type': 'categorical'},
    'question_3_household_size.csv': {'answer_col': 'household_size', 'type': 'numeric'}, # Oder kategorial, je nach Kodierung
    'question_4_accommodation.csv': {'answer_col': 'accommodation_type', 'type': 'categorical'},
    'question_5_electricity.csv': {'answer_col': 'electricity_type', 'type': 'categorical'},
    'question_6_challenges.csv': {'answer_col': 'challenge_text', 'type': 'text'}, # Für Text ist value_counts oft nicht so sinnvoll, eher NAs prüfen
    'question_7_consequence.csv': {'answer_col': 'consequence', 'type': 'categorical'},
    'question_8_importance_wide.csv': {'type': 'matrix_numeric'}, # Spezielle Behandlung für Wide-Format
    'question_9_nonuse_wide.csv': {'type': 'matrix_categorical'}, # Spezielle Behandlung für Wide-Format
    'question_10_incentive_wide.csv': {'type': 'matrix_mixed'}, # Spezielle Behandlung für Wide-Format (choice/pct)
    'question_11_notification.csv': {'answer_col': 'q11_notify', 'type': 'categorical'},
    'question_12_smartplug.csv': {'answer_col': 'q12_smartplug', 'type': 'categorical'},
    'question_13_income.csv': {'answer_col': 'q13_income', 'type': 'categorical'}, # Oder ordinal
    'question_14_education.csv': {'answer_col': 'q14_education', 'type': 'categorical'}, # Oder ordinal
    'question_15_party.csv': {'answer_col': 'q15_party', 'type': 'categorical'}
    # Füge hier alle deine 15 Dateinamen und Infos hinzu
}

print(f"=== Starte generelle Datenqualitätsprüfung für {len(processed_files_info)} Dateien ===")
print(f"Daten werden aus '{PROCESSED_DIR}' geladen.\n")

for filename, info in processed_files_info.items():
    file_path = os.path.join(PROCESSED_DIR, filename)
    print(f"\n--- Prüfung für Datei: {filename} ---")

    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except FileNotFoundError:
        print(f"FEHLER: Datei '{file_path}' nicht gefunden. Überspringe.")
        continue

    print(f"Anzahl Zeilen (Teilnehmer): {df.shape[0]}")
    print(f"Anzahl Spalten: {df.shape[1]}")
    # print("Spaltennamen:", df.columns.tolist()) # Kann hilfreich sein für Debugging

    # Generelle Prüfung auf fehlende Werte für alle Spalten in dieser Datei
    print("\nFehlende Werte pro Spalte:")
    print(df.isnull().sum())

    question_type = info.get('type')

    if question_type == 'matrix_numeric' or question_type == 'matrix_categorical' or question_type == 'matrix_mixed':
        print(f"\nMatrix-Frage '{filename}': Analysiere jede relevante Datenspalte...")
        for col in df.columns:
            if col.lower() == 'respondent_id': # respondent_id überspringen
                continue
            
            print(f"\n  Analyse für Spalte '{col}':")
            print(f"    Anzahl fehlender Werte: {df[col].isnull().sum()}")
            
            # Versuche, die Spalte als numerisch zu behandeln, wenn möglich
            try:
                numeric_col = pd.to_numeric(df[col], errors='raise') # errors='raise' um zu sehen, ob es wirklich numerisch ist
                print("    Deskriptive Statistiken (als numerisch interpretiert):")
                print(numeric_col.describe())
            except (ValueError, TypeError):
                # Wenn nicht rein numerisch, als kategorial/Text behandeln
                print("    Häufigkeitsverteilung (als kategorial/Text interpretiert):")
                print(df[col].value_counts(dropna=False).head(10)) # Zeige die Top 10 Kategorien + NAs
                if df[col].nunique() > 10:
                    print(f"    (Weitere {df[col].nunique() - 10} einzigartige Werte vorhanden)")
        
    elif 'answer_col' in info:
        answer_col_name = info.get('answer_col')
        if answer_col_name not in df.columns:
            print(f"FEHLER: Antwortspalte '{answer_col_name}' nicht in '{filename}' gefunden. Überspringe Detailanalyse.")
            continue

        print(f"\nDetailanalyse für Antwortspalte '{answer_col_name}':")
        
        if question_type == 'numeric':
            print("  Deskriptive Statistiken:")
            # pd.to_numeric mit errors='coerce' ist sicherer, falls doch Text drin ist
            numeric_series = pd.to_numeric(df[answer_col_name], errors='coerce')
            if numeric_series.notnull().sum() > 0: # Nur wenn es valide Zahlen gibt
                 print(numeric_series.describe())
                 # Hier könntest du noch Histogramme/Boxplots hinzufügen, wenn gewünscht
            else:
                print("    Keine validen numerischen Daten in dieser Spalte nach Konvertierung.")
            if numeric_series.isnull().sum() > df[answer_col_name].isnull().sum():
                print(f"    WARNUNG: {numeric_series.isnull().sum() - df[answer_col_name].isnull().sum()} Werte konnten nicht in Zahlen konvertiert werden und wurden zu NA.")

        elif question_type == 'categorical':
            print("  Häufigkeitsverteilung:")
            print(df[answer_col_name].value_counts(dropna=False))

        elif question_type == 'text':
            print(f"  Einzigartige Werte (Beispiele für Textfeld '{answer_col_name}'):")
            # Zeige einige Beispiele, falls es viele einzigartige Texte sind
            unique_values = df[answer_col_name].dropna().unique()
            if len(unique_values) > 10:
                print(list(unique_values[:10]))
                print(f"    ... und {len(unique_values) - 10} weitere einzigartige Texte.")
            else:
                print(list(unique_values))
        else:
            print(f"  Unbekannter Fragetyp '{question_type}' für '{answer_col_name}'. Zeige Basisinfos.")
            print(df[answer_col_name].head()) # Zeige die ersten paar Einträge
    else:
        print("FEHLER: Keine 'answer_col' für Detailanalyse in 'processed_files_info' definiert und kein Matrix-Typ.")


print("\n\n=== Datenqualitätsprüfung abgeschlossen ===")