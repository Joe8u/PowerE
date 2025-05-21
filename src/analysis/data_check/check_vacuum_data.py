# PowerE/src/analysis/data_check/check_vacuum_data.py

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os

# --- 1. Projekt-Setup ---
def setup_project_root() -> Path:
    """Bestimmt den Projekt-Root und fügt ihn zum sys.path hinzu."""
    try:
        # Annahme: Dieses Skript liegt in PowerE/src/analysis/data_check/
        # Der Projekt-Root "PowerE" ist drei Ebenen höher.
        script_path = Path(__file__).resolve()
        project_root = script_path.parent.parent.parent.parent
    except NameError:
        # Fallback, wenn __file__ nicht verfügbar ist (z.B. interaktive Ausführung)
        # Gehe vom aktuellen Arbeitsverzeichnis aus, dass es PowerE ist oder ein Unterordner
        print("Hinweis: __file__ nicht verfügbar. Versuche Projekt-Root vom aktuellen Arbeitsverzeichnis zu bestimmen.")
        current_dir = Path(os.getcwd()).resolve()
        # Suche nach "PowerE" im Pfad
        if current_dir.name == "PowerE":
            project_root = current_dir
        elif (current_dir.parent.name == "PowerE"):
            project_root = current_dir.parent
        elif (current_dir.parent.parent.name == "PowerE"):
            project_root = current_dir.parent.parent
        else:
            # Fallback: Annahme, dass das Skript manuell im Projekt-Root oder einem bekannten Unterverzeichnis ausgeführt wird.
            # Du musst diesen Pfad ggf. manuell anpassen, wenn die Automatik fehlschlägt.
            project_root = Path(os.getcwd()).resolve() # Fallback auf cwd
            print(f"WARNUNG: Konnte Projekt-Root nicht sicher bestimmen. Verwende aktuelles Arbeitsverzeichnis: {project_root}")
            print("Stelle sicher, dass dies dein 'PowerE'-Verzeichnis ist.")

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        print(f"Projekt-Root '{project_root}' zum sys.path hinzugefügt.")
    else:
        print(f"Projekt-Root '{project_root}' ist bereits im sys.path.")
    return project_root

PROJECT_ROOT = setup_project_root()
print(f"Verwendeter Projekt-Root für diesen Check: {PROJECT_ROOT}")

# --- Importe deiner benutzerdefinierten Module ---
# Diese müssen nach dem Setup des sys.path erfolgen.
try:
    from src.logic.respondent_level_model.data_transformer import create_respondent_flexibility_df
    from src.data_loader.survey_loader.demand_response import load_importance
    # Weitere Imports, falls für einen vollständigeren master_df_f1 Check benötigt
    # from src.data_loader.survey_loader.demographics import load_demographics
    # from src.data_loader.survey_loader.attitudes import load_attitudes
    # from src.data_loader.survey_loader.socioeconomics import load_socioeconomics
    print("Benötigte Module erfolgreich importiert.")
except ImportError as e:
    print(f"FEHLER beim Importieren von Modulen aus 'src': {e}")
    print("Stelle sicher, dass der PROJECT_ROOT korrekt ist, alle __init__.py Dateien in 'src' und")
    print("dessen Unterordnern vorhanden sind und die Modulnamen exakt stimmen.")
    print("Das Skript wird möglicherweise nicht korrekt funktionieren.")
    sys.exit(1) # Beenden, wenn Kernmodule nicht geladen werden können
except Exception as e:
    print(f"Ein unerwarteter Fehler beim Importieren der Module ist aufgetreten: {e}")
    sys.exit(1)


# --- 2. Hilfsfunktionen für den Check ---
def print_data_check_header(title):
    print("\n" + "="*60)
    print(f"DATA-CHECK: {title}")
    print("="*60)

