# PowerE/src/preprocessing/market/regelenergie/preprocess_tertiary_regulation.py
"""
preprocess_tertiary_regulation.py

Aggregiert aus den monatlichen Rohdaten der tertiären Regelleistung
nur die tatsächlich abgerufenen Mengen (called_mw > 0) und berechnet
pro 15-Minuten-Intervall die Gesamtmenge sowie den gewichteten Durchschnittspreis.
Stellt sicher, dass nur aktivierte Mengen und valide Preise in die Berechnung einfliessen.
Gibt zusätzlich das teuerste aktivierte Event für einen spezifischen Tag aus.

Speichert die aufbereiteten Monatsdateien unter:
  data/processed/market/regelenergie/YYYY-MM.csv
  mit den Spalten: timestamp, total_called_mw, avg_price_eur_mwh
"""
import pandas as pd
from pathlib import Path
import numpy as np 
import os 
import sys 
import datetime

def main():
    year = 2024
    
    try:
        SCRIPT_DIR = Path(__file__).resolve().parent
        PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent 
    except NameError: 
        PROJECT_ROOT = Path(os.getcwd()).resolve()
        print(f"[WARNUNG] __file__ nicht definiert in preprocess_tertiary_regulation.py. PROJECT_ROOT als CWD angenommen: {PROJECT_ROOT}")
        if PROJECT_ROOT.name != "PowerE":
            print(f"FEHLER: CWD ({PROJECT_ROOT}) ist wahrscheinlich nicht das erwartete Projekt-Root 'PowerE'. Bitte vom PowerE-Ordner ausführen.")
            sys.exit(1)

    raw_dir = PROJECT_ROOT / "data" / "raw" / "market" / "regelenergie" / "mfrR" / str(year)
    proc_dir = PROJECT_ROOT / "data" / "processed" / "market" / "regelenergie"
    proc_dir.mkdir(parents=True, exist_ok=True)

    print(f"Starte Verarbeitung der Tertiärregelleistungsdaten für das Jahr {year}...")

    all_activated_events_for_year = [] # Liste zum Sammeln aller aktivierten Events

    for month_path in sorted(raw_dir.glob(f"{year}-[0-1][0-9]-TRE-Ergebnis.csv")):
        month = month_path.stem.split('-')[1]
        print(f"\nVerarbeite Rohdaten für: {year}-{month} von {month_path}")
        
        try:
            df = pd.read_csv(
                month_path,
                sep=';',
                encoding='latin1',
                usecols=[ # Produkt hinzugefügt für mehr Kontext beim Debugging
                    'Ausschreibung', 'Von', 'Bis', 
                    'Abgerufene Menge', 'Preis', 'Produkt', 'Status'
                ]
            )
        except FileNotFoundError:
            print(f"  FEHLER: Datei {month_path} nicht gefunden.")
            continue
        except ValueError as ve: 
            print(f"  FEHLER beim Lesen der Spalten von {month_path}: {ve}")
            continue
        except Exception as e:
            print(f"  Ein unerwarteter Fehler ist beim Lesen der Datei {month_path.name} aufgetreten: {e}")
            continue

        if df.empty:
            print(f"  INFO: {year}-{month}: Keine Daten in der Rohdatei oder nach Spaltenauswahl.")
            out = pd.DataFrame(columns=["timestamp", "total_called_mw", "avg_price_eur_mwh"])
            out_path = proc_dir / f"{year}-{month}.csv"
            out.to_csv(out_path, index=False)
            print(f"  Leere Datei für {year}-{month} geschrieben nach: {out_path}")
            continue

        # Datums-String erstellen
        try:
            df = df[df['Ausschreibung'].apply(lambda x: isinstance(x, str))].copy() 
            df.loc[:, 'date_str'] = df['Ausschreibung'].str.split('_').apply(lambda parts: f"{year}-{parts[2]}-{parts[3]}" if len(parts) > 3 else None)
            df.dropna(subset=['date_str'], inplace=True) 
        except (IndexError, AttributeError, KeyError) as e_date: 
            print(f"  FEHLER: Konnte Datum nicht valide aus 'Ausschreibung' extrahieren in {month_path}. Problem: {e_date}.")
            if df.empty: continue


        # Start-Zeitstempel erstellen
        df.loc[:, 'timestamp'] = pd.to_datetime( 
            df['date_str'] + ' ' + df['Von'],
            format="%Y-%m-%d %H:%M",
            errors='coerce' 
        )
        df.dropna(subset=['timestamp'], inplace=True)
        if df.empty:
            print(f"  INFO: {year}-{month}: Keine validen Zeitstempel nach Konvertierung.")
            out = pd.DataFrame(columns=["timestamp", "total_called_mw", "avg_price_eur_mwh"])
            out_path = proc_dir / f"{year}-{month}.csv"
            out.to_csv(out_path, index=False)
            print(f"  Leere Datei für {year}-{month} geschrieben nach: {out_path}")
            continue

        # Spalten umbenennen
        df = df.rename(columns={
            'Abgerufene Menge': 'called_mw',
            'Preis':            'price_eur_mwh'
        })

        # Typkonvertierung
        if 'called_mw' in df.columns:
            called_mw_series = df['called_mw'].astype(str).str.replace(',', '.', regex=False)
            df.loc[:, 'called_mw'] = pd.to_numeric(called_mw_series, errors='coerce')
        else:
            print(f"  WARNUNG: Spalte 'called_mw' nicht gefunden in {month_path.name}. Überspringe Verarbeitung für diesen Monat.")
            continue
            
        if 'price_eur_mwh' in df.columns:
            price_eur_mwh_series = df['price_eur_mwh'].astype(str).str.replace(',', '.', regex=False)
            df.loc[:, 'price_eur_mwh'] = pd.to_numeric(price_eur_mwh_series, errors='coerce')
        else:
            print(f"  WARNUNG: Spalte 'price_eur_mwh' nicht gefunden in {month_path.name}. Überspringe Verarbeitung für diesen Monat.")
            continue
            
        df.dropna(subset=['called_mw', 'price_eur_mwh'], inplace=True)
        if df.empty:
            print(f"  INFO: {year}-{month}: Keine validen numerischen Daten für Menge/Preis nach Konvertierung.")
            out = pd.DataFrame(columns=["timestamp", "total_called_mw", "avg_price_eur_mwh"])
            out_path = proc_dir / f"{year}-{month}.csv"
            out.to_csv(out_path, index=False)
            print(f"  Leere Datei für {year}-{month} geschrieben nach: {out_path}")
            continue

        # Filtere nur Zeilen, bei denen tatsächlich Leistung abgerufen wurde
        df_called = df[df['called_mw'] > 0].copy()

        if not df_called.empty:
            # Füge die relevanten Spalten der aktivierten Events zur Gesamtliste hinzu
            # Behalte Originalspaltennamen für die Details des höchsten Preises
            all_activated_events_for_year.append(df_called[['timestamp', 'called_mw', 'price_eur_mwh', 'Von', 'Bis', 'Produkt', 'Status', 'Ausschreibung']].copy())

            df_called.loc[:, 'cost'] = df_called['called_mw'] * df_called['price_eur_mwh']
            
            agg = df_called.groupby('timestamp').agg(
                total_called_mw=('called_mw', 'sum'),
                total_cost=('cost', 'sum')
            )
            
            agg['avg_price_eur_mwh'] = np.where(agg['total_called_mw'] != 0, agg['total_cost'] / agg['total_called_mw'], 0)
            
            out = agg[['total_called_mw', 'avg_price_eur_mwh']].reset_index()
            out.rename(columns={'timestamp': 'timestamp'}, inplace=True) 
        else:
            print(f"  INFO: {year}-{month}: keine positiven Aktivierungen nach Filterung gefunden.")
            out = pd.DataFrame(columns=["timestamp", "total_called_mw", "avg_price_eur_mwh"])


        out_path = proc_dir / f"{year}-{month}.csv"
        out.to_csv(out_path, index=False)
        print(f"  Processed {year}-{month} → {out_path}")

    print(f"\nVerarbeitung für das Jahr {year} abgeschlossen.")

    # --- Zusätzliche Analyse: Höchster Preis für aktiviertes Event am 2024-01-19 ---
    if all_activated_events_for_year:
        df_all_activated_year = pd.concat(all_activated_events_for_year, ignore_index=True)
        
        # Stelle sicher, dass 'timestamp' ein Datetime-Objekt ist
        if not pd.api.types.is_datetime64_any_dtype(df_all_activated_year['timestamp']):
            df_all_activated_year['timestamp'] = pd.to_datetime(df_all_activated_year['timestamp'], errors='coerce')
        
        # Filtere nach dem spezifischen Datum
        target_date_str = f"{year}-01-19"
        target_date = pd.to_datetime(target_date_str).date()
        
        df_specific_day_activated = df_all_activated_year[df_all_activated_year['timestamp'].dt.date == target_date].copy()
        
        if not df_specific_day_activated.empty:
            # Finde das Event mit dem höchsten Preis an diesem Tag
            # Stelle sicher, dass price_eur_mwh numerisch ist (sollte es schon sein)
            df_specific_day_activated.loc[:, 'price_eur_mwh'] = pd.to_numeric(df_specific_day_activated['price_eur_mwh'], errors='coerce')
            
            if df_specific_day_activated['price_eur_mwh'].notna().any():
                highest_price_event = df_specific_day_activated.loc[df_specific_day_activated['price_eur_mwh'].idxmax()]
            
                print("\n\n--- Höchster Preis für ein aktiviertes Event am 2024-01-19 ---")
                print(f"Zeitstempel (Start): {highest_price_event['timestamp']}")
                print(f"Von: {highest_price_event['Von']}")
                print(f"Bis: {highest_price_event['Bis']}")
                print(f"Produkt: {highest_price_event['Produkt']}")
                print(f"Status: {highest_price_event['Status']}")
                print(f"Ausschreibung: {highest_price_event['Ausschreibung']}")
                print(f"Abgerufene Menge (called_mw): {highest_price_event['called_mw']} MW")
                print(f"Preis (price_eur_mwh): {highest_price_event['price_eur_mwh']} EUR/MWh")
                print("-------------------------------------------------------------")
            else:
                print(f"\nKeine Events mit validen Preisen am {target_date_str} gefunden.")
        else:
            print(f"\nKeine aktivierten Events für den {target_date_str} gefunden.")
    else:
        print("\nKeine aktivierten Events im gesamten Jahr gefunden, um den höchsten Preis zu bestimmen.")


if __name__ == "__main__":
    main()
