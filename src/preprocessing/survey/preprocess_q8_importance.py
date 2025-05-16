#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preprocess_q8_importance_wide.py

Liest die Rohdaten zu Frage 8 ein, extrahiert die sechs Appliance-Ratings
(die jetzt eine Spalte früher beginnen) und schreibt sie im Wide-Format
(respondent_id + je eine Spalte pro Gerät).
"""

import os
import sys
import re
import pandas as pd

# Pfad-Konstanten anpassen
BASE_DIR      = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, os.pardir, os.pardir))
RAW_DIR       = os.path.join(BASE_DIR, 'data', 'raw', 'survey')
OUT_DIR       = os.path.join(BASE_DIR, 'data', 'processed', 'survey')
RAW_FILENAME  = 'Energieverbrauch und Teilnahmebereitschaft an Demand-Response-Programmen in Haushalten.csv'
OUT_FILENAME  = 'question_8_importance_wide.csv'

RAW_PATH = os.path.join(RAW_DIR, RAW_FILENAME)
OUT_PATH = os.path.join(OUT_DIR, OUT_FILENAME)


def parse_rating(x: str) -> int:
    """
    Wandelt Strings wie '5 = sehr wichtig' oder '1 = sehr unwichtig'
    bzw. rein numerische Strings in einen int um. Fehlende Werte → NaN.
    """
    if pd.isna(x):
        return pd.NA
    m = re.match(r'^\s*([1-5])', x)
    if m:
        return int(m.group(1))
    return pd.NA


def preprocess_q8_importance_wide(raw_csv: str, out_csv: str):
    # 1) Einlesen mit flachem Header
    df = pd.read_csv(raw_csv, header=0, skiprows=[1], dtype=str)

    # 2) Fragetext identifizieren
    question = (
        "Bitte bewerten Sie, wie wichtig es für Sie ist, die folgenden "
        "Haushaltsgeräte jederzeit nutzen zu können (1 = sehr unwichtig, 5 = sehr wichtig)"
    )
    if question not in df.columns:
        print(f"Frage nicht gefunden im Header: {question}", file=sys.stderr)
        sys.exit(1)

    # 3) Spaltenindex der Frage bestimmen
    q_idx = df.columns.get_loc(question)

    # 4) Gerätenamen aus Zeile 2 extrahieren — **ohne +1**, weil jetzt eine Spalte nach links verschoben
    second_row = pd.read_csv(
        raw_csv, header=None, skiprows=1, nrows=1, dtype=str
    ).iloc[0].tolist()
    appliances = second_row[q_idx : q_idx + 6]
    if len(appliances) != 6:
        print(f"Erwartet 6 Geräte, gefunden {len(appliances)}: {appliances}", file=sys.stderr)
        sys.exit(1)

    # 5) Daten­Spalten extrahieren und in numerische Ratings parsen
    #    respondent_id plus genau diese 6 Spalten (ebenfalls ohne +1)
    cols = [df.columns.get_loc('respondent_id')] + list(range(q_idx, q_idx + 6))
    data = df.iloc[:, cols].copy()
    data.columns = ['respondent_id'] + appliances

    for col in appliances:
        data[col] = data[col].apply(parse_rating)

    # 6) Ausgeben im Wide-Format
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    data.to_csv(out_csv, index=False, encoding='utf-8')
    print(f"Wide-Format Q8 gespeichert nach: {out_csv}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        preprocess_q8_importance_wide(RAW_PATH, OUT_PATH)
    elif len(sys.argv) == 3:
        _, raw, out = sys.argv
        preprocess_q8_importance_wide(raw, out)
    else:
        print(
            "Usage:\n"
            "  python preprocess_q8_importance_wide.py\n"
            "  python preprocess_q8_importance_wide.py <input.csv> <output.csv>",
            file=sys.stderr
        )
        sys.exit(1)