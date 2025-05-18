# PowerE/src/analysis/data_check/check_min_activated_srl_power.py
"""
Analysiert die Rohdaten der Tertiärregelleistung, um die kleinste tatsächlich
aktivierte Leistungsmenge (Abgerufene Menge > 0) über einen bestimmten Zeitraum
zu identifizieren und gibt ein Beispiel für einen 1-MW-Abruf aus.
"""
import pandas as pd
from pathlib import Path
import numpy as np
import os
import sys

# --- Pfad-Setup ---
try:
    CURRENT_SCRIPT_PATH = Path(__file__).resolve().parent
    PROJECT_ROOT = CURRENT_SCRIPT_PATH.parent.parent.parent 
except NameError:
    PROJECT_ROOT = Path(os.getcwd()).resolve()
    print(f"[WARNUNG] __file__ nicht definiert. PROJECT_ROOT als CWD angenommen: {PROJECT_ROOT}")

print(f"[Path Setup] PROJECT_ROOT: {PROJECT_ROOT}")

def find_minimum_activated_power_and_example(year: int = 2024):
    """
    Findet die kleinste aktivierte Leistungsmenge in den SRL-Rohdaten für das angegebene Jahr
    und gibt ein Beispiel für einen 1-MW-Abruf aus.
    """
    raw_dir = PROJECT_ROOT / "data" / "raw" / "market" / "regelenergie" / "mfrR" / str(year)
    
    if not raw_dir.exists():
        print(f"FEHLER: Rohdatenverzeichnis nicht gefunden: {raw_dir}")
        return

    print(f"\nStarte Analyse der minimal aktivierten SRL-Leistung für das Jahr {year}...")
    print(f"Suche nach Dateien in: {raw_dir}")

    all_activated_power_values = []
    first_1mw_event_details = None # Zum Speichern des ersten 1-MW-Events

    for month_path in sorted(raw_dir.glob(f"{year}-[0-1][0-9]-TRE-Ergebnis.csv")):
        month_str = month_path.stem.split('-')[1]
        print(f"\n--- Verarbeite Datei: {month_path.name} ---")
        
        try:
            df = pd.read_csv(
                month_path,
                sep=';',
                encoding='latin1',
                # Lade mehr Spalten für den Kontext des Beispiel-Events
                usecols=['Ausschreibung', 'Von', 'Bis', 'Abgerufene Menge', 'Preis', 'Produkt', 'Status']
            )
        except FileNotFoundError:
            print(f"  FEHLER: Datei nicht gefunden.")
            continue
        except ValueError as ve:
            print(f"  FEHLER beim Lesen der Spalten: {ve}")
            continue
        except Exception as e:
            print(f"  Ein unerwarteter Fehler ist beim Lesen der Datei {month_path.name} aufgetreten: {e}")
            continue

        if df.empty:
            print(f"  INFO: Datei {month_path.name} ist leer oder enthält nach Spaltenauswahl keine Daten.")
            continue
            
        # Abgerufene Menge zu numerisch konvertieren
        if 'Abgerufene Menge' in df.columns:
            df['Abgerufene Menge'] = df['Abgerufene Menge'].astype(str).str.replace(',', '.', regex=False)
            df['Abgerufene Menge'] = pd.to_numeric(df['Abgerufene Menge'], errors='coerce')
            df.dropna(subset=['Abgerufene Menge'], inplace=True)

            # Filtere nur tatsächlich abgerufene Mengen (> 0)
            df_activated_in_month = df[df['Abgerufene Menge'] > 0].copy() # .copy() um Warnungen zu vermeiden
            
            if not df_activated_in_month.empty:
                all_activated_power_values.extend(df_activated_in_month['Abgerufene Menge'].tolist())
                min_val_month = df_activated_in_month['Abgerufene Menge'].min()
                print(f"  {len(df_activated_in_month)} aktivierte Events in diesem Monat gefunden. Kleinster Wert: {min_val_month} MW")

                # Suche nach dem ersten 1-MW-Event, falls noch nicht gefunden
                if first_1mw_event_details is None:
                    one_mw_events = df_activated_in_month[df_activated_in_month['Abgerufene Menge'] == 1.0]
                    if not one_mw_events.empty:
                        first_1mw_event_details = one_mw_events.iloc[0].to_dict()
                        first_1mw_event_details['source_file'] = month_path.name
                        # Datums-String für das Event erstellen
                        try:
                            ausschreibung_parts = first_1mw_event_details['Ausschreibung'].split('_')
                            event_date_str = f"{year}-{ausschreibung_parts[2]}-{ausschreibung_parts[3]}"
                            first_1mw_event_details['event_date'] = event_date_str
                        except IndexError:
                            first_1mw_event_details['event_date'] = "Datum konnte nicht extrahiert werden"
                        print(f"    INFO: Erstes 1-MW-Event in dieser Datei gefunden und gespeichert.")
            else:
                print(f"  INFO: Keine positiven Aktivierungen in {month_path.name} gefunden.")
        else:
            print(f"  WARNUNG: Spalte 'Abgerufene Menge' nicht in {month_path.name} gefunden.")

    print("\n\n--- Gesamtergebnis der Analyse der minimal aktivierten Leistung ---")
    if not all_activated_power_values:
        print("Keine aktivierten SRL-Events im gesamten Zeitraum gefunden.")
    else:
        min_activated_power = min(all_activated_power_values)
        max_activated_power = max(all_activated_power_values)
        avg_activated_power = np.mean(all_activated_power_values)
        median_activated_power = np.median(all_activated_power_values)
        
        print(f"Analysierte aktivierte Events insgesamt: {len(all_activated_power_values)}")
        print(f"Kleinste tatsächlich aktivierte Leistungsmenge im Jahr {year}: {min_activated_power} MW")
        print(f"Größte tatsächlich aktivierte Leistungsmenge im Jahr {year}: {max_activated_power} MW")
        print(f"Durchschnittliche aktivierte Leistungsmenge im Jahr {year}: {avg_activated_power:.2f} MW")
        print(f"Median der aktivierten Leistungsmenge im Jahr {year}: {median_activated_power:.2f} MW")

        s_all_activated = pd.Series(all_activated_power_values)
        print("\nVerteilung der aktivierten Leistungsmengen (MW):")
        print(s_all_activated.describe(percentiles=[.01, .05, .1, .25, .5, .75, .9, .95, .99]).to_string())
        
        # Gib das gespeicherte 1-MW-Event aus, falls gefunden
        if first_1mw_event_details:
            print("\n--- Beispiel für ein Event mit genau 1 MW Abruf ---")
            print(f"Quelldatei: {first_1mw_event_details.get('source_file')}")
            print(f"Datum (aus Ausschreibung): {first_1mw_event_details.get('event_date')}")
            print(f"Von: {first_1mw_event_details.get('Von')}")
            print(f"Bis: {first_1mw_event_details.get('Bis')}")
            print(f"Produkt: {first_1mw_event_details.get('Produkt')}")
            print(f"Abgerufene Menge: {first_1mw_event_details.get('Abgerufene Menge')} MW")
            print(f"Preis: {first_1mw_event_details.get('Preis')} EUR/MWh") # Annahme Einheit aus Rohdaten
            print(f"Status: {first_1mw_event_details.get('Status')}")
            print("----------------------------------------------------")
        elif min_activated_power == 1.0:
             print("\nINFO: Es gab 1-MW-Events, aber das erste Beispiel konnte nicht detailliert gespeichert werden (sollte nicht passieren).")
        else:
            print("\nKein Event mit genau 1 MW Abruf im analysierten Zeitraum gefunden.")


if __name__ == "__main__":
    find_minimum_activated_power_and_example(year=2024)
