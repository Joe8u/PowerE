#!/usr/bin/env python3
# src/powere/loaders/jasm/weekly.py

import pandas as pd
from pathlib import Path
from powere.utils.settings import DATA_PROCESSED_STATIC
from .monthly import load_jasm_month

def load_jasm_week(year: int, start: str = None, end: str = None) -> pd.DataFrame:
    """
    Liest alle Monats-Profile eines Jahres und gibt die erste Kalenderwoche
    (7×96 Zeitpunkte) als 15-Minuten-Raster zurück.
    Optionales Slicing mit start/end.
    """
    # 1) Gesamtjahr laden
    df = load_jasm_month(year)

    # 2) Index als DatetimeIndex + freq setzen
    df.index = pd.to_datetime(df.index)
    df.index.freq = pd.tseries.frequencies.to_offset("15T")

    # 3) Erste 7×96 Reihen herausschneiden
    week_df = df.iloc[:7 * 96]

    # 4) Optionaler Slicing
    if start and end:
        week_df = week_df.loc[start:end]

    return week_df