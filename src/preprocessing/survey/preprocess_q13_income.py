#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preprocess_q13_income.py

Liest die Rohdaten ein, extrahiert Frage 13:
"Wie hoch ist Ihr monatliches Haushaltsnettoeinkommen?"
und schreibt respondent_id + Einkommen-Kategorie in eine neue CSV.
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
OUT_FILENAME  = 'question_13_income.csv'

RAW_PATH = os.path.join(RAW_DIR, RAW_FILENAME)
OUT_PATH = os.path.join(OUT_DIR, OUT_FILENAME)


def preprocess_q13_income(raw_csv: str, out_csv: str):
    # 1) Rohdaten einlesen
    df = pd.read_csv(raw_csv, header=0, skiprows=[1], dtype=str)

    # 2) respondent_id prüfen
    if 'respondent_id' not in df.columns:
        print("Spalte 'respondent_id' nicht gefunden.", file=sys.stderr)
        sys.exit(1)

    # 3) Spalte für Q13 dynamisch ermitteln
    #    Suche nach Schlüsselwort "Haushaltsnettoeinkommen"
    pattern = r"Haushaltsnettoeinkommen"
    matches = [c for c in df.columns if isinstance(c, str) and pattern in c]
    if len(matches) != 1:
        print(f"Erwartet genau eine Spalte zu Q13, gefunden: {matches!r}", file=sys.stderr)
        sys.exit(1)
    q13_col = matches[0]
    print(f"→ Verarbeite Spalte für Q13: {q13_col!r}")

    # 4) respondent_id + Antwort extrahieren
    out = df[['respondent_id', q13_col]].copy()
    out = out.rename(columns={q13_col: 'q13_income_raw'})

    # 5) Kategorien bereinigen und evtl. fehlende Werte als "Keine Angabe" markieren
    def clean_income(x):
        if pd.isna(x) or x.strip() == "":
            return "Keine Angabe"
        return x.strip()

    out['q13_income'] = out['q13_income_raw'].apply(clean_income)
    out = out.drop(columns=['q13_income_raw'])

    # 6) Speichern
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    out.to_csv(out_csv, index=False, encoding='utf-8')
    print(f"Q13 (Haushaltsnettoeinkommen) gespeichert nach: {out_csv}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        preprocess_q13_income(RAW_PATH, OUT_PATH)
    elif len(sys.argv) == 3:
        _, raw, out = sys.argv
        preprocess_q13_income(raw, out)
    else:
        print(
            "Usage:\n"
            "  python preprocess_q13_income.py\n"
            "  python preprocess_q13_income.py <input.csv> <output.csv>",
            file=sys.stderr
        )
        sys.exit(1)