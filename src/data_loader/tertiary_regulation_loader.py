#/Users/jonathan/Documents/GitHub/PowerE/src/data_loader/tertiary_regulation_loader.py

import pandas as pd
from pathlib import Path
from typing import List, Optional
import datetime

# Basis-Verzeichnis für die vorprozessierten tertiären Regelleistungsdaten
BASE_DIR = Path("data/processed/market/regelenergie")


def list_regulation_months(year: int) -> List[int]:
    """
    Gibt eine sortierte Liste der Monatsnummern zurück, für die vorprozessierte CSVs existieren.
    Beispiel: [1, 2, ..., 12]
    """
    months: List[int] = []
    for file in BASE_DIR.glob(f"{year}-[0-1][0-9].csv"):
        # Dateiname: "YYYY-MM.csv"
        stem = file.stem  # z.B. "2024-01"
        parts = stem.split('-')
        try:
            m = int(parts[1])
        except (IndexError, ValueError):
            continue
        months.append(m)
    return sorted(set(months))


def load_regulation_month(
    year: int,
    month: int,
    *,
    tz: str = "Europe/Zurich"
) -> pd.DataFrame:
    """
    Lädt die vorprozessierte Monatsdatei für tertiäre Regelleistung.
    CSV hat Spalten: timestamp, total_called_mw, avg_price_eur_mwh
    Index ist timestamp (naiv, lokalisiert nach tz und dann tz-untagged).
    """
    path = BASE_DIR / f"{year}-{month:02d}.csv"
    df = pd.read_csv(
        path,
        parse_dates=["timestamp"]
    )
    # Zeitstempel lokalzeiten
    df["timestamp"] = (
        df["timestamp"]
          .dt.tz_localize(tz)
          .dt.tz_convert(None)
    )
    return df.set_index("timestamp")


def load_regulation_range(
    start: datetime.datetime,
    end:   datetime.datetime,
    *,
    tz: str = "Europe/Zurich"
) -> pd.DataFrame:
    """
    Lädt die vorprozessierten tertiären Regelleistungsdaten zwischen 'start' und 'end'.
    Unterstützt nur einen Zeitraum innerhalb eines Jahres.
    """
    if start.year != end.year:
        raise ValueError("Start und Enddatum müssen im selben Jahr liegen")
    year = start.year
    months = sorted({start.month, end.month})
    parts: List[pd.DataFrame] = []
    for m in months:
        df_m = load_regulation_month(year, m, tz=tz)
        parts.append(df_m)
    full = pd.concat(parts).sort_index()
    # Auf den gewünschten Bereich schneiden
    return full.loc[start:end]
