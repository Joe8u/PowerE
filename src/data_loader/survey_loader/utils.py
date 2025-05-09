#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils.py

Gemeinsame Helferfunktionen für das Survey-Preprocessing und -Loading.
"""

import re
import pandas as pd


def parse_rating(x: str) -> pd.Int64Dtype:
    """
    Wandelt Strings wie '5 = sehr wichtig', '1 = sehr unwichtig' oder reine Ziffern
    in einen integer (1-5) um. Fehlende oder ungültige Werte → <NA>.
    """
    if pd.isna(x):
        return pd.NA
    m = re.match(r"^\s*([1-5])", str(x))
    if m:
        return int(m.group(1))
    return pd.NA


def parse_percentage(x: str) -> pd.Float64Dtype:
    """
    Extrahiert die erste Zahl aus einem String wie '15%' oder '20' und liefert sie als float.
    Fehlende oder ungültige Werte → <NA>.
    """
    if pd.isna(x):
        return pd.NA
    m = re.search(r"(\d{1,3})(?:[.,]\d+)?", str(x))
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return pd.NA
    return pd.NA


def parse_duration(x: str) -> pd.Float64Dtype:
    """
    Parst deutsche Dauer-Antworten wie:
      - 'Ja, für maximal 24 Stunden'
      - 'Ja, für 3 bis 6 Stunden'
      - 'Ja, für mehr als 24 Stunden'
    und gibt einen numerischen Wert in Stunden zurück.
    Bei Bereichsangabe: Median des Intervalls. Bei 'mehr als': untere Grenze.
    Fehlende oder unbekannte Formate → <NA>.
    """
    if pd.isna(x):
        return pd.NA
    s = str(x).lower()
    # Explicit 'mehr als' case
    m = re.search(r"mehr als\s*(\d+)", s)
    if m:
        return float(m.group(1))
    # Range case
    m = re.search(r"(\d+)\s*b[a-z]*\s*(\d+)", s)
    if m:
        lo, hi = map(float, m.groups())
        return (lo + hi) / 2
    # Single value case
    m = re.search(r"(\d+)", s)
    if m:
        return float(m.group(1))
    return pd.NA


def merge_on_respondent(dfs: list[pd.DataFrame], how: str = 'outer') -> pd.DataFrame:
    """
    Merge eine Liste von DataFrames auf der Spalte 'respondent_id'.
    Standardmäßig outer-join, um alle IDs zu behalten.

    Parameters
    ----------
    dfs : list of pandas.DataFrame
    how : str
        Join-Typ, z.B. 'outer', 'inner', 'left', 'right'.

    Returns
    -------
    pandas.DataFrame
        Gemergte Tabelle.
    """
    if not dfs:
        return pd.DataFrame()
    df_merged = dfs[0]
    for df in dfs[1:]:
        df_merged = df_merged.merge(df, on='respondent_id', how=how)
    return df_merged
