#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preprocess_q4_accommodation.py

Liest die Rohdaten zu Frage 4 ("In welcher Art von Unterkunft wohnen Sie?")
ein, extrahiert aus allen Spalten eine der vier gültigen Antworten und
schreibt das Ergebnis in eine neue CSV.
"""

import os
import sys
import pandas as pd

# ======================
# Pfad-Konstanten
# ======================
BASE_DIR = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, os.pardir, os.pardir))
RAW_DIR         = os.path.join(BASE_DIR, 'data', 'raw', 'survey')
PROCESSED_DIR   = os.path.join(BASE_DIR, 'data', 'processed', 'survey')
RAW_FILENAME    = 'Energieverbrauch und Teilnahmebereitschaft an Demand-Response-Programmen in Haushalten.csv'
OUTPUT_FILENAME = 'question_4_accommodation.csv'

# Vollständige Pfade errechnen
RAW_CSV_PATH    = os.path.join(RAW_DIR, RAW_FILENAME)
OUT_CSV_PATH    = os.path.join(PROCESSED_DIR, OUTPUT_FILENAME)

# ======================
# Hauptfunktion
# ======================
def main(raw_csv_path: str, out_csv_path: str):
    # 1) Rohdaten einlesen (alle Spalten als String)
    try:
        df = pd.read_csv(raw_csv_path, header=0, skiprows=[1], dtype=str)
    except FileNotFoundError:
        print(f"Datei nicht gefunden: {raw_csv_path}", file=sys.stderr)
        sys.exit(1)

    # 2) Set mit den erlaubten Antworten
    valid_answers = {
        "Wohnung (Eigentum)",
        "Wohnung (Miete)",
        "Haus (Miete)",
        "Haus (Eigentum)",
    }

    # 3) Funktion, die pro Zeile den ersten gültigen Wert liefert
    def find_accommodation(row):
        for cell in row:
            if pd.notna(cell) and cell in valid_answers:
                return cell
        return pd.NA

    # 4) Auf alle Spalten anwenden und neue Spalte füllen
    df["accommodation_type"] = df.apply(find_accommodation, axis=1)

    # 5) Prüfen, ob alle Antworten gesetzt wurden
    missing = df["accommodation_type"].isna().sum()
    if missing:
        print(f"Warnung: {missing} Zeilen ohne gültige Unterkunfts-Antwort.", file=sys.stderr)

    # 6) Nur respondent_id und accommodation_type speichern
    df_out = df.loc[:, ["respondent_id", "accommodation_type"]]

    # Zielverzeichnis anlegen, falls es nicht existiert
    os.makedirs(os.path.dirname(out_csv_path), exist_ok=True)

    df_out.to_csv(out_csv_path, index=False)
    print(f"Verarbeitet und gespeichert nach: {out_csv_path}")

# ======================
# Skript-Entry-Point
# ======================
if __name__ == "__main__":
    # Wenn du die Konstanten nutzen willst, kannst du das Skript ohne Argumente aufrufen:
    if len(sys.argv) == 1:
        main(RAW_CSV_PATH, OUT_CSV_PATH)
    # Oder mit zwei Pfad-Argumenten:
    elif len(sys.argv) == 3:
        _, raw_csv, out_csv = sys.argv
        main(raw_csv, out_csv)
    else:
        print("Usage:\n"
              "  # Mit vordefinierten Pfaden:\n"
              "  python preprocess_q4_accommodation.py\n\n"
              "  # Oder mit individuellen Pfaden:\n"
              "  python preprocess_q4_accommodation.py <input_raw.csv> <output.csv>",
              file=sys.stderr)
        sys.exit(1)