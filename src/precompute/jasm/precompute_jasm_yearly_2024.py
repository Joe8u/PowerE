#!/usr/bin/env python3
# src/precompute/jasm/precompute_jasm_yearly_2024.py

import pandas as pd
from pathlib import Path

TARGET_YEAR = 2024
ROOT        = Path(__file__).resolve().parents[3]
IN_DIR      = ROOT / "data" / "processed" / "static" / "jasm" / str(TARGET_YEAR) / "monthly"
OUT_DIR     = ROOT / "data" / "processed" / "static" / "jasm" / str(TARGET_YEAR) / "yearly"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Lade alle 12 Monats-Profile
dfs = []
for m in range(1,13):
    p = IN_DIR / f"appliance_monthly_{TARGET_YEAR}_{m:02d}.csv"
    dfs.append(pd.read_csv(p, index_col=0, parse_dates=True))

full = pd.concat(dfs)
# Monatsextrakt (1–12)
full["month"] = full.index.month
# Mittel je Monat
yearly = full.groupby("month").mean().drop(columns=["month"])

out_file = OUT_DIR / f"appliance_yearly_avg_{TARGET_YEAR}.csv"
yearly.to_csv(out_file)
print(f"✅ Jahres-Durchschnitt für {TARGET_YEAR} in {out_file}")