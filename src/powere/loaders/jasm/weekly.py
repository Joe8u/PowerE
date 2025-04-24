# src/powere/loaders/jasm/weekly.py
import pandas as pd
from powere.loaders.jasm.monthly import load_jasm_month
from powere.utils.settings import TZ

def load_jasm_week(year: int, start: str = None, end: str = None) -> pd.DataFrame:
    """
    Schneidet aus dem statischen Monats-Profil die ersten 7 Tage
    heraus und liefert genau 7×96 Zeilen im Raster freq "15T".
    """
    # 1) komplettes Jahres-Monatsprofil laden
    df = load_jasm_month(year)

    # 2) ersten Tag (00:00) ermitteln
    first = pd.Timestamp(df.index[0].date(), tz=TZ)
    last  = first + pd.Timedelta(days=7) - pd.Timedelta(minutes=15)

    # 3) slice und alsfreq
    week_df = df.loc[first:last]
    return week_df.asfreq("15T")