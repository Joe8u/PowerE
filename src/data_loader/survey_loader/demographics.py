# PowerE/src/data_loader/survey_loader/demographics.py
import pandas as pd
from pathlib import Path
import numpy as np

# KEINE Modul-level Definition von PROJECT_ROOT oder PROCESSED_DIR hier!

FILES = {
    'age':            'question_1_age.csv',
    'gender':         'question_2_gender.csv',
    'household_size': 'question_3_household_size.csv',
    'accommodation':  'question_4_accommodation.csv',
    'electricity':    'question_5_electricity.csv',
}

def load_demographics(project_root_path: Path) -> dict[str, pd.DataFrame]: # Akzeptiert Argument
    PROCESSED_DIR = project_root_path / "data" / "processed" / "survey"
    dfs: dict[str, pd.DataFrame] = {}
    for key, fname in FILES.items():
        path = PROCESSED_DIR / fname
        current_df = pd.DataFrame()
        if not path.is_file():
            print(f"WARNUNG [demographics.py]: Datei nicht gefunden: {path}. DataFrame für '{key}' wird leer sein.")
            dfs[key] = current_df
            continue
        try:
            rows_to_skip = [1] if key == 'age' and fname == 'question_1_age.csv' else None
            current_df = pd.read_csv(path, dtype=str, skiprows=rows_to_skip)
            if not current_df.empty and 'respondent_id' in current_df.columns:
                current_df['respondent_id'] = current_df['respondent_id'].str.replace(r'\.0$', '', regex=True)
                current_df['respondent_id'] = current_df['respondent_id'].replace(r'^\s*$', np.nan, regex=True).replace('nan', np.nan)
                current_df.dropna(subset=['respondent_id'], inplace=True)
                if key == 'age' and 'age' in current_df.columns:
                    current_df['age'] = pd.to_numeric(current_df['age'], errors='coerce')
            elif not current_df.empty:
                 print(f"WARNUNG [demographics.py]: Spalte 'respondent_id' nicht in {fname} gefunden.")
        except Exception as e:
            print(f"FEHLER [demographics.py] beim Lesen/Bereinigen von {path}: {e}")
        dfs[key] = current_df
    return dfs

if __name__ == "__main__":
    # Zum direkten Testen dieses Moduls (Pfad muss hier explizit bestimmt werden)
    try:
        test_project_root = Path(__file__).resolve().parent.parent.parent.parent
        print(f"Demographics Loader Direktaufruf - Test PROJECT_ROOT: {test_project_root}")
        data = load_demographics(test_project_root)
        print("\nDemographie-Daten (direkt aus demographics.py geladen):")
        for k, v_df in data.items(): print(f"  {k}: {v_df.shape}")
    except Exception as e: print(f"Fehler im demographics.py __main__: {e}")