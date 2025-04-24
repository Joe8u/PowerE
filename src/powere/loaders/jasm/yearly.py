# src/loaders/jasm/yearly.py
import pandas as pd
from pathlib import Path
from powere.utils.settings import DATA_PROCESSED_STATIC

def load_jasm_year(year: int) -> pd.DataFrame:
    """
    Liest das vor-kalkulierte Jahres-Durchschnitts-CSV:
    index=month (1–12), columns=Appliances.
    """
    fn = (
        Path(DATA_PROCESSED_STATIC)
        / "jasm" / str(year) / "yearly"
        / f"appliance_yearly_avg_{year}.csv"
    )
    df = pd.read_csv(fn, index_col="month")
    return df