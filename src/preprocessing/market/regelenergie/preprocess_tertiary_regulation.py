#!/usr/bin/env python3
"""
preprocess_tertiary_regulation.py

Aggregiert aus den monatlichen Rohdaten der tertiären Regelleistung
nur die tatsächlich abgerufenen Mengen (called_mw > 0) und berechnet
pro 15-Minuten-Intervall die Gesamtmenge sowie den gewichteten Durchschnittspreis.
Speichert die aufbereiteten Monatsdateien unter:
  data/processed/market/regelenergie/YYYY-MM.csv
"""
import pandas as pd
from pathlib import Path

def main():
    year = 2024
    raw_dir = Path("data/raw/market/regelenergie/mfrR") / str(year)
    proc_dir = Path("data/processed/market/regelenergie")
    proc_dir.mkdir(parents=True, exist_ok=True)

    for month_path in sorted(raw_dir.glob(f"{year}-[0-1][0-9]-TRE-Ergebnis.csv")):
        month = month_path.stem.split('-')[1]
        df = pd.read_csv(
            month_path,
            sep=';',
            encoding='latin1',
            usecols=[
                'Ausschreibung', 'Von',
                'Abgerufene Menge', 'Preis'
            ]
        )
        # parse date
        df['date'] = df['Ausschreibung'].str.split('_').apply(lambda parts: f"{year}-{parts[2]}-{parts[3]}")
        df['timestamp'] = pd.to_datetime(
            df['date'] + ' ' + df['Von'],
            format="%Y-%m-%d %H:%M"
        )
        # rename
        df = df.rename(columns={
            'Abgerufene Menge': 'called_mw',
            'Preis':            'price_eur_mwh'
        })
        # filter only called
        df = df[df['called_mw'] > 0]

        if df.empty:
            print(f"{year}-{month}: keine Aktivierungen gefunden, leere Datei")
            out = pd.DataFrame(columns=["timestamp", "total_called_mw", "avg_price_eur_mwh"])
        else:
            # Kosten-Spalte
            df['cost'] = df['called_mw'] * df['price_eur_mwh']
            # Aggregation pro Timestamp
            agg = df.groupby('timestamp').agg(
                total_called_mw=('called_mw', 'sum'),
                total_cost=('cost', 'sum')
            )
            # Gewichteter Durchschnittspreis
            agg['avg_price_eur_mwh'] = agg['total_cost'] / agg['total_called_mw']
            # finale Spalten und Reset Index
            out = agg[['total_called_mw', 'avg_price_eur_mwh']].reset_index()

        # Schreibe Datei
        out_path = proc_dir / f"{year}-{month}.csv"
        out.to_csv(out_path, index=False)
        print(f"Processed {year}-{month} → {out_path}")

if __name__ == "__main__":
    main()