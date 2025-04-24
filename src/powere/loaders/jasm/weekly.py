# src/powere/loaders/jasm/weekly.py

import pandas as pd
from powere.loaders.jasm.monthly import load_jasm_month

def load_jasm_week(year: int, start: str = None, end: str = None) -> pd.DataFrame:
    """
    Liest das gesamte Jahres-Raster und schneidet die erste Kalenderwoche heraus.
    """
    # lade das ganze Jahr in 15-Min-Abständen
    df = load_jasm_month(year)

    # Ersten Tag bestimmen und 7-Tage-Fenster
    first_date = df.index.normalize()[0]
    week_df = df.loc[first_date : first_date + pd.Timedelta(days=7)]

    # damit pytest df.index.freqstr überprüfen kann:
    week_df.index.freq = pd.tseries.frequencies.to_offset("15T")
    return week_df