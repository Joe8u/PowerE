#!/usr/bin/env python3
# src/powere/loaders/jasm/daily.py

import pandas as pd
from pathlib import Path
from powere.utils.settings import DATA_RAW_DIR

def load_jasm_day(year: int, month: int, day_type: str = "weekday") -> pd.DataFrame:
    """
    Lädt ein 15-Minuten-Raster für einen einzigen Kalendertag:
      – year, month, day_type in {"weekday","weekend"}.
      – Index: 96 Zeitpunkte über 24h, freq="15T".
      – Spalten: Appliances.
      – Werte: Leistung in kW (MW×1000), linear interpoliert.
    """
    # 1) Roh‐CSV einlesen und filtern
    csv_path = Path(DATA_RAW_DIR) / "jasm" / "Swiss_load_curves_2015_2035_2050.csv"
    df = pd.read_csv(
        csv_path, sep=";",
        usecols=["Year","Month","Day type","Time","Appliances","Power (MW)"]
    )
    df = df[
        (df["Year"] == year) &
        (df["Month"] == month) &
        (df["Day type"] == day_type)
    ].copy()

    # 2) Pivot + MW→kW
    base = pd.Timestamp(2000, 1, 1)  # Platzhalterdatum
    pivot = (
        df.assign(timestamp=base + pd.to_timedelta(df["Time"]))
          .pivot(index="timestamp", columns="Appliances", values="Power (MW)")
          .mul(1_000)
    )

    # 3) Vollständiges 15-Min-Raster aufbauen
    full_idx = pd.date_range(start=base, periods=96, freq="15T")
    day_df = pivot.reindex(full_idx).interpolate(method="linear")

    # 4) freq‐Attribut setzen
    day_df.index.freq = pd.tseries.frequencies.to_offset("15T")
    return day_df