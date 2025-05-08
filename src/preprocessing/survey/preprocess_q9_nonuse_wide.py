#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preprocess_q9_nonuse_wide.py

Liest die Rohdaten zu Frage 9 ein,
extrahiert die sechs Appliance-Antworten und
schreibt sie im Wide-Format (respondent_id + je eine Spalte pro Gerät).
"""

import os
import sys
import pandas as pd

# ======================
# Pfad-Konstanten
# ======================
BASE_DIR      = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, os.pardir, os.pardir))
RAW_DIR       = os.path.join(BASE_DIR, 'data', 'raw',  'survey')
OUT_DIR       = os.path.join(BASE_DIR, 'data', 'processed', 'survey')
RAW_FILENAME  = 'Energieverbrauch und Teilnahmebereitschaft an Demand-Response-Programmen in Haushalten.csv'
OUT_FILENAME  = 'question_9_nonuse_wide.csv'

RAW_PATH = os.path.join(RAW_DIR, RAW_FILENAME)
OUT_PATH = os.path.join(OUT_DIR, OUT_FILENAME)

def preprocess_q9_nonuse_wide(raw_csv: str, out_csv: str):
    # 1) Einlesen mit flachem Header (Zeile 0)
    df = pd.read_csv(raw_csv, header=0, dtype=str)

    # 2) Exakter Fragetext
    question = (
        "Könnten Sie sich vorstellen, eines der folgenden Haushaltsgeräte "
        "für einen begrenzten Zeitraum nicht einzuschalten, wenn Sie vom "
        "Elektrizitätswerk darum gebeten werden?"
    )
    if question not in df.columns:
        print(f"Frage nicht gefunden im Header: {question}", file=sys.stderr)
        sys.exit(1)

    # 3) Spaltenindex der Frage
    q_idx = df.columns.get_loc(question)

    # 4) Geräte-Namen aus Zeile 2 extrahieren (jetzt ab q_idx statt q_idx+1)
    second_row = pd.read_csv(
        raw_csv,
        header=None,
        skiprows=1,
        nrows=1,
        dtype=str
    ).iloc[0].tolist()
    appliances = second_row[q_idx : q_idx + 6]
    if len(appliances) != 6:
        print(f"Erwartet 6 Geräte, gefunden {len(appliances)}: {appliances}", file=sys.stderr)
        sys.exit(1)

    # 5) Spalten respondent_id + die 6 Antwort-Spalten auswählen (ebenfalls ab q_idx)
    cols = ['respondent_id'] + df.columns[q_idx : q_idx + 6].tolist()
    data = df[cols].copy()

    # 6) Spalten umbenennen: respondent_id + echte Geräte-Namen
    data.columns = ['respondent_id'] + appliances

    # 7) Wide-CSV schreiben
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    data.to_csv(out_csv, index=False, encoding='utf-8')
    print(f"Wide-Format Q9 gespeichert nach: {out_csv}")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        preprocess_q9_nonuse_wide(RAW_PATH, OUT_PATH)
    elif len(sys.argv) == 3:
        _, raw, out = sys.argv
        preprocess_q9_nonuse_wide(raw, out)
    else:
        print(
            "Usage:\n"
            "  python preprocess_q9_nonuse_wide.py\n"
            "  python preprocess_q9_nonuse_wide.py <input.csv> <output.csv>",
            file=sys.stderr
        )
        sys.exit(1)