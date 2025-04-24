# src/powere/loaders/jasm/weekly.py

import pandas as pd
from powere.loaders.jasm.monthly import load_jasm_month

def load_jasm_week(year: int, start: str = None, end: str = None) -> pd.DataFrame:
    """
    Schneidet aus dem vor-kalkulierten Jahresprofil die ersten 7 Tage
    heraus und liefert genau 7×96 = 672 Zeilen, freqstr "15T".
    """
    # 1) Ganzes Jahr in 15-Minuten-Raster laden
    df = load_jasm_month(year)

    # 2) Index in echten DatetimeIndex umwandeln (parse_dates sollte das schon tun)
    df.index = pd.DatetimeIndex(df.index)

    # 3) Ersten Tag bestimmen (Mitternacht)
    first_day = df.index.normalize()[0]

    # 4) Voller 7-Tage-Index
    full_idx = pd.date_range(
        start=first_day,
        periods=7 * 96,
        freq="15T"
    )

    # 5) Reindex + interpolate
    week_df = df.reindex(full_idx).interpolate(method="linear")

    return week_df