# src/powere/loaders/jasm/daily.py

import pandas as pd
from pathlib import Path
from powere.utils.settings import DATA_PROC_STATIC

def load_jasm_day(year: int, month: int, day_type: str = "weekday") -> pd.DataFrame:
    """
    Lädt den 1. Kalendertag des Monats als 15-Min-Raster
    aus der vor­berechneten Monats-CSV.
    day_type wird im Moment ignoriert (alle Loader arbeiten nur mit
    den vorgefertigten monthly-Daten, die bereits DST-handling enthalten).
    """
    # Datei mit dem 15-Min-Raster für den ganzen Monat
    fpath = Path(DATA_PROC_STATIC) / "jasm" / str(year) / "monthly" / f"appliance_monthly_{year}_{month:02d}.csv"
    df = pd.read_csv(fpath, index_col=0, parse_dates=True)

    # Ersten Tag herausschneiden
    first_date = df.index.normalize()[0]
    mask = (df.index >= first_date) & (df.index < first_date + pd.Timedelta(days=1))
    day_df = df.loc[mask]

    # damit pytest df.index.freqstr überprüfen kann:
    day_df.index.freq = pd.tseries.frequencies.to_offset("15T")
    return day_df