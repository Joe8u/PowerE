# PowerE/src/analysis/data_check/check_srl_raw_interval_durations.py
"""
Überprüft die Dauer der tatsächlich aktivierten Tertiärregelleistungs-Intervalle
aus den Rohdatendateien.

Dieses Skript liest die monatlichen Rohdateien der tertiären Regelleistung,
filtert nach Einträgen, bei denen Leistung abgerufen wurde (Abgerufene Menge > 0),
berechnet die Dauer jedes dieser Events basierend auf 'Von'- und 'Bis'-Zeiten
und gibt eine Zusammenfassung der gefundenen Dauern aus.
Ziel ist es zu verifizieren, ob alle Aktivierungen konsistent 15-Minuten-Intervalle sind.
"""
import pandas as pd
from pathlib import Path
import numpy as np
import os
import sys

# --- Pfad-Setup ---
try:
    # Annahme: Dieses Skript liegt in PowerE/src/analysis/data_check/
    CURRENT_SCRIPT_PATH = Path(__file__).resolve()
    # Vier .parent Aufrufe, um zum PowerE-Ordner (Projekt-Root) zu gelangen
    PROJECT_ROOT = CURRENT_SCRIPT_PATH.parent.parent.parent.parent 
except NameError:
    # Fallback
    PROJECT_ROOT = Path(os.getcwd()).resolve()
    print(f"[WARNUNG] __file__ nicht definiert. PROJECT_ROOT als CWD angenommen: {PROJECT_ROOT}")

print(f"[Path Setup] PROJECT_ROOT: {PROJECT_ROOT}")

