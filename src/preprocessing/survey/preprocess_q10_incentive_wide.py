#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preprocess_q10_incentive_wide.py

Liest die Rohdaten zu Frage 10 ein,
extrahiert für sechs Geräte jeweils
  - die gewählte Incentive-Option (Ja f / Ja + / Nein)
  - den eingegebenen Prozent-Rabatt
und speichert das Ergebnis im Wide-Format.
"""

import os
import sys
import pandas as pd
import re

# ======================
# Pfad-Konstanten
# ======================
BASE_DIR      = os.path.abspath(
    os.path.join(__file__, os.pardir, os.pardir, os.pardir, os.pardir)
)
RAW_DIR       = os.path.join(BASE_DIR, 'data', 'raw',  'survey')
OUT_DIR       = os.path.join(BASE_DIR, 'data', 'processed', 'survey')
RAW_FILENAME  = 'Energieverbrauch und Teilnahmebereitschaft an Demand-Response-Programmen in Haushalten.csv'
OUT_FILENAME  = 'question_10_incentive_wide.csv'

RAW_PATH = os.path.join(RAW_DIR, RAW_FILENAME)
OUT_PATH = os.path.join(OUT_DIR, OUT_FILENAME)


def parse_pct(x: str) -> pd.Int64Dtype:
    """Entfernt das Prozent‐Zeichen und wandelt in Integer um."""
    if pd.isna(x):
        return pd.NA
    m = re.search(r'(\d+)', str(x))
    return int(m.group(1)) if m else pd.NA


def preprocess_q10_incentive_wide(raw_csv: str, out_csv: str):
    # 1) Rohdaten einlesen
    df = pd.read_csv(raw_csv, header=0, dtype=str)

    # 2) Fragetext lokalisieren
    question = (
        "Würde sich Ihre Bereitschaft erhöhen, die folgenden Haushaltsgeräte "
        "nicht zu nutzen, wenn Sie dafür eine finanzielle Belohnung erhalten würden?"
    )
    if question not in df.columns:
        print(f"Frage nicht gefunden im Header: {question}", file=sys.stderr)
        sys.exit(1)

    # 3) Spaltenindex der Frage
    q_idx = df.columns.get_loc(question)

    # 4) Geräte-Namen aus Zeile 2 extrahieren
    second = pd.read_csv(raw_csv, header=None, skiprows=1, nrows=1, dtype=str).iloc[0].tolist()
    appliances = second[q_idx : q_idx + 6]
    if len(appliances) != 6:
        print(f"Erwartet 6 Geräte, gefunden {len(appliances)}: {appliances}", file=sys.stderr)
        sys.exit(1)

    # 5) Column-Names aus Header zeile für Choice vs. Pct
    #    die Matrix hat erst 6 Spalten Dropdown1, dann 6 Spalten Prozent
    choice_cols = df.columns[q_idx : q_idx + 6].tolist()
    pct_cols    = df.columns[q_idx + 6 : q_idx + 12].tolist()

    # 6) Dataset auf respondent_id + diese 12 Spalten beschränken
    cols = ['respondent_id'] + choice_cols + pct_cols
    data = df[cols].copy()

    # 7) Spalten umbenennen auf Wide-Format: Gerät_choice, Gerät_pct
    rename_map = {}
    for i, dev in enumerate(appliances):
        rename_map[choice_cols[i]] = f"{dev}_choice"
        rename_map[pct_cols[i]]    = f"{dev}_pct"
    data = data.rename(columns=rename_map)

    # 8) Prozent-Spalten in Integer umwandeln
    for dev in appliances:
        data[f"{dev}_pct"] = data[f"{dev}_pct"].apply(parse_pct)

    # 9) Speichern
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    data.to_csv(out_csv, index=False, encoding='utf-8')
    print(f"Wide-Format Q10 gespeichert nach: {out_csv}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        preprocess_q10_incentive_wide(RAW_PATH, OUT_PATH)
    elif len(sys.argv) == 3:
        _, raw, out = sys.argv
        preprocess_q10_incentive_wide(raw, out)
    else:
        print(
            "Usage:\n"
            "  python preprocess_q10_incentive_wide.py\n"
            "  python preprocess_q10_incentive_wide.py <input.csv> <output.csv>",
            file=sys.stderr
        )
        sys.exit(1)