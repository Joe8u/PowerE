# -*- coding: utf-8 -*-
"""
survey_loader/demographics.py

Demographics loader for the PowerE survey.

Enthält Funktionen, um die vorverarbeiteten CSVs zu Q1–Q5
(Age, Gender, Household Size, Accommodation, Electricity) zu laden.
"""

import os
import pandas as pd

# === Pfad-Setup ===
# Wir gehen drei Ebenen nach oben bis zum Projekt-Root,
# dort liegen die Ordner data/processed/survey
BASE_DIR      = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, os.pardir))
PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed', 'survey')

# Mapping aus logischem Key → Dateiname
FILES = {
    'age':            'question_1_age.csv',
    'gender':         'question_2_gender.csv',
    'household_size': 'question_3_household_size.csv',
    'accommodation':  'question_4_accommodation.csv',
    'electricity':    'question_5_electricity.csv',
}

def load_demographics() -> dict[str, pd.DataFrame]:
    """
    Lädt alle Demographie-DataFrames (Q1–Q5) und gibt sie als Dict zurück.
    
    Returns:
        dict[str, pd.DataFrame]: Ein Dict mit Keys 'age', 'gender', 'household_size',
                                 'accommodation', 'electricity' und den zugehörigen DataFrames.
    """
    dfs: dict[str, pd.DataFrame] = {}
    for key, fname in FILES.items():
        path = os.path.join(PROCESSED_DIR, fname)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Processed file not found: {path}")
        # Alle Spalten als String einlesen, damit die respondent_id unverändert bleibt
        dfs[key] = pd.read_csv(path, dtype=str)
    return dfs

if __name__ == "__main__":
    # Schnelltest: lade alle Demographie-Tabellen und gib ihre Shapes aus
    try:
        data = load_demographics()
    except Exception as e:
        print(f"Fehler beim Laden der Demographie-Daten: {e}")
        exit(1)
    print("Erfolgreich alle Demographie-Daten geladen:")
    for key, df in data.items():
        print(f"  - {key:15s}: {df.shape[0]:5d} Zeilen × {df.shape[1]:2d} Spalten")