# Skript/Code-Block zur Ermittlung von N_SURVEY_BASE_DISHWASHER_OWNERS_VALID_ANSWERS
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os # Importiere os für den Fallback

# --- Pfad-Setup (stelle sicher, dass es zu deiner Struktur passt) ---
try:
    # Wenn __file__ definiert ist (z.B. wenn dies Teil eines Skripts ist)
    CURRENT_SCRIPT_PATH = Path(__file__).resolve()
    # Annahme: Dieses Skript liegt in PowerE/src/analysis/
    # Daher drei .parent Aufrufe, um zum PowerE-Ordner (Projekt-Root) zu gelangen
    PROJECT_ROOT = CURRENT_SCRIPT_PATH.parent.parent.parent 
except NameError:
    # Fallback für interaktive Umgebungen oder wenn __file__ nicht verfügbar ist
    PROJECT_ROOT = Path(os.getcwd()).resolve() # Nimmt das aktuelle Arbeitsverzeichnis
    print(f"[WARNUNG] __file__ nicht definiert. PROJECT_ROOT als CWD angenommen: {PROJECT_ROOT}")
    print(f"           Stelle sicher, dass dies der Projekt-Root 'PowerE' ist, wenn das Skript interaktiv ausgeführt wird.")

# Füge den Projekt-Root und das src-Verzeichnis zum sys.path hinzu,
# damit Module aus src (wie 'logic' oder 'data_loader') gefunden werden können.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    print(f"[Path Setup] Projekt-Root '{PROJECT_ROOT}' zum sys.path hinzugefügt.")

# Das src-Verzeichnis sollte relativ zum PROJECT_ROOT sein.
# Wenn PROJECT_ROOT = PowerE/, dann ist der Pfad zu den Modulen src/logic/...
# Daher muss PowerE/src/ im sys.path sein, damit 'from logic...' funktioniert.
# Oder, wenn PROJECT_ROOT bereits PowerE/ ist, dann ist der Import 'from src.logic...'.
# Da wir 'from logic...' haben, muss ein Verzeichnis im sys.path liegen, das 'logic' direkt enthält.
# Das ist typischerweise das 'src'-Verzeichnis.
SRC_DIR_PATH = PROJECT_ROOT / "src"
if str(SRC_DIR_PATH) not in sys.path:
     sys.path.insert(0, str(SRC_DIR_PATH))
     print(f"[Path Setup] Quellverzeichnis '{SRC_DIR_PATH}' zum sys.path hinzugefügt.")


try:
    # Der Import geht davon aus, dass 'logic' ein Top-Level-Paket im 'src'-Verzeichnis ist.
    from logic.respondent_level_model.flexibility_potential.a_survey_data_preparer import prepare_survey_flexibility_data
    print("Funktion 'prepare_survey_flexibility_data' erfolgreich importiert.")
except ImportError as e:
    print(f"FEHLER beim Importieren von 'prepare_survey_flexibility_data': {e}")
    print(f"Aktueller sys.path: {sys.path}")
    print(f"PROJECT_ROOT wurde gesetzt auf: {PROJECT_ROOT}")
    print(f"SRC_DIR_PATH wurde gesetzt auf: {SRC_DIR_PATH}")
    print("Stelle sicher, dass:")
    print("  1. Der PROJECT_ROOT korrekt auf das Hauptverzeichnis 'PowerE' zeigt.")
    print("  2. Die Verzeichnisstruktur 'PowerE/src/logic/respondent_level_model/flexibility_potential/a_survey_data_preparer.py' existiert.")
    print("  3. Die Verzeichnisse 'logic', 'respondent_level_model' und 'flexibility_potential' (innerhalb von 'src') jeweils eine (ggf. leere) '__init__.py'-Datei enthalten, um als Pakete erkannt zu werden.")
    sys.exit(1)

def get_n_survey_base_for_appliance(appliance_name: str) -> int:
    """
    Ermittelt die Anzahl der Umfrageteilnehmer, die den spezifizierten appliance_name besitzen
    und sowohl für Frage 9 (Dauer) als auch für Frage 10 (Anreiz) eine valide,
    verwertbare Antwort gegeben haben.
    """
    print(f"\nErmittle Basispopulation für Gerät: {appliance_name}...")
    
    try:
        df_survey_flex = prepare_survey_flexibility_data()
        if df_survey_flex.empty:
            print(f"WARNUNG: Aufbereitete Umfragedaten (df_survey_flex) sind leer. N_survey_base wird 0 sein.")
            return 0
    except Exception as e:
        print(f"FEHLER beim Laden/Vorbereiten der Umfragedaten mit prepare_survey_flexibility_data: {e}")
        return 0

    # Filtere für das spezifische Gerät
    df_device_specific = df_survey_flex[df_survey_flex['device'] == appliance_name].copy()

    if df_device_specific.empty:
        print(f"Keine Einträge für Gerät '{appliance_name}' im df_survey_flex gefunden.")
        return 0
        
    # Bedingungen für valide Antworten:
    # 1. survey_max_duration_h (aus Q9) darf nicht NaN sein.
    # 2. survey_incentive_choice (aus Q10) muss eine der validen gemappten Kategorien sein
    #    (d.h. nicht 'unknown_choice' oder 'unknown_choice_q10_missing' oder NaN).
    
    valid_q9_condition = df_device_specific['survey_max_duration_h'].notna()
    
    valid_q10_choices = ['yes_fixed', 'yes_conditional', 'no']
    valid_q10_condition = df_device_specific['survey_incentive_choice'].isin(valid_q10_choices)
    
    # Kombiniere die Bedingungen: Teilnehmer muss für dieses Gerät valide Q9 UND valide Q10 Antworten haben
    df_valid_respondents_for_device = df_device_specific[valid_q9_condition & valid_q10_condition]
    
    # Zähle die Anzahl der eindeutigen respondent_ids, die diese Kriterien erfüllen
    n_base = df_valid_respondents_for_device['respondent_id'].nunique()
    
    print(f"Anzahl Teilnehmer mit validen Q9 UND Q10 Antworten für '{appliance_name}': {n_base}")
    return n_base

if __name__ == "__main__":
    # Beispielhafter Aufruf für Geschirrspüler
    APPLIANCE_TO_CHECK = "Geschirrspüler"
    N_SURVEY_BASE = get_n_survey_base_for_appliance(APPLIANCE_TO_CHECK)
    
    print(f"\n>>> Der Wert für N_SURVEY_BASE_{APPLIANCE_TO_CHECK.upper().replace(' ', '_')}_OWNERS_VALID_ANSWERS ist: {N_SURVEY_BASE} <<<")
    
    # Du kannst diesen Wert dann in dein Hauptanalyse-Skript (evaluate_srl_dishwasher_potential.py)
    # für die Variable N_SURVEY_BASE_DISHWASHER_OWNERS_VALID_ANSWERS einsetzen.
    # Oder du integrierst die Funktion get_n_survey_base_for_appliance direkt dort.

