import os
import pandas as pd

# =====================================
# attitudes.py
#
# Loader für die verarbeiteten Survey-Daten zu
# Q6 (Herausforderungen) und Q7 (Konsequenzen)
# =====================================

# Basisverzeichnis: drei Ebenen hoch vom aktuellen Skript
BASE_DIR = os.path.abspath(
    os.path.join(__file__, os.pardir, os.pardir, os.pardir)
)
# Verzeichnis mit den vorverarbeiteten CSVs
PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed', 'survey')


def load_attitudes():
    """
    Lädt die DataFrames für Frage 6 und Frage 7.

    Returns:
        dict: mit Schlüsseln:
            - 'challenges': DataFrame zu Q6 (Herausforderungen)
            - 'consequence': DataFrame zu Q7 (Konsequenzen)
    """
    files = {
        'challenges': 'question_6_challenges.csv',
        'consequence': 'question_7_consequence.csv',
    }
    dfs = {}
    for key, fname in files.items():
        path = os.path.join(PROCESSED_DIR, fname)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Datei nicht gefunden: {path}")
        dfs[key] = pd.read_csv(path, dtype=str)
    return dfs