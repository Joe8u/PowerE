#!/usr/bin/env python3
"""
Script: extract_called_energies.py

Durchsucht alle 12 Monatsdateien der tertiären Regelleistung und erzeugt
im gleichen Verzeichnis eine CSV mit allen Zeitstempeln, Produkten und
abgerufenen Energiemengen (>0 MW).
"""
import pandas as pd
from pathlib import Path

def main():
    year = 2024
    raw_dir = Path("data/raw/market/regelenergie/mfrR") / str(year)
    output_path = raw_dir / f"{year}-called_energies.csv"

    # Sammelliste für alle abgerufenen Datensätze
    records = []

    for month in raw_dir.glob(f"{year}-[0-1][0-9]-TRE-Ergebnis.csv"):
        df = pd.read_csv(
            month,
            sep=';', encoding='latin1',
            usecols=[
                'Ausschreibung', 'Von', 'Produkt',
                'Abgerufene Menge', 'Preis', 'Status'
            ]
        )
        # Parse Datum (Ausschreibung, e.g. 'TRE_24_01_15') und Uhrzeit (Von)
        def parse_date(a):
            parts = a.split('_')  # ['TRE','YY','MM','DD']
            yy, mm, dd = parts[1], parts[2], parts[3]
            yyyy = str(year)
            return f"{yyyy}-{mm}-{dd}"

        df['date'] = df['Ausschreibung'].apply(parse_date)
        df['timestamp'] = pd.to_datetime(
            df['date'] + ' ' + df['Von'],
            format="%Y-%m-%d %H:%M"
        )
        # Filter abgerufene Menge > 0
        df = df[df['Abgerufene Menge'] > 0]
        if df.empty:
            continue
        # Wähle relevante Spalten
        out = df[['timestamp', 'Produkt', 'Abgerufene Menge', 'Preis', 'Status']].copy()
        out.columns = ['timestamp', 'product', 'called_mw', 'price_eur_mwh', 'status']
        records.append(out)

    if not records:
        print("Keine Abfragen gefunden: Abgerufene Menge ist in allen Dateien 0.")
        return

    # Alles zusammenführen und speichern
    result = pd.concat(records).sort_values('timestamp')
    result.to_csv(output_path, index=False)
    print(f"Gefundene Abfragen gespeichert in: {output_path}")

if __name__ == '__main__':
    main()
