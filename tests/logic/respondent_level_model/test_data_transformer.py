# PowerE/tests/logic/respondent_level_model/test_data_transformer.py

import pytest
import pandas as pd
import numpy as np
from pandas.testing import assert_frame_equal # Wird oft für DataFrame-Vergleiche verwendet
from pathlib import Path # Importiert für monkeypatch, falls _SURVEY_DATA_DIR im Loader angepasst wird

# Importiere die zu testende Funktion
# Annahme: src ist im Python-Pfad (z.B. durch tests/conftest.py)
from logic.respondent_level_model.data_transformer import create_respondent_flexibility_df

# --- Pytest Fixtures für simulierte Loader-Ausgaben ---

@pytest.fixture
def mock_q9_data_fixture() -> pd.DataFrame: # Umbenannt, um Konflikte zu vermeiden, falls eine Variable mock_q9_data heißt
    """Simuliert die Ausgabe von load_q9_nonuse_long()."""
    data = {
        'respondent_id': ["resp1", "resp1", "resp2", "resp3", "resp_only_q9"],
        'device': ["Waschmaschine", "Geschirrspüler", "Waschmaschine", "Geschirrspüler", "Bürogeräte"],
        'q9_duration_text': [
            "Ja, für 3 bis 6 Stunden", # -> 4.5
            "Nein, auf keinen Fall",   # -> 0.0
            "Ja, aber maximal für 3 Stunden", # -> 1.5
            np.nan, # Fehlende Antwort
            "Ja, für 6 bis 12 Stunden" # -> 9.0
        ]
    }
    return pd.DataFrame(data)

@pytest.fixture
def mock_q10_data_fixture() -> pd.DataFrame: # Umbenannt
    """Simuliert die Ausgabe von load_q10_incentives_long()."""
    data = {
        'respondent_id': ["resp1", "resp1", "resp2", "resp2", "resp_only_q10"],
        'device': ["Waschmaschine", "Geschirrspüler", "Waschmaschine", "Bürogeräte", "Waschmaschine"],
        'q10_choice_text': ["Ja, +", "Ja, f", "Nein", "Ja, +", "Ja, f"],
        'q10_pct_required_text': ["15 % ", " ", None, "20", "5"] # Mit Leerzeichen, None etc.
    }
    return pd.DataFrame(data)

# --- Testfunktionen ---

