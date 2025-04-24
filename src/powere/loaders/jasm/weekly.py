import pandas as pd
from typing import Optional
from pathlib import Path
from powere.utils.settings import DATA_PROCESSED_STATIC
from powere.loaders.jasm.monthly import load_jasm_month

def load_jasm_week(year: int,
                   start: Optional[str] = None,
                   end: Optional[str] = None) -> pd.DataFrame:
    """
    Schneidet aus dem vor-kalkulierten Jahresprofil die ersten 7 Tage 
    heraus und liefert genau 7×96 = 672 Zeilen, freqstr "15T".
    """
    # 1) Ganzes Jahr laden
    df = load_jasm_month(year)

    # 2) Window der ersten Kalenderwoche
    first_ts = df.index[0].floor("D")
    week_end = first_ts + pd.Timedelta(days=7)
    week_df = df.loc[first_ts:week_end]

    # 3) Nicht-200% volle Wochenfüllung abfangen, dann neu indizieren
    full_idx = pd.date_range(
        start=first_ts,
        periods=7 * 96,
        freq="15T",
        tz=week_df.index.tz
    )
    week_df = week_df.reindex(full_idx).interpolate(method="linear")

    # 4) freq und freqstr setzen
    week_df.index.freq = pd.tseries.frequencies.to_offset("15T")
    week_df.index.freqstr = "15T"

    return week_df