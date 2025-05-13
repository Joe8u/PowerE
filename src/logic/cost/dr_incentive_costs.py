# src/logic/cost/dr_incentive_costs.py

def calculate_dr_incentive_costs(
    total_shifted_energy_kwh: float,
    average_incentive_cost_per_kwh: float # Dieser Wert wird später von scenario_analyzer.py berechnet
) -> float:
    if total_shifted_energy_kwh <= 0 or average_incentive_cost_per_kwh <= 0:
        return 0.0
    total_costs = total_shifted_energy_kwh * average_incentive_cost_per_kwh
    print(f"[INFO] calculate_dr_incentive_costs: Verschobene Energie={total_shifted_energy_kwh:.2f} kWh, "
          f"Anreiz/kWh={average_incentive_cost_per_kwh:.4f} EUR/kWh, Gesamte Anreizkosten={total_costs:.2f} EUR")
    return total_costs