def test_create_respondent_flexibility_df_successful_merge_and_transform(monkeypatch, mock_q9_data_fixture, mock_q10_data_fixture):
    """
    Testet die erfolgreiche Transformation und Zusammenführung von Q9- und Q10-Daten.
    """
    # Mocke die Loader-Funktionen, damit sie unsere Test-DataFrames zurückgeben
    monkeypatch.setattr("logic.respondent_level_model.data_transformer.load_q9_nonuse_long", lambda: mock_q9_data_fixture)
    monkeypatch.setattr("logic.respondent_level_model.data_transformer.load_q10_incentives_long", lambda: mock_q10_data_fixture)

    result_df = create_respondent_flexibility_df()

    assert isinstance(result_df, pd.DataFrame)
    
    expected_columns = [
        'respondent_id', 'device', 'max_duration_hours', 
        'incentive_choice', 'incentive_pct_required'
    ]
    assert all(col in result_df.columns for col in expected_columns), f"Fehlende Spalten: {set(expected_columns) - set(result_df.columns)}"
    assert len(result_df.columns) == len(expected_columns), f"Unerwartete Anzahl von Spalten: {len(result_df.columns)}, erwartet: {len(expected_columns)}"

    # Überprüfe einige transformierte Werte Stichprobenartig
    # Respondent 1, Waschmaschine
    r1_wm = result_df[(result_df['respondent_id'] == "resp1") & (result_df['device'] == "Waschmaschine")]
    assert len(r1_wm) == 1, "Eintrag für resp1, Waschmaschine nicht eindeutig gefunden."
    assert r1_wm.iloc[0]['max_duration_hours'] == 4.5
    assert r1_wm.iloc[0]['incentive_choice'] == "yes_conditional"
    assert r1_wm.iloc[0]['incentive_pct_required'] == 15.0

    # Respondent 1, Geschirrspüler
    r1_gs = result_df[(result_df['respondent_id'] == "resp1") & (result_df['device'] == "Geschirrspüler")]
    assert len(r1_gs) == 1, "Eintrag für resp1, Geschirrspüler nicht eindeutig gefunden."
    assert r1_gs.iloc[0]['max_duration_hours'] == 0.0
    assert r1_gs.iloc[0]['incentive_choice'] == "yes_fixed"
    assert r1_gs.iloc[0]['incentive_pct_required'] == 0.0

    # Respondent 2, Waschmaschine
    r2_wm = result_df[(result_df['respondent_id'] == "resp2") & (result_df['device'] == "Waschmaschine")]
    assert len(r2_wm) == 1, "Eintrag für resp2, Waschmaschine nicht eindeutig gefunden."
    assert r2_wm.iloc[0]['max_duration_hours'] == 1.5
    assert r2_wm.iloc[0]['incentive_choice'] == "no"
    assert pd.isna(r2_wm.iloc[0]['incentive_pct_required'])

    # Respondent 3, Geschirrspüler (nur in Q9-Daten)
    r3_gs = result_df[(result_df['respondent_id'] == "resp3") & (result_df['device'] == "Geschirrspüler")]
    assert len(r3_gs) == 1, "Eintrag für resp3, Geschirrspüler nicht eindeutig gefunden."
    assert pd.isna(r3_gs.iloc[0]['max_duration_hours']) 
    assert r3_gs.iloc[0]['incentive_choice'] == "unknown_choice_q10_missing" # Korrigiert basierend auf Transformer-Logik
    assert pd.isna(r3_gs.iloc[0]['incentive_pct_required'])

    # Respondent nur in Q9 ("resp_only_q9", "Bürogeräte")
    r_only_q9 = result_df[(result_df['respondent_id'] == "resp_only_q9") & (result_df['device'] == "Bürogeräte")]
    assert len(r_only_q9) == 1, "Eintrag für resp_only_q9, Bürogeräte nicht eindeutig gefunden."
    assert r_only_q9.iloc[0]['max_duration_hours'] == 9.0
    assert r_only_q9.iloc[0]['incentive_choice'] == "unknown_choice_q10_missing"
    assert pd.isna(r_only_q9.iloc[0]['incentive_pct_required'])

    # Respondent nur in Q10 ("resp_only_q10", "Waschmaschine")
    r_only_q10 = result_df[(result_df['respondent_id'] == "resp_only_q10") & (result_df['device'] == "Waschmaschine")]
    assert len(r_only_q10) == 1, "Eintrag für resp_only_q10, Waschmaschine nicht eindeutig gefunden."
    assert pd.isna(r_only_q10.iloc[0]['max_duration_hours'])
    assert r_only_q10.iloc[0]['incentive_choice'] == "yes_fixed"
    assert r_only_q10.iloc[0]['incentive_pct_required'] == 0.0 # Erwartet 0.0, da 'yes_fixed' dies im Transformer setzt

    # Überprüfe die Logik für 'yes_fixed' und pct_required=0 expliziter für r_only_q10
    # Im Transformer wird für 'yes_fixed' pct_required auf 0 gesetzt, falls es NaN war.
    # Wenn in mock_q10_data für 'yes_fixed' ein Wert bei pct steht (hier "5"), sollte dieser genommen und dann von der Logik
    # if choice == 'yes_fixed' -> pct = 0 überschrieben werden.
    assert r_only_q10.iloc[0]['incentive_pct_required'] == 0.0 # Korrigiert basierend auf Transformer-Logik für 'yes_fixed'


    # Überprüfe Datentypen
    assert result_df['max_duration_hours'].dtype == np.float64
    assert result_df['incentive_pct_required'].dtype == np.float64
    
    # Erwartete Anzahl Zeilen:
    # Q9 hat 5 Einträge. Q10 hat 5 Einträge.
    # (resp1,WM), (r1,GS), (r2,WM), (r3,GS), (r_only_q9,BG) von Q9
    # (resp1,WM), (r1,GS), (r2,WM), (r2,BG), (r_only_q10,WM) von Q10
    # Eindeutige (resp,dev) Paare:
    # (r1,WM), (r1,GS), (r2,WM), (r3,GS), (r_only_q9,BG), (r2,BG), (r_only_q10,WM) -> 7 Zeilen
    assert len(result_df) == 7, f"Unerwartete Zeilenzahl: {len(result_df)}"


