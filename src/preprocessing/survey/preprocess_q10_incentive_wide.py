# PowerE/src/preprocessing/survey/preprocess_q10_incentive_wide.py
# -*- coding: utf-8 -*-
"""
preprocess_q10_incentive_wide.py
# ... (dein bestehender Docstring) ...
"""

import os
import sys
import pandas as pd
import re
import numpy as np # HINZUGEFÜGT für np.nan

# ======================
# Pfad-Konstanten
# ======================
# ... (deine bestehenden Pfad-Konstanten) ...
BASE_DIR     = os.path.abspath(
    os.path.join(__file__, os.pardir, os.pardir, os.pardir, os.pardir)
)
RAW_DIR      = os.path.join(BASE_DIR, 'data', 'raw',  'survey')
OUT_DIR      = os.path.join(BASE_DIR, 'data', 'processed', 'survey')
RAW_FILENAME = 'Energieverbrauch und Teilnahmebereitschaft an Demand-Response-Programmen in Haushalten.csv'
OUT_FILENAME = 'question_10_incentive_wide.csv'

RAW_PATH = os.path.join(RAW_DIR, RAW_FILENAME)
OUT_PATH = os.path.join(OUT_DIR, OUT_FILENAME)

def parse_pct(x: str) -> pd.Int64Dtype: # oder einfach 'object' oder 'Any' als return type hint
    """Entfernt das Prozent‐Zeichen und wandelt in Integer um."""
    if pd.isna(x) or str(x).strip() == '':
        return pd.NA # Pandas' eigenes NA-Objekt
    m = re.search(r'(\d+)', str(x))
    return int(m.group(1)) if m else pd.NA

def preprocess_q10_incentive_wide(raw_csv: str, out_csv: str):
    # 1) Rohdaten einlesen, Zeile 2 als Header
    # WICHTIG: Überprüfe, ob diese Lade-Logik für deine NEUE CSV-Datei noch optimal ist.
    # Wie besprochen, funktioniert sie für Q10 anscheinend, aber für andere Skripte
    # war header=0, skiprows=[1] empfohlen. Für Konsistenz könntest du überlegen,
    # Q10 auch so zu laden und die Spalten dann über MultiIndex oder eine Kombination
    # der ersten beiden Zeilen zu identifizieren. Da es aber zu funktionieren scheint,
    # belassen wir es vorerst bei deinem Ansatz für Q10.
    df = pd.read_csv(raw_csv, header=1, dtype=str, encoding='utf-8', sep=',') # encoding und sep hinzugefügt für Konsistenz

    # 2) Erste Spalte (egal wie sie heißt) in respondent_id umbenennen
    original_id_col = df.columns[0]
    df.rename(columns={original_id_col: 'respondent_id'}, inplace=True)

    # 3) Choice- und Pct-Spalten via Regex finden
    all_cols = df.columns.tolist()
    choice_cols_found = [c for c in all_cols if re.search(r' - Ja f, freiwilligJa \+, mit Kompensationoder Nein$', c)]
    pct_cols_found    = [c for c in all_cols if re.search(r' - Falls Ja, Stromkosten-Rabatt in Prozent$', c)]

    # 4) Geräte extrahieren und Staubsauger (6.) weglassen (oder anpassen, falls gewünscht)
    devices    = [c.split(' - ')[0] for c in choice_cols_found][:6] # Nimmt die ersten 5 Geräte
    choice_cols_to_use = choice_cols_found[:6]
    pct_cols_to_use    = pct_cols_found[:6]

    # Sicherstellen, dass wir für jedes Gerät ein Choice und ein Pct Paar haben
    if len(devices) != len(choice_cols_to_use) or len(devices) != len(pct_cols_to_use):
        print("WARNUNG: Anzahl der gefundenen Geräte, Choice-Spalten und Pct-Spalten stimmt nicht überein. Überprüfe Regex und Daten.")
        # Hier könntest du noch genauer prüfen oder abbrechen.
        # Für den Moment gehen wir davon aus, dass es passt, wenn die Längen gleich sind.

    # 5) Auf respondent_id + diese Spalten beschränken
    data = df[['respondent_id'] + choice_cols_to_use + pct_cols_to_use].copy()

    # 6) Spalten umbenennen auf Wide-Format: "<Gerät>_choice" und "<Gerät>_pct"
    rename_map = {}
    for dev, ccol, pcol in zip(devices, choice_cols_to_use, pct_cols_to_use):
        rename_map[ccol] = f"{dev}_choice"
        rename_map[pcol] = f"{dev}_pct"
    data.rename(columns=rename_map, inplace=True)

    # 7) Prozent-Strings in Integer/NA umwandeln
    for dev in devices:
        pct_col_name = f"{dev}_pct"
        if pct_col_name in data.columns:
            data[pct_col_name] = data[pct_col_name].apply(parse_pct)
            # Konvertiere die Spalte explizit zu einem numerischen Typ, der NaNs handhaben kann (Float oder Int64 mit pd.NA)
            # errors='coerce' ist hier wichtig, falls parse_pct doch mal was Unerwartetes liefert.
            data[pct_col_name] = pd.to_numeric(data[pct_col_name], errors='coerce')


    # +++ NEUER TEIL: BEREINIGUNGSREGELN ANWENDEN (KONSERVATIVER ANSATZ) +++
    print("Wende Bereinigungsregeln für Q10 an (konservativer Ansatz)...")
    for dev in devices:  # 'devices' ist die Liste deiner Geräte-Präfixe
        choice_col = f"{dev}_choice"
        pct_col = f"{dev}_pct"

        # Sicherstellen, dass die Spalten existieren, bevor wir darauf zugreifen
        if choice_col in data.columns and pct_col in data.columns:
            # Regel 1: Prozentwerte bei "Ja f" oder "Nein" auf NA setzen.
            # Die _choice Antwort bleibt gültig.
            # Wichtig: .str.strip() auf choice_col anwenden, falls dort Leerzeichen sein könnten!
            data.loc[data[choice_col].astype(str).str.strip().isin(['Ja f', 'Nein']), pct_col] = np.nan

            # Regel 2 (konservativer Ansatz): Wenn _choice fehlt (NA), aber _pct einen Wert hat,
            # setze auch _pct auf NA. _choice ist bereits NA oder wird als NA behandelt.
            # pd.Series.isna() prüft auf np.nan, None, pd.NA.
            # data[choice_col].astype(str).str.strip().str.lower() == 'nan' wäre eine Option, wenn NAs als Text "nan" vorliegen
            data.loc[data[choice_col].isna() & data[pct_col].notna(), pct_col] = np.nan
        else:
            print(f"WARNUNG: Spalten {choice_col} oder {pct_col} nicht im DataFrame 'data' gefunden. Überspringe Bereinigung für {dev}.")
    print("Bereinigungsregeln für Q10 angewendet.")
    # +++ ENDE NEUER TEIL +++

    # 8) Speichern
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    data.to_csv(out_csv, index=False, encoding='utf-8')
    print(f"Wide-Format Q10 gespeichert nach: {out_csv}")

# ======================
# Entry Point
# ======================
# ... (dein bestehender Entry Point) ...
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