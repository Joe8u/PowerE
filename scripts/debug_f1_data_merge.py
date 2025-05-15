import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path # pathlib ist oft robuster für Pfade

# === ANFANG: Robuster Pfad-Setup ===
try:
    SCRIPT_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = SCRIPT_DIR.parent # Annahme: Skript liegt in PowerE/scripts/
    if SCRIPT_DIR.name == "F1_Analyse_Kompensationsforderungen": # Falls es im Unterordner liegt
        PROJECT_ROOT = SCRIPT_DIR.parent.parent
except NameError: # Falls __file__ nicht definiert ist (z.B. in manchen interaktiven Umgebungen)
    # Versuche es relativ zum aktuellen Arbeitsverzeichnis
    PROJECT_ROOT = Path(os.getcwd()).resolve()
    # Stelle sicher, dass PROJECT_ROOT wirklich auf PowerE/ zeigt, ggf. anpassen:
    # if PROJECT_ROOT.name != "PowerE":
    # PROJECT_ROOT = PROJECT_ROOT.parent # Beispiel, falls CWD ein Unterordner von PowerE ist

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    print(f"Added project root '{PROJECT_ROOT}' to sys.path")

print(f"PROJECT_ROOT wurde gesetzt auf: {PROJECT_ROOT}")
# === ENDE: Robuster Pfad-Setup ===

# --- Importe deiner Module ---
try:
    from src.logic.respondent_level_model.data_transformer import create_respondent_flexibility_df
    from src.data_loader.survey_loader.demographics import load_demographics
    from src.data_loader.survey_loader.socioeconomics import load_socioeconomics
    # Für Q8, Q11, Q12 verwenden wir hier direktes CSV-Laden, da die Loader-Struktur
    # in demand_response.py ggf. noch angepasst werden müsste oder für ein schnelles Debugging so einfacher ist.
    print("Alle benötigten Module aus 'src' erfolgreich importiert (oder werden nicht direkt für Debug gebraucht).")
except ImportError as e:
    print(f"FEHLER beim Importieren von Modulen aus 'src': {e}")
    sys.exit(1)
except Exception as e:
    print(f"Ein unerwarteter Fehler beim Importieren ist aufgetreten: {e}")
    sys.exit(1)

