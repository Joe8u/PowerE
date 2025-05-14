# PowerE/src/logic/respondent_level_model/data_transformer.py
import pandas as pd
import numpy as np

from data_loader.survey_loader.nonuse2_loader import load_q9_nonuse_long
from data_loader.survey_loader.incentive2_loader import load_q10_incentives_long

def create_respondent_flexibility_df() -> pd.DataFrame:
    print("[INFO] create_respondent_flexibility_df: Starte Transformation der Umfragedaten...")

    # 1. Frage 9 Daten laden (Dauer)
    df_q9_long_loaded = pd.DataFrame() 
    try:
        df_q9_long_loaded = load_q9_nonuse_long()
    except FileNotFoundError as e:
        print(f"[FEHLER] Q9-Datei nicht gefunden: {e}.")
    
    if df_q9_long_loaded.empty:
        print("[WARNUNG] Q9-Daten sind leer oder konnten nicht geladen werden.")
        df_q9_processed = pd.DataFrame(columns=['respondent_id', 'device', 'max_duration_hours'])
    else:
        q9_duration_mapping = {
            "Nein, auf keinen Fall": 0.0,
            "Ja, aber maximal für 3 Stunden": 1.5,
            "Ja, für 3 bis 6 Stunden": 4.5,
            "Ja, für 6 bis 12 Stunden": 9.0,
            "Ja, für maximal 24 Stunden": 18.0,
            "Ja, für mehr als 24 Stunden": 30.0
        }
        df_q9_long_loaded['max_duration_hours'] = df_q9_long_loaded['q9_duration_text'].map(q9_duration_mapping)
        df_q9_long_loaded['max_duration_hours'] = pd.to_numeric(df_q9_long_loaded['max_duration_hours'], errors='coerce')
        df_q9_processed = df_q9_long_loaded[['respondent_id', 'device', 'max_duration_hours']].copy()
    print(f"  Q9-Daten verarbeitet (oder leer initialisiert): {len(df_q9_processed)} Zeilen.")

    # 2. Frage 10 Daten laden (Anreiz)
    df_q10_long_loaded = pd.DataFrame() 
    try:
        df_q10_long_loaded = load_q10_incentives_long()
    except FileNotFoundError as e:
        print(f"[FEHLER] Q10-Datei nicht gefunden: {e}.")
        
    if df_q10_long_loaded.empty:
        print("[WARNUNG] Q10-Daten sind leer oder konnten nicht geladen werden.")
        df_q10_processed = pd.DataFrame(columns=['respondent_id', 'device', 'incentive_choice', 'incentive_pct_required'])
    else:
        q10_choice_mapping = {
            "Ja, f": "yes_fixed",
            "Ja, +": "yes_conditional",
            "Nein": "no"
        }
        df_q10_long_loaded['incentive_choice'] = df_q10_long_loaded['q10_choice_text'].map(q10_choice_mapping)
        df_q10_long_loaded['incentive_choice'] = df_q10_long_loaded['incentive_choice'].fillna('unknown_choice') # Zuweisung ohne inplace

        df_q10_long_loaded['q10_pct_required_text'] = \
            df_q10_long_loaded['q10_pct_required_text'].str.replace('%', '', regex=False).str.strip()
        df_q10_long_loaded['incentive_pct_required'] = \
            pd.to_numeric(df_q10_long_loaded['q10_pct_required_text'], errors='coerce')

        # Für 'yes_fixed', pct_required auf 0 setzen, wenn es NaN ist NACH der Konvertierung.
        # Wenn ein Wert da stand (z.B. "5" bei "Ja, f"), wird dieser numerische Wert erstmal behalten
        # und dann von der Logik im Test explizit als 0.0 für 'yes_fixed' erwartet.
        # Sicherer ist, es hier direkt zu setzen:
        mask_yes_fixed = df_q10_long_loaded['incentive_choice'] == 'yes_fixed'
        df_q10_long_loaded.loc[mask_yes_fixed, 'incentive_pct_required'] = \
            df_q10_long_loaded.loc[mask_yes_fixed, 'incentive_pct_required'].fillna(0.0)
        # Setze explizit auf 0 für yes_fixed, falls ein Wert dastand oder es jetzt NaN ist
        df_q10_long_loaded.loc[mask_yes_fixed, 'incentive_pct_required'] = 0.0


        df_q10_processed = df_q10_long_loaded[['respondent_id', 'device', 'incentive_choice', 'incentive_pct_required']].copy()
    print(f"  Q10-Daten verarbeitet (oder leer initialisiert): {len(df_q10_processed)} Zeilen.")

    # 3. Verarbeitete Q9 und Q10 Daten zusammenführen
    if df_q9_processed.empty and df_q10_processed.empty:
        print("[WARNUNG] Sowohl Q9 als auch Q10 Daten sind leer. Gebe leeren DataFrame mit Spalten zurück.")
        return pd.DataFrame(columns=['respondent_id', 'device', 'max_duration_hours', 'incentive_choice', 'incentive_pct_required'])
    elif df_q9_processed.empty: # Nur Q10 hat Daten
        print("[INFO] Nur Q10-Daten vorhanden. Füge leere Q9-Spalten hinzu.")
        df_q10_processed['max_duration_hours'] = np.nan
        df_respondent_flexibility = df_q10_processed[['respondent_id', 'device', 'max_duration_hours', 'incentive_choice', 'incentive_pct_required']]
    elif df_q10_processed.empty: # Nur Q9 hat Daten
        print("[INFO] Nur Q9-Daten vorhanden. Füge leere Q10-Spalten hinzu.")
        df_q9_processed['incentive_choice'] = 'unknown_choice_q10_missing'
        df_q9_processed['incentive_pct_required'] = np.nan
        df_respondent_flexibility = df_q9_processed[['respondent_id', 'device', 'max_duration_hours', 'incentive_choice', 'incentive_pct_required']]
    else: # Beide haben Daten
        df_respondent_flexibility = pd.merge(
            df_q9_processed,
            df_q10_processed,
            on=['respondent_id', 'device'],
            how='outer'
        )
        print(f"  Q9 und Q10 Daten gemerged. Ergebnis-Shape vor finaler Bereinigung: {df_respondent_flexibility.shape}")
        # Fehlende 'incentive_choice' nach dem Merge füllen, falls eine Zeile nur aus Q9 kam
        df_respondent_flexibility['incentive_choice'] = df_respondent_flexibility['incentive_choice'].fillna('unknown_choice_q10_missing')

    # Finale Bereinigungen
    df_respondent_flexibility.dropna(subset=['respondent_id', 'device'], inplace=True)
    
    # Sicherstellen, dass die numerischen Spalten auch wirklich numerisch sind (wichtig nach Merge mit potenziell leeren DFs)
    if 'max_duration_hours' in df_respondent_flexibility.columns:
        df_respondent_flexibility['max_duration_hours'] = pd.to_numeric(df_respondent_flexibility['max_duration_hours'], errors='coerce')
    else: # Fall, dass df_q9_processed initial leer war und Spalte nicht existiert
        df_respondent_flexibility['max_duration_hours'] = np.nan

    if 'incentive_pct_required' in df_respondent_flexibility.columns:
        df_respondent_flexibility['incentive_pct_required'] = pd.to_numeric(df_respondent_flexibility['incentive_pct_required'], errors='coerce')
    else: # Fall, dass df_q10_processed initial leer war
        df_respondent_flexibility['incentive_pct_required'] = np.nan
        
    # Sicherstellen, dass incentive_choice existiert, auch wenn q10 leer war
    if 'incentive_choice' not in df_respondent_flexibility.columns:
        df_respondent_flexibility['incentive_choice'] = 'unknown_choice_q10_missing'


    print(f"[INFO] create_respondent_flexibility_df: Finale Daten transformiert. Shape: {df_respondent_flexibility.shape}")
    return df_respondent_flexibility

