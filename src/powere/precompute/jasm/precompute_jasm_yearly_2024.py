#!/usr/bin/env python3
# /Users/jonathan/Documents/GitHub/PowerE/src/powere/precompute/jasm/precompute_jasm_yearly_2024.py

from pathlib import Path

import pandas as pd

TARGET_YEAR = 2024
# drei Ebenen hoch, um auf project root zu kommen
PROJECT_ROOT = Path(__file__).resolve().parents[3]

IN_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "static"
    / "jasm"
    / str(TARGET_YEAR)
    / "monthly"
)
OUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "static"
    / "jasm"
    / str(TARGET_YEAR)
    / "yearly"
)
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 1) Alle 12 Monats-Profile einlesen und Index in UTC‐DatetimeIndex umwandeln
dfs = []
for m in range(1, 13):
    csv_file = IN_DIR / f"appliance_monthly_{TARGET_YEAR}_{m:02d}.csv"
    df = pd.read_csv(csv_file, index_col=0)
    # Mit utc=True in echten datetime64[ns, UTC] konvertieren
    df.index = pd.to_datetime(df.index, utc=True)
    dfs.append(df)

# 2) Zusammenführen
full = pd.concat(dfs)

# 3) (Optional) auf lokale Zeitzone zurückkonvertieren und tz‐info entfernen,
#    falls Du lieber naive Timestamps haben möchtest:
# full.index = full.index.tz_convert("Europe/Zurich").tz_localize(None)

# 4) Gruppieren nach Monat und Mittel berechnen
#    full.index ist jetzt ein DatetimeIndex → .month existiert
yearly = full.groupby(full.index.month).mean()
yearly.index.name = "month"

# 5) Speichern
out_file = OUT_DIR / f"appliance_yearly_avg_{TARGET_YEAR}.csv"
yearly.to_csv(out_file)

print(
    f"✅ Jahres-Durchschnitt für {TARGET_YEAR} gespeichert in {out_file}  "
    f"({yearly.shape[0]} Monate × {yearly.shape[1]} Spalten)"
)
