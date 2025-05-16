#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preprocess_q14_education.py

Liest die Rohdaten ein, extrahiert Frage 14:
"Was ist Ihr höchster Bildungsabschluss?"
und schreibt respondent_id + Bildungsabschluss-Kategorie in eine neue CSV.
"""

import os
import sys
import pandas as pd

# ======================
# Pfad-Konstanten
# ======================
BASE_DIR      = os.path.abspath(
    os.path.join(__file__, os.pardir, os.pardir, os.pardir, os.pardir)
)
RAW_DIR       = os.path.join(BASE_DIR, 'data', 'raw', 'survey')
OUT_DIR       = os.path.join(BASE_DIR, 'data', 'processed', 'survey')
RAW_FILENAME  = 'Energieverbrauch und Teilnahmebereitschaft an Demand-Response-Programmen in Haushalten.csv'
OUT_FILENAME  = 'question_14_education.csv'

RAW_PATH = os.path.join(RAW_DIR, RAW_FILENAME)
OUT_PATH = os.path.join(OUT_DIR, OUT_FILENAME)


def preprocess_q14_education(raw_csv: str, out_csv: str):
    # 1) Rohdaten einlesen
    try:
        df = pd.read_csv(raw_csv, header=0, skiprows=[1], dtype=str)
    except FileNotFoundError:
        print(f"Datei nicht gefunden: {raw_csv}", file=sys.stderr)
        sys.exit(1)

    # 2) respondent_id prüfen
    if 'respondent_id' not in df.columns:
        print("Spalte 'respondent_id' nicht gefunden.", file=sys.stderr)
        sys.exit(1)

    # 3) Spalte für Q14 dynamisch ermitteln
    #    Suche im Header nach "Bildungsabschluss"
    pattern = r"Bildungsabschluss"
    matches = [c for c in df.columns if isinstance(c, str) and pattern in c]
    if len(matches) != 1:
        print(f"Erwartet genau eine Spalte zu Q14, gefunden: {matches!r}", file=sys.stderr)
        sys.exit(1)
    q14_col = matches[0]
    print(f"→ Verarbeite Spalte für Q14: {q14_col!r}")

    # 4) respondent_id + Roh-Antwort extrahieren
    out = df[['respondent_id', q14_col]].copy()
    out = out.rename(columns={q14_col: 'q14_education_raw'})

    # 5) Kategorien bereinigen und fehlende als "Keine Angabe" kennzeichnen
    def clean_education(x):
        if pd.isna(x) or x.strip() == "":
            return "Keine Angabe"
        return x.strip()

    out['q14_education'] = out['q14_education_raw'].apply(clean_education)
    out = out.drop(columns=['q14_education_raw'])

    # 6) Speichern
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    out.to_csv(out_csv, index=False, encoding='utf-8')
    print(f"Q14 (Bildungsabschluss) gespeichert nach: {out_csv}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        preprocess_q14_education(RAW_PATH, OUT_PATH)
    elif len(sys.argv) == 3:
        _, raw, out = sys.argv
        preprocess_q14_education(raw, out)
    else:
        print(
            "Usage:\n"
            "  python preprocess_q14_education.py\n"
            "  python preprocess_q14_education.py <input.csv> <output.csv>",
            file=sys.stderr
        )
        sys.exit(1)