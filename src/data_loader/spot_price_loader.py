#/Users/jonathan/Documents/GitHub/PowerE/src/data_loader/spot_price_loader.py

import pandas as pd
from pathlib import Path
from typing import List, Optional
import datetime

# Basis-Verzeichnis für die vorprozessierten Spot-Preisdaten
BASE_DIR = Path("data/processed/market/spot_prices")


def list_spot_price_months(year: int) -> List[int]:
    """
    Gibt eine sortierte Liste der Monatsnummern zurück, für die vorprozessierte Spot-Preis-CSV-Dateien existieren.
    Beispiel: [1, 2, ..., 12]
    """
    months: List[int] = []
    pattern = f"{year}-[0-1][0-9].csv"
    for file in BASE_DIR.glob(pattern):
        stem = file.stem  # z.B. "2024-01"
        parts = stem.split('-')
        try:
            m = int(parts[1])
            months.append(m)
        except (IndexError, ValueError):
            continue
    return sorted(set(months))


def load_spot_price_month(
    year: int,
    month: int,
    tz: str = "Europe/Zurich",
    as_kwh: bool = False
) -> pd.DataFrame:
    """
    Lädt eine verarbeitete Spot-Preis-Monatsdatei (CSV).
    - year, month: Jahr und Monat
    - tz: Zeitzone, in die der Timestamp konvertiert und dann tz-naiv ausgegeben wird
    - as_kwh: Wenn True, wandelt price_eur_mwh in price_eur_kwh (/1000) um

    Rückgabe: DataFrame mit Index=timestamp und Spalte 'price_eur_mwh' (oder 'price_eur_kwh').
    """
    path = BASE_DIR / f"{year}-{month:02d}.csv"
    df = pd.read_csv(path, parse_dates=["timestamp"])  # timestamp ist bereits lokal und tz-naiv

    # Sicherstellen, dass Index tz-naiv ist
    df["timestamp"] = (
        df["timestamp"]
          .dt.tz_localize(tz, ambiguous='infer')
          .dt.tz_convert(None)
    )
    df = df.set_index("timestamp")

    # Umrechnung in EUR/kWh falls benötigt
    if as_kwh:
        df = df.rename(columns={"price_eur_mwh": "price_eur_kwh"})
        df["price_eur_kwh"] = df["price_eur_kwh"] / 1000.0
    return df


def load_spot_price_range(
    start: datetime.datetime,
    end:   datetime.datetime,
    tz: str = "Europe/Zurich",
    as_kwh: bool = False
) -> pd.DataFrame:
    """
    Lädt Spot-Preisdaten zwischen 'start' und 'end' (innerhalb eines Jahres).
    - Verwendet load_spot_price_month für die benötigten Monate.
    - Schneidet anschließend auf den Label-Bereich.
    """
    if start.year != end.year:
        raise ValueError("start und end müssen im selben Jahr liegen")
    year = start.year
    months = sorted({start.month, end.month})
    parts: List[pd.DataFrame] = []
    for m in months:
        df_month = load_spot_price_month(year, m, tz=tz, as_kwh=as_kwh)
        parts.append(df_month)
    full = pd.concat(parts).sort_index()
    return full.loc[start:end]
