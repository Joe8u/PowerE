'''PowerE/src/data_loader/survey_loader/incentive_loader.py

Ein separater Loader nur für Frage 10 (Incentives) aus question_10_incentive_wide.csv
'''
import os
import pandas as pd

# Absoluter Pfad zum Ordner data/processed/survey
dir_path = os.path.abspath(
    os.path.join(
        __file__,                # incentive_loader.py
        os.pardir,  # survey_loader
        os.pardir,  # data_loader
        os.pardir,  # src
        os.pardir,  # PowerE (Projekt-Root)
        'data', 'processed', 'survey'
    )
)

# Dateiname für Q10
_INCENTIVE_FILE = 'question_10_incentive_wide.csv'


def load_question_10_incentives() -> pd.DataFrame:
    """
    Lädt die Wide-CSV für Frage 10:
    PowerE/data/processed/survey/question_10_incentive_wide.csv
    Rückgabe als pandas DataFrame mit allen Spalten als strings.
    """
    path = os.path.join(dir_path, _INCENTIVE_FILE)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Incentive-Datei nicht gefunden: {path}")
    return pd.read_csv(path, dtype=str)
