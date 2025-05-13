# PowerE/tests/logic/test_load_shifting_simulation.py

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.stats import lognorm

# Importiere die zu testende Funktion
# Annahme: Dein Projekt-Root ist im PYTHONPATH, wenn du pytest ausführst,
# oder du hast src/ als Source-Root in deiner IDE konfiguriert.
# Alternativ: from ...src.logic.load_shifting_simulation import run_load_shifting_simulation
from logic.load_shifting_simulation import run_load_shifting_simulation

# --- Pytest Fixtures für Testdaten ---

@pytest.fixture
def sample_appliances() -> list:
    return ["Waschmaschine", "Geschirrspüler"]

@pytest.fixture
def sample_timestamps() -> pd.DatetimeIndex:
    # Erzeugt Zeitstempel für 2 Tage in 15-Minuten-Intervallen
    return pd.date_range(start="2024-01-01 00:00:00", end="2024-01-02 23:45:00", freq="15min")

@pytest.fixture
def sample_df_load_profiles(sample_timestamps, sample_appliances) -> pd.DataFrame:
    data = {}
    # Waschmaschine läuft zwischen 10 und 11 Uhr mit 1 kW
    data["Waschmaschine"] = pd.Series(0.0, index=sample_timestamps)
    data["Waschmaschine"].loc[
        (sample_timestamps >= pd.Timestamp("2024-01-01 10:00:00")) &
        (sample_timestamps < pd.Timestamp("2024-01-01 11:00:00"))
    ] = 1.0 # 1 kW

    # Geschirrspüler läuft zwischen 14 und 16 Uhr mit 0.8 kW
    data["Geschirrspüler"] = pd.Series(0.0, index=sample_timestamps)
    data["Geschirrspüler"].loc[
        (sample_timestamps >= pd.Timestamp("2024-01-01 14:00:00")) &
        (sample_timestamps < pd.Timestamp("2024-01-01 16:00:00"))
    ] = 0.8 # 0.8 kW
    
    # Ein Gerät, das nicht in sample_appliances ist, um Vollständigkeit zu testen
    data["Bürogeräte"] = pd.Series(0.1, index=sample_timestamps) # Läuft immer mit 0.1 kW

    return pd.DataFrame(data)

@pytest.fixture
def sample_shift_metrics(sample_appliances) -> dict:
    metrics = {}
    # Für die Geräte, die wir aktiv testen wollen
    # Waschmaschine: Gute Flexibilität
    metrics["Waschmaschine"] = {
        "participation_rate": 0.8, # Basis-Rate aus Q9 (wird hier nicht direkt verwendet, aber ist Teil der Struktur)
        "lognorm_shape": 0.5,      # Beispielwerte für eine Log-Normal-Verteilung
        "lognorm_loc": 0,
        "lognorm_scale": np.exp(1.5), # E[D] ca. 5.7h, Median ca. 4.5h
        "expected_duration_willing": 5.7,
        "median_duration_willing": 4.5
    }
    # Geschirrspüler: Weniger flexibel in der Dauer
    metrics["Geschirrspüler"] = {
        "participation_rate": 0.9,
        "lognorm_shape": 0.8,
        "lognorm_loc": 0,
        "lognorm_scale": np.exp(0.5), # E[D] ca. 2.0h, Median ca. 1.6h
        "expected_duration_willing": 2.0,
        "median_duration_willing": 1.6
    }
    # Bürogeräte: Keine Flexibilität in der Dauer angenommen
    metrics["Bürogeräte"] = {
        "participation_rate": 0.1,
        "lognorm_shape": np.nan, # Keine positive Dauer angegeben
        "lognorm_loc": 0,
        "lognorm_scale": np.nan,
        "expected_duration_willing": np.nan,
        "median_duration_willing": np.nan
    }
    return metrics

@pytest.fixture
def sample_df_participation_curve_q10(sample_appliances) -> pd.DataFrame:
    data = []
    for dev in sample_appliances + ["Bürogeräte"]: # Füge alle Geräte hinzu, die in Lastprofilen vorkommen
        # Einfache lineare Kurve: 0% Teilnahme bei 0% Anreiz, 100% Teilnahme bei 20% Anreiz
        data.append({"device": dev, "comp_pct": 0, "participation_pct": 0})
        data.append({"device": dev, "comp_pct": 10, "participation_pct": 50})
        data.append({"device": dev, "comp_pct": 20, "participation_pct": 100})
    return pd.DataFrame(data)

