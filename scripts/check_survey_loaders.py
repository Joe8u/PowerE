# PowerE/scripts/check_survey_loaders.py

import pandas as pd
import os
import sys
from pathlib import Path

# === ANFANG: Robuster Pfad-Setup ===
# Dieser Block ist wichtig, damit das Skript die Module in src findet
try:
    SCRIPT_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = SCRIPT_DIR.parent
except NameError:
    PROJECT_ROOT = Path(os.getcwd()).resolve()
    if PROJECT_ROOT.name == "scripts": PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    print(f"Added project root '{PROJECT_ROOT}' to sys.path")
print(f"PROJECT_ROOT wurde gesetzt auf: {PROJECT_ROOT}")
# === ENDE: Robuster Pfad-Setup ===

# === Importiere Module aus src ===
print("\nImportiere Module aus src...")
try:
    from src.logic.respondent_level_model.data_transformer import create_respondent_flexibility_df
    from src.data_loader.survey_loader.demographics import load_demographics
    from src.data_loader.survey_loader.attitudes import load_attitudes
    from src.data_loader.survey_loader.demand_response import (
        load_importance, load_notification, load_smart_plug
    )
    from src.data_loader.survey_loader.socioeconomics import load_socioeconomics
    print("Alle benötigten Loader-Funktionen erfolgreich importiert.")
except ImportError as e:
    print(f"FEHLER beim Importieren von Modulen aus 'src': {e}")
    sys.exit(1)
except Exception as e:
    print(f"Ein unerwarteter Fehler beim Importieren ist aufgetreten: {e}")
    sys.exit(1)

# === Hilfsfunktion ===
def print_df_preview(df_name: str, df: pd.DataFrame):
    print(f"\n--- Vorschau für: {df_name} ---")
    if df is not None and not df.empty:
        print(f"Shape: {df.shape}")
        if 'respondent_id' in df.columns:
            try:
                df_resp_id_str = df['respondent_id'].astype(str)
                print(f"  respondent_id (als str) dtype: {df_resp_id_str.dtype}, unique count: {df_resp_id_str.nunique()}")
                unique_ids_sample = df_resp_id_str.dropna().unique()
                print(f"    Beispiel respondent_ids: {unique_ids_sample[:min(3, len(unique_ids_sample))]}")
            except Exception as e:
                print(f"    Fehler bei der Analyse von respondent_id: {e}")
        else:
            print("  WARNUNG: Spalte 'respondent_id' nicht im DataFrame vorhanden.")
        print("Erste 5 Zeilen (Head):")
        print(df.head())
    elif df is not None and df.empty: print("DataFrame ist leer.")
    else: print("DataFrame konnte nicht geladen werden (ist None).")

def run_loader_checks(project_root_to_pass: Path): # Akzeptiere den PROJECT_ROOT als Parameter
    print("\nStarte Überprüfung der Survey-Datenlader...")

    # Teste create_respondent_flexibility_df (Q9 & Q10)
    # Diese Funktion muss ggf. AUCH angepasst werden, um project_root_to_pass
    # an ihre internen Loader (nonuse2_loader, incentive2_loader) weiterzugeben,
    # FALLS diese es benötigen. Aktuell scheint es ohne zu funktionieren, was bedeutet,
    # dass nonuse2_loader und incentive2_loader ihre Pfade intern korrekt finden.
    # Das ist erstmal okay so.
    print("\nTeste create_respondent_flexibility_df (für Q9 & Q10)...")
    try:
        df_flex = create_respondent_flexibility_df()
        print_df_preview("df_flexibility (kombiniert Q9 & Q10)", df_flex)
    except Exception as e:
        print(f"FEHLER beim Erstellen von df_flexibility: {e}")

    print("\nTeste Demographics Loader (Q1-Q5)...")
    try:
        # Hier wird project_root_to_pass übergeben!
        demographics_data_dict = load_demographics(project_root_to_pass)
        for key, df_demo in demographics_data_dict.items():
            print_df_preview(f"Demographics - {key}", df_demo)
    except Exception as e:
        print(f"FEHLER beim Laden von Demographics: {e}")

    print("\nTeste Attitudes Loader (Q6-Q7)...")
    try:
        # Hier wird project_root_to_pass übergeben!
        attitudes_data_dict = load_attitudes(project_root_to_pass)
        for key, df_att in attitudes_data_dict.items():
            print_df_preview(f"Attitudes - {key}", df_att)
    except Exception as e:
        print(f"FEHLER beim Laden von Attitudes: {e}")

    print("\nTeste Demand Response Loader (Teile)...")
    try:
        # Hier wird project_root_to_pass übergeben!
        df_q8 = load_importance(project_root_to_pass)
        print_df_preview("Q8 Importance", df_q8)
    except Exception as e:
        print(f"FEHLER beim Laden von Q8 Importance: {e}")
    
    try:
        # Hier wird project_root_to_pass übergeben!
        df_q11 = load_notification(project_root_to_pass)
        print_df_preview("Q11 Notification", df_q11)
    except Exception as e:
        print(f"FEHLER beim Laden von Q11 Notification: {e}")

    try:
        # Hier wird project_root_to_pass übergeben!
        df_q12 = load_smart_plug(project_root_to_pass)
        print_df_preview("Q12 Smart Plug", df_q12)
    except Exception as e:
        print(f"FEHLER beim Laden von Q12 Smart Plug: {e}")

    print("\nTeste Socioeconomics Loader (Q13-Q15)...")
    try:
        # Hier wird project_root_to_pass übergeben!
        socioeconomics_data_dict = load_socioeconomics(project_root_to_pass)
        for key, df_socio in socioeconomics_data_dict.items():
            print_df_preview(f"Socioeconomics - {key}", df_socio)
    except Exception as e:
        print(f"FEHLER beim Laden von Socioeconomics: {e}")

    print("\n--- Überprüfung der Survey-Datenlader beendet ---")

if __name__ == "__main__":
    # PROJECT_ROOT wird oben im Skript global definiert.
    # Wir übergeben es jetzt an run_loader_checks.
    run_loader_checks(PROJECT_ROOT)