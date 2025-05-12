#PowerE/src/data_loader/survey_loader/nonuse_loader.py

import os
import pandas as pd

# Absoluter Pfad zum Ordner data/processed/survey
_DIR = os.path.abspath(
    os.path.join(
        __file__,                # nonuse_loader.py
        os.pardir,  # survey_loader
        os.pardir,  # data_loader
        os.pardir,  # src
        os.pardir,  # PowerE (Projekt-Root)
        'data', 'processed', 'survey'
    )
)

# Dateiname für Q9
_NONUSE_FILE = 'question_9_nonuse_wide.csv'

def load_question_9_nonuse() -> pd.DataFrame:
    """
    Lädt die Wide-CSV für Frage 9 (Non-Use-Dauer):
    PowerE/data/processed/survey/question_9_nonuse_wide.csv

    Gibt ein pandas DataFrame zurück, alle Spalten als strings.
    """
    path = os.path.join(_DIR, _NONUSE_FILE)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Nonuse-Datei nicht gefunden: {path}")
    return pd.read_csv(path, dtype=str)