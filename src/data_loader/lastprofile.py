# src/data_loader/lastprofile.py

import pandas as pd
from pathlib import Path
from typing import List, Optional
import datetime

BASE_DIR = Path("data/processed/lastprofile")

# 1) Meta-Info: Welche Appliances gibt es?
def list_appliances(year: int) -> List[str]:
    sample = pd.read_csv(BASE_DIR/str(year)/f"{year}-01.csv", nrows=1)
    return [c for c in sample.columns if c != "timestamp"]

# 2) Lade genau einen Monat (alle Appliances)
def load_month(
    year: int,
    month: int,
    tz: str = "Europe/Zurich"
) -> pd.DataFrame:
    """
    Lädt die CSV für Jahr/Monat, konvertiert Timestamp → naive datetime.
    Gibt DataFrame mit Index timestamp und allen Appliance-Spalten zurück.
    """
    path = BASE_DIR/str(year)/f"{year}-{month:02d}.csv"
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df["timestamp"] = (
        pd.to_datetime(df["timestamp"], utc=True)
          .dt.tz_convert(tz)
          .dt.tz_localize(None)
    )
    return df.set_index("timestamp")

# 3) Lade Daten für einen beliebigen Zeitbereich (quer über Monate)
def load_range(
    start: datetime.datetime,
    end: datetime.datetime,
    year: Optional[int] = None,
    tz: str = "Europe/Zurich"
) -> pd.DataFrame:
    """
    Lädt nur die Monats-Dateien, die in den Bereich fallen, und liefert
    einen DataFrame mit allen Appliance-Spalten im gegebenen Zeitfenster.
    """
    if year is None:
        year = start.year
    # Liste der Monate, die im Bereich liegen
    months = sorted({start.month, end.month}) if start.year == end.year else range(1,13)
    dfs = []
    for m in months:
        df_m = load_month(year, m, tz)
        dfs.append(df_m)
    full = pd.concat(dfs)
    return full.loc[start:end]

# 4) Lade nur einzelne Appliance-Spalten
def load_appliances(
    appliances: List[str],
    start: datetime.datetime,
    end: datetime.datetime,
    year: Optional[int] = None,
    tz: str = "Europe/Zurich"
) -> pd.DataFrame:
    """
    Lädt für das gegebene Zeitfenster nur die angegebenen Appliance-Spalten.
    Das spart Speicher, wenn man nur wenige Appliances braucht.
    """
    df_range = load_range(start, end, year, tz)
    cols = ["timestamp"] + [a for a in appliances if a in df_range.columns]
    return df_range[appliances]

# 5) Chunked Loader für sehr große Dateien (falls nötig)
def load_range_chunked(
    start: datetime.datetime,
    end: datetime.datetime,
    appliances: List[str],
    year: Optional[int] = None,
    tz: str = "Europe/Zurich",
    chunksize: int = 10_000
) -> pd.DataFrame:
    """
    Liest die CSVs in Chunks, filtert pro Chunk nach Zeitbereich und Spalten,
    und rollt dann alle Teil-DataFrames zusammen.
    Nützlich bei extrem großen Dateien.
    """
    if year is None:
        year = start.year
    months = sorted({start.month, end.month}) if start.year == end.year else range(1,13)
    frames = []
    for m in months:
        path = BASE_DIR/str(year)/f"{year}-{m:02d}.csv"
        for chunk in pd.read_csv(
            path, parse_dates=["timestamp"], chunksize=chunksize
        ):
            # Zeitzone verwerfen
            chunk["timestamp"] = (
                pd.to_datetime(chunk["timestamp"], utc=True)
                  .dt.tz_convert(tz)
                  .dt.tz_localize(None)
            )
            mask = (chunk["timestamp"] >= start) & (chunk["timestamp"] <= end)
            sel = chunk.loc[mask, ["timestamp"] + appliances]
            if not sel.empty:
                frames.append(sel.set_index("timestamp"))
    return pd.concat(frames)