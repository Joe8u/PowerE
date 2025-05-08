#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preprocess_q11_notification.py

Extrahiert Frage 11 (Benachrichtigungsbereitschaft)
und schreibt respondent_id + Ja/Nein in eine neue CSV.
"""

import os
import sys
import pandas as pd

BASE_DIR      = os.path.abspath(
    os.path.join(__file__, os.pardir, os.pardir, os.pardir, os.pardir)
)
RAW_DIR       = os.path.join(BASE_DIR, 'data', 'raw', 'survey')
OUT_DIR       = os.path.join(BASE_DIR, 'data', 'processed', 'survey')
RAW_FILENAME  = 'Energieverbrauch und Teilnahmebereitschaft an Demand-Response-Programmen in Haushalten.csv'
OUT_FILENAME  = 'question_11_notification.csv'

RAW_PATH = os.path.join(RAW_DIR, RAW_FILENAME)
OUT_PATH = os.path.join(OUT_DIR, OUT_FILENAME)


def preprocess_q11_notification(raw_csv: str, out_csv: str):
    # 1) Einlesen
    df = pd.read_csv(raw_csv, header=0, dtype=str)

    # 2) respondent_id prüfen
    if 'respondent_id' not in df.columns:
        print("Spalte 'respondent_id' nicht gefunden.", file=sys.stderr)
        sys.exit(1)

    # 3) Frage-11-Spalte dynamisch ermitteln
    #    wir suchen nach dem Schlüsselwort "benachrichtigt"
    candidates = [c for c in df.columns if "benachrichtigt" in c.lower()]
    if len(candidates) != 1:
        print(f"Erwartet genau eine Spalte zu Q11, gefunden: {candidates!r}", file=sys.stderr)
        sys.exit(1)
    q11_col = candidates[0]
    print(f"→ Verarbeite Spalte: {q11_col!r}")

    # 4) respondent_id + Antwort extrahieren und benennen
    out = df[['respondent_id', q11_col]].copy()
    out = out.rename(columns={q11_col: 'q11_notify'})

    # 5) Werte säubern: trimmen, erste Buchstabe groß
    out['q11_notify'] = (
        out['q11_notify']
          .str.strip()
          .str.capitalize()
    )

    # 6) Speichern
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    out.to_csv(out_csv, index=False, encoding='utf-8')
    print(f"Q11 (Notification) gespeichert nach: {out_csv}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        preprocess_q11_notification(RAW_PATH, OUT_PATH)
    elif len(sys.argv) == 3:
        _, raw, out = sys.argv
        preprocess_q11_notification(raw, out)
    else:
        print(
            "Usage:\n"
            "  python preprocess_q11_notification.py\n"
            "  python preprocess_q11_notification.py <input.csv> <output.csv>",
            file=sys.stderr
        )
        sys.exit(1)