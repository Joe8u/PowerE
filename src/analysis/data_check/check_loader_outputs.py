# PowerE/src/analysis/data_check/check_loader_outputs.py
"""
Skript zur Überprüfung der Ausgaben der verschiedenen Survey-Daten-Loader.

Dieses Skript importiert die Ladefunktionen aus den survey_loader-Modulen,
ruft sie auf und gibt die ersten paar Zeilen der geladenen DataFrames aus.
Dies dient dazu, zu überprüfen, ob die Loader mit den (jetzt sauberen)
vorverarbeiteten CSV-Dateien korrekt funktionieren, insbesondere nachdem
explizite 'skiprows'-Anweisungen in den Loadern entfernt wurden.
"""
import os
import sys
import pandas as pd
from pathlib import Path

# Füge das 'src'-Verzeichnis zum Python-Pfad hinzu, damit die Loader-Module gefunden werden.
# Annahme: Dieses Skript liegt in PowerE/src/analysis/data_check/
# Das src-Verzeichnis ist also drei Ebenen höher.
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
sys.path.append(str(PROJECT_ROOT)) # Fügt PowerE/ zum sys.path hinzu
sys.path.append(str(PROJECT_ROOT / "src")) # Fügt PowerE/src/ zum sys.path hinzu

# Importiere die Loader-Funktionen
# Es ist wichtig, dass die __init__.py Dateien in den survey_loader Verzeichnissen existieren,
# damit Python sie als Pakete erkennt, oder dass die Pfade korrekt sind.
# Sicherer ist oft, den Pfad relativ zum Projekt-Root zu verwenden.
try:
    from data_loader.survey_loader.attitudes import load_attitudes
    from data_loader.survey_loader.demographics import load_demographics
    from data_loader.survey_loader.demand_response import load_demand_response, load_importance, load_notification, load_smart_plug
    from data_loader.survey_loader.incentive_loader import load_question_10_incentives
    from data_loader.survey_loader.incentive2_loader import load_q10_incentives_long
    from data_loader.survey_loader.nonuse_loader import load_question_9_nonuse
    from data_loader.survey_loader.nonuse2_loader import load_q9_nonuse_long
    from data_loader.survey_loader.socioeconomics import load_socioeconomics
    print("Alle Loader-Module erfolgreich importiert.\n")
except ImportError as e:
    print(f"FEHLER beim Importieren der Loader-Module: {e}")
    print("Stelle sicher, dass das Skript aus dem Hauptverzeichnis (PowerE) ausgeführt wird oder die Pfade korrekt sind.")
    print("Überprüfe auch, ob __init__.py Dateien in den relevanten Unterordnern von src/data_loader/survey_loader/ existieren.")
    exit()

def print_df_head(df_name: str, df: pd.DataFrame, num_rows: int = 2):
    """Gibt den Namen und die ersten Zeilen eines DataFrames aus."""
    print(f"\n--- Daten für: {df_name} ---")
    if df is None or df.empty:
        print("DataFrame ist leer oder None.")
    else:
        print(f"Shape: {df.shape}")
        print(f"Erste {num_rows} Zeilen:")
        print(df.head(num_rows).to_string())
    print("-" * 70)

def main():
    print("=== Starte Überprüfung der Loader-Ausgaben ===")
    
    # Das project_root_path Argument für die Loader, die es benötigen
    project_root_for_loaders = PROJECT_ROOT

    # Teste attitudes.py
    try:
        attitudes_data = load_attitudes(project_root_for_loaders)
        for key, df_att in attitudes_data.items():
            print_df_head(f"Attitudes - {key}", df_att)
    except Exception as e:
        print(f"FEHLER beim Laden von Attitudes-Daten: {e}")

    # Teste demographics.py
    try:
        demographics_data = load_demographics(project_root_for_loaders)
        for key, df_dem in demographics_data.items():
            print_df_head(f"Demographics - {key}", df_dem)
    except Exception as e:
        print(f"FEHLER beim Laden von Demographics-Daten: {e}")

    # Teste demand_response.py (den Hauptloader und ggf. einzelne)
    try:
        demand_response_data = load_demand_response(project_root_for_loaders)
        for key, df_dr in demand_response_data.items():
            print_df_head(f"Demand Response (via Hauptloader) - {key}", df_dr)
        
        # Optional: Teste einzelne Loader aus demand_response.py, falls gewünscht
        # df_importance = load_importance(project_root_for_loaders)
        # print_df_head("Demand Response - Importance (direkt)", df_importance)
    except Exception as e:
        print(f"FEHLER beim Laden von Demand Response-Daten: {e}")

    # Teste incentive_loader.py
    try:
        df_q10_incentives_wide = load_question_10_incentives() # Dieser Loader nimmt keinen project_root_path
        print_df_head("Q10 Incentives (Wide Format, incentive_loader.py)", df_q10_incentives_wide)
    except Exception as e:
        print(f"FEHLER beim Laden von Q10 Incentives (Wide): {e}")

    # Teste incentive2_loader.py
    try:
        df_q10_incentives_long = load_q10_incentives_long() # Dieser Loader nimmt auch keinen project_root_path
        print_df_head("Q10 Incentives (Long Format, incentive2_loader.py)", df_q10_incentives_long)
    except Exception as e:
        print(f"FEHLER beim Laden von Q10 Incentives (Long): {e}")

    # Teste nonuse_loader.py
    try:
        df_q9_nonuse_wide = load_question_9_nonuse() # Dieser Loader nimmt keinen project_root_path
        print_df_head("Q9 Non-Use (Wide Format, nonuse_loader.py)", df_q9_nonuse_wide)
    except Exception as e:
        print(f"FEHLER beim Laden von Q9 Non-Use (Wide): {e}")

    # Teste nonuse2_loader.py
    try:
        df_q9_nonuse_long = load_q9_nonuse_long() # Dieser Loader nimmt auch keinen project_root_path
        print_df_head("Q9 Non-Use (Long Format, nonuse2_loader.py)", df_q9_nonuse_long)
    except Exception as e:
        print(f"FEHLER beim Laden von Q9 Non-Use (Long): {e}")
        
    # Teste socioeconomics.py
    try:
        socioeconomics_data = load_socioeconomics(project_root_for_loaders)
        for key, df_socio in socioeconomics_data.items():
            print_df_head(f"Socioeconomics - {key}", df_socio)
    except Exception as e:
        print(f"FEHLER beim Laden von Socioeconomics-Daten: {e}")

    print("\n\n=== Überprüfung der Loader-Ausgaben abgeschlossen ===")

if __name__ == "__main__":
    main()