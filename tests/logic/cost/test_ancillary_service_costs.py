# PowerE/tests/logic/cost/test_ancillary_service_costs.py

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

# Importiere die zu testende Funktion
from logic.cost.ancillary_service_costs import calculate_mfrr_savings_opportunity

# --- Pytest Fixtures für Testdaten ---

@pytest.fixture
def sample_index() -> pd.DatetimeIndex:
    """Erzeugt ein paar Zeitstempel im 15-Minuten-Abstand."""
    return pd.to_datetime([
        "2024-01-01 14:00:00", "2024-01-01 14:15:00",
        "2024-01-01 14:30:00", "2024-01-01 14:45:00",
        "2024-01-01 15:00:00"
    ])

@pytest.fixture
def interval_h() -> float:
    return 0.25

# --- Testfunktionen ---

def test_no_savings_if_no_dr_potential(sample_index, interval_h):
    """Testet, ob 0 Einsparungen zurückgegeben werden, wenn kein DR-Potenzial vorhanden ist."""
    df_reg = pd.DataFrame({
        'total_called_mw': [10, 10, 10, 10, 10],
        'avg_price_eur_mwh': [100, 100, 100, 100, 100]
    }, index=sample_index)
    df_shiftable_kw = pd.Series([0, 0, 0, 0, 0], index=sample_index, dtype=float)
    cost_dr_eur_mwh = 50.0
    
    savings = calculate_mfrr_savings_opportunity(df_reg, df_shiftable_kw, cost_dr_eur_mwh, interval_h)
    assert savings == 0.0

def test_no_savings_if_no_as_called(sample_index, interval_h):
    """Testet, ob 0 Einsparungen zurückgegeben werden, wenn keine Regelenergie abgerufen wurde."""
    df_reg = pd.DataFrame({
        'total_called_mw': [0, 0, 0, 0, 0],
        'avg_price_eur_mwh': [100, 100, 100, 100, 100]
    }, index=sample_index)
    df_shiftable_kw = pd.Series([10000, 10000, 10000, 10000, 10000], index=sample_index, dtype=float) # 10 MW
    cost_dr_eur_mwh = 50.0
    
    savings = calculate_mfrr_savings_opportunity(df_reg, df_shiftable_kw, cost_dr_eur_mwh, interval_h)
    assert savings == 0.0

def test_no_savings_if_dr_too_expensive(sample_index, interval_h):
    """Testet, ob 0 Einsparungen zurückgegeben werden, wenn DR teurer ist als Markt-RE."""
    df_reg = pd.DataFrame({
        'total_called_mw': [10, 10, 10, 10, 10],
        'avg_price_eur_mwh': [100, 100, 100, 100, 100]
    }, index=sample_index)
    df_shiftable_kw = pd.Series([10000, 10000, 10000, 10000, 10000], index=sample_index, dtype=float) # 10 MW
    cost_dr_eur_mwh = 150.0 # DR ist teurer
    
    savings = calculate_mfrr_savings_opportunity(df_reg, df_shiftable_kw, cost_dr_eur_mwh, interval_h)
    assert savings == 0.0

def test_basic_saving_scenario_dr_displaces_all_as(sample_index, interval_h):
    """DR ist günstiger und kann den gesamten RE-Bedarf decken."""
    df_reg = pd.DataFrame({
        'total_called_mw':   [10,  0, 10,  0, 10], # Bedarf in Intervall 1, 3, 5
        'avg_price_eur_mwh': [100, 80, 120, 90, 110]
    }, index=sample_index)
    # DR kann 12 MW (12000 kW) liefern, wenn es aktiv ist
    df_shiftable_kw = pd.Series([12000, 12000, 12000, 12000, 12000], index=sample_index, dtype=float)
    cost_dr_eur_mwh = 50.0
    
    # Erwartete Einsparung:
    # Int 1: min(10, 12) * 0.25h * (100-50) = 10 * 0.25 * 50 = 125 EUR
    # Int 2: kein RE-Bedarf -> 0 EUR
    # Int 3: min(10, 12) * 0.25h * (120-50) = 10 * 0.25 * 70 = 175 EUR
    # Int 4: kein RE-Bedarf -> 0 EUR
    # Int 5: min(10, 12) * 0.25h * (110-50) = 10 * 0.25 * 60 = 150 EUR
    # Total = 125 + 175 + 150 = 450 EUR
    expected_savings = 450.0
    
    actual_savings = calculate_mfrr_savings_opportunity(df_reg, df_shiftable_kw, cost_dr_eur_mwh, interval_h)
    assert actual_savings == pytest.approx(expected_savings)

