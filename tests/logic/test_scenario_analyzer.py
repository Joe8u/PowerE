# PowerE/tests/logic/test_scenario_analyzer.py

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Importiere die zu testende Hauptfunktion
from logic.scenario_analyzer import evaluate_dr_scenario

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
def sample_df_load_to_simulate(test_timestamps, simulation_appliances) -> pd.DataFrame:
    """Erzeugt Beispiel-Lastprofile für die zu simulierenden Geräte."""
    data = {}
    # Waschmaschine läuft 13:00-14:00 mit 1 kW
    data["Waschmaschine"] = pd.Series(0.0, index=test_timestamps, dtype=float)
    data["Waschmaschine"].loc[
        (test_timestamps >= pd.Timestamp("2024-01-01 13:00:00")) &
        (test_timestamps < pd.Timestamp("2024-01-01 14:00:00"))
    ] = 1.0

    # Geschirrspüler läuft 14:00-15:00 mit 0.8 kW
    data["Geschirrspüler"] = pd.Series(0.0, index=test_timestamps, dtype=float)
    data["Geschirrspüler"].loc[
        (test_timestamps >= pd.Timestamp("2024-01-01 14:00:00")) &
        (test_timestamps < pd.Timestamp("2024-01-01 15:00:00"))
    ] = 0.8
    return pd.DataFrame(data)

@pytest.fixture
def sample_shift_metrics(simulation_appliances) -> dict:
    """Beispiel Shift-Metriken (Ergebnisse aus Q9)."""
    metrics = {}
    for i, dev in enumerate(simulation_appliances):
        metrics[dev] = {
            "participation_rate": 0.8 + i*0.1, # Nur für Vollständigkeit, wird nicht direkt verwendet
            "lognorm_shape": 0.5 + i*0.1,
            "lognorm_loc": 0,
            "lognorm_scale": np.exp(1.0 + i*0.2),
            "expected_duration_willing": 3.0 + i,
            "median_duration_willing": 2.5 + i
        }
    return metrics

@pytest.fixture
def sample_df_participation_curve_q10(simulation_appliances) -> pd.DataFrame:
    """Beispiel Teilnahme-Kurve (Ergebnisse aus Q10)."""
    data = []
    for dev in simulation_appliances:
        data.append({"device": dev, "comp_pct": 0, "participation_pct": 0})
        data.append({"device": dev, "comp_pct": 10, "participation_pct": 50})
        data.append({"device": dev, "comp_pct": 20, "participation_pct": 100})
    return pd.DataFrame(data)

@pytest.fixture
def sample_event_parameters() -> dict:
    """Beispiel DR-Event Parameter."""
    return {
        'start_time': pd.Timestamp("2024-01-01 13:30:00"),
        'end_time': pd.Timestamp("2024-01-01 14:30:00"), # 1-Stunden-Event
        'required_duration_hours': 1.0,
        'incentive_percentage': 0.15 # 15% Anreizangebot
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
    # Einfache Preisstruktur: Teurer während eines Teils des Events
    prices = pd.Series(50.0, index=test_timestamps, dtype=float)
    prices.loc[
        (test_timestamps >= pd.Timestamp("2024-01-01 13:00:00")) &
        (test_timestamps < pd.Timestamp("2024-01-01 15:00:00"))
    ] = 150.0 # Teure Phase
    return prices

@pytest.fixture
def sample_df_reg_original_data(test_timestamps) -> pd.DataFrame:
    """Beispiel Regelenergiedaten."""
    # Einfach: konstanter Abruf und Preis während eines Teils des Events
    data = {
        'total_called_mw': pd.Series(0.0, index=test_timestamps, dtype=float),
        'avg_price_eur_mwh': pd.Series(0.0, index=test_timestamps, dtype=float)
    }
    mask = (test_timestamps >= pd.Timestamp("2024-01-01 13:30:00")) & \
           (test_timestamps < pd.Timestamp("2024-01-01 14:30:00"))
    data['total_called_mw'].loc[mask] = 5.0 # 5 MW Bedarf
    data['avg_price_eur_mwh'].loc[mask] = 200.0 # zu 200 EUR/MWh
    return pd.DataFrame(data)

@pytest.fixture
def sample_cost_model_assumptions() -> dict:
    """Beispiel Kostenmodell-Annahmen."""
    return {
        'avg_household_electricity_price_eur_kwh': 0.276, # Beispiel: 0.29 CHF umgerechnet
        'assumed_dr_events_per_month': 12,
        'as_displacement_factor': 0.1
    }

# --- Testfunktionen ---

def test_evaluate_dr_scenario_runs_and_returns_structure(
    sample_df_load_to_simulate,
    sample_shift_metrics,
    sample_df_participation_curve_q10,
    sample_event_parameters,
    sample_simulation_assumptions,
    sample_df_spot_prices_eur_mwh,
    sample_df_reg_original_data,
    sample_cost_model_assumptions,
    simulation_appliances # Die Liste der Geräte, die simuliert werden sollen
):
    """
    Testet, ob evaluate_dr_scenario ohne Fehler läuft und die erwartete Ausgabestruktur hat.
    """
    results = evaluate_dr_scenario(
        df_load_to_simulate=sample_df_load_to_simulate, # <<< Korrekter Name für den 1. Parameter
        # appliances_for_simulation WIRD NICHT MEHR ÜBERGEBEN
        shift_metrics=sample_shift_metrics,
        df_participation_curve_q10=sample_df_participation_curve_q10,
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
        "average_payout_rate_eur_per_kwh_event"
    ]
    for key in expected_keys:
        assert key in results, f"Erwarteter Schlüssel '{key}' fehlt im Ergebnis."

    # Typprüfungen (Beispiele)
    assert isinstance(results["value_added_eur"], float)
    assert isinstance(results["original_aggregated_load_kw"], pd.Series)
    assert isinstance(results["df_shiftable_per_appliance"], pd.DataFrame)
    assert isinstance(results["shifted_energy_per_device_kwh_event"], dict)

    # Prüfe Index und Spalten der Ergebnis-DataFrames (Beispiel für einen)
    if not sample_df_load_to_simulate.empty:
        pd.testing.assert_index_equal(results["df_shiftable_per_appliance"].index, sample_df_load_to_simulate.index)
        # Spalten sollten die simulierten Geräte sein
        assert all(col in results["df_shiftable_per_appliance"].columns for col in sample_df_load_to_simulate.columns)
        assert len(results["df_shiftable_per_appliance"].columns) == len(sample_df_load_to_simulate.columns)

# Hier könnten später spezifischere Tests für den Value Added etc. folgen,
# wenn die Erwartungswerte manuell berechenbar sind.
# def test_evaluate_dr_scenario_specific_value_added():
#     # ... Setup mit sehr einfachen, kontrollierten Daten ...
#     # results = evaluate_dr_scenario(...)
#     # assert results["value_added_eur"] == pytest.approx(MANUELL_BERECHNETER_WERT)