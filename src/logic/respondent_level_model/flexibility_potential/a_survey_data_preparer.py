# PowerE/src/logic/respondent_level_model/flexibility_potential/a_survey_data_preparer.py
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os # Importiere os, falls du es im except NameError Block verwendest

# --- BEGINN: Robuster Pfad-Setup für Standalone-Ausführung und Modul-Import ---
try:
    CURRENT_SCRIPT_PATH = Path(__file__).resolve()
    # Korrektur: Fünf .parent Aufrufe, um zum PowerE-Ordner zu gelangen
    PROJECT_ROOT = CURRENT_SCRIPT_PATH.parent.parent.parent.parent.parent 
except NameError:
    # Fallback, falls __file__ nicht definiert ist.
    # Dieser Block sollte bei direkter Skriptausführung nicht erreicht werden.
    PROJECT_ROOT = Path(os.getcwd()).resolve() 
    print(f"[WARNUNG] __file__ nicht definiert. PROJECT_ROOT als aktuelles Arbeitsverzeichnis angenommen: {PROJECT_ROOT}")
    # Wenn dieser Fall eintritt, musst du sicherstellen, dass du das Skript vom PowerE-Ordner aus startest.

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    print(f"[Path Setup] Projekt-Root '{PROJECT_ROOT}' zum sys.path hinzugefügt.")
else:
    print(f"[Path Setup] Projekt-Root '{PROJECT_ROOT}' ist bereits im sys.path.")
# --- ENDE: Robuster Pfad-Setup ---

# Importiere deine existierenden Loader für Q9 und Q10
# Diese sollten jetzt gefunden werden.
from src.data_loader.survey_loader.nonuse2_loader import load_q9_nonuse_long
from src.data_loader.survey_loader.incentive2_loader import load_q10_incentives_long



