# PowerE/src/preprocessing/survey/preprocess_q10_incentive_wide.py
# -*- coding: utf-8 -*-
"""
preprocess_q10_incentive_wide.py

Liest die Rohdaten zu Frage 10 ein (zweizeiliger Header),
extrahiert für fünf Geräte jeweils
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
BASE_DIR     = os.path.abspath(
    os.path.join(__file__, os.pardir, os.pardir, os.pardir, os.pardir)
)
RAW_DIR      = os.path.join(BASE_DIR, 'data', 'raw',  'survey')
OUT_DIR      = os.path.join(BASE_DIR, 'data', 'processed', 'survey')
RAW_FILENAME = 'Energieverbrauch und Teilnahmebereitschaft an Demand-Response-Programmen in Haushalten.csv'
OUT_FILENAME = 'question_10_incentive_wide.csv'

RAW_PATH = os.path.join(RAW_DIR, RAW_FILENAME)
OUT_PATH = os.path.join(OUT_DIR, OUT_FILENAME)

def parse_pct(x: str) -> pd.Int64Dtype:
    """Entfernt das Prozent‐Zeichen und wandelt in Integer um."""
    if pd.isna(x) or str(x).strip() == '':
        return pd.NA
    m = re.search(r'(\d+)', str(x))
    return int(m.group(1)) if m else pd.NA

def preprocess_q10_incentive_wide(raw_csv: str, out_csv: str):
    # 1) Rohdaten einlesen, Zeile 2 als Header
    df = pd.read_csv(raw_csv, header=1, dtype=str)

    # 2) Erste Spalte (egal wie sie heißt) in respondent_id umbenennen
    original_id_col = df.columns[0]
    df.rename(columns={original_id_col: 'respondent_id'}, inplace=True)

    # 3) Choice- und Pct-Spalten via Regex finden
    all_cols = df.columns.tolist()
    choice_cols = [c for c in all_cols if re.search(r' - Ja f, freiwilligJa \+, mit Kompensationoder Nein$', c)]
    pct_cols    = [c for c in all_cols if re.search(r' - Falls Ja, Stromkosten-Rabatt in Prozent$', c)]

    # 4) Geräte extrahieren und Staubsauger (6.) weglassen
    devices    = [c.split(' - ')[0] for c in choice_cols][:5]
    choice_cols = choice_cols[:5]
    pct_cols    = pct_cols[:5]

    # 5) Auf respondent_id + diese Spalten beschränken
    data = df[['respondent_id'] + choice_cols + pct_cols].copy()

    # 6) Spalten umbenennen auf Wide-Format: "<Gerät>_choice" und "<Gerät>_pct"
    rename_map = {}
    for dev, ccol, pcol in zip(devices, choice_cols, pct_cols):
        rename_map[ccol] = f"{dev}_choice"
        rename_map[pcol] = f"{dev}_pct"
    data.rename(columns=rename_map, inplace=True)

    # 7) Prozent-Strings in Integer umwandeln
    for dev in devices:
        data[f"{dev}_pct"] = data[f"{dev}_pct"].apply(parse_pct)

    # 8) Speichern
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