# PowerE/scripts/run_scenario_analysis_script.py
import pandas as pd
import datetime
import sys
from pathlib import Path

# Füge das src-Verzeichnis zum Python-Pfad hinzu, damit Imports aus logic etc. funktionieren
# Dies ist notwendig, wenn das Skript direkt aus dem scripts-Ordner ausgeführt wird.
# Passe den Pfad an, falls dein Skript woanders liegt oder dein PYTHONPATH anders konfiguriert ist.
project_root = Path(__file__).resolve().parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Importiere deine Module aus src/ (Pfade könnten je nach deiner genauen Struktur leicht variieren)
from data_loader.lastprofile import load_appliances, list_appliances
from data_loader.spot_price_loader import load_spot_price_range
from data_loader.tertiary_regulation_loader import load_regulation_range
from dashboard.components.details.survey_graphs.participation_graphs import get_participation_df
from dashboard.components.details.survey_graphs.shift_duration_all import calculate_shift_potential_data
from logic.scenario_analyzer import evaluate_dr_scenario

def print_scenario_results(scenario_name: str, results: dict):
    """Hilfsfunktion zur formatierten Ausgabe der Ergebnisse eines Szenarios."""
    print(f"\n--- Ergebnisse für Szenario: {scenario_name} ---")
    if not results or results.get("error"):
        print(f"Fehler im Szenario: {results.get('error', 'Unbekannter Fehler')}")
        return

    print(f"  Value Added (Nettoersparnis):         {results.get('value_added_eur', 0.0):.2f} EUR")
    print(f"  Baseline Spotmarktkosten:           {results.get('baseline_spot_costs_eur', 0.0):.2f} EUR")
    print(f"  Szenario Spotmarktkosten (nach DR): {results.get('scenario_spot_costs_eur', 0.0):.2f} EUR")
    spot_savings = results.get("baseline_spot_costs_eur", 0.0) - results.get("scenario_spot_costs_eur", 0.0)
    print(f"  -> Spotmarkt Einsparung:             {spot_savings:.2f} EUR")
    print(f"  DR-Programmkosten (Anreize):        {results.get('dr_program_costs_eur', 0.0):.2f} EUR")
    print(f"    (Avg. Anreizkostenrate:           {results.get('average_payout_rate_eur_per_kwh_event', 0.0):.4f} EUR/kWh)")
    print(f"  Regelenergie-Einsparung (modelliert): {results.get('ancillary_service_savings_eur', 0.0):.2f} EUR")
    print(f"  Insgesamt verschobene Energie (Event):{results.get('total_shifted_energy_kwh_event', 0.0):.2f} kWh")

    # Detailliertere physische Ergebnisse (optional mehr ausgeben)
    # original_agg = results.get("original_aggregated_load_kw")
    # shifted_agg = results.get("final_shifted_aggregated_load_kw")
    # if original_agg is not None and not original_agg.empty:
    #     print(f"  Original Agg. Last Max:             {original_agg.max():.2f} kW bei {original_agg.idxmax()}")
    # if shifted_agg is not None and not shifted_agg.empty:
    #     print(f"  Verschobene Agg. Last Max:          {shifted_agg.max():.2f} kW bei {shifted_agg.idxmax()}")
    print("--------------------------------------------------")