def prepare_survey_flexibility_data() -> pd.DataFrame:
    """
    Lädt und transformiert die Umfragedaten zu Q9 (Nichtnutzungsdauer) und 
    Q10 (Anreizbedingungen) und führt sie zu einem DataFrame zusammen.
    Verwendet das überarbeitete Q9-Mapping.

    Output Spalten (Beispielnamen, können angepasst werden):
        - respondent_id (str)
        - device (str)
        - survey_max_duration_h (float): Numerische Dauer aus Q9.
        - survey_incentive_choice (str): 'yes_fixed', 'yes_conditional', 'no', 'unknown_choice'.
        - survey_incentive_pct_required (float): Numerischer Prozentwert für Kompensation.
                                                  0.0 für 'yes_fixed'. NaN wenn nicht anwendbar/nicht gegeben.
    """
    print("[INFO] prepare_survey_flexibility_data: Starte Aufbereitung der Flexibilitätsdaten aus Umfrage...")

    # 1. Frage 9 Daten laden und verarbeiten (Dauer)
    print("[INFO] Lade und verarbeite Q9 Daten (Dauer)...")
    df_q9_long_loaded = pd.DataFrame() 
    try:
        df_q9_long_loaded = load_q9_nonuse_long()
    except FileNotFoundError as e:
        print(f"[FEHLER] Q9 Rohdatendatei nicht gefunden: {e}.")
        # Option: Leeren DataFrame mit erwarteten Spalten zurückgeben oder Fehler werfen
    
    if df_q9_long_loaded.empty:
        print("[WARNUNG] Q9-Daten sind leer oder konnten nicht geladen werden.")
        # Erstelle einen leeren DataFrame mit den erwarteten Spalten, damit der Merge nicht fehlschlägt
        df_q9_processed = pd.DataFrame(columns=['respondent_id', 'device', 'survey_max_duration_h'])
    else:
        # Dein überarbeitetes q9_duration_mapping
        q9_duration_mapping = {
            "Nein, auf keinen Fall": 0.0,
            "Ja, aber maximal für 3 Stunden": 1.5,
            "Ja, für 3 bis 6 Stunden": 4.5,
            "Ja, für 6 bis 12 Stunden": 9.0,
            "Ja, für maximal 24 Stunden": 24.0,
            "Ja, für mehr als 24 Stunden": 30.0
        }
        df_q9_long_loaded['survey_max_duration_h'] = df_q9_long_loaded['q9_duration_text'].map(q9_duration_mapping)
        df_q9_long_loaded['survey_max_duration_h'] = pd.to_numeric(df_q9_long_loaded['survey_max_duration_h'], errors='coerce')
        df_q9_processed = df_q9_long_loaded[['respondent_id', 'device', 'survey_max_duration_h']].copy()
    print(f"  Q9-Daten verarbeitet. Shape: {df_q9_processed.shape}")

    # 2. Frage 10 Daten laden und verarbeiten (Anreiz)
    print("\n[INFO] Lade und verarbeite Q10 Daten (Anreiz)...")
    df_q10_long_loaded = pd.DataFrame() 
    try:
        df_q10_long_loaded = load_q10_incentives_long()
    except FileNotFoundError as e:
        print(f"[FEHLER] Q10 Rohdatendatei nicht gefunden: {e}.")

    if df_q10_long_loaded.empty:
        print("[WARNUNG] Q10-Daten sind leer oder konnten nicht geladen werden.")
        df_q10_processed = pd.DataFrame(columns=['respondent_id', 'device', 'survey_incentive_choice', 'survey_incentive_pct_required'])
    else:
        q10_choice_mapping = {
            "Ja, f": "yes_fixed",
            "Ja, +": "yes_conditional",
            "Nein": "no"
        }
        df_q10_long_loaded['survey_incentive_choice'] = df_q10_long_loaded['q10_choice_text'].map(q10_choice_mapping)
        df_q10_long_loaded['survey_incentive_choice'] = df_q10_long_loaded['survey_incentive_choice'].fillna('unknown_choice')

        df_q10_long_loaded['q10_pct_required_text'] = \
            df_q10_long_loaded['q10_pct_required_text'].str.replace('%', '', regex=False).str.strip()
        df_q10_long_loaded['survey_incentive_pct_required'] = \
            pd.to_numeric(df_q10_long_loaded['q10_pct_required_text'], errors='coerce')

        mask_yes_fixed = df_q10_long_loaded['survey_incentive_choice'] == 'yes_fixed'
        df_q10_long_loaded.loc[mask_yes_fixed, 'survey_incentive_pct_required'] = 0.0

        df_q10_processed = df_q10_long_loaded[['respondent_id', 'device', 'survey_incentive_choice', 'survey_incentive_pct_required']].copy()
    print(f"  Q10-Daten verarbeitet. Shape: {df_q10_processed.shape}")

    # 3. Verarbeitete Q9 und Q10 Daten zusammenführen
    print("\n[INFO] Führe Q9 und Q10 Daten zusammen...")
    if df_q9_processed.empty and df_q10_processed.empty:
        print("[WARNUNG] Sowohl Q9 als auch Q10 Daten sind leer. Gebe leeren DataFrame zurück.")
        return pd.DataFrame(columns=['respondent_id', 'device', 'survey_max_duration_h', 'survey_incentive_choice', 'survey_incentive_pct_required'])
    
    # Outer Merge, um alle Teilnehmer und Geräte zu behalten, auch wenn eine Frage fehlt
    df_survey_flexibility = pd.merge(
        df_q9_processed,
        df_q10_processed,
        on=['respondent_id', 'device'],
        how='outer' # Wichtig, um alle Daten zu behalten
    )
    print(f"  Q9 und Q10 Daten gemerged. Shape vor finaler Bereinigung: {df_survey_flexibility.shape}")

    # Finale Bereinigungen und Überprüfungen
    # Fehlende 'survey_incentive_choice' nach dem Merge füllen (falls eine Zeile nur aus Q9 kam)
    if 'survey_incentive_choice' in df_survey_flexibility.columns:
        df_survey_flexibility['survey_incentive_choice'] = df_survey_flexibility['survey_incentive_choice'].fillna('unknown_choice_q10_missing')
    else: # Falls Q10 komplett leer war
        df_survey_flexibility['survey_incentive_choice'] = 'unknown_choice_q10_missing'
        df_survey_flexibility['survey_incentive_pct_required'] = np.nan


    # Sicherstellen, dass respondent_id und device nicht NaN sind (sollte durch Loader schon erledigt sein)
    df_survey_flexibility.dropna(subset=['respondent_id', 'device'], inplace=True)
    
    # Typkonvertierungen für die numerischen Spalten sicherstellen
    if 'survey_max_duration_h' in df_survey_flexibility.columns:
        df_survey_flexibility['survey_max_duration_h'] = pd.to_numeric(df_survey_flexibility['survey_max_duration_h'], errors='coerce')
    else: # Falls Q9 komplett leer war
        df_survey_flexibility['survey_max_duration_h'] = np.nan

    if 'survey_incentive_pct_required' in df_survey_flexibility.columns:
        df_survey_flexibility['survey_incentive_pct_required'] = pd.to_numeric(df_survey_flexibility['survey_incentive_pct_required'], errors='coerce')
    # Keine else-Bedingung für survey_incentive_pct_required nötig, da oben schon abgedeckt.

    # Spaltennamen standardisieren für den Output (optional, aber gute Praxis)
    final_columns = ['respondent_id', 'device', 'survey_max_duration_h', 
                     'survey_incentive_choice', 'survey_incentive_pct_required']
    df_survey_flexibility = df_survey_flexibility[final_columns]


    print(f"[INFO] prepare_survey_flexibility_data: Finale Daten aufbereitet. Shape: {df_survey_flexibility.shape}")
    return df_survey_flexibility

