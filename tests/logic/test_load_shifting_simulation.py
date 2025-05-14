# PowerE/tests/logic/test_scenario_analyzer.py

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Importiere die zu testende Hauptfunktion
from logic.scenario_analyzer import evaluate_dr_scenario

# Dieser Import wird für die Struktur der Fixture sample_df_respondent_flexibility verwendet,
# um sicherzustellen, dass die Testdaten der erwarteten Struktur entsprechen.
# Es ist nicht zwingend notwendig, wenn die Struktur manuell korrekt erstellt wird,
# aber es hilft, die Konsistenz mit dem data_transformer zu verdeutlichen.
# from logic.respondent_level_model.data_transformer import create_respondent_flexibility_df 

# --- Pytest Fixtures für Testdaten ---

@pytest.fixture
def simulation_appliances() -> list:
    """Definiert die Geräte, die in der Simulation betrachtet werden."""
    return ["Waschmaschine", "Geschirrspüler"]

@pytest.fixture
def test_timestamps() -> pd.DatetimeIndex:
    """Erzeugt Zeitstempel für einen kurzen Testzeitraum."""
    return pd.date_range(start="2024-01-01 12:00:00", periods=16, freq="15min") # 4 Stunden

@pytest.fixture
def sample_df_average_load_profiles(test_timestamps, simulation_appliances) -> pd.DataFrame:
    """Erzeugt Beispiel-Durchschnitts-Lastprofile für die zu simulierenden Geräte."""
    data = {}
    # Waschmaschine läuft 13:00-14:00 mit 1 kW
    if "Waschmaschine" in simulation_appliances:
        data["Waschmaschine"] = pd.Series(0.0, index=test_timestamps, dtype=float)
        data["Waschmaschine"].loc[
            (test_timestamps >= pd.Timestamp("2024-01-01 13:00:00")) &
            (test_timestamps < pd.Timestamp("2024-01-01 14:00:00"))
        ] = 1.0

    # Geschirrspüler läuft 14:00-15:00 mit 0.8 kW
    if "Geschirrspüler" in simulation_appliances:
        data["Geschirrspüler"] = pd.Series(0.0, index=test_timestamps, dtype=float)
        data["Geschirrspüler"].loc[
            (test_timestamps >= pd.Timestamp("2024-01-01 14:00:00")) &
            (test_timestamps < pd.Timestamp("2024-01-01 15:00:00"))
        ] = 0.8
    
    # Sicherstellen, dass alle in simulation_appliances definierten Spalten vorhanden sind,
    # auch wenn oben keine spezifische Last definiert wurde (um KeyErrors zu vermeiden).
    for app in simulation_appliances:
        if app not in data:
            data[app] = pd.Series(0.0, index=test_timestamps, dtype=float)
            
    return pd.DataFrame(data)

@pytest.fixture
def sample_df_respondent_flexibility(simulation_appliances) -> pd.DataFrame:
    """
    Erzeugt einen Beispiel-DataFrame für die Flexibilität der Befragten.
    Struktur: 'respondent_id', 'device', 'max_duration_hours', 
              'incentive_choice', 'incentive_pct_required'
    """
    data = []
    # Respondent 1
    if "Waschmaschine" in simulation_appliances:
        data.append({
            'respondent_id': "R1", 'device': "Waschmaschine", 
            'max_duration_hours': 2.0, 'incentive_choice': "yes_conditional", 'incentive_pct_required': 10.0
        })
    if "Geschirrspüler" in simulation_appliances:
        data.append({
            'respondent_id': "R1", 'device': "Geschirrspüler", 
            'max_duration_hours': 1.0, 'incentive_choice': "yes_fixed", 'incentive_pct_required': 0.0 
        })

    # Respondent 2
    if "Waschmaschine" in simulation_appliances:
        data.append({
            'respondent_id': "R2", 'device': "Waschmaschine", 
            'max_duration_hours': 0.5, 'incentive_choice': "yes_fixed", 'incentive_pct_required': 0.0
        }) # Dauer zu kurz für ein 1h Event
    if "Geschirrspüler" in simulation_appliances:
        data.append({
            'respondent_id': "R2", 'device': "Geschirrspüler", 
            'max_duration_hours': 3.0, 'incentive_choice': "yes_conditional", 'incentive_pct_required': 20.0
        }) # Benötigter Anreiz zu hoch für 15% Angebot

    # Respondent 3 (stellt sicher, dass num_survey_base_for_dev > num_effective_shifters_dev sein kann)
    if "Waschmaschine" in simulation_appliances:
        data.append({
            'respondent_id': "R3", 'device': "Waschmaschine", 
            'max_duration_hours': 3.0, 'incentive_choice': "no", 'incentive_pct_required': np.nan
        })
        
    if not data: 
        # Fallback, um einen leeren DataFrame mit korrekten Spalten zurückzugeben, falls keine Geräte übereinstimmen
        return pd.DataFrame(columns=['respondent_id', 'device', 'max_duration_hours', 'incentive_choice', 'incentive_pct_required'])
        
    return pd.DataFrame(data)