def test_create_respondent_flexibility_df_empty_inputs(monkeypatch):
    """Testet das Verhalten, wenn einer oder beide Loader leere DataFrames zurückgeben."""
    empty_q9 = pd.DataFrame(columns=['respondent_id', 'device', 'q9_duration_text'])
    empty_q10 = pd.DataFrame(columns=['respondent_id', 'device', 'q10_choice_text', 'q10_pct_required_text'])

    # Fall 1: Q9 leer, Q10 hat Daten
    monkeypatch.setattr("logic.respondent_level_model.data_transformer.load_q9_nonuse_long", lambda: empty_q9.copy())
    monkeypatch.setattr("logic.respondent_level_model.data_transformer.load_q10_incentives_long", lambda: pd.DataFrame({
        'respondent_id': ["resp1"], 'device': ["Waschmaschine"], 
        'q10_choice_text': ["Ja, f"], 'q10_pct_required_text': [""]
    }))
    result1 = create_respondent_flexibility_df()
    assert not result1.empty
    assert len(result1) == 1
    assert result1.iloc[0]['device'] == "Waschmaschine"
    assert pd.isna(result1.iloc[0]['max_duration_hours'])
    assert result1.iloc[0]['incentive_choice'] == "yes_fixed"

    # Fall 2: Q10 leer, Q9 hat Daten
    monkeypatch.setattr("logic.respondent_level_model.data_transformer.load_q9_nonuse_long", lambda: pd.DataFrame({
        'respondent_id': ["resp1"], 'device': ["Waschmaschine"], 
        'q9_duration_text': ["Ja, aber maximal für 3 Stunden"]
    }))
    monkeypatch.setattr("logic.respondent_level_model.data_transformer.load_q10_incentives_long", lambda: empty_q10.copy())
    result2 = create_respondent_flexibility_df()
    assert not result2.empty
    assert len(result2) == 1
    assert result2.iloc[0]['device'] == "Waschmaschine"
    assert result2.iloc[0]['max_duration_hours'] == 1.5
    assert result2.iloc[0]['incentive_choice'] == "unknown_choice_q10_missing"

    # Fall 3: Beide leer
    monkeypatch.setattr("logic.respondent_level_model.data_transformer.load_q9_nonuse_long", lambda: empty_q9.copy())
    monkeypatch.setattr("logic.respondent_level_model.data_transformer.load_q10_incentives_long", lambda: empty_q10.copy())
    result3 = create_respondent_flexibility_df()
    # Die Funktion create_respondent_flexibility_df gibt einen leeren DF mit Spalten zurück, wenn beide Inputs leer sind.
    assert result3.empty or len(result3) == 0 # Je nachdem, wie 'empty' für einen DF mit Spalten aber ohne Zeilen definiert ist.
                                              # len(result3)==0 ist präziser.


def test_create_respondent_flexibility_df_file_not_found(monkeypatch):
    """Testet das Verhalten, wenn eine der Loader-Dateien nicht gefunden wird."""
    def mock_loader_raises_file_not_found():
        raise FileNotFoundError("Test File Not Found")

    # Teste, wenn Q9-Loader fehlschlägt
    monkeypatch.setattr("logic.respondent_level_model.data_transformer.load_q9_nonuse_long", mock_loader_raises_file_not_found)
    monkeypatch.setattr("logic.respondent_level_model.data_transformer.load_q10_incentives_long", lambda: pd.DataFrame({
        'respondent_id': ["resp1"], 'device': ["Waschmaschine"], 
        'q10_choice_text': ["Ja, f"], 'q10_pct_required_text': [""]
    })) # Q10 gibt normale Daten
    
    result_q9_fail = create_respondent_flexibility_df()
    # Erwartet einen DataFrame mit nur Q10-Daten, Q9-Spalten sollten NaN sein
    assert not result_q9_fail.empty
    assert result_q9_fail.iloc[0]['incentive_choice'] == "yes_fixed"
    assert pd.isna(result_q9_fail.iloc[0]['max_duration_hours'])


    # Teste, wenn Q10-Loader fehlschlägt (setze Q9-Loader zurück auf einen normalen Mock)
    monkeypatch.setattr("logic.respondent_level_model.data_transformer.load_q9_nonuse_long", lambda: pd.DataFrame({
         'respondent_id': ["resp1"], 'device': ["Waschmaschine"], 
         'q9_duration_text': ["Ja, aber maximal für 3 Stunden"]
    }))
    monkeypatch.setattr("logic.respondent_level_model.data_transformer.load_q10_incentives_long", mock_loader_raises_file_not_found)

    result_q10_fail = create_respondent_flexibility_df()
    assert not result_q10_fail.empty
    assert result_q10_fail.iloc[0]['max_duration_hours'] == 1.5
    assert result_q10_fail.iloc[0]['incentive_choice'] == "unknown_choice_q10_missing"