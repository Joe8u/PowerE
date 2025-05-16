# PowerE/src/data_loader/survey_loader/attitudes.py
import pandas as pd
from pathlib import Path
import numpy as np

FILES = {
    'challenges': 'question_6_challenges.csv',
    'consequence': 'question_7_consequence.csv',
}

def load_attitudes(project_root_path: Path) -> dict[str, pd.DataFrame]:
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
            # Liest die (jetzt saubere) vorverarbeitete CSV-Datei
            current_df = pd.read_csv(path, dtype=str, encoding='utf-8') # encoding hinzugefügt für Konsistenz
            if not current_df.empty and 'respondent_id' in current_df.columns:
                # Diese Bereinigungen für respondent_id sind weiterhin sinnvoll
                current_df['respondent_id'] = current_df['respondent_id'].str.replace(r'\.0$', '', regex=True)
                current_df['respondent_id'] = current_df['respondent_id'].replace(r'^\s*$', np.nan, regex=True).replace('nan', np.nan)
                # Diese Zeile wird jetzt keine Artefakt-Zeile mehr entfernen,
                # aber immer noch Zeilen mit wirklich fehlender respondent_id (was gut ist).
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