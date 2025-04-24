#/Users/jonathan/Documents/GitHub/PowerE/src/powere/loaders/jasm/daily.py
import pandas as pd
from powere.loaders.jasm.monthly import load_jasm_month
from powere.utils.settings import TZ

def load_jasm_day(year: int, month: int, day: int = 1) -> pd.DataFrame:
    """
    Lädt aus dem statischen Monats-Profil genau einen Tag:
      – year, month, day
      – Index tz-aware mit freq "15T"
      – genau 96 Zeilen (24h × 4)
    """
    # 1) komplettes Monats-Profil laden
    df = load_jasm_month(year)

    # 2) gewünschten Tag herausschneiden
    start = pd.Timestamp(year=year, month=month, day=day, tz=TZ)
    end   = start + pd.Timedelta(days=1) - pd.Timedelta(minutes=15)
    day_df = df.loc[start:end]

    # 3) als 15-Min-Raster mit correktem freq markieren
    return day_df.asfreq("15T")