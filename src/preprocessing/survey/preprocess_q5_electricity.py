#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preprocess_q5_electricity.py

Liest die Rohdaten zu Frage 5 ("Welche Art von Strom beziehen Sie hauptsächlich?")
ein, extrahiert die gültigen Antworten und schreibt sie in eine neue CSV.
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
OUTPUT_FILENAME = 'question_5_electricity.csv'

# Vollständige Pfade errechnen
RAW_CSV_PATH    = os.path.join(RAW_DIR, RAW_FILENAME)
OUT_CSV_PATH    = os.path.join(PROCESSED_DIR, OUTPUT_FILENAME)

# ======================
# Hauptfunktion
# ======================
def main(raw_csv_path: str, out_csv_path: str):
    # 1) Rohdaten einlesen (alle Spalten als String)
    try:
        df = pd.read_csv(raw_csv_path, dtype=str)
    except FileNotFoundError:
        print(f"Datei nicht gefunden: {raw_csv_path}", file=sys.stderr)
        sys.exit(1)

    # 2) Set mit den erlaubten Antworten
    valid_answers = {
        'Ökostrom (aus erneuerbaren Energien wie Wasser, Sonne, Wind)',
        'Konventionellen Strom (Kernenergie und fossilen Brennstoffen)',
        'Eine Mischung aus konventionellem Strom und Ökostrom',
        'Weiss nicht',
    }

    # 3) Extraktion der Spalte
    col_raw = 'Welche Art von Strom beziehen Sie hauptsächlich?'
    if col_raw not in df.columns:
        print(f"Spalte nicht gefunden: {col_raw}", file=sys.stderr)
        sys.exit(1)

    # 4) Filterung und Mapping
    df['electricity_type'] = df[col_raw].where(df[col_raw].isin(valid_answers), pd.NA)

    # 5) Prüfen, ob alle Antworten gesetzt wurden
    missing = df['electricity_type'].isna().sum()
    if missing:
        print(f"Warnung: {missing} Zeilen ohne gültige Stromarten-Antwort.", file=sys.stderr)

    # 6) Nur respondent_id und electricity_type speichern
    if 'respondent_id' not in df.columns:
        print("Spalte 'respondent_id' nicht gefunden", file=sys.stderr)
        sys.exit(1)
    df_out = df[['respondent_id', 'electricity_type']]

    # Zielverzeichnis anlegen, falls es nicht existiert
    os.makedirs(os.path.dirname(out_csv_path), exist_ok=True)

    df_out.to_csv(out_csv_path, index=False)
    print(f"Verarbeitet und gespeichert nach: {out_csv_path}")

# ======================
# Skript-Entry-Point
# ======================
if __name__ == "__main__":
    # Aufruf ohne Argumente nutzt die Konstanten
    if len(sys.argv) == 1:
        main(RAW_CSV_PATH, OUT_CSV_PATH)
    elif len(sys.argv) == 3:
        _, raw_csv, out_csv = sys.argv
        main(raw_csv, out_csv)
    else:
        print(
            "Usage:\n"
            "  python preprocess_q5_electricity.py\n"
            "  python preprocess_q5_electricity.py <input_raw.csv> <output.csv>",
            file=sys.stderr
        )
        sys.exit(1)
