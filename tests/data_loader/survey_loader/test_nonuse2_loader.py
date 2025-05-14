# PowerE/tests/data_loader/survey_loader/test_nonuse2_loader.py

import pytest
import pandas as pd
from pandas.testing import assert_frame_equal
import io
from pathlib import Path
import numpy as np # Für pd.isna und np.nan

# Importiere die zu testende Funktion und die relevanten globalen Variablen
from data_loader.survey_loader.nonuse2_loader import (
    load_q9_nonuse_long,
    _Q9_DEVICES as LOADER_Q9_DEVICES, # Importiere die Geräteliste aus dem Loader
    _SURVEY_DATA_DIR as LOADER_SURVEY_DATA_DIR_ORIG,
    _NONUSE_FILE_NAME
)

# --- Pytest Fixtures ---

@pytest.fixture
def mock_survey_dir_q9(tmp_path: Path) -> Path:
    """Erstellt ein temporäres Survey-Datenverzeichnis für Q9-Tests."""
    # tmp_path ist eine eingebaute Pytest-Fixture, die ein temporäres Verzeichnis bereitstellt
    # Wir erstellen die Unterordner-Struktur, die der Loader erwartet
    survey_dir = tmp_path / "processed" / "survey" 
    survey_dir.mkdir(parents=True, exist_ok=True)
    return survey_dir

@pytest.fixture
def q9_sample_devices_in_csv() -> list:
    """Geräte, für die im Test-CSV tatsächlich Spalten existieren."""
    return ["Geschirrspüler", "Waschmaschine"]

@pytest.fixture
def q9_sample_csv_header(q9_sample_devices_in_csv: list) -> str:
    """Erzeugt den Header für die Q9 Test-CSV."""
    return "respondent_id," + ",".join(q9_sample_devices_in_csv) + "\n"

@pytest.fixture
def q9_sample_csv_subheader_row(q9_sample_devices_in_csv: list) -> str:
    """Erzeugt die problematische Sub-Header-Zeile für die Q9 Test-CSV."""
    # Annahme: respondent_id ist leer, dann folgen die Gerätenamen
    return "," + ",".join(q9_sample_devices_in_csv) + "\n"

@pytest.fixture
def q9_sample_csv_data_rows() -> str:
    """Erzeugt einige Datenzeilen für die Q9 Test-CSV."""
    row1 = "resp1,Ja max 3h,Nein auf keinen Fall\n"
    row2 = "resp2,Ja 3-6h,Ja max 3h\n"
    row3 = "resp3,,Ja 6-12h\n" # Geschirrspüler-Antwort leer
    return row1 + row2 + row3

@pytest.fixture
def q9_wide_csv_with_subheader(q9_sample_csv_header, q9_sample_csv_subheader_row, q9_sample_csv_data_rows) -> str:
    """Kombiniert Header, Sub-Header und Daten für einen Testfall."""
    return q9_sample_csv_header + q9_sample_csv_subheader_row + q9_sample_csv_data_rows

@pytest.fixture
def q9_wide_csv_clean(q9_sample_csv_header, q9_sample_csv_data_rows) -> str:
    """Kombiniert Header und Daten (OHNE Sub-Header) für einen Testfall."""
    return q9_sample_csv_header + q9_sample_csv_data_rows

@pytest.fixture
def q9_wide_csv_missing_one_device(q9_sample_devices_in_csv) -> str:
    """Erzeugt CSV-Inhalt, bei dem Spalten für das zweite Gerät fehlen."""
    device_to_keep = q9_sample_devices_in_csv[0] # z.B. Geschirrspüler
    header = f"respondent_id,{device_to_keep}\n"
    row1 = "resp1,Ja max 3h\n"
    row2 = "resp2,Ja 3-6h\n"
    row3 = "resp3,\n"
    return header + row1 + row2 + row3


# --- Testfunktionen ---

def test_load_q9_structure_and_types_with_subheader_cleaning(monkeypatch, mock_survey_dir_q9, q9_wide_csv_with_subheader, q9_sample_devices_in_csv):
    """Testet Struktur, Typen und die Bereinigung der Sub-Header-Zeile."""
    file_path = mock_survey_dir_q9 / _NONUSE_FILE_NAME
    with open(file_path, "w") as f:
        f.write(q9_wide_csv_with_subheader)

    monkeypatch.setattr("data_loader.survey_loader.nonuse2_loader._SURVEY_DATA_DIR", mock_survey_dir_q9)

    # Wichtig: Stelle sicher, dass _Q9_DEVICES im Loader die q9_sample_devices_in_csv abdeckt
    # oder patche _Q9_DEVICES für diesen Test, um präzise zu sein.
    # Hier gehen wir davon aus, dass _Q9_DEVICES im Loader mindestens diese Geräte enthält.
    # Die Logik im Loader sollte Geräte überspringen, die nicht in der CSV sind.
    
    df_long = load_q9_nonuse_long()

    assert isinstance(df_long, pd.DataFrame)
    expected_columns = ['respondent_id', 'device', 'q9_duration_text']
    assert all(col in df_long.columns for col in expected_columns)
    assert len(df_long.columns) == len(expected_columns)
    for col in df_long.columns:
        assert df_long[col].dtype == object

    assert not df_long['respondent_id'].isnull().any(), "Alle respondent_ids sollten nach Bereinigung gültig sein."
    
    # Nach Entfernung der Sub-Header-Zeile und Transformation: 3 Respondenten * 2 Geräte = 6 Zeilen
    num_respondents_in_sample_data = 3
    assert len(df_long) == num_respondents_in_sample_data * len(q9_sample_devices_in_csv)
    assert set(df_long['device'].unique()) == set(q9_sample_devices_in_csv)

    # Überprüfen, dass keine Gerätenamen in q9_duration_text sind
    for device_name in q9_sample_devices_in_csv:
        assert device_name not in df_long['q9_duration_text'].unique()


