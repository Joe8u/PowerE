# PowerE/src/data_loader/survey_loader/attitudes.py
import pandas as pd
from pathlib import Path
import numpy as np

# KEINE Modul-level Definition von PROJECT_ROOT oder PROCESSED_DIR hier!

FILES = {
    'challenges': 'question_6_challenges.csv',
    'consequence': 'question_7_consequence.csv',
}

def load_attitudes(project_root_path: Path) -> dict[str, pd.DataFrame]: # Akzeptiert Argument
    PROCESSED_DIR = project_root_path / "data" / "processed" / "survey"
    dfs: dict[str, pd.DataFrame] = {}
    for key, fname in FILES.items():
        path = PROCESSED_DIR / fname
        current_df = pd.DataFrame()
        if not path.is_file():
            print(f"WARNUNG [attitudes.py]: Datei nicht gefunden: {path}. DataFrame für '{key}' wird leer sein.")
            dfs[key] = current_df
            continue
        try:
            current_df = pd.read_csv(path, dtype=str)
            if not current_df.empty and 'respondent_id' in current_df.columns:
                current_df['respondent_id'] = current_df['respondent_id'].str.replace(r'\.0$', '', regex=True)
                current_df['respondent_id'] = current_df['respondent_id'].replace(r'^\s*$', np.nan, regex=True).replace('nan', np.nan)
                current_df.dropna(subset=['respondent_id'], inplace=True)
            elif not current_df.empty:
                 print(f"WARNUNG [attitudes.py]: Spalte 'respondent_id' nicht in {fname} gefunden.")
        except Exception as e:
            print(f"FEHLER [attitudes.py] beim Lesen/Bereinigen von {path}: {e}")
        dfs[key] = current_df
    return dfs

if __name__ == "__main__":
    try:
        test_project_root = Path(__file__).resolve().parent.parent.parent.parent
        print(f"Attitudes Loader Direktaufruf - Test PROJECT_ROOT: {test_project_root}")
        data = load_attitudes(test_project_root)
        print("\nAttitudes-Daten (direkt aus attitudes.py geladen):")
        for k, v_df in data.items(): print(f"  {k}: {v_df.shape}")
    except Exception as e: print(f"Fehler im attitudes.py __main__: {e}")