from pathlib import Path

import pandas as pd
from pandas.tseries.frequencies import to_offset

from powere.loaders.jasm.monthly import load_jasm_month


def load_jasm_week(year: int, start: str = None, end: str = None) -> pd.DataFrame:
    """
    Schneidet aus den vor­berechneten Monats-Profilen
    die erste Kalenderwoche (7×96 Punkte) heraus.
    Liefert mindestens 672 Zeilen, freqstr "15T".
    """
    # 1) Ganzes Jahr als 15T-Raster laden
    df = load_jasm_month(year)

    # 2) Beginn der ersten Kalenderwoche (am 1. Januar)
    first_ts = df.index[0].floor("D")

    # 3) Vollständigen 7-Tage-Index erzeugen
    full_idx = pd.date_range(
        start=first_ts,
        periods=7 * 96,
        freq="15T"
    )

    # 4) DataFrame neu indizieren und interpolieren
    week_df = df.reindex(full_idx).interpolate(method="linear")

    # 5) Exakt 15-Tonnen-Offset an den Index hängen
    week_df.index.freq = to_offset("15T")

    return week_df