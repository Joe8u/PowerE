#!/usr/bin/env python3
"""
precompute_jasm_yearly_2024.py

Berechnet aus den 15-Min-Monatsprofilen für TARGET_YEAR=2024
den Durchschnitt je Appliance und Monat und speichert das Ergebnis
als CSV in data/processed/static/jasm/2024/yearly/.
"""

import pandas as pd
from pathlib import Path

# === Konfiguration ===
TARGET_YEAR = 2024

# Projektwurzel (dreimal parents ab src/precompute/jasm)
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Eingabe- und Ausgabe-Verzeichnisse
IN_DIR  = PROJECT_ROOT / "data" / "processed" / "static" / "jasm" / str(TARGET_YEAR) / "monthly"
OUT_DIR = PROJECT_ROOT / "data" / "processed" / "static" / "jasm" / str(TARGET_YEAR) / "yearly"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    # für jeden Monat den Mittelwert je Spalte berechnen
    records = []
    for month in range(1, 13):
        csv_file = IN_DIR / f"appliance_monthly_{TARGET_YEAR}_{month:02d}.csv"
        df = pd.read_csv(csv_file, index_col=0, parse_dates=True)

        # Mittelwert über alle Zeitpunkte
        avg = df.mean()
        avg.name = month
        records.append(avg)

    # DataFrame mit Monatsindex aufbauen
    yearly_avg = pd.DataFrame(records)
    yearly_avg.index.name = "month"

    # Speichern
    out_file = OUT_DIR / f"appliance_yearly_avg_{TARGET_YEAR}.csv"
    yearly_avg.to_csv(out_file)
    print(f"✅ Gespeichert: {out_file}  ({yearly_avg.shape[0]} Monate × {yearly_avg.shape[1]} Appliances)")


if __name__ == "__main__":
    main()