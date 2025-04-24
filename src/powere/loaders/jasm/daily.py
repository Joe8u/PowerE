# src/powere/loaders/jasm/daily.py
import pandas as pd
from pathlib import Path
from powere.utils.settings import DATA_PROCESSED_STATIC

def load_jasm_day(year: int, month: int, day_type: str = None) -> pd.DataFrame:
    """
    Lädt das statische Monatsprofil und gibt das erste Tagesprofil
    (96 × 15 Min) für year/month zurück, mit index.freqstr '15T'.
    """
    # 1) Pfad zur vor­berechneten Monats-CSV
    fpath = (
        Path(DATA_PROCESSED_STATIC)
        / "jasm"
        / str(year)
        / "monthly"
        / f"appliance_monthly_{year}_{month:02d}.csv"
    )

    # 2) CSV laden
    df = pd.read_csv(fpath, index_col=0, parse_dates=True)

    # 3) Erstes Tagesprofil (genau 96 Zeilen)
    day_df = df.iloc[:96].copy()

    # 4) freq auf 15T setzen und Zeitzone übernehmen
    freq = pd.tseries.frequencies.to_offset("15T")
    tz = day_df.index.tz
    day_df.index = pd.DatetimeIndex(day_df.index.values, tz=tz, freq=freq)

    return day_df