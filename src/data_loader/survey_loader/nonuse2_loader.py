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
    "Waschmaschine"
]

def load_q9_nonuse_long() -> pd.DataFrame:
    """
    Lädt die Wide-CSV für Frage 9 (Non-Use-Dauer), bereinigt die erste fehlerhafte Datenzeile
    und transformiert sie in ein langes Format.
    """
    file_path = _SURVEY_DATA_DIR / _NONUSE_FILE_NAME
    if not file_path.exists():
        raise FileNotFoundError(f"Non-Use-Datei (Frage 9) nicht gefunden: {file_path}")

    df_wide_raw = pd.read_csv(file_path, dtype=str)

    # --- NEU: Bereinigung der ersten Datenzeile ---
    # Annahme: Die erste Zeile nach dem Header (Index 0 in df_wide_raw) ist die problematische Zeile,
    # die die Spaltennamen als Daten enthält. Wir überspringen sie.
    if not df_wide_raw.empty and len(df_wide_raw) > 1:
        # Überprüfe, ob die erste Zeile tatsächlich das Problem sein könnte
        # (z.B. indem respondent_id NaN ist oder ein Gerätename in einer Gerätespalte steht)
        # Für eine einfache Lösung überspringen wir sie, wenn sie typische Header-Merkmale aufweist.
        # Eine robustere Prüfung wäre, ob die erste ID NaN ist und die erste Gerätespalte ihren eigenen Namen enthält.
        # Hier eine vereinfachte Annahme: Wenn die erste Zeile in der ersten Gerätespalte den Gerätenamen enthält:
        first_device_col_name = _Q9_DEVICES[0] # z.B. "Geschirrspüler"
        if first_device_col_name in df_wide_raw.columns and \
           df_wide_raw.iloc[0][first_device_col_name] == first_device_col_name and \
           pd.isna(df_wide_raw.iloc[0][df_wide_raw.columns[0]]): # Prüft ob respondent_id in erster Zeile NaN ist
            
            print(f"[INFO] load_q9_nonuse_long: Überspringe die erste Datenzeile (Index 0), da sie wie ein Sub-Header aussieht.")
            df_wide = df_wide_raw.iloc[1:].reset_index(drop=True)
        else:
            # Falls die erste Zeile nicht dem erwarteten fehlerhaften Muster entspricht, nehmen wir alle Daten
            print("[INFO] load_q9_nonuse_long: Erste Datenzeile scheint regulär zu sein oder Muster nicht erkannt.")
            df_wide = df_wide_raw
    elif not df_wide_raw.empty: # Nur eine Datenzeile vorhanden
        df_wide = df_wide_raw # Nimm sie, weitere Filterung unten greift bei Bedarf
    else: # DataFrame ist leer
        print("[WARNUNG] load_q9_nonuse_long: CSV-Datei ist leer oder enthält nur Header.")
        return pd.DataFrame(columns=['respondent_id', 'device', 'q9_duration_text'])


    rows_list = []
    id_col_name = 'respondent_id'
    if id_col_name not in df_wide.columns:
        first_col_actual_name = df_wide.columns[0]
        if 'id' in first_col_actual_name.lower() or 'respondent' in first_col_actual_name.lower():
            id_col_name = first_col_actual_name
        else:
            raise KeyError(f"Spalte '{id_col_name}' nicht in CSV für Frage 9 gefunden und erste Spalte '{first_col_actual_name}' unklar.")

    # Zusätzliche Bereinigung: Entferne Zeilen, bei denen respondent_id immer noch NaN ist
    # (falls die obige Logik nicht alle Fälle abdeckt oder die erste Zeile doch regulär war)
    df_wide = df_wide[df_wide[id_col_name].notna()]
    df_wide = df_wide[~df_wide[id_col_name].astype(str).str.lower().isin([id_col_name.lower(), 'nan', ''])]


    for device_name in _Q9_DEVICES:
        if device_name in df_wide.columns:
            # Erstelle temp_df nur mit den Zeilen, die für respondent_id einen gültigen Wert haben
            temp_df_subset = df_wide[[id_col_name, device_name]].copy()
            temp_df_subset.rename(columns={
                id_col_name: "respondent_id",
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
    df_long['q9_duration_text'] = df_long['q9_duration_text'].replace(r'^\s*$', np.nan, regex=True)

    print(f"[INFO] load_q9_nonuse_long: {len(df_long)} Zeilen im langen Format aus Frage 9 geladen (nach Bereinigung).")
    return df_long

if __name__ == '__main__':
    try:
        df_q9_long_data = load_q9_nonuse_long()
        print("\nBeispielhafte Ausgabe von load_q9_nonuse_long():")
        print(df_q9_long_data.head())
        print("\nBeispiele mit verschiedenen Antworten:")
        valid_responses = df_q9_long_data[df_q9_long_data['q9_duration_text'].notna()]
        if not valid_responses.empty:
            print(valid_responses.sample(min(5, len(valid_responses))))
        else:
            print("Keine validen Antworten für Stichprobe gefunden.")
        print(f"\nForm des DataFrames: {df_q9_long_data.shape}")
        if not df_q9_long_data.empty:
            print(f"Eindeutige Geräte: {df_q9_long_data['device'].unique()}")
            print("\nInfos zum DataFrame:")
            df_q9_long_data.info()
            print("\nAnzahl der verschiedenen Antworten für 'q9_duration_text':")
            print(df_q9_long_data['q9_duration_text'].value_counts(dropna=False))
        else:
            print("DataFrame ist leer.")
    except FileNotFoundError as e:
        print(e)
    except KeyError as e:
        print(f"KeyError beim Laden: {e}")