@pytest.fixture
def sample_event_parameters() -> dict:
    return {
        'start_time': pd.Timestamp("2024-01-01 14:00:00"),
        'end_time': pd.Timestamp("2024-01-01 16:00:00"), # 2-Stunden-Event
        'required_duration_hours': 2.0,
        'incentive_percentage': 0.15 # 15% Anreiz
    }

@pytest.fixture
def sample_simulation_assumptions() -> dict:
    return {
        'reality_discount_factor': 1.0, # Kein Discount für einfachen Test
        'payback_model': {'type': 'uniform_after_event', 'duration_hours': 2.0, 'delay_hours': 0.0}
    }

# --- Testfunktionen ---

def test_simulation_runs_and_returns_correct_structure(
    sample_df_load_profiles,
    sample_shift_metrics,
    sample_df_participation_curve_q10,
    sample_event_parameters,
    sample_simulation_assumptions
):
    """
    Testet, ob die Simulation ohne Fehler durchläuft und die erwartete Datenstruktur zurückgibt.
    """
    result = run_load_shifting_simulation(
        df_load_profiles=sample_df_load_profiles,
        shift_metrics=sample_shift_metrics,
        df_participation_curve_q10=sample_df_participation_curve_q10,
        event_parameters=sample_event_parameters,
        simulation_assumptions=sample_simulation_assumptions
    )

    assert isinstance(result, dict), "Ergebnis sollte ein Dictionary sein."
    assert "df_shiftable_per_appliance" in result, "Schlüssel 'df_shiftable_per_appliance' fehlt."
    assert "df_payback_per_appliance" in result, "Schlüssel 'df_payback_per_appliance' fehlt."

    df_shiftable = result["df_shiftable_per_appliance"]
    df_payback = result["df_payback_per_appliance"]

    assert isinstance(df_shiftable, pd.DataFrame), "df_shiftable_per_appliance sollte ein DataFrame sein."
    assert isinstance(df_payback, pd.DataFrame), "df_payback_per_appliance sollte ein DataFrame sein."

    # Prüfe, ob Index und Spalten mit den Eingangs-Lastprofilen übereinstimmen
    pd.testing.assert_index_equal(df_shiftable.index, sample_df_load_profiles.index)
    pd.testing.assert_index_equal(df_payback.index, sample_df_load_profiles.index)
    
    # Spalten sollten die Geräte aus den Eingangs-Lastprofilen sein
    assert all(col in df_shiftable.columns for col in sample_df_load_profiles.columns)
    assert all(col in df_payback.columns for col in sample_df_load_profiles.columns)
    assert len(df_shiftable.columns) == len(sample_df_load_profiles.columns)
    assert len(df_payback.columns) == len(sample_df_load_profiles.columns)


# HIER KÖNNEN WEITERE, SPEZIFISCHERE TESTS FOLGEN
# z.B. test_no_shift_if_no_load, test_shift_values_for_specific_device, test_payback_timing_and_amount

