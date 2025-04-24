import pandas as pd
from pathlib import Path

from powere.loaders.jasm.monthly import load_jasm_month


def load_jasm_week(year: int, start: str = None, end: str = None) -> pd.DataFrame:
    """
    Schneidet aus den vor­berechneten Monats-Profilen
    die erste Kalenderwoche (7×96 Punkte) heraus.
    Liefert genau 672 Zeilen, freqstr "15T".
    """
    # 1) ganzes Jahr als 15T-Raster
    df = load_jasm_month(year)

    # 2) Index in echten DatetimeIndex (ohne Objekt-Dtype)
    df.index = pd.DatetimeIndex(df.index)

    # 3) tz-lokalisieren, falls noch nicht geschehen
    if df.index.tz is None:
        df.index = df.index.tz_localize(
            "Europe/Zurich", nonexistent="shift_forward", ambiguous="infer"
        )

    # 4) Grid der ersten Kalenderwoche erzeugen
    first_ts = df.index[0].floor("D")
    full_idx = pd.date_range(
        start=first_ts,
        periods=7 * 96,
        freq="15T",
        tz=df.index.tz
    )

    # 5) neu indizieren & füllen
    week_df = df.reindex(full_idx).interpolate(method="linear")

    # full_idx bringt freqstr "15T" mit
    return week_df