# PowerE/tests/logic/cost/test_dr_incentive_costs.py

import pytest

# Importiere die zu testende Funktion
# Annahme: Dein Projekt-Root ist im PYTHONPATH, wenn du pytest ausführst
# oder src/ ist als Source-Root in deiner IDE konfiguriert.
from logic.cost.dr_incentive_costs import calculate_dr_incentive_costs

# Testfälle definieren mit pytest.mark.parametrize
# Jeder Tupel ist (total_shifted_energy_kwh, average_incentive_cost_per_kwh, expected_total_costs)
test_data = [
    (100.0, 0.05, 5.0),   # Positiver Fall: 100 kWh * 0.05 CHF/kWh = 5.0 CHF
    (0.0, 0.05, 0.0),     # Keine verschobene Energie -> keine Kosten
    (100.0, 0.0, 0.0),     # Kein Anreizkostensatz -> keine Kosten
    (-50.0, 0.05, 0.0),    # Negative verschobene Energie (ungewöhnlich, sollte 0 Kosten ergeben)
    (100.0, -0.02, 0.0),   # Negativer Anreizkostensatz (ungewöhnlich, sollte 0 Kosten ergeben)
    (0.0, 0.0, 0.0),       # Beide Null -> keine Kosten
    (123.45, 0.0234, 123.45 * 0.0234), # Ein anderer positiver Fall mit Dezimalzahlen
]

@pytest.mark.parametrize("shifted_kwh, cost_per_kwh, expected_total", test_data)
def test_calculate_dr_incentive_costs_various_scenarios(shifted_kwh, cost_per_kwh, expected_total):
    """
    Testet die Funktion calculate_dr_incentive_costs mit verschiedenen Szenarien.
    """
    actual_total_costs = calculate_dr_incentive_costs(shifted_kwh, cost_per_kwh)
    assert actual_total_costs == pytest.approx(expected_total)

def test_calculate_dr_incentive_costs_edge_cases_return_zero():
    """
    Testet spezifisch, dass bei <=0 Inputs für Energie oder Kosten pro kWh
    das Ergebnis 0.0 ist, wie in der Funktion definiert.
    """
    assert calculate_dr_incentive_costs(total_shifted_energy_kwh=0, average_incentive_cost_per_kwh=0.1) == 0.0
    assert calculate_dr_incentive_costs(total_shifted_energy_kwh=10, average_incentive_cost_per_kwh=0) == 0.0
    assert calculate_dr_incentive_costs(total_shifted_energy_kwh=-10, average_incentive_cost_per_kwh=0.1) == 0.0
    assert calculate_dr_incentive_costs(total_shifted_energy_kwh=10, average_incentive_cost_per_kwh=-0.1) == 0.0
    assert calculate_dr_incentive_costs(total_shifted_energy_kwh=0, average_incentive_cost_per_kwh=0) == 0.0