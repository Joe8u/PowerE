# PowerE/src/data_loader/survey_loader/nonuse2_loader.py
import os
import pandas as pd
from pathlib import Path
import numpy as np

_SURVEY_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed" / "survey"
_NONUSE_FILE_NAME = 'question_9_nonuse_wide.csv'

_Q9_DEVICES = [
    "Geschirrspüler",
    "Backofen und Herd",
    "Fernseher und Entertainment-Systeme",
    "Bürogeräte",
    "Waschmaschine",
    "Staubsauger" 
]

def load_q9_nonuse_long() -> pd.DataFrame:
    """
    Lädt die (jetzt saubere) Wide-CSV für Frage 9 (Non-Use-Dauer)
    und transformiert sie in ein langes Format.
    """
    file_path = _SURVEY_DATA_DIR / _NONUSE_FILE_NAME
    if not file_path.exists():
        raise FileNotFoundError(f"Non-Use-Datei (Frage 9) nicht gefunden: {file_path}")

    # Liest die (jetzt saubere) vorverarbeitete CSV-Datei
    # Kein Überspringen von Zeilen hier mehr nötig, da die CSV sauber sein sollte.
    df_wide = pd.read_csv(file_path, dtype=str, encoding='utf-8')

    if df_wide.empty:
        print("[WARNUNG] load_q9_nonuse_long: CSV-Datei ist leer oder enthält nur Header.")
        return pd.DataFrame(columns=['respondent_id', 'device', 'q9_duration_text'])

    # --- Bereinigung der respondent_id und Entfernen von Zeilen mit fehlender respondent_id ---
    # Diese Logik ist weiterhin sinnvoll, um sicherzustellen, dass nur Zeilen mit gültiger ID verarbeitet werden.
    id_col_name = 'respondent_id' # Standardname
    if id_col_name not in df_wide.columns:
        # Versuche, die ID-Spalte zu erraten, falls sie anders benannt wurde (sollte aber nicht der Fall sein)
        first_col_actual_name = df_wide.columns[0]
        if 'id' in first_col_actual_name.lower() or 'respondent' in first_col_actual_name.lower():
            id_col_name = first_col_actual_name
            df_wide = df_wide.rename(columns={id_col_name: 'respondent_id'}) # Stelle sicher, dass sie 'respondent_id' heißt
            print(f"[INFO] load_q9_nonuse_long: Erste Spalte als '{id_col_name}' interpretiert und zu 'respondent_id' umbenannt.")
        else:
            raise KeyError(f"Spalte 'respondent_id' nicht in CSV für Frage 9 gefunden und erste Spalte '{first_col_actual_name}' unklar.")
    
    # Bereinige die respondent_id-Spalte (entferne .0, wandle "nan"-Strings und leere Strings zu np.nan)
    df_wide['respondent_id'] = df_wide['respondent_id'].astype(str).str.replace(r'\.0$', '', regex=True)
    df_wide['respondent_id'] = df_wide['respondent_id'].replace(r'^\s*$', np.nan, regex=True).replace('nan', np.nan)
    
    # Entferne Zeilen, bei denen respondent_id nach der Bereinigung immer noch NaN ist
    df_wide.dropna(subset=['respondent_id'], inplace=True)
    
    if df_wide.empty:
        print("[WARNUNG] load_q9_nonuse_long: DataFrame ist leer nach dem Entfernen von Zeilen mit fehlender respondent_id.")
        return pd.DataFrame(columns=['respondent_id', 'device', 'q9_duration_text'])
    # --- Ende Bereinigung respondent_id ---


    rows_list = []
    for device_name in _Q9_DEVICES:
        if device_name in df_wide.columns:
            temp_df_subset = df_wide[['respondent_id', device_name]].copy()
            temp_df_subset.rename(columns={
                # respondent_id heißt schon so
                device_name: "q9_duration_text"
            }, inplace=True)
            temp_df_subset['device'] = device_name
            rows_list.append(temp_df_subset)
        else:
            print(f"[WARNUNG] load_q9_nonuse_long: Spalte für Gerät '{device_name}' nicht in CSV für Frage 9 gefunden. Überspringe Gerät.")

    if not rows_list:
        print("[WARNUNG] load_q9_nonuse_long: Keine gültigen Gerätedaten zum Verarbeiten gefunden nach Filterung. Gebe leeren DataFrame zurück.")
        return pd.DataFrame(columns=['respondent_id', 'device', 'q9_duration_text'])

    df_long = pd.concat(rows_list, ignore_index=True)
    
    # Ersetze leere Strings in der Antwortspalte durch NaN für Konsistenz
    df_long['q9_duration_text'] = df_long['q9_duration_text'].replace(r'^\s*$', np.nan, regex=True)

    print(f"[INFO] load_q9_nonuse_long: {len(df_long)} Zeilen im langen Format aus Frage 9 geladen (nach Bereinigung).")
    return df_long

if __name__ == '__main__':
    try:
        df_q9_long_data = load_q9_nonuse_long()
        print("\nBeispielhafte Ausgabe von load_q9_nonuse_long():")
        print(df_q9_long_data.head())
        # ... (Rest deines Test-Codes) ...
    except FileNotFoundError as e:
        print(e)
    except KeyError as e:
        print(f"KeyError beim Laden: {e}")
