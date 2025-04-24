# src/powere/loaders/jasm/daily.py

import pandas as pd
from pathlib import Path
from powere.utils.settings import DATA_PROCESSED_STATIC

def load_jasm_day(year: int, month: int) -> pd.DataFrame:
    """
    Liest aus den vor­kalkulierten Monats-CSV
    nur den ersten Tag heraus und gibt genau 96 Zeilen
    im 15-Minuten-Raster zurück.
    """
    # Pfad zur Monatsdatei
    fpath = Path(DATA_PROCESSED_STATIC) / "jasm" / str(year) / "monthly" / f"appliance_monthly_{year}_{month:02d}.csv"
    df = pd.read_csv(fpath, index_col=0, parse_dates=[0])

    # erstes Datum normalisieren (00:00)
    df.index = pd.to_datetime(df.index)  # sicherstellen DatetimeIndex
    day0 = df.index.normalize()[0]
    day_end = day0 + pd.Timedelta(days=1) - pd.Timedelta(minutes=15)

    # genau einen Tag herausschneiden
    day_df = df.loc[day0:day_end].copy()
    # Index-Frequenz setzen
    day_df.index.freq = pd.tseries.frequencies.to_offset("15T")
    return day_df