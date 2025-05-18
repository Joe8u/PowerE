# PowerE/src/analysis/srl_evaluation_pipeline/_05_economic_evaluator.py
import pandas as pd

def evaluate_economics_for_peaks(
    df_analysis_peaks: pd.DataFrame, # Muss Spalten 'vpp_flex_kw' und 'srl_price_chf_kwh' enthalten
    avg_actual_incentive_paid_chf_kwh: float,
    time_resolution_jasm_minutes: int
):
    """
    Führt die Wirtschaftlichkeitsberechnung für die identifizierten Spitzenperioden durch.
    """
    if df_analysis_peaks.empty or 'vpp_flex_kw' not in df_analysis_peaks.columns or 'srl_price_chf_kwh' not in df_analysis_peaks.columns:
        print("WARNUNG: df_analysis_peaks ist leer oder enthält nicht die benötigten Spalten für die Wirtschaftlichkeitsanalyse.")
        return {
            'num_analyzed_peak_periods': 0,
            'total_energy_shifted_kwh': 0.0,
            'total_potential_revenue_chf': 0.0,
            'total_incentive_costs_chf': 0.0,
            'total_net_value_aggregator_chf': 0.0
        }

    # Energie pro Zeitintervall (z.B. 15 Minuten = 0.25 Stunden)
    interval_duration_h = time_resolution_jasm_minutes / 60.0
    
    df_analysis_peaks_calc = df_analysis_peaks.copy() # Kopie für Berechnungen
    df_analysis_peaks_calc['energy_shifted_kwh_per_interval'] = df_analysis_peaks_calc['vpp_flex_kw'] * interval_duration_h
    
    # Erlöse und Kosten pro Intervall
    df_analysis_peaks_calc['revenue_chf_per_interval'] = df_analysis_peaks_calc['energy_shifted_kwh_per_interval'] * df_analysis_peaks_calc['srl_price_chf_kwh']
    df_analysis_peaks_calc['incentive_cost_chf_per_interval'] = df_analysis_peaks_calc['energy_shifted_kwh_per_interval'] * avg_actual_incentive_paid_chf_kwh
    df_analysis_peaks_calc['net_value_aggregator_per_interval'] = df_analysis_peaks_calc['revenue_chf_per_interval'] - df_analysis_peaks_calc['incentive_cost_chf_per_interval']

    # Summen über alle analysierten Spitzenperioden
    total_energy_shifted_kwh = df_analysis_peaks_calc['energy_shifted_kwh_per_interval'].sum()
    total_potential_revenue_chf = df_analysis_peaks_calc['revenue_chf_per_interval'].sum()
    total_incentive_costs_chf = df_analysis_peaks_calc['incentive_cost_chf_per_interval'].sum()
    total_net_value_aggregator_chf = df_analysis_peaks_calc['net_value_aggregator_per_interval'].sum()

    return {
        'num_analyzed_peak_periods': len(df_analysis_peaks_calc),
        'total_energy_shifted_kwh': total_energy_shifted_kwh,
        'total_potential_revenue_chf': total_potential_revenue_chf,
        'total_incentive_costs_chf': total_incentive_costs_chf,
        'total_net_value_aggregator_chf': total_net_value_aggregator_chf
    }

if __name__ == '__main__':
    print("Testlauf für _05_economic_evaluator.py")
    # Erstelle Dummy df_analysis_peaks für den Test
    dummy_data = {
        'vpp_flex_kw': [10000, 12000, 8000], # kW
        'srl_price_chf_kwh': [0.8, 0.75, 0.9] # CHF/kWh
    }
    dummy_df_peaks = pd.DataFrame(dummy_data)
    
    test_avg_incentive = 0.0256 # CHF/kWh
    test_time_res_min = 15

    results = evaluate_economics_for_peaks(dummy_df_peaks, test_avg_incentive, test_time_res_min)
    print("\nWirtschaftlichkeitsergebnisse (Test):")
    for key, value in results.items():
        print(f"  {key}: {value}")

