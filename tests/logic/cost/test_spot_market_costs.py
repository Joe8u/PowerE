# PowerE/tests/logic/cost/test_spot_market_costs.py

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

# Importiere die zu testende Funktion
# Annahme: Dein Projekt-Root ist im PYTHONPATH, wenn du pytest ausführst
# oder src/ ist als Source-Root in deiner IDE konfiguriert.
from logic.cost.spot_market_costs import calculate_spot_market_costs

# --- Pytest Fixtures für Testdaten ---

@pytest.fixture
def sample_15min_timestamps_4_intervals() -> pd.DatetimeIndex:
    """Erzeugt 4 Zeitstempel im 15-Minuten-Abstand."""
    return pd.to_datetime([
        "2024-01-01 10:00:00",
        "2024-01-01 10:15:00",
        "2024-01-01 10:30:00",
        "2024-01-01 10:45:00"
    ])

@pytest.fixture
def sample_hourly_timestamps_2_intervals() -> pd.DatetimeIndex:
    """Erzeugt 2 Zeitstempel im Stunden-Abstand."""
    return pd.to_datetime([
        "2024-01-01 10:00:00",
        "2024-01-01 11:00:00"
    ])

# --- Testfunktionen ---

def test_basic_cost_calculation_15min_interval(sample_15min_timestamps_4_intervals):
    """Testet eine einfache Kostenberechnung mit 15-Minuten-Intervallen."""
    timestamps = sample_15min_timestamps_4_intervals
    load_profile = pd.Series([10, 10, 20, 20], index=timestamps, name="load_kw", dtype=float) # kW
    # Preise in EUR/MWh. Wenn Spotpreise stündlich sind, sollten sie auf 15min hochgerechnet/weitergeschrieben werden.
    # Hier nehmen wir an, die Preise sind bereits für das 15-Min-Raster vorhanden oder werden korrekt gematcht.
    spot_prices = pd.Series([50, 50, 60, 60], index=timestamps, name="price_eur_mwh", dtype=float) # EUR/MWh

    # Erwartete Berechnung:
    # Intervall 1: 10 kW * 0.25 h * (50 EUR/MWh / 1000 kWh/MWh) = 0.125 EUR
    # Intervall 2: 10 kW * 0.25 h * (50 EUR/MWh / 1000 kWh/MWh) = 0.125 EUR
    # Intervall 3: 20 kW * 0.25 h * (60 EUR/MWh / 1000 kWh/MWh) = 0.300 EUR
    # Intervall 4: 20 kW * 0.25 h * (60 EUR/MWh / 1000 kWh/MWh) = 0.300 EUR
    # Total = 0.125 + 0.125 + 0.300 + 0.300 = 0.85 EUR
    expected_cost = 0.85

    actual_cost = calculate_spot_market_costs(load_profile, spot_prices)
    assert actual_cost == pytest.approx(expected_cost)

def test_hourly_prices_on_15min_load(sample_15min_timestamps_4_intervals, sample_hourly_timestamps_2_intervals):
    """Testet, wie stündliche Preise auf 15-Min-Lasten angewendet werden (ffill)."""
    load_timestamps = sample_15min_timestamps_4_intervals # 10:00, 10:15, 10:30, 10:45
    load_profile = pd.Series([10, 10, 20, 20], index=load_timestamps, name="load_kw", dtype=float)

    price_timestamps = sample_hourly_timestamps_2_intervals # 10:00, 11:00
    # Preis für 10:00-11:00 ist 50 EUR/MWh, für 11:00-12:00 ist 80 EUR/MWh
    spot_prices = pd.Series([50, 80], index=price_timestamps, name="price_eur_mwh", dtype=float)

    # Erwartete Berechnung (durch ffill in calculate_spot_market_costs):
    # aligned_spot_prices für 10:00, 10:15, 10:30, 10:45 wird [50, 50, 50, 50]
    # Intervall 1 (10:00): 10 kW * 0.25 h * (50 EUR/MWh / 1000) = 0.125 EUR
    # Intervall 2 (10:15): 10 kW * 0.25 h * (50 EUR/MWh / 1000) = 0.125 EUR
    # Intervall 3 (10:30): 20 kW * 0.25 h * (50 EUR/MWh / 1000) = 0.250 EUR
    # Intervall 4 (10:45): 20 kW * 0.25 h * (50 EUR/MWh / 1000) = 0.250 EUR
    # Total = 0.125 + 0.125 + 0.250 + 0.250 = 0.75 EUR
    expected_cost = 0.75

    actual_cost = calculate_spot_market_costs(load_profile, spot_prices)
    assert actual_cost == pytest.approx(expected_cost)

def test_zero_load_returns_zero_cost(sample_15min_timestamps_4_intervals):
    """Testet, ob bei Nulllast die Kosten Null sind."""
    timestamps = sample_15min_timestamps_4_intervals
    load_profile = pd.Series([0, 0, 0, 0], index=timestamps, name="load_kw", dtype=float)
    spot_prices = pd.Series([50, 50, 60, 60], index=timestamps, name="price_eur_mwh", dtype=float)
    
    expected_cost = 0.0
    actual_cost = calculate_spot_market_costs(load_profile, spot_prices)
    assert actual_cost == pytest.approx(expected_cost)

