# PowerE/src/data_loader/survey_loader/socioeconomics.py
import pandas as pd
from pathlib import Path
import numpy as np

# KEINE Modul-level Definition von PROJECT_ROOT oder PROCESSED_DIR hier!

_FILES = {
    'income':     'question_13_income.csv',
    'education':  'question_14_education.csv',
    'party_pref': 'question_15_party.csv',
}

def _load_csv_socio(key: str, fname: str, project_root_path: Path) -> pd.DataFrame:
    PROCESSED_DIR = project_root_path / "data" / "processed" / "survey"
    path = PROCESSED_DIR / fname
    df = pd.DataFrame()
    if not path.is_file():
        print(f"WARNUNG [socioeconomics.py]: Datei nicht gefunden: {path}. DF für '{key}' wird leer sein.")
        return df
    try:
        df = pd.read_csv(path, dtype=str)
        if not df.empty and 'respondent_id' in df.columns:
            df['respondent_id'] = df['respondent_id'].str.replace(r'\.0$', '', regex=True)
            df['respondent_id'] = df['respondent_id'].replace(r'^\s*$', np.nan, regex=True).replace('nan', np.nan)
            df.dropna(subset=['respondent_id'], inplace=True)
        elif not df.empty:
            print(f"WARNUNG [socioeconomics.py]: Spalte 'respondent_id' nicht in {fname}.")
    except Exception as e:
        print(f"FEHLER [socioeconomics.py] beim Lesen/Bereinigen von {path}: {e}")
    return df

def load_socioeconomics(project_root_path: Path) -> dict[str, pd.DataFrame]:
    return { key: _load_csv_socio(key, fname, project_root_path) for key, fname in _FILES.items() }

# Convenience Loader müssen jetzt auch project_root_path annehmen
def load_income(project_root_path: Path) -> pd.DataFrame:
    return _load_csv_socio('income', _FILES['income'], project_root_path)
def load_education(project_root_path: Path) -> pd.DataFrame:
    return _load_csv_socio('education', _FILES['education'], project_root_path)
def load_party_pref(project_root_path: Path) -> pd.DataFrame:
    return _load_csv_socio('party_pref', _FILES['party_pref'], project_root_path)

if __name__ == "__main__":
    try:
        test_project_root = Path(__file__).resolve().parent.parent.parent.parent
        print(f"Socioeconomics Loader Direktaufruf - Test PROJECT_ROOT: {test_project_root}")
        data = load_socioeconomics(test_project_root)
        print("\nSocioeconomics-Daten (direkt aus socioeconomics.py geladen):")
        for k, v_df in data.items(): print(f"  {k}: {v_df.shape}")
    except Exception as e: print(f"Fehler im socioeconomics.py __main__: {e}")