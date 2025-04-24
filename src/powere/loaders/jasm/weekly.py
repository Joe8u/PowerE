# src/powere/loaders/jasm/weekly.py

import pandas as pd
from powere.loaders.jasm.monthly import load_jasm_month

def load_jasm_week(year: int, start: str = None, end: str = None) -> pd.DataFrame:
    """
    Schneidet die ersten 7 Tage (7×96 = 672 Intervalle) aus dem statischen
    Jahresprofil und gibt DataFrame mit index.freqstr '15T' zurück.
    """
    # Ganzes Jahr laden (15-Min-Raster)
    df = load_jasm_month(year)

    # Startzeitpunkt und 7-Tage-Fenster
    first_day = df.index[0].floor("D")
    week_df = df.loc[first_day : first_day + pd.Timedelta(days=7)]

    # vollständigen 7×96-Index erzeugen
    freq = pd.tseries.frequencies.to_offset("15T")
    tz = week_df.index.tz
    full_idx = pd.date_range(start=first_day, periods=7 * 96, freq=freq, tz=tz)

    # neu indexieren und ggf. lücken füllen
    week_df = week_df.reindex(full_idx).interpolate(method="linear")
    week_df.index = pd.DatetimeIndex(week_df.index.values, tz=tz, freq=freq)

    return week_df