def check_device_in_df(df, df_name, device_name="Staubsauger",
                       columns_to_show=None, id_col='respondent_id',
                       print_all_devices=True):
    print(f"\n--- Prüfung für Gerät '{device_name}' in DataFrame '{df_name}' ---")
    if df is None or df.empty:
        print(f"INFO: DataFrame '{df_name}' ist leer oder None.")
        return False

    if 'device' not in df.columns:
        print(f"FEHLER: DataFrame '{df_name}' hat keine Spalte 'device'. Spalten: {df.columns.tolist()}")
        return False

    if print_all_devices:
        unique_devices = df['device'].unique()
        print(f"INFO: Einzigartige Geräte in '{df_name}': {unique_devices}")

    if device_name in df['device'].unique():
        print(f"ERFOLG: '{device_name}' ist als Gerät in '{df_name}' vorhanden.")
        df_device_subset = df[df['device'] == device_name].copy()
        print(f"  Anzahl Zeilen für '{device_name}': {len(df_device_subset)}")

        current_cols_to_show = []
        if id_col in df_device_subset.columns:
             current_cols_to_show.append(id_col)
        current_cols_to_show.append('device') # 'device' immer anzeigen

        if columns_to_show:
            for col in columns_to_show:
                if col in df_device_subset.columns and col not in current_cols_to_show:
                    current_cols_to_show.append(col)
        
        if not df_device_subset.empty:
            print(f"  Beispieldaten für '{device_name}' (Spalten: {current_cols_to_show}):")
            print(df_device_subset[current_cols_to_show].head())
        else: # Sollte nicht passieren, wenn device_name in unique_devices ist
            print(f"  HINWEIS: '{device_name}' wurde als unique gefunden, aber Subset ist leer. (Unerwartet)")
        return True
    else:
        print(f"WARNUNG: '{device_name}' NICHT als Gerät in '{df_name}' gefunden.")
        return False

