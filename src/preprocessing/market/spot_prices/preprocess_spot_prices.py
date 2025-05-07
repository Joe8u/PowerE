#!/usr/bin/env python3
"""
preprocess_spot_prices.py

Konvertiert die rohen Spot-Preis-Dateien (mit Zeitzone-Angabe)
zum lokalen, naiven 15-Min-Timestamp und speichert sie unter:
  data/processed/market/spot_prices/YYYY-MM.csv
"""
import pandas as pd
from pathlib import Path

def main():
    year = 2024
    raw_dir = Path("data/raw/market/spot_prices") / str(year)
    proc_dir = Path("data/processed/market/spot_prices")
    proc_dir.mkdir(parents=True, exist_ok=True)

    # Alle Monatsdateien verarbeiten
    for file in sorted(raw_dir.glob(f"{year}-[0-1][0-9].csv")):
        month = file.stem.split('-')[1]
        # Einlesen ohne automatisches Parsen der Timestamps
        df = pd.read_csv(file, parse_dates=False)

        # Parse timestamp inklusive Zeitzone: alle werden auf UTC normalisiert
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        # Nun in Europe/Zurich konvertieren und Zeitzone entfernen
        df['timestamp'] = (
            df['timestamp']
              .dt.tz_convert('Europe/Zurich')
              .dt.tz_localize(None)
        )

        # Umbenennen für Klarheit
        df = df.rename(columns={'price': 'price_eur_mwh'})

        # Ausgabe-Pfad
        out_path = proc_dir / f"{year}-{month}.csv"
        # Speichern
        df.to_csv(out_path, index=False)
        print(f"Processed spot prices: {out_path}")

if __name__ == '__main__':
    main()