@pytest.fixture
def sample_event_parameters() -> dict:
    """Beispiel DR-Event Parameter."""
    return {
        'start_time': pd.Timestamp("2024-01-01 13:30:00"),
        'end_time': pd.Timestamp("2024-01-01 14:30:00"), # 1-Stunden-Event
        'required_duration_hours': 1.0,
        'incentive_percentage': 0.15 # 15% Anreizangebot (als 0-1 Wert)
    }

@pytest.fixture
def sample_simulation_assumptions() -> dict:
    """Beispiel Simulationsannahmen."""
    return {
        'reality_discount_factor': 0.7, 
        'payback_model': {'type': 'uniform_after_event', 'duration_hours': 1.0, 'delay_hours': 0.25}
    }

@pytest.fixture
def sample_df_spot_prices_eur_mwh(test_timestamps) -> pd.Series:
    """Beispiel Spotpreise."""
    prices = pd.Series(50.0, index=test_timestamps, dtype=float)
    prices.loc[
        (test_timestamps >= pd.Timestamp("2024-01-01 13:00:00")) &
        (test_timestamps < pd.Timestamp("2024-01-01 15:00:00"))
    ] = 150.0 
    return prices

@pytest.fixture
def sample_df_reg_original_data(test_timestamps) -> pd.DataFrame:
    """Beispiel Regelenergiedaten."""
    data = {
        'total_called_mw': pd.Series(0.0, index=test_timestamps, dtype=float),
        'avg_price_eur_mwh': pd.Series(0.0, index=test_timestamps, dtype=float)
    }
    mask = (test_timestamps >= pd.Timestamp("2024-01-01 13:30:00")) & \
           (test_timestamps < pd.Timestamp("2024-01-01 14:30:00")) 
    data['total_called_mw'].loc[mask] = 5.0 
    data['avg_price_eur_mwh'].loc[mask] = 200.0
    return pd.DataFrame(data)

@pytest.fixture
def sample_cost_model_assumptions() -> dict:
    """Beispiel Kostenmodell-Annahmen."""
    return {
        'avg_household_electricity_price_eur_kwh': 0.276, 
        'assumed_dr_events_per_month': 12,
        'as_displacement_factor': 0.1 
    }

# --- Testfunktionen ---

