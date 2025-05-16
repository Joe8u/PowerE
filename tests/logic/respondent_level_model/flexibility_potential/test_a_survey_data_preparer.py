# PowerE/tests/logic/respondent_level_model/flexibility_potential/test_a_survey_data_preparer.py
import pandas as pd
import numpy as np
import pytest # Importiere pytest
from unittest.mock import patch # Zum Mocken der Ladefunktionen

# Importiere die zu testende Funktion
# Stelle sicher, dass der Pfad für den Import relativ zum PROJECT_ROOT korrekt ist.
# Wenn deine Tests vom PROJECT_ROOT aus mit pytest ausgeführt werden, sollte das so funktionieren,
# vorausgesetzt, dein PROJECT_ROOT ist im PYTHONPATH (was pytest oft automatisch für das Hauptverzeichnis macht)
# oder du hast eine conftest.py, die sys.path anpasst.
from src.logic.respondent_level_model.flexibility_potential.a_survey_data_preparer import prepare_survey_flexibility_data

# --- Testdaten für Q9 und Q10 ---
# Diese DataFrames simulieren, was deine Loader normalerweise aus den CSVs lesen würden.
@pytest.fixture
def mock_q9_data() -> pd.DataFrame:
    """Erstellt Beispieldaten, wie sie von load_q9_nonuse_long() zurückgegeben werden könnten."""
    data = {
        'respondent_id': ['R1', 'R1', 'R2', 'R2', 'R3'], # R3 hinzugefügt
        'device': ['Geschirrspüler', 'Waschmaschine', 'Geschirrspüler', 'Waschmaschine', 'Bürogeräte'], # Gerät für R3
        'q9_duration_text': [
            "Ja, aber maximal für 3 Stunden", # -> 1.5
            "Nein, auf keinen Fall",           # -> 0.0
            "Ja, für 3 bis 6 Stunden",       # -> 4.5
            "Ja, für maximal 24 Stunden",     # -> 24.0
            "Ja, für mehr als 24 Stunden"      # -> 30.0 (NEUER FALL)
        ]
    }
    return pd.DataFrame(data)

@pytest.fixture
def mock_q10_data() -> pd.DataFrame:
    """Erstellt Beispieldaten, wie sie von load_q10_incentives_long() zurückgegeben werden könnten."""
    data = {
        'respondent_id': ['R1', 'R1', 'R2', 'R2', 'R3'],
        'device': ['Geschirrspüler', 'Waschmaschine', 'Geschirrspüler', 'Waschmaschine', 'Ofen'], # Ofen nur in Q10
        'q10_choice_text': ["Ja, +", "Nein", "Ja, f", "Ja, +", "Ja, +"],
        'q10_pct_required_text': ["10%", np.nan, np.nan, "20", "15%"]
    }
    return pd.DataFrame(data)

