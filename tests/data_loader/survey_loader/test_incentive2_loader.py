# PowerE/tests/data_loader/survey_loader/test_incentive2_loader.py

import pytest
import pandas as pd
from pandas.testing import assert_frame_equal
import io # Für das Erstellen von CSV-ähnlichen String-Daten
from pathlib import Path

# Importiere die zu testende Funktion und die Liste der Geräte
# Passe den Importpfad ggf. an, wenn deine Ordnerstruktur anders ist
# Annahme: src ist im Python-Pfad oder Tests werden vom Root-Verzeichnis ausgeführt
from data_loader.survey_loader.incentive2_loader import load_q10_incentives_long, _Q10_DEVICES, _SURVEY_DATA_DIR, _INCENTIVE_FILE_NAME

# --- Pytest Fixtures ---

@pytest.fixture
def mock_survey_dir(tmp_path: Path) -> Path:
    """Erstellt ein temporäres Survey-Datenverzeichnis."""
    survey_dir = tmp_path / "processed" / "survey"
    survey_dir.mkdir(parents=True, exist_ok=True)
    return survey_dir

@pytest.fixture
def sample_q10_wide_csv_content_valid() -> str:
    """Erzeugt validen CSV-Inhalt für Frage 10 im Wide-Format."""
    header = "respondent_id,Geschirrspüler_choice,Geschirrspüler_pct,Waschmaschine_choice,Waschmaschine_pct\n"
    row1 = "resp1,Ja f,10,Ja +,15\n"
    row2 = "resp2,Nein,,Ja f,5\n" # Leerzeichen für pct bei Nein
    row3 = "resp3,Ja +,5,, \n"  # Leerzeichen/kein Wert für Waschmaschine
    return header + row1 + row2 + row3

@pytest.fixture
def sample_q10_wide_csv_content_missing_device(sample_q10_wide_csv_content_valid: str) -> str:
    """Erzeugt CSV-Inhalt, bei dem Spalten für 'Waschmaschine' fehlen."""
    # Entferne Waschmaschine-Spalten aus dem validen Inhalt
    lines = sample_q10_wide_csv_content_valid.splitlines()
    header_parts = lines[0].split(',')
    new_header_parts = [p for p in header_parts if not p.startswith("Waschmaschine")]
    lines[0] = ",".join(new_header_parts)
    
    new_lines = [lines[0]]
    for line in lines[1:]:
        row_parts = line.split(',')
        # Nehme respondent_id und die Geschirrspüler-Spalten (die ersten 3)
        new_lines.append(",".join(row_parts[:3]))
        
    return "\n".join(new_lines) + "\n"


# --- Testfunktionen ---

def test_load_q10_incentives_long_structure_and_types(monkeypatch, mock_survey_dir, sample_q10_wide_csv_content_valid):
    """
    Testet die Grundstruktur, Spaltennamen und Datentypen des geladenen DataFrames.
    """
    # Erstelle die Dummy-CSV-Datei im temporären Verzeichnis
    file_path = mock_survey_dir / _INCENTIVE_FILE_NAME
    with open(file_path, "w") as f:
        f.write(sample_q10_wide_csv_content_valid)

    # Monkeypatch, um den Pfad zu unserer Dummy-Datei zu verwenden
    monkeypatch.setattr("data_loader.survey_loader.incentive2_loader._SURVEY_DATA_DIR", mock_survey_dir) # Muss auf 'processed' zeigen

    df_long = load_q10_incentives_long()

    assert isinstance(df_long, pd.DataFrame), "Die Funktion sollte einen DataFrame zurückgeben."
    
    expected_columns = ['respondent_id', 'device', 'q10_choice_text', 'q10_pct_required_text']
    assert all(col in df_long.columns for col in expected_columns), "Einige erwartete Spalten fehlen."
    assert len(df_long.columns) == len(expected_columns), "Unerwartete Anzahl von Spalten."

    # Alle Spalten sollten object/string sein, wie vom Loader definiert
    for col in df_long.columns:
        assert df_long[col].dtype == object, f"Spalte '{col}' sollte dtype 'object' haben, hat aber '{df_long[col].dtype}'."

    # respondent_id und device sollten keine NaNs haben (basierend auf Transformation)
    assert not df_long['respondent_id'].isnull().any(), "respondent_id sollte keine NaNs enthalten."
    assert not df_long['device'].isnull().any(), "device sollte keine NaNs enthalten."
    
    # Basierend auf 3 Respondenten und 2 Geräten im sample CSV (Geschirrspüler, Waschmaschine)
    # Die _Q10_DEVICES Liste im Loader muss dies widerspiegeln für diesen Test
    # Wenn _Q10_DEVICES mehr Geräte enthält, die nicht im CSV sind, werden diese übersprungen
    # In sample_q10_wide_csv_content_valid sind 2 Geräte explizit definiert
    # Die aktuelle _Q10_DEVICES Liste im Loader hat 5 Geräte.
    # Die Funktion generiert Zeilen für jedes Gerät in _Q10_DEVICES, wenn die Spalten existieren.
    # Hier existieren Spalten für "Geschirrspüler" und "Waschmaschine".
    # Daher: 3 Respondenten * 2 Geräte = 6 Zeilen
    # Die Anzahl der _Q10_DEVICES die tatsächlich Spalten in sample_q10_wide_csv_content_valid haben ist 2.
    num_devices_in_sample_csv = 2 
    num_respondents_in_sample_csv = 3
    assert len(df_long) == num_respondents_in_sample_csv * num_devices_in_sample_csv, "Unerwartete Anzahl von Zeilen im langen Format."