if __name__ == '__main__':
    # Beispielhafter Aufruf zum Testen dieses Transformers
    try:
        df_final_flex_data = create_respondent_flexibility_df()
        if not df_final_flex_data.empty:
            print("\nBeispielhafte Ausgabe von create_respondent_flexibility_df():")
            print(df_final_flex_data.head())
            
            print(f"\nForm des finalen DataFrames: {df_final_flex_data.shape}")
            print("\nInfos zum finalen DataFrame:")
            df_final_flex_data.info()
            
            print("\nValue Counts für 'max_duration_hours':")
            print(df_final_flex_data['max_duration_hours'].value_counts(dropna=False).sort_index())
            
            print("\nValue Counts für 'incentive_choice':")
            print(df_final_flex_data['incentive_choice'].value_counts(dropna=False))
            
            print("\nValue Counts für 'incentive_pct_required' (gerundet für Übersicht):")
            print(df_final_flex_data['incentive_pct_required'].round(0).value_counts(dropna=False).sort_index())
            
            # Überprüfe, ob es Kombinationen gibt, wo incentive_choice 'yes_conditional' ist, aber pct NaN
            missing_pct_for_conditional = df_final_flex_data[
                (df_final_flex_data['incentive_choice'] == 'yes_conditional') &
                (df_final_flex_data['incentive_pct_required'].isna())
            ]
            if not missing_pct_for_conditional.empty:
                print(f"\n[WARNUNG] {len(missing_pct_for_conditional)} Fälle von 'yes_conditional' ohne Prozentangabe gefunden.")
                # print(missing_pct_for_conditional) # Für detaillierte Ansicht
        else:
            print("Transformer hat einen leeren DataFrame zurückgegeben.")

    except Exception as e: # Breitere Exception für den Testlauf
        print(f"Ein Fehler ist im Testlauf aufgetreten: {e}")
        import traceback
        traceback.print_exc()