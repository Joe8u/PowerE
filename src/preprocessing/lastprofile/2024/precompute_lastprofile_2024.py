#!/usr/bin/env python3
# src/preprocessing/lastprofile/2024/precompute_lastprofile_2024.py

import pandas as pd
from pathlib import Path

# --- 0) Config ---------------------------------------------------------------
RAW_CSV = Path("data/raw/lastprofile/Swiss_load_curves_2015_2035_2050.csv")
BASE    = Path("data/processed/lastprofile")
OUT_DIR = BASE / "2024"
OUT_DIR.mkdir(exist_ok=True)

# Linearer Mischfaktor zwischen 2015 und 2035 für das Jahr 2024
f = (2024 - 2015) / (2035 - 2015)  # = 0.45

# --- 1) Raw einlesen ---------------------------------------------------------
df_raw = pd.read_csv(
    RAW_CSV,
    sep=";",
    dtype={
        "Year":       int,
        "Month":      int,
        "Day type":   str,
        "Time":       str,
        "Appliances": str,
        "Power (MW)": float
    },
    parse_dates=False
)

# Spalten vereinheitlichen
df_raw.columns = (
    df_raw.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)

# --- 2) Pivot-Jahre aufbauen ------------------------------------------------
def pivot_year(df: pd.DataFrame, year: int) -> pd.DataFrame:
    df_y = df[df["year"] == year]
    df_y = (
        df_y
        .groupby(
            ["month", "day_type", "time", "appliances"],
            as_index=False
        )["power_(mw)"]
        .mean()
    )
    # in kW umbenennen
    df_y["power_kw"] = df_y["power_(mw)"]
    # pivot: index=(month, day_type, time), columns=appliances
    return (
        df_y
        .pivot(
            index=["month", "day_type", "time"],
            columns="appliances",
            values="power_kw"
        )
        .sort_index()
    )

pivot15 = pivot_year(df_raw, 2015)
pivot35 = pivot_year(df_raw, 2035)

# --- 3) Saisonale Interpolation für 2024 ------------------------------------
pivot24 = (1 - f) * pivot15 + f * pivot35

# --- 4) Kalender mit 15-Min-Raster erzeugen ---------------------------------
rng = pd.date_range(
    "2024-01-01",
    "2024-12-31 23:45:00",
    freq="15T",
    tz="Europe/Zurich"
)
df_cal = pd.DataFrame({"timestamp": rng})

# **Zeitzone entfernen**, damit im CSV nur naive Zeitstamps stehen:
df_cal["timestamp"] = df_cal["timestamp"].dt.tz_localize(None)

# Hilfsspalten für Merge
df_cal["month"]    = df_cal["timestamp"].dt.month
df_cal["day_type"] = df_cal["timestamp"].dt.weekday.map(
    lambda d: "weekday" if d < 5 else "weekend"
)
df_cal["time"]     = df_cal["timestamp"].dt.strftime("%H:00:00")

# --- 5) Merge mit interpoliertem Profil ------------------------------------
df_merged = (
    df_cal
    .merge(
        pivot24.reset_index(),
        on=["month", "day_type", "time"],
        how="left"
    )
    .drop(columns=["month", "day_type", "time"])
)

# --- 6) Split in Monats-CSVs im Original-Format ----------------------------
for m in range(1, 13):
    df_m = df_merged[df_merged["timestamp"].dt.month == m]
    # Spalten-Reihenfolge von 2015 übernehmen
    cols2015 = (
        pd.read_csv(BASE/"2015"/f"2015-{m:02d}.csv", nrows=1)
          .columns
          .tolist()
    )
    df_out  = df_m[cols2015]
    outpath = OUT_DIR / f"2024-{m:02d}.csv"
    df_out.to_csv(outpath, index=False)
    print(f"Wrote {outpath}")