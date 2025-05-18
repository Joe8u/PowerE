#!/usr/bin/env python3
# src/preprocessing/lastprofile/2024/precompute_lastprofile_2024.py

import pandas as pd
from pathlib import Path
import os # Importiere os für den Fallback im Pfad-Setup
import sys # Importiere sys für sys.exit()

# --- BEGINN: Robuster Pfad-Setup ---
try:
    # Annahme: Dieses Skript liegt in PowerE/src/preprocessing/lastprofile/2024/
    CURRENT_SCRIPT_PATH = Path(__file__).resolve()
    # Fünf .parent Aufrufe, um zum PowerE-Ordner (Projekt-Root) zu gelangen
    PROJECT_ROOT = CURRENT_SCRIPT_PATH.parent.parent.parent.parent.parent 
except NameError:
    # Fallback, falls __file__ nicht definiert ist (z.B. interaktive Ausführung)
    PROJECT_ROOT = Path(os.getcwd()).resolve()
    print(f"[WARNUNG] __file__ nicht definiert in precompute_lastprofile_2024.py. PROJECT_ROOT als CWD angenommen: {PROJECT_ROOT}")
    print(f"           Stelle sicher, dass dies der Projekt-Root 'PowerE' ist.")
print(f"[Path Setup in precompute_lastprofile_2024.py] PROJECT_ROOT: {PROJECT_ROOT}")
# --- ENDE: Robuster Pfad-Setup ---


# --- 0) Config ---------------------------------------------------------------
# Definiere Pfade relativ zum PROJECT_ROOT
RAW_CSV_RELPATH = Path("data/raw/lastprofile/Swiss_load_curves_2015_2035_2050.csv")
BASE_PROCESSED_RELPATH = Path("data/processed/lastprofile")

RAW_CSV_ABS_PATH = PROJECT_ROOT / RAW_CSV_RELPATH
BASE_PROCESSED_ABS_PATH = PROJECT_ROOT / BASE_PROCESSED_RELPATH

OUT_DIR = BASE_PROCESSED_ABS_PATH / "2024"
OUT_DIR.mkdir(parents=True, exist_ok=True) # parents=True erstellt auch übergeordnete Verzeichnisse falls nötig

f = (2024 - 2015) / (2035 - 2015)  # = 0.45

# --- 1) Raw einlesen ---------------------------------------------------------
print(f"Lese Rohdaten von: {RAW_CSV_ABS_PATH}")
try:
    df_raw = pd.read_csv(
        RAW_CSV_ABS_PATH, sep=";", dtype={
            "Year": int, "Month": int, "Day type": str,
            "Time": str, "Appliances": str, "Power (MW)": float
        }
    )
except FileNotFoundError:
    print(f"FEHLER: Rohdatendatei nicht gefunden unter {RAW_CSV_ABS_PATH}")
    sys.exit(1) # Beende das Skript, wenn die Rohdaten nicht gefunden werden.

df_raw.columns = (
    df_raw.columns
    .str.strip().str.lower()
    .str.replace(" ", "_")
)

# --- 2) Pivot-Jahre aufbauen ------------------------------------------------
def pivot_year(df, year):
    df_y = df[df["year"] == year]
    df_y = (
        df_y
        .groupby(["month","day_type","time","appliances"], as_index=False)
        ["power_(mw)"].mean()
    )
    df_y["power_mw_val"] = df_y["power_(mw)"] 
    return (
        df_y
        .pivot(index=["month","day_type","time"],
               columns="appliances",
               values="power_mw_val") 
        .sort_index()
    )

print("Erstelle Pivot-Tabellen für 2015 und 2035...")
pivot15 = pivot_year(df_raw, 2015)
pivot35 = pivot_year(df_raw, 2035)

# --- 3) Saisonale Interpolation für 2024 ------------------------------------
print("Interpoliere Daten für 2024...")
pivot24 = (1 - f) * pivot15 + f * pivot35

# --- 4) Kalender mit 15-Min-Raster erzeugen --------------------------------
print("Erzeuge Kalender für 2024...")
# Korrektur für FutureWarning: 'T' ist veraltet, verwende 'min'
rng = pd.date_range("2024-01-01","2024-12-31 23:45:00",freq="15min",tz="Europe/Zurich")
df_cal = pd.DataFrame({"timestamp": rng})
df_cal["timestamp"] = df_cal["timestamp"].dt.tz_localize(None) 
df_cal["month"]    = df_cal["timestamp"].dt.month
df_cal["day_type"] = df_cal["timestamp"].dt.weekday.map(lambda d: "weekday" if d<5 else "weekend")
df_cal["time"]     = df_cal["timestamp"].dt.strftime("%H:00:00")

# --- 5) Merge mit interpoliertem Profil ------------------------------------
print("Merge Kalender mit interpolierten Profildaten...")
df_merged = (
    df_cal
    .merge(pivot24.reset_index(), 
           on=["month","day_type","time"],
           how="left")
    .drop(columns=["month","day_type","time"])
)

# --- 5a) Gruppieren gemäß Survey-Kategorien -------------------------------
print("Gruppiere Appliance-Daten gemäss Survey-Kategorien...")
group_map = {
    "Geschirrspüler":                     ["Dishwasher"],
    "Backofen und Herd":                  ["Cooking"], 
    "Fernseher und Entertainment-Systeme":["TV","STB","DVB","Music"], 
    "Bürogeräte":                         ["Computer"], 
    "Waschmaschine":                      ["Washing machine"] 
}

df_grouped = pd.DataFrame({"timestamp": df_merged["timestamp"]})
for cat, cols_to_sum in group_map.items():
    existing_cols_in_df = [c for c in cols_to_sum if c in df_merged.columns]
    if not existing_cols_in_df:
        print(f"WARNUNG: Keine der Spalten {cols_to_sum} für Kategorie '{cat}' im gemergten DataFrame gefunden. Verfügbare Spalten: {df_merged.columns.tolist()}")
        df_grouped[cat] = 0.0 
    else:
        df_grouped[cat] = df_merged[existing_cols_in_df].sum(axis=1)

# --- 6) Split in Monats-CSVs mit neuen Kategorien ---------------------------
print("Schreibe monatliche CSV-Dateien...")
for m in range(1, 13):
    if not pd.api.types.is_datetime64_any_dtype(df_grouped["timestamp"]):
        df_grouped["timestamp"] = pd.to_datetime(df_grouped["timestamp"])
        
    df_month = df_grouped[df_grouped["timestamp"].dt.month == m].copy() 
    
    if not pd.api.types.is_datetime64_any_dtype(df_month["timestamp"]): # Double check
         df_month["timestamp"] = pd.to_datetime(df_month["timestamp"])
    df_month["timestamp"] = df_month["timestamp"].dt.tz_localize(None)

    outpath = OUT_DIR / f"2024-{m:02d}.csv"
    df_month.to_csv(outpath, index=False)
    print(f"Wrote {outpath}")

print("\nVorverarbeitung der Lastprofile für 2024 abgeschlossen.")