def run_debug_analysis():
    print("\nStarte Debug-Analyse für F1 Daten-Merge...")

    # --- Lade df_respondent_flexibility (Q9 & Q10 kombiniert) ---
    print("\nLade df_respondent_flexibility...")
    df_flex = pd.DataFrame() # Initialisiere als leerer DataFrame
    try:
        df_flex = create_respondent_flexibility_df()
        print(f"df_flexibility geladen. Shape: {df_flex.shape}")
        if df_flex.empty:
            print("WARNUNG: df_flexibility ist leer!")
        else:
            if 'respondent_id' in df_flex.columns:
                df_flex['respondent_id'] = df_flex['respondent_id'].astype(str)
                print(f"  'respondent_id' in df_flex dtype: {df_flex['respondent_id'].dtype}, unique: {df_flex['respondent_id'].nunique()}")
            else:
                print("  WARNUNG: 'respondent_id' fehlt in df_flex!")
    except Exception as e:
        print(f"  FEHLER beim Erstellen von df_flexibility: {e}")

    # --- Lade einzelne soziodemografische und andere Umfragedaten ---
    data_to_load_and_check = []

    # Q1-Q5 (Demographics)
    print("\nLade Demographics (Q1-Q5)...")
    try:
        demographics_dfs_dict = load_demographics()
        if 'age' in demographics_dfs_dict:
            data_to_load_and_check.append({'name': "df_age (Q1)", 'df': demographics_dfs_dict['age'], 'cols_to_check': ['age']})
        else:
            print("  WARNUNG: 'age' DataFrame nicht im demographics_dfs_dict gefunden.")
        # Füge hier bei Bedarf weitere DataFrames aus demographics_dfs_dict hinzu, wenn du sie prüfen willst
        # z.B. data_to_load_and_check.append({'name': "df_gender (Q2)", 'df': demographics_dfs_dict['gender'], 'cols_to_check': ['gender']})

    except Exception as e:
        print(f"  FEHLER beim Laden von Demographics: {e}")

    # Q13-Q15 (Socioeconomics)
    print("\nLade Socioeconomics (Q13-Q15)...")
    try:
        socioeconomics_dfs_dict = load_socioeconomics()
        if 'income' in socioeconomics_dfs_dict:
            # Dein preprocess_q13_income.py speichert die Spalte als 'q13_income'
            data_to_load_and_check.append({'name': "df_income (Q13)", 'df': socioeconomics_dfs_dict['income'], 'cols_to_check': ['q13_income']})
        else:
            print("  WARNUNG: 'income' DataFrame nicht im socioeconomics_dfs_dict gefunden.")
    except Exception as e:
        print(f"  FEHLER beim Laden von Socioeconomics: {e}")

    # Q12 (Smart Plug) - Direkter CSV-Ladevorgang
    print("\nLade Q12 (Smart Plug)...")
    q12_filename = PROJECT_ROOT / "data" / "processed" / "survey" / "question_12_smartplug.csv"
    try:
        df_q12 = pd.read_csv(q12_filename, dtype={'respondent_id': str}) # Lese respondent_id direkt als String
        # Dein preprocess_q12_smartplug.py speichert die Spalte als 'q12_smartplug'
        data_to_load_and_check.append({'name': "df_q12_smartplug", 'df': df_q12, 'cols_to_check': ['q12_smartplug']})
    except FileNotFoundError:
        print(f"  FEHLER: Datei nicht gefunden: {q12_filename}")
        data_to_load_and_check.append({'name': "df_q12_smartplug", 'df': pd.DataFrame(), 'cols_to_check': ['q12_smartplug']}) # Füge leeren DF hinzu, um spätere Schleife nicht zu brechen
    except Exception as e:
        print(f"  FEHLER beim Laden von {q12_filename}: {e}")
        data_to_load_and_check.append({'name': "df_q12_smartplug", 'df': pd.DataFrame(), 'cols_to_check': ['q12_smartplug']})


    # === DEBUG-BLOCK 1: Zustand der einzelnen DataFrames VOR dem Mergen ===
    print("\n\n--- DEBUGGING: Zustand der einzelnen DataFrames VOR dem Mergen ---")
    all_loaded_dfs_for_merge = []
    if not df_flex.empty:
        all_loaded_dfs_for_merge.append(df_flex.copy()) # Starte mit einer Kopie von df_flex

    for item in data_to_load_and_check:
        df_current = item['df']
        print(f"\n--- {item['name']} ---")
        if not df_current.empty:
            print(f"  Shape: {df_current.shape}")
            print(f"  Columns: {df_current.columns.tolist()}")
            if 'respondent_id' in df_current.columns:
                df_current['respondent_id'] = df_current['respondent_id'].astype(str) # Stelle sicher, dass es String ist
                print(f"  respondent_id dtype: {df_current['respondent_id'].dtype}, unique: {df_current['respondent_id'].nunique()}")
                if df_current['respondent_id'].nunique() > 0:
                     print(f"    Beispiel respondent_ids: {df_current['respondent_id'].unique()[:3]}")
                all_loaded_dfs_for_merge.append(df_current) # Füge zur Liste für den Merge hinzu
            else:
                print("  WARNUNG: 'respondent_id' fehlt!")
            
            for col_check in item['cols_to_check']:
                if col_check in df_current.columns:
                    print(f"  Spalte '{col_check}': Nicht-Null-Werte={df_current[col_check].notna().sum()}, dtype={df_current[col_check].dtype}")
                else:
                    print(f"  WARNUNG: Spalte '{col_check}' fehlt!")
        else:
            print("  DataFrame ist leer.")

    # === Merge-Prozess ===
    print("\n\n--- Starte Merge-Prozess zu master_df ---")
    master_df = pd.DataFrame()
    if all_loaded_dfs_for_merge:
        master_df = all_loaded_dfs_for_merge[0] # Starte mit df_flex
        for i, df_to_merge in enumerate(all_loaded_dfs_for_merge[1:]):
            df_name_for_suffix = data_to_load_and_check[i]['name'].replace("df_", "").replace(" (Q", "_q").replace(")", "") # Erzeuge Suffix aus Namen
            print(f"  Merging mit DataFrame #{i+1} (ursprünglich '{data_to_load_and_check[i]['name']}')")
            if 'respondent_id' in df_to_merge.columns and not df_to_merge.empty:
                master_df = pd.merge(master_df, df_to_merge, on="respondent_id", how="left", suffixes=('', f'_{df_name_for_suffix}'))
            else:
                print(f"    Überspringe Merge für DataFrame #{i+1}, da 'respondent_id' fehlt oder DF leer ist.")
    else:
        print("Keine DataFrames zum Mergen vorhanden (df_flex ist wahrscheinlich leer).")


    # === DEBUG-BLOCK 2: Zustand des master_df NACH dem Mergen ===
    print("\n\n--- DEBUGGING: Zustand des master_df NACH dem Mergen ---")
    if not master_df.empty:
        print(f"Shape von master_df: {master_df.shape}")
        print("\nAlle Spalten in master_df:")
        print(master_df.columns.tolist())
        
        print("\nInfo zu master_df (zeigt Datentypen und Nicht-Null-Werte):")
        master_df.info(verbose=True, show_counts=True) # Ausführlichere Info

        if 'respondent_id' in master_df.columns:
            print(f"\nUnique respondent_ids in master_df: {master_df['respondent_id'].nunique()}")
        else:
            print("WARNUNG: 'respondent_id' fehlt im finalen master_df!")


        print("\nÜberprüfung der spezifisch interessierenden Spalten in master_df:")
        cols_of_interest = ['age', 'q13_income', 'q12_smartplug'] # Füge hier ggf. weitere hinzu, die du erwartest
        for col_to_check in cols_of_interest:
            if col_to_check in master_df.columns:
                print(f"Spalte '{col_to_check}': Vorhanden, dtype={master_df[col_to_check].dtype}, Nicht-Null-Werte={master_df[col_to_check].notna().sum()}")
                if master_df[col_to_check].notna().sum() > 0:
                    sample_values = master_df[col_to_check].dropna().unique()
                    print(f"    Beispielwerte für '{col_to_check}': {sample_values[:min(5, len(sample_values))]}")
                else:
                    print(f"    WARNUNG: Spalte '{col_to_check}' hat nur Null-Werte (NaNs).")
            else:
                print(f"FEHLER: Spalte '{col_to_check}' fehlt in master_df!")
                # Suche nach ähnlichen Spalten, falls Suffixe hinzugefügt wurden
                similar_cols = [col for col in master_df.columns if col_to_check in col]
                if similar_cols:
                    print(f"    Mögliche alternative Spalten (durch Merge-Suffixe?): {similar_cols}")

    else:
        print("master_df ist leer nach dem Mergen.")

    print("\n--- Debug-Analyse beendet ---")

if __name__ == "__main__":
    run_debug_analysis()