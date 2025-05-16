# PowerE/src/data_loader/survey_loader/demand_response.py
import pandas as pd
import numpy as np
from pathlib import Path

# KEINE Modul-level Definition von PROJECT_ROOT oder BASE_DIR hier!
    
_FILES = {
    'importance':   'question_8_importance_wide.csv',
    # 'curtailment' und 'incentives' hier ggf. nicht relevant für F1-Master-DF, wenn Q9/Q10 aus data_transformer kommen
    'notification': 'question_11_notification.csv',
    'smart_plug':   'question_12_smartplug.csv',
}

def _load_csv_dr(name: str, project_root_path: Path) -> pd.DataFrame: # Akzeptiert project_root_path
    PROCESSED_DIR = project_root_path / "data" / "processed" / "survey"
    fname = _FILES.get(name)
    if fname is None:
        raise KeyError(f"No such survey component in _FILES for demand_response: {name}")
    
    path = PROCESSED_DIR / fname
    df = pd.DataFrame()
    if not path.is_file():
        print(f"WARNUNG [demand_response.py]: Datei nicht gefunden: {path}. DF für '{name}' wird leer sein.")
        return df

    try:
        # KORRIGIERTER TEIL: Die rows_to_skip Logik wurde entfernt.
        # Wir fügen encoding='utf-8' für Konsistenz hinzu.
        df = pd.read_csv(path, dtype=str, encoding='utf-8') # skiprows=rows_to_skip entfernt

        if not df.empty and 'respondent_id' in df.columns:
            df['respondent_id'] = df['respondent_id'].str.replace(r'\.0$', '', regex=True)
            df['respondent_id'] = df['respondent_id'].replace(r'^\s*$', np.nan, regex=True).replace('nan', np.nan)
            # Diese dropna-Zeile ist weiterhin in Ordnung. Sie entfernt jetzt keine Artefakt-Zeile mehr,
            # aber würde eine Zeile entfernen, falls ein echter Teilnehmer eine fehlende respondent_id hätte.
            df.dropna(subset=['respondent_id'], inplace=True)
        elif not df.empty:
            print(f"WARNUNG [demand_response.py]: Spalte 'respondent_id' nicht in {fname}.")
    except Exception as e:
        print(f"FEHLER [demand_response.py] beim Lesen/Bereinigen von {path}: {e}")
    return df

def load_demand_response(project_root_path: Path) -> dict[str, pd.DataFrame]: # Akzeptiert Argument
    # Lädt nur die für F1 relevanten Teile, die nicht schon durch data_transformer kommen
    keys_to_load = ['importance', 'notification', 'smart_plug']
    return { name: _load_csv_dr(name, project_root_path) for name in keys_to_load }

def load_importance(project_root_path: Path) -> pd.DataFrame: # Akzeptiert Argument
    return _load_csv_dr('importance', project_root_path)
def load_notification(project_root_path: Path) -> pd.DataFrame: # Akzeptiert Argument
    return _load_csv_dr('notification', project_root_path)
def load_smart_plug(project_root_path: Path) -> pd.DataFrame: # Akzeptiert Argument
    return _load_csv_dr('smart_plug', project_root_path)

if __name__ == "__main__":
    try:
        test_project_root = Path(__file__).resolve().parent.parent.parent.parent
        print(f"Demand Response Loader Direktaufruf - Test PROJECT_ROOT: {test_project_root}")

        print("\nTeste explizit load_smart_plug...")
        # Temporär den Pfad direkt in _load_csv_dr ausgeben für 'smart_plug'
        # In _load_csv_dr: print(f"DEBUG: Trying to load {path}")
        df_sp = load_smart_plug(test_project_root) # Rufe die Funktion mit dem Pfad auf
        print(f"--- Smart Plug (Q12) --- Shape: {df_sp.shape}")
        if not df_sp.empty:
            print(df_sp.head())
        else:
            print("Q12 DataFrame ist leer nach dem Laden.")
    except Exception as e_main:
        print(f"Fehler im demand_response.py __main__: {e_main}")