def test_load_q10_incentives_long_transformation_values(monkeypatch, mock_survey_dir, sample_q10_wide_csv_content_valid):
    """Testet die korrekte Umwandlung der Werte für ein Beispiel."""
    file_path = mock_survey_dir / _INCENTIVE_FILE_NAME
    with open(file_path, "w") as f:
        f.write(sample_q10_wide_csv_content_valid)
    monkeypatch.setattr("data_loader.survey_loader.incentive2_loader._SURVEY_DATA_DIR", mock_survey_dir)

    df_long = load_q10_incentives_long()

    # Teste spezifische Werte für resp1 und Geschirrspüler
    resp1_gs = df_long[(df_long['respondent_id'] == "resp1") & (df_long['device'] == "Geschirrspüler")]
    assert len(resp1_gs) == 1
    assert resp1_gs.iloc[0]['q10_choice_text'] == "Ja f"
    assert resp1_gs.iloc[0]['q10_pct_required_text'] == "10"

    # Teste spezifische Werte für resp2 und Waschmaschine
    resp2_wm = df_long[(df_long['respondent_id'] == "resp2") & (df_long['device'] == "Waschmaschine")]
    assert len(resp2_wm) == 1
    assert resp2_wm.iloc[0]['q10_choice_text'] == "Ja f"
    assert resp2_wm.iloc[0]['q10_pct_required_text'] == "5"
    
    # Teste Fall mit leeren/fehlenden Werten (resp3, Waschmaschine)
    resp3_wm = df_long[(df_long['respondent_id'] == "resp3") & (df_long['device'] == "Waschmaschine")]
    assert len(resp3_wm) == 1
    assert pd.isna(resp3_wm.iloc[0]['q10_choice_text']) or resp3_wm.iloc[0]['q10_choice_text'] == '' # Je nachdem wie pd.read_csv leere Strings liest
    assert pd.isna(resp3_wm.iloc[0]['q10_pct_required_text']) or resp3_wm.iloc[0]['q10_pct_required_text'].strip() == ''


def test_load_q10_file_not_found(monkeypatch, mock_survey_dir):
    """Testet, ob FileNotFoundError ausgelöst wird, wenn die Datei nicht existiert."""
    # Stelle sicher, dass die Datei NICHT existiert
    file_path = mock_survey_dir / _INCENTIVE_FILE_NAME
    if file_path.exists():
        file_path.unlink()
    
    monkeypatch.setattr("data_loader.survey_loader.incentive2_loader._SURVEY_DATA_DIR", mock_survey_dir)
    
    with pytest.raises(FileNotFoundError):
        load_q10_incentives_long()

def test_load_q10_missing_device_columns_handled(monkeypatch, mock_survey_dir, sample_q10_wide_csv_content_missing_device, capsys):
    """Testet, ob Geräte übersprungen werden, wenn Spalten fehlen, und eine Warnung ausgegeben wird."""
    file_path = mock_survey_dir / _INCENTIVE_FILE_NAME
    with open(file_path, "w") as f:
        f.write(sample_q10_wide_csv_content_missing_device) # CSV ohne Waschmaschine-Spalten
    monkeypatch.setattr("data_loader.survey_loader.incentive2_loader._SURVEY_DATA_DIR", mock_survey_dir)

    df_long = load_q10_incentives_long()
    
    captured = capsys.readouterr()
    assert "Spalten für Gerät 'Waschmaschine'" in captured.out # Prüfe auf Warnung
    assert "Waschmaschine" not in df_long['device'].unique() # Waschmaschine sollte nicht im Ergebnis sein
    assert "Geschirrspüler" in df_long['device'].unique()   # Aber Geschirrspüler schon
    
    num_devices_in_sample_csv = 1 # Nur Geschirrspüler
    num_respondents_in_sample_csv = 3
    assert len(df_long) == num_respondents_in_sample_csv * num_devices_in_sample_csv