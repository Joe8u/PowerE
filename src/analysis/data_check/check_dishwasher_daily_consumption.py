# PowerE/src/analysis/data_check/check_dishwasher_daily_consumption.py
"""
Skript zur Analyse des täglichen Stromverbrauchs eines Geschirrspülers
basierend auf den geladenen Lastprofildaten (JASM-Daten).
"""
import os
import sys
import pandas as pd
from pathlib import Path
import datetime

# --- BEGINN: Robuster Pfad-Setup (ähnlich wie in deinen anderen Skripten) ---
try:
    # Annahme: Dieses Skript liegt in src/analysis/data_check/
    CURRENT_SCRIPT_PATH = Path(__file__).resolve()
    # Korrektur: Vier .parent Aufrufe, um zum PowerE-Ordner (Projekt-Root) zu gelangen
    PROJECT_ROOT = CURRENT_SCRIPT_PATH.parent.parent.parent.parent 
except NameError:
    # Fallback, falls __file__ nicht definiert ist (z.B. in einer interaktiven Konsole, die das Skript nicht direkt ausführt)
    # Wenn das Skript normal ausgeführt wird, sollte __file__ definiert sein.
    PROJECT_ROOT = Path(os.getcwd()).resolve() # Nimmt das aktuelle Arbeitsverzeichnis
    print(f"[WARNUNG] __file__ nicht definiert. PROJECT_ROOT als aktuelles Arbeitsverzeichnis angenommen: {PROJECT_ROOT}")
    print(f"           Stelle sicher, dass das Skript vom PowerE-Ordner aus gestartet wird oder passe den Pfad an, wenn dies nicht der Projekt-Root ist.")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    print(f"[Path Setup] Projekt-Root '{PROJECT_ROOT}' zum sys.path hinzugefügt.")
else:
    print(f"[Path Setup] Projekt-Root '{PROJECT_ROOT}' ist bereits im sys.path.")


try:
    # Annahme: lastprofile.py liegt in src/data_loader/
    # Da PROJECT_ROOT (PowerE/) jetzt im sys.path ist, kann Python 'src' als Top-Level-Paket finden.
    from src.data_loader.lastprofile import load_appliances 
    print("Loader 'lastprofile.py' erfolgreich importiert.\n")
except ImportError as e:
    print(f"FEHLER beim Importieren von 'lastprofile.py': {e}")
    print(f"Aktueller sys.path: {sys.path}")
    print(f"PROJECT_ROOT wurde gesetzt auf: {PROJECT_ROOT}")
    print("Stelle sicher, dass das Skript im korrekten Pfad liegt und der PROJECT_ROOT korrekt auf das Hauptverzeichnis 'PowerE' zeigt.")
    sys.exit(1)
# --- ENDE: Robuster Pfad-Setup ---

# --- Parameter für die Analyse ---
APPLIANCE_NAME = "Geschirrspüler" # Muss mit group_map in lastprofile.py oder CSV-Spaltennamen übereinstimmen
TARGET_YEAR = 2024
TARGET_MONTH = 2
TARGET_DAY = 3 # Beispieltag, passend zur JASM-URL die du erwähnt hast

# !!! WICHTIGE ANNAHME: Zeitliche Auflösung der Daten in Minuten !!!
# Überprüfe dies unbedingt mit der JASM-Datensatzbeschreibung und passe es an!
# Beispiele:
# 1  -> für 1-Minuten-Werte
# 15 -> für 15-Minuten-Werte
# 60 -> für Stunden-Werte
TIME_RESOLUTION_MINUTES = 15 

# Annahme zur Einheit der Leistungswerte aus dem Loader (basierend auf deiner Info)
POWER_UNIT_IS_MW = True # ****** BITTE ÜBERPRÜFEN! Wenn es kW sind, setze auf False und prüfe Umrechnung ******