def test_zero_prices_returns_zero_cost(sample_15min_timestamps_4_intervals):
    """Testet, ob bei Nullpreisen die Kosten Null sind."""
    timestamps = sample_15min_timestamps_4_intervals
    load_profile = pd.Series([10, 10, 20, 20], index=timestamps, name="load_kw", dtype=float)
    spot_prices = pd.Series([0, 0, 0, 0], index=timestamps, name="price_eur_mwh", dtype=float)
    
    expected_cost = 0.0
    actual_cost = calculate_spot_market_costs(load_profile, spot_prices)
    assert actual_cost == pytest.approx(expected_cost)

def test_empty_inputs_return_zero_cost():
    """Testet, ob leere Inputs zu Kosten von Null führen."""
    empty_load = pd.Series(dtype=float)
    empty_prices = pd.Series(dtype=float)
    timestamps = pd.to_datetime(["2024-01-01 10:00:00"])
    some_load = pd.Series([10], index=timestamps)
    some_prices = pd.Series([50], index=timestamps)

    assert calculate_spot_market_costs(empty_load, some_prices) == 0.0
    assert calculate_spot_market_costs(some_load, empty_prices) == 0.0
    assert calculate_spot_market_costs(empty_load, empty_prices) == 0.0
    
def test_input_with_nans_in_load(sample_15min_timestamps_4_intervals):
    """Testet den Umgang mit NaNs in den Lastdaten."""
    timestamps = sample_15min_timestamps_4_intervals
    load_profile = pd.Series([10, np.nan, 20, np.nan], index=timestamps, dtype=float)
    spot_prices = pd.Series([50, 50, 60, 60], index=timestamps, dtype=float)
    
    # Erwartete Berechnung (NaNs in Last werden bei Multiplikation zu NaN, np.nansum behandelt sie als 0):
    # Intervall 1: 10 kW * 0.25 h * (50/1000) = 0.125 EUR
    # Intervall 2: NaN -> 0 EUR
    # Intervall 3: 20 kW * 0.25 h * (60/1000) = 0.300 EUR
    # Intervall 4: NaN -> 0 EUR
    # Total = 0.125 + 0.300 = 0.425 EUR
    expected_cost = 0.425
    actual_cost = calculate_spot_market_costs(load_profile, spot_prices)
    assert actual_cost == pytest.approx(expected_cost)

def test_input_with_nans_in_price(sample_15min_timestamps_4_intervals):
    """Testet den Umgang mit NaNs in den Preisdaten (nach Reindex)."""
    timestamps = sample_15min_timestamps_4_intervals
    load_profile = pd.Series([10, 10, 20, 20], index=timestamps, dtype=float)
    # Preise mit Lücke, die durch ffill/bfill gefüllt werden sollten
    price_idx_with_gap = pd.to_datetime(["2024-01-01 10:00:00", "2024-01-01 10:30:00"])
    spot_prices_gappy = pd.Series([50, 60], index=price_idx_with_gap, dtype=float)
    
    # Erwartete Berechnung nach ffill (10:00->50, 10:15->50, 10:30->60, 10:45->60):
    # Intervall 1 (10:00): 10 kW * 0.25 h * (50/1000) = 0.125 EUR
    # Intervall 2 (10:15): 10 kW * 0.25 h * (50/1000) = 0.125 EUR
    # Intervall 3 (10:30): 20 kW * 0.25 h * (60/1000) = 0.300 EUR
    # Intervall 4 (10:45): 20 kW * 0.25 h * (60/1000) = 0.300 EUR
    # Total = 0.125 + 0.125 + 0.300 + 0.300 = 0.85 EUR
    expected_cost = 0.85
    actual_cost = calculate_spot_market_costs(load_profile, spot_prices_gappy)
    assert actual_cost == pytest.approx(expected_cost)

def test_single_data_point_load_profile(sample_15min_timestamps_4_intervals):
    """ Testet Verhalten mit nur einem Datenpunkt im Lastprofil. 
        Die Funktion sollte eine Warnung ausgeben und eine angenommene Intervalldauer verwenden.
    """
    # Wir verwenden nur den ersten Zeitstempel
    single_timestamp_index = sample_15min_timestamps_4_intervals[:1] 
    load_profile = pd.Series([10], index=single_timestamp_index, dtype=float) # 10 kW
    spot_prices = pd.Series([40], index=single_timestamp_index, dtype=float)  # 40 EUR/MWh
    
    # Annahme in calculate_spot_market_costs für einzelnen Punkt ist 0.25h (Warnung wird ausgegeben)
    # Kosten = 10 kW * 0.25 h * (40 EUR/MWh / 1000 kWh/MWh) = 0.1 EUR
    expected_cost = 0.1
    
    actual_cost = calculate_spot_market_costs(load_profile, spot_prices)
    assert actual_cost == pytest.approx(expected_cost)