def test_evaluate_dr_scenario_runs_and_returns_structure(
    sample_df_respondent_flexibility, 
    sample_df_average_load_profiles,  
    sample_event_parameters,
    sample_simulation_assumptions,
    sample_df_spot_prices_eur_mwh,
    sample_df_reg_original_data,
    sample_cost_model_assumptions
):
    """
    Testet, ob evaluate_dr_scenario ohne Fehler läuft und die erwartete Ausgabestruktur hat,
    unter Verwendung des respondenten-basierten Simulationsmodells.
    """
    if sample_df_respondent_flexibility.empty and not sample_df_average_load_profiles.empty :
        pytest.skip("Skipping test: sample_df_respondent_flexibility is empty but average loads are not.")
        
    results = evaluate_dr_scenario(
        df_respondent_flexibility=sample_df_respondent_flexibility, 
        df_average_load_profiles=sample_df_average_load_profiles,   
        event_parameters=sample_event_parameters,
        simulation_assumptions=sample_simulation_assumptions,
        df_spot_prices_eur_mwh=sample_df_spot_prices_eur_mwh,
        df_reg_original_data=sample_df_reg_original_data,
        cost_model_assumptions=sample_cost_model_assumptions
    )

    assert isinstance(results, dict), "Ergebnis sollte ein Dictionary sein."
    
    expected_keys = [
        "value_added_eur", "baseline_spot_costs_eur", "scenario_spot_costs_eur",
        "dr_program_costs_eur", "ancillary_service_savings_eur",
        "original_aggregated_load_kw", "final_shifted_aggregated_load_kw",
        "df_shiftable_per_appliance", "df_payback_per_appliance",
        "total_shifted_energy_kwh_event", "shifted_energy_per_device_kwh_event",
        "average_payout_rate_eur_per_kwh_event",
        "detailed_participation_for_costing" 
    ]
    for key in expected_keys:
        assert key in results, f"Erwarteter Schlüssel '{key}' fehlt im Ergebnis. Vorhandene Schlüssel: {list(results.keys())}"

    assert isinstance(results["value_added_eur"], (float, np.floating))
    assert isinstance(results["original_aggregated_load_kw"], pd.Series)
    assert isinstance(results["df_shiftable_per_appliance"], pd.DataFrame)
    assert isinstance(results["shifted_energy_per_device_kwh_event"], dict)
    assert isinstance(results["detailed_participation_for_costing"], list)

    if not sample_df_average_load_profiles.empty:
        pd.testing.assert_index_equal(results["df_shiftable_per_appliance"].index, sample_df_average_load_profiles.index)
        assert all(col in results["df_shiftable_per_appliance"].columns for col in sample_df_average_load_profiles.columns)
        assert len(results["df_shiftable_per_appliance"].columns) == len(sample_df_average_load_profiles.columns)
    elif "error" not in results: 
        assert results["df_shiftable_per_appliance"].empty


def test_evaluate_dr_scenario_empty_load_profiles(
    sample_df_respondent_flexibility, 
    sample_event_parameters,
    sample_simulation_assumptions,
    sample_df_spot_prices_eur_mwh,
    sample_df_reg_original_data,
    sample_cost_model_assumptions
):
    """Testet das Verhalten von evaluate_dr_scenario, wenn leere Lastprofile übergeben werden."""
    empty_average_load_profiles = pd.DataFrame()
    
    results = evaluate_dr_scenario(
        df_respondent_flexibility=sample_df_respondent_flexibility,
        df_average_load_profiles=empty_average_load_profiles,
        event_parameters=sample_event_parameters,
        simulation_assumptions=sample_simulation_assumptions,
        df_spot_prices_eur_mwh=sample_df_spot_prices_eur_mwh,
        df_reg_original_data=sample_df_reg_original_data,
        cost_model_assumptions=sample_cost_model_assumptions
    )
    
    # Gemäß der Logik in evaluate_dr_scenario bei leeren df_average_load_profiles
    assert results["value_added_eur"] == 0.0
    assert results["baseline_spot_costs_eur"] == 0.0
    assert results["scenario_spot_costs_eur"] == 0.0
    assert results["dr_program_costs_eur"] == 0.0
    assert results["ancillary_service_savings_eur"] == 0.0
    assert results["original_aggregated_load_kw"].empty
    assert results["final_shifted_aggregated_load_kw"].empty
    assert results["df_shiftable_per_appliance"].empty
    assert results["df_payback_per_appliance"].empty
    assert results["total_shifted_energy_kwh_event"] == 0.0
    assert not results["shifted_energy_per_device_kwh_event"] 
    assert results["average_payout_rate_eur_per_kwh_event"] == 0.0
    assert not results["detailed_participation_for_costing"]