# /Users/jonathan/Documents/GitHub/PowerE/src/powere/loaders/jasm/weekly.py
import pandas as pd
from pathlib import Path
from powere.utils.settings import DATA_PROC_STATIC

def load_jasm_week(year: int, start: str = None, end: str = None) -> pd.DataFrame:
    """
    Liest alle vor-kalkulierten Wochen-Profile eines Jahres und
    gibt sie als DataFrame zurück. Optional slice nach Datum.
    """
    base = Path(DATA_PROC_STATIC) / "jasm" / str(year) / "weekly"
    dfs = []
    # erwartet Dateien wie "appliance_weekly_{year}_W01.csv", …
    for fn in sorted(base.glob(f"appliance_weekly_{year}_W*.csv")):
        df = pd.read_csv(fn, index_col=0, parse_dates=True)
        dfs.append(df)

    full = pd.concat(dfs).sort_index()
    if start and end:
        full = full.loc[start:end]
    return full