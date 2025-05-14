# PowerE/src/data_loader/survey_loader/incentive2_loader.py
import os
import pandas as pd
from pathlib import Path # Importiere Path für einen moderneren Pfad Umgang

# Absoluter Pfad zum Ordner data/processed/survey
# Verwende Path für eine robustere Pfadkonstruktion
_SURVEY_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed" / "survey"

# Dateiname für Q10 (bleibt gleich)
_INCENTIVE_FILE_NAME = 'question_10_incentive_wide.csv'

# Geräte, wie sie als Spaltenpräfixe in der CSV-Datei vorkommen (basierend auf deiner Umfragebeschreibung)
# und wie sie in der Umfrage benannt wurden.
# Wichtig: "Staubsauger" war auch in Frage 10.
# Die Entscheidung, ob "Waschmaschine" oder "Waschmaschine (Laundry)" hier steht, hängt davon ab,
# wie die Spalten in deiner "question_10_incentive_wide.csv" *tatsächlich* heißen.
# Ich gehe davon aus, dass die Spalten die Original-Umfragenamen verwenden, also "Waschmaschine".
# Wenn du die Spaltennamen in der CSV bereits zu "Waschmaschine (Laundry)" geändert hattest,
# müsstest du das hier anpassen. Für ein sauberes respondentenbasiertes Modell
# ist es aber besser, hier die ursprünglichen Umfragekategorien zu verwenden.
_Q10_DEVICES = [
    "Geschirrspüler",
    "Backofen und Herd",
    "Fernseher und Entertainment-Systeme",
    "Bürogeräte",
    "Waschmaschine",
    #"Staubsauger" #
]

def load_q10_incentives_long() -> pd.DataFrame:
    """
    Lädt die Wide-CSV für Frage 10 (Incentives) und transformiert sie in ein langes Format.

    Die Wide-CSV wird erwartet unter: PowerE/data/processed/survey/question_10_incentive_wide.csv
    Die Spaltennamen für Geräte-spezifische Antworten werden als '{device}_choice' und '{device}_pct' erwartet.

    Rückgabe:
        pd.DataFrame: Ein DataFrame im langen Format mit den Spalten:
                      'respondent_id': ID des Befragten.
                      'device': Name des Geräts (aus _Q10_DEVICES).
                      'q10_choice_text': Die Textantwort aus Dropdown 1 (z.B. "Ja, f", "Ja, +", "Nein").
                      'q10_pct_required_text': Die Texteingabe für den Prozent-Rabatt (als String).
                                              Bleibt leer oder NaN, wenn keine Prozentangabe gemacht wurde.
    """
    file_path = _SURVEY_DATA_DIR / _INCENTIVE_FILE_NAME
    if not file_path.exists():
        raise FileNotFoundError(f"Incentive-Datei nicht gefunden: {file_path}")

    df_wide = pd.read_csv(file_path, dtype=str)

    rows_list = []

    # Stelle sicher, dass 'respondent_id' existiert
    if 'respondent_id' not in df_wide.columns:
        # Falls deine ID-Spalte anders heißt, passe es hier an oder werfe einen Fehler.
        # Beispiel: Annahme, die erste Spalte ist die ID, wenn 'respondent_id' fehlt.
        if df_wide.columns[0].lower() == 'id' or 'id' in df_wide.columns[0].lower():
             df_wide = df_wide.rename(columns={df_wide.columns[0]: 'respondent_id'})
        else:
            raise KeyError("Spalte 'respondent_id' nicht in der CSV-Datei gefunden.")


    for device_name in _Q10_DEVICES:
        choice_col = f"{device_name}_choice"
        pct_col = f"{device_name}_pct"

        # Prüfe, ob die erwarteten Spalten für das Gerät existieren
        if choice_col in df_wide.columns and pct_col in df_wide.columns:
            temp_df = df_wide[['respondent_id', choice_col, pct_col]].copy()
            temp_df.rename(columns={
                choice_col: "q10_choice_text",
                pct_col: "q10_pct_required_text"
            }, inplace=True)
            temp_df['device'] = device_name
            rows_list.append(temp_df)
        else:
            print(f"[WARNUNG] load_q10_incentives_long: Spalten für Gerät '{device_name}' ('{choice_col}', '{pct_col}') nicht in CSV gefunden. Überspringe Gerät.")

    if not rows_list:
        print("[WARNUNG] load_q10_incentives_long: Keine Gerätedaten zum Verarbeiten gefunden. Gebe leeren DataFrame zurück.")
        return pd.DataFrame(columns=['respondent_id', 'device', 'q10_choice_text', 'q10_pct_required_text'])

    df_long = pd.concat(rows_list, ignore_index=True)
    
    # Optionale Bereinigung: Fülle leere Prozentangaben mit einem konsistenten Wert (z.B. leerer String oder explizit np.nan)
    # pd.read_csv mit dtype=str liest leere Zellen als leere Strings. Wenn du NaN willst:
    # df_long['q10_pct_required_text'].replace('', np.nan, inplace=True)

    print(f"[INFO] load_q10_incentives_long: {len(df_long)} Zeilen im langen Format aus Frage 10 geladen.")
    return df_long

if __name__ == '__main__':
    # Beispielhafter Aufruf zum Testen des Loaders
    try:
        df_q10_long_data = load_q10_incentives_long()
        print("\nBeispielhafte Ausgabe von load_q10_incentives_long():")
        print(df_q10_long_data.head())
        print(f"\nForm des DataFrames: {df_q10_long_data.shape}")
        print(f"\Eindeutige Geräte: {df_q10_long_data['device'].unique()}")
        print("\nInfos zum DataFrame:")
        df_q10_long_data.info()
    except FileNotFoundError as e:
        print(e)
    except KeyError as e:
        print(f"KeyError beim Laden: {e}")