def test_load_q9_transformation_values(monkeypatch, mock_survey_dir_q9, q9_wide_csv_clean, q9_sample_devices_in_csv):
    """Testet korrekte Werte nach Transformation (mit sauberer CSV ohne Sub-Header)."""
    file_path = mock_survey_dir_q9 / _NONUSE_FILE_NAME
    with open(file_path, "w") as f:
        f.write(q9_wide_csv_clean) # Verwende hier die saubere CSV
    monkeypatch.setattr("data_loader.survey_loader.nonuse2_loader._SURVEY_DATA_DIR", mock_survey_dir_q9)
    
    # Für diesen Test patchen wir _Q9_DEVICES im Loader, um exakt q9_sample_devices_in_csv zu entsprechen
    original_loader_devices = LOADER_Q9_DEVICES[:]
    monkeypatch.setattr("data_loader.survey_loader.nonuse2_loader._Q9_DEVICES", q9_sample_devices_in_csv)

    df_long = load_q9_nonuse_long()

    monkeypatch.setattr("data_loader.survey_loader.nonuse2_loader._Q9_DEVICES", original_loader_devices) # Zurücksetzen


    resp1_gs = df_long[(df_long['respondent_id'] == "resp1") & (df_long['device'] == "Geschirrspüler")]
    assert len(resp1_gs) == 1
    assert resp1_gs.iloc[0]['q9_duration_text'] == "Ja max 3h"

    resp3_wm = df_long[(df_long['respondent_id'] == "resp3") & (df_long['device'] == "Waschmaschine")]
    assert len(resp3_wm) == 1
    assert resp3_wm.iloc[0]['q9_duration_text'] == "Ja 6-12h"
    
    resp3_gs = df_long[(df_long['respondent_id'] == "resp3") & (df_long['device'] == "Geschirrspüler")]
    assert len(resp3_gs) == 1
    assert pd.isna(resp3_gs.iloc[0]['q9_duration_text']) # q9_duration_text.replace('', np.nan) im Loader


def test_load_q9_file_not_found(monkeypatch, mock_survey_dir_q9):
    file_path = mock_survey_dir_q9 / _NONUSE_FILE_NAME
    if file_path.exists():
        file_path.unlink()
    monkeypatch.setattr("data_loader.survey_loader.nonuse2_loader._SURVEY_DATA_DIR", mock_survey_dir_q9)
    
    with pytest.raises(FileNotFoundError):
        load_q9_nonuse_long()

def test_load_q9_missing_device_columns_handled(monkeypatch, mock_survey_dir_q9, q9_wide_csv_missing_one_device, q9_sample_devices_in_csv, capsys):
    file_path = mock_survey_dir_q9 / _NONUSE_FILE_NAME
    with open(file_path, "w") as f:
        f.write(q9_wide_csv_missing_one_device) # CSV nur mit erstem Gerät aus q9_sample_devices_in_csv
    monkeypatch.setattr("data_loader.survey_loader.nonuse2_loader._SURVEY_DATA_DIR", mock_survey_dir_q9)

    # _Q9_DEVICES im Loader soll beide Geräte erwarten, aber CSV liefert nur eines
    original_loader_devices = LOADER_Q9_DEVICES[:]
    monkeypatch.setattr("data_loader.survey_loader.nonuse2_loader._Q9_DEVICES", q9_sample_devices_in_csv)

    df_long = load_q9_nonuse_long()
    
    captured = capsys.readouterr()
    device_actually_missing_in_csv = q9_sample_devices_in_csv[1] # Das zweite Gerät
    
    assert f"Spalte für Gerät '{device_actually_missing_in_csv}' nicht in CSV für Frage 9 gefunden" in captured.out
    assert device_actually_missing_in_csv not in df_long['device'].unique()
    assert q9_sample_devices_in_csv[0] in df_long['device'].unique()
    
    num_devices_actually_in_csv = 1
    num_respondents_in_sample_data = 3
    assert len(df_long) == num_respondents_in_sample_data * num_devices_actually_in_csv

    monkeypatch.setattr("data_loader.survey_loader.nonuse2_loader._Q9_DEVICES", original_loader_devices)