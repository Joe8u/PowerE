# src/powere/loaders/jasm/weekly.py
import pandas as pd

from powere.loaders.jasm.monthly import load_jasm_month
from powere.utils.settings import TZ


def load_jasm_week(
    year: int,
    start: str = None,
    end: str = None
) -> pd.DataFrame:
    """
    Schneidet die ersten 7 Tage (7×96 = 672 Intervalle) aus dem statischen
    Jahresprofil und gibt DataFrame mit index.freqstr == "15T" zurück.
    """
    # 1) Ganzes Jahr laden
    df = load_jasm_month(year)

    # 2) Start der ersten Kalenderwoche
    first_day = df.index[0].floor("D")
    week_df = df.loc[first_day : first_day + pd.Timedelta(days=7)]

    # 3) Vollständiges 7×96-Raster erzwingen
    full_idx = pd.date_range(
        start=first_day,
        periods=7 * 96,
        freq="15T",
        tz=TZ
    )

    # 4) Reindex + Lücken füllen
    week_df = week_df.reindex(full_idx).interpolate(method="linear")

    # 5) 15-Min-Frequent setzen
    week_df = week_df.asfreq("15T")

    return week_df