# --- Der eigentliche Test ---
# Wir verwenden @patch, um die echten Ladefunktionen durch unsere Mocks zu ersetzen,
# wenn prepare_survey_flexibility_data aufgerufen wird.
@patch('src.logic.respondent_level_model.flexibility_potential.a_survey_data_preparer.load_q10_incentives_long')
@patch('src.logic.respondent_level_model.flexibility_potential.a_survey_data_preparer.load_q9_nonuse_long')
def test_prepare_survey_flexibility_data_logic(mock_load_q9, mock_load_q10, mock_q9_data, mock_q10_data):
    """
    Testet die Kernlogik von prepare_survey_flexibility_data 
    (Mapping, Merging, Spaltennamen, Default-Werte).
    """
    # Konfiguriere die Mocks, damit sie unsere Test-DataFrames zurückgeben
    mock_load_q9.return_value = mock_q9_data
    mock_load_q10.return_value = mock_q10_data

    # Rufe die zu testende Funktion auf
    result_df = prepare_survey_flexibility_data()

    # --- Überprüfungen (Assertions) ---
    assert not result_df.empty, "Der Ergebnis-DataFrame sollte nicht leer sein."
    
    # Erwartete Spalten
    expected_columns = ['respondent_id', 'device', 'survey_max_duration_h', 
                        'survey_incentive_choice', 'survey_incentive_pct_required']
    assert all(col in result_df.columns for col in expected_columns), "Nicht alle erwarteten Spalten sind vorhanden."
    assert len(result_df.columns) == len(expected_columns), "Die Anzahl der Spalten stimmt nicht."

    # Überprüfe das Q9 Mapping für einen spezifischen Fall
    # R1, Geschirrspüler: "Ja, aber maximal für 3 Stunden" -> 1.5
    r1_gs_q9 = result_df[
        (result_df['respondent_id'] == 'R1') & (result_df['device'] == 'Geschirrspüler')
    ]['survey_max_duration_h'].iloc[0]
    assert r1_gs_q9 == 1.5, f"Fehler im Q9 Mapping für R1-Geschirrspüler. Erwartet 1.5, bekam {r1_gs_q9}"

    # R2, Waschmaschine: "Ja, für maximal 24 Stunden" -> 24.0
    r2_wm_q9 = result_df[
        (result_df['respondent_id'] == 'R2') & (result_df['device'] == 'Waschmaschine')
    ]['survey_max_duration_h'].iloc[0]
    assert r2_wm_q9 == 24.0, f"Fehler im Q9 Mapping für R2-Waschmaschine. Erwartet 24.0, bekam {r2_wm_q9}"


    # Überprüfe Q10 'yes_fixed' Logik
    # R2, Geschirrspüler: "Ja, f" -> incentive_choice='yes_fixed', pct_required=0.0
    r2_gs_q10_row = result_df[
        (result_df['respondent_id'] == 'R2') & (result_df['device'] == 'Geschirrspüler')
    ]
    assert r2_gs_q10_row['survey_incentive_choice'].iloc[0] == 'yes_fixed'
    assert r2_gs_q10_row['survey_incentive_pct_required'].iloc[0] == 0.0

    # Überprüfe Q10 'yes_conditional' und Prozent-Konvertierung
    # R1, Geschirrspüler: "Ja, +", "10%" -> incentive_choice='yes_conditional', pct_required=10.0
    r1_gs_q10_row = result_df[
        (result_df['respondent_id'] == 'R1') & (result_df['device'] == 'Geschirrspüler')
    ]
    assert r1_gs_q10_row['survey_incentive_choice'].iloc[0] == 'yes_conditional'
    assert r1_gs_q10_row['survey_incentive_pct_required'].iloc[0] == 10.0

    # R2, Waschmaschine: "Ja, +", "20" -> incentive_choice='yes_conditional', pct_required=20.0
    r2_wm_q10_row = result_df[
        (result_df['respondent_id'] == 'R2') & (result_df['device'] == 'Waschmaschine')
    ]
    assert r2_wm_q10_row['survey_incentive_choice'].iloc[0] == 'yes_conditional'
    assert r2_wm_q10_row['survey_incentive_pct_required'].iloc[0] == 20.0

    # R3, Bürogeräte: "Ja, für mehr als 24 Stunden" -> 30.0
    r3_bg_q9 = result_df[
        (result_df['respondent_id'] == 'R3') & (result_df['device'] == 'Bürogeräte')
    ]['survey_max_duration_h'].iloc[0]
    assert r3_bg_q9 == 30.0, f"Fehler im Q9 Mapping für R3-Bürogeräte. Erwartet 30.0, bekam {r3_bg_q9}"

    
    # Überprüfe den Outer Merge (Gerät 'Ofen' nur in Q10-Daten)
    # Sollte eine Zeile für R3, Ofen haben, mit survey_max_duration_h = NaN
    # und survey_incentive_choice = 'yes_conditional', survey_incentive_pct_required = 15.0
    r3_ofen_row = result_df[
        (result_df['respondent_id'] == 'R3') & (result_df['device'] == 'Ofen')
    ]
    assert not r3_ofen_row.empty, "Zeile für R3, Ofen (nur in Q10-Daten) sollte existieren."
    assert pd.isna(r3_ofen_row['survey_max_duration_h'].iloc[0]), "survey_max_duration_h für R3, Ofen sollte NaN sein."
    assert r3_ofen_row['survey_incentive_choice'].iloc[0] == 'yes_conditional'
    assert r3_ofen_row['survey_incentive_pct_required'].iloc[0] == 15.0

    # Überprüfe die Anzahl der Zeilen (R1: 2 Geräte, R2: 2 Geräte, R3: 1 Gerät -> 5 Zeilen)
    assert len(result_df) == 6, f"Erwartet 6 Zeilen im Ergebnis, bekam {len(result_df)}"

    print("\nTest test_prepare_survey_flexibility_data_logic erfolgreich durchgelaufen (wenn keine Assertions fehlschlagen).")

# Um die Tests auszuführen, würdest du im Terminal (im PowerE Hauptverzeichnis) ausführen:
# pytest tests/logic/respondent_level_model/flexibility_potential/test_a_survey_data_preparer.py