def run_analysis():
    print("Starte Analyse-Skript...")

    # --- 1. Konstante Parameter für alle Szenarien ---
    # Datumsbereich für die Analyse (z.B. ein oder zwei typische Tage)
    start_date_str = "2024-01-01"
    end_date_str = "2024-01-02" # Exklusiv für DatePickerRange, inklusiv für .loc Slice bis Tagesende
    start_dt = datetime.datetime.fromisoformat(start_date_str)
    # Für load_appliances etc. wollen wir oft bis Ende des Tages
    # Für einen einzelnen Tag wäre end_dt = start_dt.replace(hour=23, minute=59, second=59)
    # Für zwei Tage:
    end_dt = datetime.datetime.fromisoformat(end_date_str).replace(hour=23, minute=59, second=59)


    # Geräteauswahl (nimm alle für die Analyse relevanten)
    # Hole die Liste der gruppierten Geräte, für die du Lastprofile hast
    # Annahme: list_appliances(group=True) liefert die korrekten Namen nach deinem Preprocessing
    try:
        # Stelle sicher, dass list_appliances mit group=True die Namen liefert,
        # die auch in den Spalten deiner von load_appliances(group=True) geladenen Daten stehen
        all_grouped_appliances = list_appliances(2024, group=True) # group=True ist wichtig, wenn dein Preprocessing gruppiert
                                                               # und dein Loader ebenfalls group=True verwendet.
                                                               # Wenn precompute_lastprofile_2024 die gruppierten Spalten
                                                               # bereits erzeugt, ist group=False hier evtl. richtiger
                                                               # oder die Logik in list_appliances muss das berücksichtigen.
                                                               # Aktuell ist es so, dass dein precompute_lastprofile_2024
                                                               # die Namen aus seinem group_map als Spalten schreibt.
                                                               # list_appliances(group=False) liest diese Spaltennamen.
                                                               # list_appliances(group=True) liest die keys aus seinem *eigenen* group_map.
                                                               # Stelle Konsistenz her!
                                                               # Annahme für jetzt: precompute_lastprofile erzeugt Spalten wie "Waschmaschine"
                                                               # und list_appliances(group=False) gibt diese zurück.
        appliances_to_simulate = list_appliances(2024, group=False) # Nimmt die Spaltennamen aus den 2024er CSVs
        # Entferne Geräte, für die keine Umfragedaten existieren könnten (z.B. wenn "Trockner" als Spalte existiert)
        # Dies wird aber auch in evaluate_dr_scenario gehandhabt
        print(f"Gefundene Geräte aus Lastprofilen (2024): {appliances_to_simulate}")

    except FileNotFoundError:
        print(f"FEHLER: Konnte Beispieldatei für list_appliances nicht finden. Stelle sicher, dass data/processed/lastprofile/2024/2024-01.csv existiert.")
        print(f"Du musst eventuell dein Skript src/preprocessing/lastprofile/2024/precompute_lastprofile_2024.py ausführen.")
        return
    
    # Lade die Basisdaten einmal
    df_load_base = load_appliances(appliances=appliances_to_simulate, start=start_dt, end=end_dt, year=2024)
    df_spot_prices = load_spot_price_range(start_dt, end_dt, as_kwh=False) # EUR/MWh
    df_reg_data = load_regulation_range(start_dt, end_dt)

    if df_load_base.empty:
        print(f"FEHLER: Keine Lastdaten für den Zeitraum {start_date_str} - {end_date_str} für Geräte {appliances_to_simulate} geladen.")
        return

    shift_metrics_all = calculate_shift_potential_data()["metrics"]
    df_participation_q10 = get_participation_df()

    # Filter shift_metrics und df_participation_q10 auf die tatsächlich vorhandenen Geräte in df_load_base
    active_appliances_in_load = df_load_base.columns.tolist()
    shift_metrics = {dev: data for dev, data in shift_metrics_all.items() if dev in active_appliances_in_load}
    # df_participation_q10 wird intern in evaluate_dr_scenario gefiltert

    print(f"Simuliere für folgende Geräte: {list(shift_metrics.keys())}")


    # Konstante Kostenannahmen
    haushalts_strompreis_chf_kwh = 0.29
    chf_to_eur_conversion_factor = 1.05 # 1 CHF = 1.05 EUR
    avg_household_price_eur_kwh = haushalts_strompreis_chf_kwh * chf_to_eur_conversion_factor
    
    base_cost_model_assumptions = {
        'avg_household_electricity_price_eur_kwh': avg_household_price_eur_kwh,
        'assumed_dr_events_per_month': 12,
        'as_displacement_factor': 0.1 # Startwert
    }

    base_simulation_assumptions = {
        'reality_discount_factor': 0.7,
        # Payback-Modell wird pro Szenario definiert
    }

    # --- 2. Definiere verschiedene Szenarien ---
    scenarios = []

    # Szenario 1: Kurzes Event (2h), kurze Payback-Dauer (gleich Event-Dauer)
    event_params_1 = {
        'start_time': pd.Timestamp(f"{start_date_str} 14:00:00"),
        'end_time': pd.Timestamp(f"{start_date_str} 16:00:00"),
        'required_duration_hours': 2.0,
        'incentive_percentage': 0.15 # 15%
    }
    sim_assumptions_1 = {**base_simulation_assumptions, 
                         'payback_model': {'type': 'uniform_after_event', 'duration_hours': 2.0, 'delay_hours': 0.25}}
    scenarios.append({"name": "Szenario 1: 2h Event, 2h Payback", 
                      "event_params": event_params_1, 
                      "sim_assumps": sim_assumptions_1,
                      "cost_assumps": base_cost_model_assumptions})

    # Szenario 2: Kurzes Event (2h), LÄNGERE Payback-Dauer (z.B. 6h)
    event_params_2 = event_params_1 # Gleiche Event-Zeit
    sim_assumptions_2 = {**base_simulation_assumptions,
                         'payback_model': {'type': 'uniform_after_event', 'duration_hours': 6.0, 'delay_hours': 0.25}}
    scenarios.append({"name": "Szenario 2: 2h Event, 6h Payback (geglättet)", 
                      "event_params": event_params_2, 
                      "sim_assumps": sim_assumptions_2,
                      "cost_assumps": base_cost_model_assumptions})

    # Szenario 3: Längeres Event (z.B. 4h), Payback-Dauer = Event-Dauer
    event_params_3 = {
        'start_time': pd.Timestamp(f"{start_date_str} 13:00:00"),
        'end_time': pd.Timestamp(f"{start_date_str} 17:00:00"),
        'required_duration_hours': 4.0,
        'incentive_percentage': 0.15
    }
    sim_assumptions_3 = {**base_simulation_assumptions,
                         'payback_model': {'type': 'uniform_after_event', 'duration_hours': 4.0, 'delay_hours': 0.25}}
    scenarios.append({"name": "Szenario 3: 4h Event, 4h Payback", 
                      "event_params": event_params_3, 
                      "sim_assumps": sim_assumptions_3,
                      "cost_assumps": base_cost_model_assumptions})
    
    # Szenario 4: Anderer Anreiz (z.B. 30%) für das 2h-Event mit langem Payback
    event_params_4 = event_params_2 # Gleiche Zeiten wie Szenario 2
    event_params_4_updated = {**event_params_4, 'incentive_percentage': 0.30} # Nur Anreiz ändern
    scenarios.append({"name": "Szenario 4: 2h Event, 6h Payback, 30% Anreiz", 
                      "event_params": event_params_4_updated, 
                      "sim_assumps": sim_assumptions_2, # Gleiche Payback-Annahme wie Szenario 2
                      "cost_assumps": base_cost_model_assumptions})


    # --- 3. Führe Szenarien aus und gib Ergebnisse aus ---
    for scenario in scenarios:
        print(f"\n\nLAUFE SZENARIO: {scenario['name']}")
        # Stelle sicher, dass df_load_base nur die Spalten enthält, für die auch shift_metrics existieren
        # (sim_appliances im Callback macht das, hier müssen wir es manuell machen, wenn df_load_base breiter ist)
        # Die appliances_to_simulate sind bereits die Spalten von df_load_base
        # df_load_for_sim wird in evaluate_dr_scenario intern aus df_load_to_simulate und dessen Spalten erstellt
        
        results = evaluate_dr_scenario(
            df_load_to_simulate=df_load_base[list(shift_metrics.keys())].copy(), # Nur Geräte mit Flex-Daten übergeben
            # appliances_for_simulation parameter wird in evaluate_dr_scenario nicht mehr separat erwartet
            shift_metrics=shift_metrics,
            df_participation_curve_q10=df_participation_q10,
            event_parameters=scenario["event_params"],
            simulation_assumptions=scenario["sim_assumps"],
            df_spot_prices_eur_mwh=df_spot_prices['price_eur_mwh'], # Annahme: df_spot_prices hat Spalte 'price_eur_mwh'
            df_reg_original_data=df_reg_data,
            cost_model_assumptions=scenario["cost_assumps"]
        )
        print_scenario_results(scenario["name"], results)

if __name__ == "__main__":
    run_analysis()