# --- 3. Daten-Checks ---
def run_checks():
    print_data_check_header("Start der Datenüberprüfung für 'Staubsauger'")

    # --- Check 1: Q8 Wichtigkeit (load_importance und simulierter melt) ---
    print_data_check_header("1. Q8 (Wichtigkeit) Verarbeitung")
    df_q8_raw = None
    df_q8_long = None
    try:
        print("1a. Lade Rohdaten mit load_importance...")
        df_q8_raw = load_importance(PROJECT_ROOT) # Übergabe PROJECT_ROOT
        if df_q8_raw is not None and not df_q8_raw.empty:
            q8_raw_columns = df_q8_raw.columns.tolist()
            print(f"  Spalten in Rohdaten von load_importance: {q8_raw_columns}")
            if "Staubsauger" in q8_raw_columns:
                print("  ERFOLG: Spalte 'Staubsauger' in Rohdaten von load_importance vorhanden.")
                # print("    Beispielwerte für 'Staubsauger':")
                # print(df_q8_raw[['respondent_id', 'Staubsauger']].head())
            else:
                print("  WARNUNG: Spalte 'Staubsauger' NICHT in Rohdaten von load_importance gefunden.")
                print("    HINWEIS: Prüfe 'question_8_importance_wide.csv' und die `load_importance` Funktion.")
        else:
            print("  INFO: Rohdaten von load_importance (df_q8_raw) sind leer.")

        # Simuliere den Melt-Vorgang aus dem Hauptnotebook
        if df_q8_raw is not None and not df_q8_raw.empty and 'respondent_id' in df_q8_raw.columns:
            print("\n1b. Simuliere 'melt' Operation für Q8-Daten...")
            device_columns_q8 = [col for col in df_q8_raw.columns if col != 'respondent_id']
            if device_columns_q8:
                df_q8_long = df_q8_raw.melt(
                    id_vars=['respondent_id'],
                    value_vars=device_columns_q8,
                    var_name='device',
                    value_name='importance_rating' # Annahme basierend auf Notebook
                )
                # Konvertiere respondent_id und importance_rating wie im Notebook
                df_q8_long['respondent_id'] = df_q8_long['respondent_id'].astype(str)
                df_q8_long['importance_rating'] = pd.to_numeric(df_q8_long['importance_rating'], errors='coerce')

                print(f"  'df_q8_long' erstellt. Shape: {df_q8_long.shape}")
                check_device_in_df(df_q8_long, "df_q8_long (simuliert)",
                                   columns_to_show=['importance_rating'])
            else:
                print("  WARNUNG: Keine Gerätespalten in df_q8_raw für melt-Operation gefunden (außer respondent_id).")
        elif df_q8_raw is not None and not df_q8_raw.empty:
             print("  WARNUNG: 'respondent_id' nicht in df_q8_raw gefunden. Melt kann nicht durchgeführt werden.")

    except FileNotFoundError as e:
        print(f"  FEHLER bei Q8 Check (FileNotFoundError): {e}. Stelle sicher, dass die CSV-Datei existiert.")
    except Exception as e:
        print(f"  FEHLER bei Q8 Check: {e}")
        import traceback
        traceback.print_exc()


    # --- Check 2: df_flex (aus create_respondent_flexibility_df) ---
    print_data_check_header("2. df_flex (Q9/Q10 kombiniert)")
    df_flex = None
    try:
        print("Lade df_flex mit create_respondent_flexibility_df()...")
        # ANNAHME: create_respondent_flexibility_df benötigt PROJECT_ROOT oder findet es selbst.
        # Dein Notebook ruft es ohne Argument auf. Falls es PROJECT_ROOT braucht:
        # df_flex = create_respondent_flexibility_df(PROJECT_ROOT)
        df_flex = create_respondent_flexibility_df()

        if df_flex is not None and not df_flex.empty:
            print(f"  'df_flex' geladen. Shape: {df_flex.shape}")
            # Spaltenaufbereitung wie im Notebook (ggf. schon in create_respondent_flexibility_df passiert)
            if 'respondent_id' in df_flex.columns:
                df_flex['respondent_id'] = df_flex['respondent_id'].astype(str)

            columns_to_check_in_flex = []
            if 'max_duration_hours' in df_flex.columns: # Originalname aus create_respondent_flexibility_df
                df_flex.rename(columns={'max_duration_hours': 'max_duration_hours_num'}, inplace=True, errors='ignore')
                df_flex['max_duration_hours_num'] = pd.to_numeric(df_flex['max_duration_hours_num'], errors='coerce')
                columns_to_check_in_flex.append('max_duration_hours_num')
            elif 'max_duration_hours_num' in df_flex.columns: # Falls schon so benannt
                 df_flex['max_duration_hours_num'] = pd.to_numeric(df_flex['max_duration_hours_num'], errors='coerce')
                 columns_to_check_in_flex.append('max_duration_hours_num')


            if 'incentive_pct_required' in df_flex.columns: # Originalname
                df_flex.rename(columns={'incentive_pct_required': 'incentive_pct_required_num'}, inplace=True, errors='ignore')
                df_flex['incentive_pct_required_num'] = pd.to_numeric(df_flex['incentive_pct_required_num'], errors='coerce')
                columns_to_check_in_flex.append('incentive_pct_required_num')
            elif 'incentive_pct_required_num' in df_flex.columns: # Falls schon so benannt
                df_flex['incentive_pct_required_num'] = pd.to_numeric(df_flex['incentive_pct_required_num'], errors='coerce')
                columns_to_check_in_flex.append('incentive_pct_required_num')

            if 'incentive_choice' in df_flex.columns:
                 columns_to_check_in_flex.append('incentive_choice')

            staubsauger_in_df_flex = check_device_in_df(df_flex, "df_flex",
                                                      columns_to_show=columns_to_check_in_flex)
            if not staubsauger_in_df_flex:
                print("\n  KRITISCHER HINWEIS für df_flex:")
                print("  Wenn 'Staubsauger' hier fehlt, kann er im finalen DataFrame nicht korrekt mit Q8-Daten angereichert werden.")
                print("  Mögliche Ursachen und Lösungen:")
                print("  1. Die internen Ladefunktionen `load_q9_nonuse_long()` und `load_q10_incentives_long()`")
                print("     (aufgerufen in `create_respondent_flexibility_df`) liefern keine Daten für 'Staubsauger'")
                print("     oder verwenden einen anderen Gerätenamen.")
                print("     -> Überprüfe diese Ladefunktionen und die von ihnen gelesenen CSV-Dateien.")
                print("  2. Deine Q9/Q10-Umfrage hat den Staubsauger nicht spezifisch abgefragt.")
                print("     -> In diesem Fall musst du `create_respondent_flexibility_df` anpassen, damit es eine Zeile")
                print("        für 'Staubsauger' pro Respondent erstellt (ggf. mit NaN für Dauer/Anreiz).")
                print("        Das Konzept hierfür (Erstellung eines Basis-DataFrames) wurde bereits diskutiert.")
        else:
            print("  INFO: 'df_flex' ist nach dem Laden leer oder None.")
            print("    HINWEIS: Dies ist ein schwerwiegendes Problem, das die weitere Analyse verhindert.")

    except FileNotFoundError as e:
        print(f"  FEHLER beim Laden von df_flex (FileNotFoundError): {e}. Eine der Q9/Q10 CSVs fehlt möglicherweise.")
    except Exception as e:
        print(f"  FEHLER bei df_flex Check: {e}")
        import traceback
        traceback.print_exc()

    # --- Check 3: Simulierter master_df_f1 (Merge von df_flex und df_q8_long) ---
    print_data_check_header("3. Simulierter master_df_f1 (Merge von df_flex und df_q8_long)")
    master_df_check = None
    if df_flex is not None and not df_flex.empty and \
       df_q8_long is not None and not df_q8_long.empty:
        try:
            print("Simuliere Merge von df_flex mit df_q8_long...")
            # Stelle sicher, dass 'device' in beiden DFs existiert und für den Merge verwendet werden kann
            if 'device' not in df_flex.columns:
                print("  FEHLER: 'device'-Spalte fehlt in df_flex. Merge nicht möglich.")
            elif 'device' not in df_q8_long.columns:
                print("  FEHLER: 'device'-Spalte fehlt in df_q8_long. Merge nicht möglich.")
            else:
                # Wichtig: Der Merge-Key 'device' muss in beiden DFs die gleiche Benennung haben
                # (z.B. "Staubsauger" in beiden, nicht "Q8_Staubsauger" in einem und "Staubsauger" im anderen)
                master_df_check = pd.merge(df_flex, df_q8_long, on=['respondent_id', 'device'], how='left')
                print(f"  'master_df_check' erstellt. Shape: {master_df_check.shape}")

                columns_to_check_final = ['importance_rating']
                if 'max_duration_hours_num' in master_df_check.columns:
                    columns_to_check_final.append('max_duration_hours_num')
                if 'incentive_pct_required_num' in master_df_check.columns:
                    columns_to_check_final.append('incentive_pct_required_num')

                staubsauger_in_master_check = check_device_in_df(master_df_check, "master_df_check (simuliert)",
                                                               columns_to_show=columns_to_check_final)
                if staubsauger_in_master_check:
                    staubsauger_daten_final = master_df_check[master_df_check['device'] == 'Staubsauger']
                    if 'importance_rating' in staubsauger_daten_final.columns:
                        nan_importance = staubsauger_daten_final['importance_rating'].isna().sum()
                        total_staubsauger = len(staubsauger_daten_final)
                        print(f"    Für 'Staubsauger' im simulierten Master-DF: {nan_importance}/{total_staubsauger} Zeilen haben NaN für 'importance_rating'.")
                        if nan_importance == total_staubsauger and total_staubsauger > 0:
                             print("      WARNUNG: Alle 'importance_rating' für Staubsauger sind NaN. Der Merge mit Q8-Daten hat nicht funktioniert.")
                             print("               Mögliche Gründe: 'device'-Namen in df_flex und df_q8_long stimmen nicht überein ODER")
                             print("               'Staubsauger' war in df_q8_long nicht vorhanden (siehe Check 1b).")
                    else:
                        print("    WARNUNG: Spalte 'importance_rating' fehlt im master_df_check für Staubsauger nach Merge.")

        except Exception as e:
            print(f"  FEHLER beim Erstellen/Prüfen von master_df_check: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("  INFO: df_flex oder df_q8_long ist leer/None, daher kann der Merge für master_df_check nicht durchgeführt werden.")

    print_data_check_header("Ende der Datenüberprüfung")

# --- Skript ausführen ---
if __name__ == "__main__":
    run_checks()