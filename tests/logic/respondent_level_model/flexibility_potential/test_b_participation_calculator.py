# PowerE/tests/logic/respondent_level_model/flexibility_potential/test_b_participation_calculator.py
import pandas as pd
import numpy as np
import pytest

# Importiere die zu testende Funktion
from src.logic.respondent_level_model.flexibility_potential.b_participation_calculator import calculate_participation_metrics

@pytest.fixture
def sample_survey_flex_data() -> pd.DataFrame:
    """
    Erstellt einen Beispiel-DataFrame, wie er von prepare_survey_flexibility_data()
    zurückgegeben werden könnte, um verschiedene Szenarien zu testen.
    """
    data = {
        'respondent_id': [
            'R1', 'R1', # R1 für 2 Geräte
            'R2', 'R2', # R2 für 2 Geräte
            'R3',       # R3 für 1 Gerät
            'R4',       # R4 für 1 Gerät (wird nicht teilnehmen - Dauer)
            'R5',       # R5 für 1 Gerät (wird nicht teilnehmen - Anreiz)
            'R6',       # R6 für 1 Gerät (lehnt ab)
            'R7',       # R7 für 1 Gerät (Q9=0, Event > 0)
            'R8'        # R8 für ein anderes Gerät
        ],
        'device': [
            'Geschirrspüler', 'Waschmaschine',    # R1
            'Geschirrspüler', 'Waschmaschine',    # R2
            'Geschirrspüler',                     # R3
            'Geschirrspüler',                     # R4
            'Geschirrspüler',                     # R5
            'Geschirrspüler',                     # R6
            'Geschirrspüler',                     # R7
            'Ofen'                                # R8
        ],
        'survey_max_duration_h': [
            4.5, 1.5,      # R1
            9.0, 24.0,     # R2
            4.5,           # R3
            1.5,           # R4 (Dauer zu kurz für 3h Event)
            4.5,           # R5
            4.5,           # R6
            0.0,           # R7 (Q9 "Nein, auf keinen Fall")
            9.0            # R8
        ],
        'survey_incentive_choice': [
            'yes_conditional', 'yes_fixed',      # R1
            'yes_fixed', 'yes_conditional',      # R2
            'yes_conditional',                   # R3
            'yes_fixed',                         # R4
            'yes_conditional',                   # R5
            'no',                                # R6
            'yes_fixed',                         # R7
            'yes_conditional'                    # R8
        ],
        'survey_incentive_pct_required': [
            10.0, 0.0,      # R1 (GS: 10% gefordert, WM: fest)
            0.0, 15.0,      # R2 (GS: fest, WM: 15% gefordert)
            20.0,           # R3 (GS: 20% gefordert)
            0.0,            # R4 (GS: fest)
            25.0,           # R5 (GS: 25% gefordert - zu hoch für 20% Angebot)
            np.nan,         # R6 (GS: lehnt ab)
            0.0,            # R7 (GS: fest, aber Q9=0)
            10.0            # R8 (Ofen: 10% gefordert)
        ]
    }
    return pd.DataFrame(data)

# --- Testfälle ---

def test_no_participants_if_device_data_empty(sample_survey_flex_data):
    """Testet, dass 0 Teilnehmer zurückgegeben werden, wenn keine Daten für das Zielgerät vorhanden sind."""
    metrics = calculate_participation_metrics(
        df_survey_flex_input=sample_survey_flex_data,
        target_appliance="Nicht_Existierendes_Gerät",
        event_duration_h=3.0,
        offered_incentive_pct=10.0
    )
    assert metrics['num_participants'] == 0
    assert metrics['base_population'] == 0
    assert metrics['raw_participation_rate'] == 0.0

def test_fixed_participation_duration_met(sample_survey_flex_data):
    """R2, Geschirrspüler: 'yes_fixed', survey_max_duration_h=9.0. Event: 3.0h, Anreiz egal."""
    metrics = calculate_participation_metrics(
        df_survey_flex_input=sample_survey_flex_data,
        target_appliance="Geschirrspüler",
        event_duration_h=3.0,
        offered_incentive_pct=0.0 # Anreiz sollte egal sein für 'yes_fixed'
    )
    # Erwartet: R2 nimmt für Geschirrspüler teil.
    # R1 (10% cond), R3 (20% cond), R4 (1.5h zu kurz), R5 (25% req), R6 (no), R7 (0h)
    # Basispopulation für Geschirrspüler: R1, R2, R3, R4, R5, R6, R7 -> 7
    # Teilnehmer: R2 (fixed, 9h >= 3h)
    assert metrics['num_participants'] == 1, "R2 sollte für Geschirrspüler teilnehmen (fixed, Dauer ok)"
    assert metrics['base_population'] == 7
    assert metrics['raw_participation_rate'] == 1/7

def test_fixed_participation_duration_not_met(sample_survey_flex_data):
    """R4, Geschirrspüler: 'yes_fixed', survey_max_duration_h=1.5. Event: 3.0h."""
    # R4 würde teilnehmen, wenn die Dauer passt.
    # Hier testen wir speziell, ob die Dauerprüfung greift.
    df_r4_only = sample_survey_flex_data[sample_survey_flex_data['respondent_id'] == 'R4'].copy()
    metrics = calculate_participation_metrics(
        df_survey_flex_input=df_r4_only, # Nur R4 betrachten
        target_appliance="Geschirrspüler",
        event_duration_h=3.0, # Event ist länger als R4 kann
        offered_incentive_pct=0.0
    )
    assert metrics['num_participants'] == 0, "R4 sollte nicht teilnehmen (Dauer nicht erfüllt)"
    assert metrics['base_population'] == 1

