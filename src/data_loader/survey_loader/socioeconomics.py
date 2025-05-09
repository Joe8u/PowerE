# src/preprocessing/survey/socioeconomics.py

import os
import pandas as pd

# Directory where all the processed survey CSVs live
BASE_DIR = os.path.abspath(
    os.path.join(__file__, os.pardir, os.pardir, os.pardir, 'data', 'processed', 'survey')
)

# Logical → filename map for Q13–Q15
_FILES = {
    'income':     'question_13_income.csv',     # Q13: Haushaltseinkommen
    'education':  'question_14_education.csv',  # Q14: Bildungsabschluss
    'party_pref': 'question_15_party.csv',      # Q15: Parteien-Präferenz
}

def _load_csv(key: str) -> pd.DataFrame:
    """
    Load a single CSV by its logical key.
    Raises KeyError if key unknown or FileNotFoundError if missing.
    """
    try:
        fname = _FILES[key]
    except KeyError:
        raise KeyError(f"No such socio-economic component: {key!r}")
    path = os.path.join(BASE_DIR, fname)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Could not find processed CSV at: {path}")
    return pd.read_csv(path, dtype=str)

def load_socioeconomics() -> dict[str, pd.DataFrame]:
    """
    Load all socio-economic survey tables (Q13–Q15).

    Returns
    -------
    dict
        Keys are ['income', 'education', 'party_pref'] mapping to DataFrames.
    """
    return { key: _load_csv(key) for key in _FILES }

# Convenience loaders:
def load_income() -> pd.DataFrame:
    """Q13: Haushalts-Nettoeinkommen"""
    return _load_csv('income')

def load_education() -> pd.DataFrame:
    """Q14: Höchster Bildungsabschluss"""
    return _load_csv('education')

def load_party_pref() -> pd.DataFrame:
    """Q15: Partei-Präferenz"""
    return _load_csv('party_pref')