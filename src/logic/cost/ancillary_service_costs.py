# src/logic/cost/ancillary_service_costs.py
import pandas as pd
import numpy as np

def calculate_mfrr_savings_opportunity(
    df_reg_original: pd.DataFrame,           # Original Regelenergie-Daten von deinem Loader
                                             # Erwartet Spalten: 'total_called_mw' (>0 für pos. mFRR)
                                             #                 'avg_price_eur_mwh'
    df_shiftable_total_kw: pd.Series,      # Aggregierte LastREDUKTION durch DR (kW, positive Werte)
                                             # Index muss mit df_reg_original übereinstimmen können
    cost_of_dr_activation_eur_per_mwh: float, # Deine berechneten Kosten für 1 MWh DR-Reduktion
    interval_duration_h: float,            # Dauer eines Zeitintervalls in Stunden (z.B. 0.25)
    technical_availability_factor: float = 1.0 # Faktor (0-1) für technische Verfügbarkeit/Zuverlässigkeit von DR
) -> float:
    """
    Berechnet die potenziellen Kosteneinsparungen (Opportunitätskosten) durch den Einsatz
    von Haushalts-DR zur Verdrängung von positiver Tertiärregelleistung (mFRR).

    Args:
        df_reg_original: DataFrame mit dem ursprünglichen positiven mFRR-Abruf und Preisen.
        df_shiftable_total_kw: Series mit der gesamten Lastreduktion durch DR in kW.
        cost_of_dr_activation_eur_per_mwh: Die Kosten für die Aktivierung von 1 MWh DR.
        interval_duration_h: Dauer eines Planungsintervalls in Stunden.
        technical_availability_factor: Annahme zur technischen Verfügbarkeit des DR-Potenzials für mFRR.

    Returns:
        float: Geschätzte gesamte Opportunitäts-Einsparung bei den mFRR-Kosten in EUR.
    """
    if df_reg_original.empty or df_shiftable_total_kw.empty or interval_duration_h <= 0:
        print("[INFO] calculate_mfrr_savings_opportunity: Ungültige oder leere Eingaben. Keine Einsparungen berechnet.")
        return 0.0

    if not (0 <= technical_availability_factor <= 1):
        print("[WARNUNG] calculate_mfrr_savings_opportunity: technical_availability_factor außerhalb [0,1]. Setze auf 1.0.")
        technical_availability_factor = 1.0
        
    # Arbeitskopie erstellen und für Analyse vorbereiten
    df_analysis = df_reg_original.copy()

    # DR-Reduktionspotenzial an den Index von df_reg_original anpassen und in MW umrechnen
    # Positive Werte in df_shiftable_total_kw bedeuten Lastreduktion
    dr_reduction_mw_series = (
        df_shiftable_total_kw.reindex(df_analysis.index, fill_value=0.0) / 1000.0 # kW -> MW
    ) * technical_availability_factor
    
    df_analysis['available_dr_reduction_mw'] = dr_reduction_mw_series

    # Nur Zeitpunkte betrachten, an denen positive mFRR abgerufen wurde und DR günstiger ist
    # und DR auch ein Reduktionspotenzial anbietet.
    # avg_price_eur_mwh ist der Preis, den der Netzbetreiber für mFRR zahlt.
    # DR ist vorteilhaft, wenn seine Aktivierungskosten darunterliegen.
    
    economic_condition = cost_of_dr_activation_eur_per_mwh < df_analysis['avg_price_eur_mwh']
    positive_mfrr_called = df_analysis['total_called_mw'] > 0 # Per Definition deines Preprocessings
    dr_potential_available = df_analysis['available_dr_reduction_mw'] > 0
    
    eligible_intervals_mask = economic_condition & positive_mfrr_called & dr_potential_available

    # Volumen der mFRR, das durch DR verdrängt werden könnte
    df_analysis['mfrr_displaced_by_dr_mw'] = 0.0
    df_analysis.loc[eligible_intervals_mask, 'mfrr_displaced_by_dr_mw'] = np.minimum(
        df_analysis.loc[eligible_intervals_mask, 'total_called_mw'],
        df_analysis.loc[eligible_intervals_mask, 'available_dr_reduction_mw']
    )

    # Kostendifferenz pro MWh (Einsparung pro MWh durch DR-Einsatz statt Markt-mFRR)
    df_analysis['price_spread_eur_mwh'] = 0.0
    df_analysis.loc[eligible_intervals_mask, 'price_spread_eur_mwh'] = (
        df_analysis.loc[eligible_intervals_mask, 'avg_price_eur_mwh'] -
        cost_of_dr_activation_eur_per_mwh # Dieser Wert ist ein Skalar
    )

    # Einsparung pro Intervall
    df_analysis['interval_savings_eur'] = (
        df_analysis['mfrr_displaced_by_dr_mw'] *
        interval_duration_h * # MWh = MW * h
        df_analysis['price_spread_eur_mwh']
    )
    
    total_savings_eur = df_analysis['interval_savings_eur'].sum()

    print(f"[INFO] calculate_mfrr_savings_opportunity: Potenziell verdrängtes mFRR-Volumen (Summe über Zeit) = {df_analysis['mfrr_displaced_by_dr_mw'].sum() * interval_duration_h:.2f} MWh")
    print(f"[INFO] calculate_mfrr_savings_opportunity: Geschätzte Gesamteinsparung Regelenergie (mFRR pos) = {total_savings_eur:.2f} EUR")
    
    return total_savings_eur