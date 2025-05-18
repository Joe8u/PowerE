# PowerE/src/analysis/srl_evaluation_pipeline/_02_incentive_calculator.py

def calculate_max_offerable_incentive(avg_peak_srl_price_chf_kwh: float, aggregator_margin_pct: float) -> float:
    """
    Berechnet den maximal bietbaren Anreiz für Teilnehmer basierend auf dem SRL-Spitzenpreis
    und der Aggregator-Marge.
    """
    if not (0 <= aggregator_margin_pct <= 100):
        raise ValueError("Aggregator-Marge muss zwischen 0 und 100 liegen.")
    
    max_offerable = avg_peak_srl_price_chf_kwh * (1 - aggregator_margin_pct / 100.0)
    return max_offerable

if __name__ == '__main__':
    print("Testlauf für _02_incentive_calculator.py")
    test_srl_price = 1.0386 # CHF/kWh
    test_margin = 30.0 # %
    incentive = calculate_max_offerable_incentive(test_srl_price, test_margin)
    print(f"Bei SRL-Preis {test_srl_price} CHF/kWh und {test_margin}% Marge -> Max. Anreiz: {incentive:.4f} CHF/kWh")
