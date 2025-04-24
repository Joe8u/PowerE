# src/powere/loaders/jasm/weekly.py

import pandas as pd
from powere.loaders.jasm.monthly import load_jasm_month

def load_jasm_week(year: int) -> pd.DataFrame:
    """
    Gibt die ersten 7×96 = 672 (oder mehr) Zeilen
    des Jahres-Rasters im 15-Minuten-Takt zurück.
    """
    # komplettes Jahr laden
    df = load_jasm_month(year)
    df.index = pd.to_datetime(df.index)  # sicherstellen DatetimeIndex

    # erster Kalendertag
    start = df.index.normalize()[0]
    end   = start + pd.Timedelta(days=7) - pd.Timedelta(minutes=15)

    week_df = df.loc[start:end].copy()
    week_df.index.freq = pd.tseries.frequencies.to_offset("15T")
    return week_df