#/Users/jonathan/Documents/GitHub/PowerE/src/powere/loaders/jasm/daily.py
from typing import Optional

import pandas as pd
from pathlib import Path

from powere.utils.settings import DATA_PROCESSED_STATIC, TZ


def load_jasm_day(
    year: int,
    month: int,
    day: Optional[int] = 1
) -> pd.DataFrame:
    """
    Lädt das statische Monatsprofil und gibt das Tagesprofil (96 × 15 Min)
    für year/month/day zurück, mit index.freqstr == "15T" und tz == TZ.
    """
    # 1) Monats-CSV einlesen
    fpath = (
        Path(DATA_PROCESSED_STATIC)
        / "jasm"
        / str(year)
        / "monthly"
        / f"appliance_monthly_{year}_{month:02d}.csv"
    )
    df = pd.read_csv(fpath, index_col=0, parse_dates=True)

    # 2) sicherstellen, dass der Index tz-aware ist
    if df.index.tz is None:
        df.index = df.index.tz_localize(
            TZ,
            ambiguous="infer",
            nonexistent="shift_forward"
        )
    else:
        df.index = df.index.tz_convert(TZ)

    # 3) Tagesfenster herausschneiden (96 Intervalle)
    start = pd.Timestamp(year=year, month=month, day=day, tz=TZ)
    end   = start + pd.Timedelta(hours=24) - pd.Timedelta(minutes=15)
    day_df = df.loc[start:end]

    # 4) 15-Min-Raster forcieren
    day_df = day_df.asfreq("15T")

    return day_df