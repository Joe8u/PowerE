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

    # 3) Tagesfenster definieren
    start = pd.Timestamp(year=year, month=month, day=day, tz=TZ)
    end = start + pd.Timedelta(hours=24) - pd.Timedelta(minutes=15)

    # 4) Vollständiges 15-Min-Raster erzeugen
    full_idx = pd.date_range(start=start, end=end, freq="15T", tz=TZ)

    # 5) Daten neu indexieren und fehlende Werte interpolieren
    day_df = df.reindex(full_idx)
    day_df = day_df.interpolate(method="time")
    day_df.index.freq = "15T"

    return day_df