if __name__ == '__main__':
    # Kleiner Trick, um den PROJECT_ROOT zu finden, wenn das Skript direkt ausgeführt wird.
    # Annahme: Dieses Skript ist in PowerE/src/logic/respondent_level_model/flexibility_potential/
    current_script_path = Path(__file__).resolve()
    project_root_for_test = current_script_path.parent.parent.parent.parent # PowerE Ordner
    
    # Stelle sicher, dass der Projekt-Root im sys.path ist für die src-Importe
    if str(project_root_for_test) not in sys.path:
        sys.path.insert(0, str(project_root_for_test))
        print(f"Test-Modus: '{project_root_for_test}' zu sys.path hinzugefügt für standalone Ausführung.")
    
    # Erneuter Versuch, die Loader zu importieren, falls der erste try-except Block oben im Skript
    # nicht erfolgreich war, weil das Skript standalone ausgeführt wird.
    try:
        from src.data_loader.survey_loader.nonuse2_loader import load_q9_nonuse_long
        from src.data_loader.survey_loader.incentive2_loader import load_q10_incentives_long
    except ImportError as e:
        print(f"Fehler beim Nachladen der Loader im Testblock: {e}. Stelle sicher, dass der Pfad korrekt ist.")
        # Hier ggf. sys.exit(), wenn die Loader kritisch sind.

    print("\n--- Starte Testlauf für a_survey_data_preparer.py ---")
    try:
        df_prepared_data = prepare_survey_flexibility_data() # df_prepared_data wird HIER definiert
        
        if not df_prepared_data.empty:
            print("\nErste 5 Zeilen des aufbereiteten DataFrames:")
            print(df_prepared_data.head())
            
            print(f"\nShape des aufbereiteten DataFrames: {df_prepared_data.shape}")
            print("\nInfos zum aufbereiteten DataFrame:")
            df_prepared_data.info()
            
            # ----- DIESE PRINT-ANWEISUNGEN WAREN DAS PROBLEM -> JETZT SIND SIE NACH DER DEFINITION -----
            print("\nValue Counts für 'survey_max_duration_h' (zeigt das neue Mapping):")
            print(df_prepared_data['survey_max_duration_h'].value_counts(dropna=False).sort_index())
            
            print("\nValue Counts für 'survey_incentive_choice':")
            print(df_prepared_data['survey_incentive_choice'].value_counts(dropna=False))
            
            print("\nDeskriptive Statistik für 'survey_incentive_pct_required':")
            print(df_prepared_data['survey_incentive_pct_required'].describe())

            # Beispielhafte Prüfung für Konsistenz:
            fixed_check = df_prepared_data[
                (df_prepared_data['survey_incentive_choice'] == 'yes_fixed') & \
                (df_prepared_data['survey_incentive_pct_required'] != 0.0)
            ]
            if not fixed_check.empty:
                print(f"\n[WARNUNG] {len(fixed_check)} Fälle, wo 'yes_fixed', aber survey_incentive_pct_required nicht 0.0 ist:")
                print(fixed_check)
            else:
                print("\n[INFO] Konsistenzcheck für 'yes_fixed' und survey_incentive_pct_required == 0.0 bestanden.")
        else:
            print("Aufbereiteter DataFrame ist leer.")

    except Exception as e:
        print(f"Ein Fehler ist im Testlauf aufgetreten: {e}")
        import traceback
        traceback.print_exc()
    print("\n--- Testlauf für a_survey_data_preparer.py beendet ---")