def test_specific_shift_and_payback_geschirrspueler(
    sample_df_load_profiles, # Geschirrspüler läuft 14-16 Uhr mit 0.8 kW
    sample_shift_metrics,    # Geschirrspüler: P(D>=2h) wird berechnet, Median 1.6h, E[D] 2.0h
    sample_df_participation_curve_q10, # Bei 15% Anreiz -> 75% Teilnahme
    sample_event_parameters, # Event 14-16 Uhr, Dauer 2h, Anreiz 15%
    sample_simulation_assumptions # Kein Discount, Payback 16-18 Uhr
):
    """ Testet die konkreten Werte für ein Gerät."""
    result = run_load_shifting_simulation(
        df_load_profiles=sample_df_load_profiles,
        shift_metrics=sample_shift_metrics,
        df_participation_curve_q10=sample_df_participation_curve_q10,
        event_parameters=sample_event_parameters,
        simulation_assumptions=sample_simulation_assumptions
    )
    
    df_shiftable = result["df_shiftable_per_appliance"]
    df_payback = result["df_payback_per_appliance"]

    # --- Für Geschirrspüler ---
    dev = "Geschirrspüler"
    
    # p_participate_incentive (Q10): 15% Anreiz -> 75% Teilnahme (0.75)
    # (weil 10% -> 50%, 20% -> 100%, linear interpoliert für 15% ist (50+100)/2 = 75%)
    expected_p_incentive = 0.75 
    
    # p_duration_ok (Q9): P(D_max >= 2h) für Geschirrspüler
    # shape=0.8, scale=np.exp(0.5) approx 1.6487
    # 1 - lognorm.cdf(2, s=0.8, loc=0, scale=np.exp(0.5))
    # Dieses Ergebnis können wir extern berechnen und hier einsetzen
    # lognorm.cdf(2, s=0.8, loc=0, scale=np.exp(0.5)) = 0.6456...
    # p_duration_ok = 1 - 0.6456 = 0.3544
    expected_p_duration_ok = 1 - lognorm.cdf(2, s=0.8, loc=0, scale=np.exp(0.5))
    
    expected_p_effective = expected_p_incentive * expected_p_duration_ok # * reality_discount (hier 1.0)
    # expected_p_effective = 0.75 * 0.3544 = 0.2658
    
    # Erwartete Reduktion: 0.8 kW * 0.2658 = 0.21264 kW
    expected_reduction_kw = 0.8 * expected_p_effective

    event_start = sample_event_parameters['start_time']
    event_end = sample_event_parameters['end_time']
    
    # Überprüfe Reduktion während des Events
    reduction_during_event = df_shiftable[dev].loc[event_start:event_end - pd.Timedelta(minutes=1)] # Exklusive Endzeit
    assert np.allclose(reduction_during_event, expected_reduction_kw), \
        f"Unerwartete Reduktion für {dev}. Erwartet: {expected_reduction_kw}, Bekommen: {reduction_during_event.unique()}"
    
    # Überprüfe, ob außerhalb des Events (vorher) keine Reduktion stattfindet
    assert df_shiftable[dev].loc[:event_start - pd.Timedelta(minutes=1)].sum() == 0.0
    # Überprüfe, ob außerhalb des Events (nachher) keine Reduktion stattfindet
    assert df_shiftable[dev].loc[event_end:].sum() == 0.0


    # Überprüfe Payback
    # dt_h = 0.25 Stunden (15 Minuten)
    # shifted_energy_kwh_dev = expected_reduction_kw * 2 Stunden (Dauer des Events)
    # (Annahme: Reduktion ist konstant über die 2h)
    # Korrekter: summe der df_shiftable[dev] während des Events * dt_h
    dt_h = 0.25 
    shifted_energy_kwh_dev = df_shiftable[dev].loc[event_start:event_end - pd.Timedelta(minutes=1)].sum() * dt_h
    
    payback_duration_hours = sample_simulation_assumptions['payback_model']['duration_hours']
    expected_payback_power_kw = shifted_energy_kwh_dev / payback_duration_hours
    
    payback_start = event_end + pd.Timedelta(hours=sample_simulation_assumptions['payback_model']['delay_hours'])
    payback_end = payback_start + pd.Timedelta(hours=payback_duration_hours)
    
    payback_during_window = df_payback[dev].loc[payback_start : payback_end - pd.Timedelta(minutes=1)]
    
    assert np.allclose(payback_during_window, expected_payback_power_kw), \
         f"Unerwarteter Payback für {dev}. Erwartet: {expected_payback_power_kw}, Bekommen: {payback_during_window.unique()}"

    # Überprüfe, ob außerhalb des Payback-Fensters kein Payback stattfindet
    assert df_payback[dev].loc[:payback_start - pd.Timedelta(minutes=1)].sum() == 0.0
    if payback_end < df_payback[dev].index.max(): # Nur prüfen, wenn Payback-Ende nicht am Ende des gesamten Zeitraums liegt
         assert df_payback[dev].loc[payback_end:].sum() == 0.0