def test_conditional_participation_incentive_and_duration_met(sample_survey_flex_data):
    """R1, Geschirrspüler: 'yes_conditional', 10% req, survey_max_duration_h=4.5. Event: 3.0h, 15% Angebot."""
    metrics = calculate_participation_metrics(
        df_survey_flex_input=sample_survey_flex_data,
        target_appliance="Geschirrspüler",
        event_duration_h=3.0,
        offered_incentive_pct=15.0
    )
    # Basispopulation GS: 7
    # Teilnehmer:
    # R1: yes_cond, 10% <= 15%, 4.5h >= 3h -> JA
    # R2: yes_fixed, 9h >= 3h -> JA
    # R3: yes_cond, 20% > 15% -> NEIN
    # R4: yes_fixed, 1.5h < 3h -> NEIN (Dauer)
    # R5: yes_cond, 25% > 15% -> NEIN (Anreiz)
    # R6: no -> NEIN
    # R7: yes_fixed, 0h < 3h -> NEIN (Dauer wegen Q9=0)
    assert metrics['num_participants'] == 2, "R1 und R2 sollten für Geschirrspüler teilnehmen"
    assert metrics['raw_participation_rate'] == 2/7

def test_conditional_participation_incentive_not_met(sample_survey_flex_data):
    """R5, Geschirrspüler: 'yes_conditional', 25% req, survey_max_duration_h=4.5. Event: 3.0h, 20% Angebot."""
    df_r5_only = sample_survey_flex_data[sample_survey_flex_data['respondent_id'] == 'R5'].copy()
    metrics = calculate_participation_metrics(
        df_survey_flex_input=df_r5_only,
        target_appliance="Geschirrspüler",
        event_duration_h=3.0,
        offered_incentive_pct=20.0 # Angebot (20%) < Forderung (25%)
    )
    assert metrics['num_participants'] == 0, "R5 sollte nicht teilnehmen (Anreiz nicht erfüllt)"

def test_choice_is_no_no_participation(sample_survey_flex_data):
    """R6, Geschirrspüler: 'no'."""
    df_r6_only = sample_survey_flex_data[sample_survey_flex_data['respondent_id'] == 'R6'].copy()
    metrics = calculate_participation_metrics(
        df_survey_flex_input=df_r6_only,
        target_appliance="Geschirrspüler",
        event_duration_h=3.0,
        offered_incentive_pct=50.0 # Hoher Anreiz, sollte aber egal sein
    )
    assert metrics['num_participants'] == 0, "R6 sollte nicht teilnehmen (incentive_choice='no')"

def test_q9_duration_zero_event_duration_positive(sample_survey_flex_data):
    """R7, Geschirrspüler: survey_max_duration_h=0.0. Event: 3.0h > 0."""
    df_r7_only = sample_survey_flex_data[sample_survey_flex_data['respondent_id'] == 'R7'].copy()
    metrics = calculate_participation_metrics(
        df_survey_flex_input=df_r7_only,
        target_appliance="Geschirrspüler",
        event_duration_h=3.0, # Positive Event-Dauer
        offered_incentive_pct=10.0
    )
    assert metrics['num_participants'] == 0, "R7 sollte nicht teilnehmen (Q9 Dauer war 0.0, Event-Dauer > 0)"

def test_base_population_correctness(sample_survey_flex_data):
    """Prüft, ob base_population korrekt für ein spezifisches Gerät gezählt wird."""
    metrics_gs = calculate_participation_metrics(sample_survey_flex_data, "Geschirrspüler", 1.0, 0)
    assert metrics_gs['base_population'] == 7 # R1, R2, R3, R4, R5, R6, R7 haben Geschirrspüler-Einträge

    metrics_wm = calculate_participation_metrics(sample_survey_flex_data, "Waschmaschine", 1.0, 0)
    assert metrics_wm['base_population'] == 2 # Nur R1, R2 haben Waschmaschinen-Einträge
    
    metrics_ofen = calculate_participation_metrics(sample_survey_flex_data, "Ofen", 1.0, 0)
    assert metrics_ofen['base_population'] == 1 # Nur R8 hat Ofen-Einträge

# Wenn du das Skript direkt ausführst (nicht über pytest), kannst du hier Testaufrufe machen:
if __name__ == '__main__':
    # Erstelle die Testdaten manuell, da die Fixtures nur mit pytest funktionieren
    test_data = sample_survey_flex_data() # Ruft die Fixture-Funktion direkt auf (nur für diesen Demo-Zweck)
    print("--- Manuelle Testaufrufe (außerhalb von pytest) ---")
    
    metrics1 = calculate_participation_metrics(test_data, "Geschirrspüler", 3.0, 15.0)
    print(f"Geschirrspüler (3.0h, 15%): Teilnehmer={metrics1['num_participants']}, Quote={metrics1['raw_participation_rate']:.2%}")

    metrics2 = calculate_participation_metrics(test_data, "Waschmaschine", 1.0, 0.0) # R1 sollte teilnehmen
    print(f"Waschmaschine (1.0h, 0%): Teilnehmer={metrics2['num_participants']}, Quote={metrics2['raw_participation_rate']:.2%}")
    
    # Du könntest hier die Assertions aus den Testfunktionen manuell prüfen, wenn du möchtest
    # z.B. if metrics1['num_participants'] == 2: print("Test 1 OK") else: print("Test 1 FAILED")