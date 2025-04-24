# /Users/jonathan/Documents/GitHub/PowerE/src/powere/loaders/jasm/monthly.py
import pandas as pd
from pathlib import Path
from powere.utils.settings import DATA_PROCESSED_STATIC, TZ

def load_jasm_month(year: int, start: str = None, end: str = None) -> pd.DataFrame:
    """
    Liest alle 12 Monats-Profile eines Jahres und
    gibt sie als einen einzigen DataFrame zurück.
    Wenn start/end angegeben, wird darauf gesliced.
    """
    base = Path(DATA_PROCESSED_STATIC) / "jasm" / str(year) / "monthly"
    dfs = []
    for m in range(1, 13):
        fn = base / f"appliance_monthly_{year}_{m:02d}.csv"
        df = pd.read_csv(fn, index_col=0, parse_dates=True)
        # TZ-Info wiederherstellen (CSV enthält tz-aware Timestamps)
        df.index = df.index.tz_localize(TZ, ambiguous="infer", nonexistent="shift_forward")
        dfs.append(df)
    full = pd.concat(dfs).sort_index()
    if start and end:
        full = full.loc[start:end]
    return full