def test_saving_scenario_dr_displaces_partial_as(sample_index, interval_h):
    """DR ist günstiger, kann aber nur einen Teil des RE-Bedarfs decken."""
    df_reg = pd.DataFrame({
        'total_called_mw':   [20,  0, 15,  0, 25], # Bedarf
        'avg_price_eur_mwh': [100, 80, 120, 90, 110]
    }, index=sample_index)
    # DR kann nur 10 MW (10000 kW) liefern
    df_shiftable_kw = pd.Series([10000, 10000, 10000, 10000, 10000], index=sample_index, dtype=float)
    cost_dr_eur_mwh = 50.0
    
    # Erwartete Einsparung:
    # Int 1: min(20, 10) * 0.25h * (100-50) = 10 * 0.25 * 50 = 125 EUR
    # Int 3: min(15, 10) * 0.25h * (120-50) = 10 * 0.25 * 70 = 175 EUR
    # Int 5: min(25, 10) * 0.25h * (110-50) = 10 * 0.25 * 60 = 150 EUR
    # Total = 125 + 175 + 150 = 450 EUR
    expected_savings = 450.0
    
    actual_savings = calculate_mfrr_savings_opportunity(df_reg, df_shiftable_kw, cost_dr_eur_mwh, interval_h)
    assert actual_savings == pytest.approx(expected_savings)

def test_saving_with_technical_availability_factor(sample_index, interval_h):
    """Testet den Einfluss des technical_availability_factor."""
    df_reg = pd.DataFrame({
        'total_called_mw':   [10],
        'avg_price_eur_mwh': [100]
    }, index=sample_index[:1]) # Nur ein Intervall für Einfachheit
    # DR hat theoretisch 20 MW Potenzial
    df_shiftable_kw = pd.Series([20000], index=sample_index[:1], dtype=float)
    cost_dr_eur_mwh = 50.0
    availability_factor = 0.4 # Nur 40% sind technisch verfügbar -> 20 MW * 0.4 = 8 MW
    
    # Erwartete Einsparung:
    # Verfügbares DR = 20 MW * 0.4 = 8 MW
    # Verdrängt = min(10 MW RE-Bedarf, 8 MW DR) = 8 MW
    # Einsparung = 8 MW * 0.25h * (100 - 50) EUR/MWh = 8 * 0.25 * 50 = 100 EUR
    expected_savings = 100.0
    
    actual_savings = calculate_mfrr_savings_opportunity(
        df_reg, df_shiftable_kw, cost_dr_eur_mwh, interval_h,
        technical_availability_factor=availability_factor
    )
    assert actual_savings == pytest.approx(expected_savings)

def test_empty_inputs_return_zero(interval_h, sample_index):
    """Testet, ob bei leeren Eingabe-DataFrames 0 zurückgegeben wird."""
    empty_df = pd.DataFrame()
    empty_series = pd.Series(dtype=float)
    
    # Dummy-Daten für den nicht-leeren Teil
    df_reg_ok = pd.DataFrame({'total_called_mw': [10], 'avg_price_eur_mwh': [100]}, index=sample_index[:1])
    df_shiftable_ok = pd.Series([10000], index=sample_index[:1], dtype=float)
    cost_dr_ok = 50.0

    assert calculate_mfrr_savings_opportunity(empty_df, df_shiftable_ok, cost_dr_ok, interval_h) == 0.0
    assert calculate_mfrr_savings_opportunity(df_reg_ok, empty_series, cost_dr_ok, interval_h) == 0.0
    assert calculate_mfrr_savings_opportunity(empty_df, empty_series, cost_dr_ok, interval_h) == 0.0

def test_interval_duration_zero_or_negative(sample_index):
    """Testet, ob bei Intervalldauer <= 0 auch 0 zurückgegeben wird."""
    df_reg = pd.DataFrame({'total_called_mw': [10], 'avg_price_eur_mwh': [100]}, index=sample_index[:1])
    df_shiftable_kw = pd.Series([10000], index=sample_index[:1], dtype=float)
    cost_dr_eur_mwh = 50.0

    assert calculate_mfrr_savings_opportunity(df_reg, df_shiftable_kw, cost_dr_eur_mwh, 0.0) == 0.0
    assert calculate_mfrr_savings_opportunity(df_reg, df_shiftable_kw, cost_dr_eur_mwh, -0.25) == 0.0