def analyze_daily_consumption():
    print(f"=== Analyse des täglichen Stromverbrauchs für: {APPLIANCE_NAME} ===")
    print(f"Zieldatum: {TARGET_YEAR}-{TARGET_MONTH:02d}-{TARGET_DAY:02d}")
    print(f"Angenommene Zeitauflösung der Quelldaten: {TIME_RESOLUTION_MINUTES} Minute(n)")
    print(f"Angenommene Einheit der Leistungswerte: {'MW' if POWER_UNIT_IS_MW else 'kW oder W (Überprüfung nötig!)'}")

    start_datetime = datetime.datetime(TARGET_YEAR, TARGET_MONTH, TARGET_DAY, 0, 0, 0)
    end_datetime = datetime.datetime(TARGET_YEAR, TARGET_MONTH, TARGET_DAY, 23, 59, 59)

    try:
        # Lade Daten für den spezifischen Tag und das Gerät
        # group=True verwendet den group_map in lastprofile.py.
        # Wenn deine JASM-CSV-Spalte direkt "Geschirrspüler" heißt und du kein Mapping brauchst,
        # könntest du group=False verwenden.
        df_appliance = load_appliances(
            appliances=[APPLIANCE_NAME],
            start=start_datetime,
            end=end_datetime,
            year=TARGET_YEAR, # year Parameter ist in deinem loader für load_range/load_appliances optional, aber hier explizit
            group=True # Annahme: group_map in lastprofile.py ist für "Geschirrspüler" konfiguriert
        )
    except FileNotFoundError:
        print(f"FEHLER: Datendatei für {TARGET_YEAR}-{TARGET_MONTH:02d}.csv nicht im erwarteten Pfad gefunden.")
        print(f"Erwarteter Basispfad für Lastprofildaten: {PROJECT_ROOT / 'data/processed/lastprofile'}")
        return
    except Exception as e:
        print(f"FEHLER beim Laden der Lastprofildaten: {e}")
        return

    if df_appliance.empty:
        print(f"Keine Daten für '{APPLIANCE_NAME}' am Zieldatum gefunden.")
        return

    if APPLIANCE_NAME not in df_appliance.columns:
        print(f"FEHLER: Die Spalte '{APPLIANCE_NAME}' wurde nicht im geladenen DataFrame gefunden.")
        print(f"Verfügbare Spalten: {df_appliance.columns.tolist()}")
        print("Bitte überprüfe den APPLIANCE_NAME und die group_map Konfiguration in lastprofile.py.")
        return

    print(f"\nErste paar Zeilen der geladenen Daten für '{APPLIANCE_NAME}':")
    print(df_appliance.head())
    print(f"\nLetzte paar Zeilen der geladenen Daten für '{APPLIANCE_NAME}':")
    print(df_appliance.tail())
    print(f"Anzahl der Datenpunkte für den Tag: {len(df_appliance)}")

    # Energieberechnung
    # Energie = Leistung * Zeitintervall
    # Zeitintervall in Stunden:
    interval_duration_h = TIME_RESOLUTION_MINUTES / 60.0

    # Leistungswerte für das Gerät
    power_values = df_appliance[APPLIANCE_NAME]

    # Entferne mögliche NaNs, bevor summiert wird (obwohl Lastprofile selten NaNs haben sollten)
    power_values_cleaned = power_values.dropna()
    if power_values_cleaned.empty:
        print("Keine validen Leistungswerte nach Entfernung von NaNs vorhanden.")
        daily_energy_mwh = 0.0
    else:
        # Summe der (Leistung * Zeitintervall) über alle Zeitpunkte des Tages
        # Wenn POWER_UNIT_IS_MW True ist, ist das Ergebnis in MWh
        daily_energy_mwh = (power_values_cleaned * interval_duration_h).sum()

    # Umrechnung in kWh für bessere Lesbarkeit
    daily_energy_kwh = daily_energy_mwh * 1000 if POWER_UNIT_IS_MW else daily_energy_mwh # Falls es schon kWh wären

    print(f"\n--- Ergebnis der Verbrauchsanalyse für '{APPLIANCE_NAME}' am {TARGET_YEAR}-{TARGET_MONTH:02d}-{TARGET_DAY:02d} ---")
    if POWER_UNIT_IS_MW:
        print(f"Geschätzter Gesamtenergieverbrauch: {daily_energy_mwh:.6f} MWh")
        print(f"Das entspricht: {daily_energy_kwh:.3f} kWh")
    else:
        # Hier müsstest du die Logik anpassen, wenn die Einheit z.B. kW wäre
        # Dann wäre daily_energy_mwh eigentlich daily_energy_kwh
        print(f"Geschätzter Gesamtenergieverbrauch: {daily_energy_kwh:.3f} kWh (angenommen, Eingabe war kW)")


    if daily_energy_kwh > 0:
        avg_power_kw = daily_energy_kwh / 24 # Durchschnittliche Leistung über den Tag in kW
        print(f"Durchschnittliche Leistung über den Tag: {avg_power_kw:.3f} kW")
    
    # Plausibilitätscheck:
    # Ein typischer Geschirrspülgang braucht ca. 0.7 - 1.5 kWh.
    # Wenn der Wert stark davon abweicht, sind entweder die Annahmen (Einheit, Auflösung)
    # oder die Interpretation der JASM-Spalte ("Was repräsentiert 'Geschirrspüler'?) zu prüfen.
    print("\nZur Erinnerung: Ein typischer Geschirrspülgang verbraucht ca. 0.7 - 1.5 kWh.")
    print("Wenn der berechnete Tagesverbrauch sehr hoch oder niedrig ist, überprüfe bitte:")
    print(f"  1. Die angenommene Zeitauflösung der Daten (aktuell: {TIME_RESOLUTION_MINUTES} Min.).")
    print(f"  2. Die angenommene Einheit der Leistungswerte (aktuell Annahme: {'MW' if POWER_UNIT_IS_MW else 'kW/W'}).")
    print(f"  3. Was genau die Spalte '{APPLIANCE_NAME}' in den JASM-Daten repräsentiert (Last eines einzelnen Geräts, Durchschnittslast pro Haushalt etc.).")

if __name__ == "__main__":
    analyze_daily_consumption()
