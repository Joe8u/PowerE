# src/data_loader/lastprofile.py

import pandas as pd
from pathlib import Path
from typing import List, Optional
import datetime

BASE_DIR = Path("data/processed/lastprofile")

# --- 0) Survey-Gruppen-Mapping (optional, nur wenn group=True) -------------
group_map = {
    "Geschirrspüler":                      ["Geschirrspüler"],
    "Backofen und Herd":                   ["Backofen und Herd"],
    "Fernseher und Entertainment-Systeme": ["Fernseher und Entertainment-Systeme"],
    "Bürogeräte":                          ["Bürogeräte"],
    "Waschmaschine":                       ["Waschmaschine"] 
    # Wenn eine Spalte in der CSV "Geschirrspüler" heißt und du die Gruppe "Geschirrspüler" willst,
    # dann ist das Mapping "Geschirrspüler": ["Geschirrspüler"].
}

# 1) Meta-Info: Welche Appliances (oder Gruppen) gibt es?
def list_appliances(
    year: int,
    *,
    group: bool = False
) -> List[str]:
    """
    Wenn group=False (Default): gibt die originalen Appliance-Spaltennamen
    zurück (z. B. 'Computer', 'TV', ...).
    Wenn group=True: gibt die Survey-Gruppennamen aus group_map zurück.
    """
    sample = pd.read_csv(
        BASE_DIR/str(year)/f"{year}-01.csv",
        nrows=1
    )
    raw = [c for c in sample.columns if c != "timestamp"]

    if not group:
        return raw
    else:
        return list(group_map.keys())

# 2) Lade genau einen Monat (alle Appliances oder Gruppen)
def load_month(
    year: int,
    month: int,
    *,
    tz: str = "Europe/Zurich",
    group: bool = False
) -> pd.DataFrame:
    """
    Lädt die CSV für Jahr/Monat, konvertiert Timestamp, und wenn group=True,
    fasst die Original-Spalten gemäß group_map zusammen.
    """
    path = BASE_DIR/str(year)/f"{year}-{month:02d}.csv"
    df = pd.read_csv(path, parse_dates=["timestamp"])
    # Timestamp → naive Lokalzeit
    df["timestamp"] = (
        pd.to_datetime(df["timestamp"], utc=True)
          .dt.tz_convert(tz)
          .dt.tz_localize(None)
    )
    df = df.set_index("timestamp")

    if not group:
        return df

    # --- grouping ---
    df_grouped = pd.DataFrame(index=df.index)
    for grp_name, cols in group_map.items():
        existing = [c for c in cols if c in df.columns]
        # falls überhaupt keine Spalte passt, liefere 0
        df_grouped[grp_name] = df[existing].sum(axis=1) if existing else 0.0

    return df_grouped

# 3) Lade Daten für einen Bereich (quer über Monate)
def load_range(
    start: datetime.datetime,
    end: datetime.datetime,
    *,
    year: Optional[int] = None,
    tz: str = "Europe/Zurich",
    group: bool = False
) -> pd.DataFrame:
    if year is None:
        year = start.year
    months = (
        sorted({start.month, end.month})
        if start.year == end.year
        else range(1, 13)
    )
    parts: List[pd.DataFrame] = []
    for m in months:
        parts.append(load_month(year, m, tz=tz, group=group))
    full = pd.concat(parts).sort_index()
    return full.loc[start:end]

# 4) Lade nur einzelne Appliances oder Gruppen
def load_appliances(
    appliances: List[str],
    start: datetime.datetime,
    end: datetime.datetime,
    *,
    year: Optional[int] = None,
    tz: str = "Europe/Zurich",
    group: bool = False
) -> pd.DataFrame:
    """
    Wenn group=False (Default): appliances bezieht sich auf RAW-Spalten
    (z.B. ['Computer','TV']).
    Wenn group=True: appliances bezieht sich auf group_map.keys()
    (z.B. ['Geschirrspüler','Fernseher und Entertainment-Systeme',...]).
    """
    df = load_range(start, end, year=year, tz=tz, group=group)
    return df[appliances]