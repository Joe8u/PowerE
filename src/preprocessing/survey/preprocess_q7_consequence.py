#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preprocess_q7_consequence.py

Liest die Rohdaten zu Frage 7 ein, findet automatisch die
Spalte mit den Antwortoptionen zu problematischen Konsequenzen
der erneuerbaren Einspeisung und schreibt respondent_id plus
Auswahl in eine neue CSV.
"""

import os
import sys
import pandas as pd

# ======================
# Pfad-Konstanten
# ======================
BASE_DIR        = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, os.pardir, os.pardir))
RAW_DIR         = os.path.join(BASE_DIR, 'data', 'raw', 'survey')
PROCESSED_DIR   = os.path.join(BASE_DIR, 'data', 'processed', 'survey')
RAW_FILENAME    = 'Energieverbrauch und Teilnahmebereitschaft an Demand-Response-Programmen in Haushalten.csv'
OUTPUT_FILENAME = 'question_7_consequence.csv'

RAW_CSV_PATH    = os.path.join(RAW_DIR, RAW_FILENAME)
OUT_CSV_PATH    = os.path.join(PROCESSED_DIR, OUTPUT_FILENAME)

# ======================
# Hauptfunktion
# ======================
def main(raw_csv_path: str, out_csv_path: str):
    # 1) Einlesen
    try:
        df = pd.read_csv(raw_csv_path, header=0, skiprows=[1], dtype=str)
    except FileNotFoundError:
        print(f"Datei nicht gefunden: {raw_csv_path}", file=sys.stderr)
        sys.exit(1)

    # 2) Spalte finden, die "Konsequenzen" enthält
    question_cols = [c for c in df.columns if 'Konsequenzen' in c]
    if not question_cols:
        print("Spalte mit 'Konsequenzen' im Namen nicht gefunden.", file=sys.stderr)
        print("Verfügbare Spalten:", ', '.join(df.columns), file=sys.stderr)
        sys.exit(1)
    question_col = question_cols[0]

    # 3) Antworten direkt übernehmen (NA bleiben NA)
    df['consequence'] = df[question_col].astype(str).str.strip().replace({'nan': pd.NA})

    # 4) Fehlende zählen
    missing = df['consequence'].isna().sum()
    if missing:
        print(f"Warnung: {missing} fehlende Antworten zu Frage 7.", file=sys.stderr)

    # 5) respondent_id prüfen
    if 'respondent_id' not in df.columns:
        print("Spalte 'respondent_id' nicht gefunden.", file=sys.stderr)
        sys.exit(1)

    # 6) Export
    df_out = df[['respondent_id', 'consequence']]
    os.makedirs(os.path.dirname(out_csv_path), exist_ok=True)
    df_out.to_csv(out_csv_path, index=False)
    print(f"Verarbeitet und gespeichert nach: {out_csv_path}")

# ======================
# Entry Point
# ======================
if __name__ == "__main__":
    if len(sys.argv) == 1:
        main(RAW_CSV_PATH, OUT_CSV_PATH)
    elif len(sys.argv) == 3:
        _, raw_csv, out_csv = sys.argv
        main(raw_csv, out_csv)
    else:
        print(
            "Usage:\n"
            "  python preprocess_q7_consequence.py\n"
            "  python preprocess_q7_consequence.py <input_raw.csv> <output.csv>",
            file=sys.stderr
        )
        sys.exit(1)