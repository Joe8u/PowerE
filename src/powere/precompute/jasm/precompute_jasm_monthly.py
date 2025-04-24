#!/usr/bin/env python3
# /Users/jonathan/Documents/GitHub/PowerE/src/powere/precompute/jasm/precompute_jasm_monthly.py

import calendar
from pathlib import Path

import pandas as pd

from src.powere.loaders.jasm.jasm_loader import build_month_profile

# Diese Skripte sollen in <project_root>/src/precompute/jasm/ liegen.
# Wir heben daher dreimal .parents nach oben, um auf project_root zu kommen:
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Jahresliste
YEARS = [2015, 2035, 2050]


def precompute_for_year(year: int, appliances=None):
    """
    Generiert alle Monatsprofile für ein Jahr und
    speichert sie in data/processed/static/jasm/{year}/monthly/
    """
    out_dir = (
        PROJECT_ROOT / "data" / "processed" / "static" / "jasm" / str(year) / "monthly"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    for month in range(1, 13):
        # build_month_profile liefert 15-Min-Raster für den ganzen Monat
        df = build_month_profile(year, month, appliances=appliances)
        fn = out_dir / f"appliance_monthly_{year}_{month:02d}.csv"
        df.to_csv(fn)
        print(f"→ gespeichert: {fn}  ({len(df)} Zeilen)")


if __name__ == "__main__":
    APPS = None  # None = alle Geräte; oder Liste z.B. ["Dishwasher","Oven",...]
    for y in YEARS:
        print(f"\n--- Erzeuge monthly für {y} ---")
        precompute_for_year(y, appliances=APPS)