def analyze_raw_srl_durations(year: int = 2024):
    """
    Analysiert die Dauer der aktivierten SRL-Events für das angegebene Jahr.
    """
    raw_dir = PROJECT_ROOT / "data" / "raw" / "market" / "regelenergie" / "mfrR" / str(year)
    
    if not raw_dir.exists():
        print(f"FEHLER: Rohdatenverzeichnis nicht gefunden: {raw_dir}")
        return

    print(f"\nStarte Analyse der SRL-Rohdaten-Intervalldauern für das Jahr {year}...")
    print(f"Suche nach Dateien in: {raw_dir}")

    all_durations = []
    overall_consistent_15_min = True

    for month_path in sorted(raw_dir.glob(f"{year}-[0-1][0-9]-TRE-Ergebnis.csv")):
        month_str = month_path.stem.split('-')[1]
        print(f"\n--- Verarbeite Datei: {month_path.name} ---")
        
        try:
            df = pd.read_csv(
                month_path,
                sep=';',
                encoding='latin1',
                usecols=['Ausschreibung', 'Von', 'Bis', 'Abgerufene Menge']
            )
        except FileNotFoundError:
            print(f"  FEHLER: Datei nicht gefunden.")
            overall_consistent_15_min = False
            continue
        except ValueError as ve:
            print(f"  FEHLER beim Lesen der Spalten (möglicherweise fehlen 'Von', 'Bis' oder 'Abgerufene Menge'): {ve}")
            overall_consistent_15_min = False
            continue

        if df.empty:
            print(f"  INFO: Datei {month_path.name} ist leer oder enthält nach Spaltenauswahl keine Daten.")
            continue

        # Datums-String erstellen
        try:
            df['date_str'] = df['Ausschreibung'].str.split('_').apply(lambda parts: f"{year}-{parts[2]}-{parts[3]}")
        except IndexError:
            print(f"  FEHLER: Konnte Datum nicht aus 'Ausschreibung' extrahieren. Überspringe Datei.")
            overall_consistent_15_min = False
            continue
            
        # Start- und End-Zeitstempel erstellen
        df['timestamp_start_dt'] = pd.to_datetime(df['date_str'] + ' ' + df['Von'], format="%Y-%m-%d %H:%M", errors='coerce')
        
        def calculate_end_dt(row):
            if pd.isna(row['date_str']) or pd.isna(row['Bis']) or pd.isna(row['Von']): return pd.NaT
            if row['Bis'] == '00:00' and row['Von'] != '00:00': # Ende des Tages
                return pd.to_datetime(row['date_str'] + ' ' + "23:59", format="%Y-%m-%d %H:%M") + pd.Timedelta(minutes=1)
            end_time = pd.to_datetime(row['date_str'] + ' ' + row['Bis'], format="%Y-%m-%d %H:%M", errors='coerce')
            if pd.notna(row['timestamp_start_dt']) and pd.notna(end_time) and end_time < row['timestamp_start_dt'] and row['Bis'] == '00:00':
                 end_time += pd.Timedelta(days=1) # Bis ist am nächsten Tag 00:00
            return end_time

        df['timestamp_end_dt'] = df.apply(calculate_end_dt, axis=1)
        df.dropna(subset=['timestamp_start_dt', 'timestamp_end_dt'], inplace=True)

        # Abgerufene Menge zu numerisch konvertieren
        df['Abgerufene Menge'] = pd.to_numeric(df['Abgerufene Menge'], errors='coerce')
        df.dropna(subset=['Abgerufene Menge'], inplace=True)

        # Filtere nur tatsächlich abgerufene Mengen
        df_called = df[df['Abgerufene Menge'] > 0].copy()

        if df_called.empty:
            print(f"  INFO: Keine positiven Aktivierungen in {month_path.name} gefunden.")
            continue
            
        # Dauer berechnen
        df_called['duration_minutes'] = (df_called['timestamp_end_dt'] - df_called['timestamp_start_dt']).dt.total_seconds() / 60
        df_called.dropna(subset=['duration_minutes'], inplace=True) # Entferne Fälle, wo Dauer nicht berechnet werden konnte

        if df_called.empty:
            print(f"  INFO: Keine Aktivierungen mit berechenbarer Dauer in {month_path.name} gefunden.")
            continue

        print(f"  Gefundene Dauern für aktivierte Events (in Minuten) in {month_path.name}:")
        duration_counts = df_called['duration_minutes'].value_counts().sort_index()
        print(duration_counts.to_string())
        
        all_durations.extend(df_called['duration_minutes'].tolist())

        if not all(duration_counts.index == 15.0):
            print(f"  WARNUNG: Nicht alle Aktivierungen in {month_path.name} haben eine Dauer von exakt 15 Minuten!")
            overall_consistent_15_min = False
        else:
            print(f"  INFO: Alle {len(df_called)} Aktivierungen in {month_path.name} haben eine Dauer von 15 Minuten.")

    print("\n\n--- Gesamtzusammenfassung der Intervall-Dauern (aktivierte Events) ---")
    if not all_durations:
        print("Keine aktivierten Events gefunden, für die eine Dauer berechnet werden konnte.")
    else:
        s_all_durations = pd.Series(all_durations)
        print("Verteilung aller beobachteten Dauern (in Minuten):")
        print(s_all_durations.value_counts().sort_index().to_string())
        
        if overall_consistent_15_min and all(s_all_durations == 15.0):
            print("\nFazit: Alle analysierten, aktivierten SRL-Events hatten eine Dauer von exakt 15 Minuten.")
            print("Dein ursprüngliches Preprocessing-Skript (das nur 'Von' für den Timestamp verwendet) ist für die Aggregation wahrscheinlich ausreichend.")
        else:
            print("\nFazit: Es wurden aktivierte SRL-Events mit Dauern ungleich 15 Minuten gefunden oder es gab Fehler.")
            print("Eine genauere Betrachtung der 'Von'- und 'Bis'-Zeiten im Preprocessing ist empfohlen, wenn die Intervalle nicht konsistent sind.")
            print("Die Version 'preprocess_tertiary_regulation_py_v2' (mit timestamp_start und timestamp_end) könnte hier robuster sein.")

if __name__ == "__main__":
    # Du kannst das Jahr hier anpassen, falls nötig
    analyze_raw_srl_durations(year=2024)
