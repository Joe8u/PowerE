#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preprocess_q12_smartplug.py

Extrahiert Frage 12:
"Könnten Sie sich vorstellen, einen intelligenten Zwischenstecker (Smart Plug) an Ihren Geräten
zu installieren, damit Ihr Elektrizitätswerk Ihren Beitrag messen und Sie entsprechend vergüten kann?"
und schreibt respondent_id + Ja/Nein in eine neue CSV.
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
OUT_FILENAME  = 'question_12_smartplug.csv'

RAW_PATH = os.path.join(RAW_DIR, RAW_FILENAME)
OUT_PATH = os.path.join(OUT_DIR, OUT_FILENAME)


def preprocess_q12_smartplug(raw_csv: str, out_csv: str):
    # 1) Rohdaten einlesen
    df = pd.read_csv(raw_csv, header=0, skiprows=[1], dtype=str)

    # 2) respondent_id prüfen
    if 'respondent_id' not in df.columns:
        print("Spalte 'respondent_id' nicht gefunden.", file=sys.stderr)
        sys.exit(1)

    # 3) Spalte für Q12 dynamisch ermitteln
    #    Suche nach "zwischenstecker" oder "smart plug" im Spaltennamen
    pattern = r"zwischenstecker|smart\s*plug"
    candidates = [c for c in df.columns if pd.notna(c) and pd.Series(c).str.contains(pattern, case=False, regex=True).any()]
    if len(candidates) != 1:
        print(f"Erwartet genau eine Spalte zu Q12, gefunden: {candidates!r}", file=sys.stderr)
        sys.exit(1)
    q12_col = candidates[0]
    print(f"→ Verarbeite Spalte: {q12_col!r}")

    # 4) respondent_id + Antwort extrahieren und umbenennen
    out = df[['respondent_id', q12_col]].copy()
    out = out.rename(columns={q12_col: 'q12_smartplug'})

    # 5) Werte bereinigen: trimmen, standardisieren
    out['q12_smartplug'] = (
        out['q12_smartplug']
          .str.strip()
          .str.capitalize()
    )

    # 6) Verzeichnis anlegen & speichern
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    out.to_csv(out_csv, index=False, encoding='utf-8')
    print(f"Q12 (Smart Plug) gespeichert nach: {out_csv}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        preprocess_q12_smartplug(RAW_PATH, OUT_PATH)
    elif len(sys.argv) == 3:
        _, raw, out = sys.argv
        preprocess_q12_smartplug(raw, out)
    else:
        print(
            "Usage:\n"
            "  python preprocess_q12_smartplug.py\n"
            "  python preprocess_q12_smartplug.py <input.csv> <output.csv>",
            file=sys.stderr
        )
        sys.exit(1)