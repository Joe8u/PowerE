import pandas as pd
from pathlib import Path
from src.utils.settings import DATA_PROC_STATIC

def load_jasm_yearly(year: int) -> pd.DataFrame:
    """
    Lädt den Monats-Durchschnitt für ein ganzes Jahr (yearly_avg_{year}.csv)
    und gibt ein DataFrame mit index=month, columns=Appliances zurück.
    """
    fn = Path(DATA_PROC_STATIC) / "jasm" / str(year) / "yearly" / f"appliance_yearly_avg_{year}.csv"
    df = pd.read_csv(fn, index_col="month")
    return df