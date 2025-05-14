# PowerE/scripts/run_scenario_analysis_script.py
import pandas as pd
import datetime
import sys
from pathlib import Path

# Füge das src-Verzeichnis zum Python-Pfad hinzu
project_root = Path(__file__).resolve().parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Importiere deine Module
from data_loader.lastprofile import load_appliances, list_appliances
from data_loader.spot_price_loader import load_spot_price_range
from data_loader.tertiary_regulation_loader import load_regulation_range

# NEU: Importiere die Funktion zum Erstellen der Respondenten-Flexibilitätsdaten
from logic.respondent_level_model.data_transformer import create_respondent_flexibility_df

# Importiere die (überarbeitete) Haupt-Analysefunktion
from logic.scenario_analyzer import evaluate_dr_scenario

def print_scenario_results(scenario_name: str, results: dict):
    """Hilfsfunktion zur formatierten Ausgabe der Ergebnisse eines Szenarios."""
    print(f"\n--- Ergebnisse für Szenario: {scenario_name} ---")
    if not results or results.get("error"): # Prüft auch auf den 'error' Schlüssel
        print(f"Fehler im Szenario: {results.get('error', 'Unbekannter Fehler oder keine Ergebnisse')}")
        if "value_added_eur" not in results: # Wenn auch keine normalen Keys da sind
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
    
    # Optional: Ausgabe der Teilnehmerdetails
    # detailed_participation = results.get("detailed_participation_for_costing", [])
    # if detailed_participation:
    #     print(f"  Anzahl teilnehmender Respondent-Geräte-Kombinationen: {len(detailed_participation)}")
    print("--------------------------------------------------")


def run_analysis():
    print("Starte Analyse-Skript (mit respondenten-basierter Simulation)...")

    # --- 1. Konstante Parameter für alle Szenarien ---
    start_date_str = "2024-01-01"
    end_date_str = "2024-01-02" 
    start_dt = datetime.datetime.fromisoformat(start_date_str)
    end_dt = datetime.datetime.fromisoformat(end_date_str).replace(hour=23, minute=59, second=59)

    try:
        # Annahme: Die Spaltennamen, die von precompute_lastprofile_2024.py erzeugt werden
        # (z.B. "Waschmaschine", "Geschirrspüler"), sind die, die wir hier wollen und
        # die auch in df_respondent_flexibility als 'device' vorkommen.
        # Daher group=False, um die tatsächlichen Spaltennamen zu bekommen.
        appliances_to_simulate = list_appliances(2024, group=False) 
        print(f"Gefundene Geräte aus Lastprofilen (2024): {appliances_to_simulate}")
        if not appliances_to_simulate:
            print("FEHLER: Keine Geräte in den Lastprofilen für 2024 gefunden. Bitte precompute_lastprofile_2024.py ausführen.")
            return
    except FileNotFoundError:
        print(f"FEHLER: Konnte Beispieldatei für list_appliances nicht finden. Stelle sicher, dass data/processed/lastprofile/2024/2024-01.csv existiert.")
        print(f"Du musst eventuell dein Skript src/preprocessing/lastprofile/2024/precompute_lastprofile_2024.py ausführen.")
        return
    
    # Lade die Basisdaten einmal
    # group=False, da die Spaltennamen bereits die gewünschten aggregierten Gerätenamen sein sollten
    df_average_load_profiles_base = load_appliances(
        appliances=appliances_to_simulate, start=start_dt, end=end_dt, year=2024, group=False
    )
    df_spot_prices = load_spot_price_range(start_dt, end_dt, as_kwh=False) 
    df_reg_data = load_regulation_range(start_dt, end_dt)

    if df_average_load_profiles_base.empty:
        print(f"FEHLER: Keine Lastdaten für den Zeitraum {start_date_str} - {end_date_str} für Geräte {appliances_to_simulate} geladen.")
        return

    # NEU: Lade df_respondent_flexibility
    try:
        df_respondent_flexibility = create_respondent_flexibility_df()
        if df_respondent_flexibility.empty:
            print("WARNUNG: df_respondent_flexibility ist leer. Es kann kein Shift-Potenzial aus Umfragedaten abgeleitet werden.")
            # Das Skript kann weiterlaufen, evaluate_dr_scenario sollte damit umgehen können (gibt 0 Shift zurück).
    except FileNotFoundError as e:
        print(f"FEHLER beim Laden der Roh-Umfragedatei (benötigt von create_respondent_flexibility_df): {e}")
        print("Stelle sicher, dass die zugrundeliegenden Survey-CSV-Dateien in data/processed/survey und data/raw/survey existieren.")
        return
    except Exception as e:
        print(f"FEHLER beim Erstellen von df_respondent_flexibility: {e}")
        return
        
    print(f"df_respondent_flexibility geladen, Shape: {df_respondent_flexibility.shape}")
    print(f"Verfügbare Geräte in Durchschnitts-Lastprofilen: {df_average_load_profiles_base.columns.tolist()}")


    # Konstante Kostenannahmen
    avg_household_price_eur_kwh = 0.276 # Beispielwert
    base_cost_model_assumptions = {
        'avg_household_electricity_price_eur_kwh': avg_household_price_eur_kwh,
        'assumed_dr_events_per_month': 12,
        'as_displacement_factor': 0.1 
    }

    base_simulation_assumptions = {
        'reality_discount_factor': 0.7,
    }

    # --- 2. Definiere verschiedene Szenarien ---
    scenarios = []

    event_params_1 = {
        'start_time': pd.Timestamp(f"{start_date_str} 14:00:00"),
        'end_time': pd.Timestamp(f"{start_date_str} 16:00:00"),
        'required_duration_hours': 2.0,
        'incentive_percentage': 0.15 # 15%
    }
    sim_assumptions_1 = {**base_simulation_assumptions, 
                         'payback_model': {'type': 'uniform_after_event', 'duration_hours': 2.0, 'delay_hours': 0.25}}
    scenarios.append({"name": "Szenario 1: 2h Event, 2h Payback, 15% Anreiz", 
                      "event_params": event_params_1, 
                      "sim_assumps": sim_assumptions_1,
                      "cost_assumps": base_cost_model_assumptions})

    event_params_2 = {**event_params_1, 'incentive_percentage': 0.30} # Gleiche Zeit, höherer Anreiz
    scenarios.append({"name": "Szenario 2: 2h Event, 2h Payback, 30% Anreiz", 
                      "event_params": event_params_2, 
                      "sim_assumps": sim_assumptions_1, # Gleiche Payback-Annahme wie Szenario 1
                      "cost_assumps": base_cost_model_assumptions})
    
    # Fügen Sie hier bei Bedarf weitere Szenarien hinzu

    # --- 3. Führe Szenarien aus und gib Ergebnisse aus ---
    for scenario_config in scenarios: # Umbenannt von scenario zu scenario_config zur Vermeidung von Verwechslung
        print(f"\n\nLAUFE SZENARIO: {scenario_config['name']}")
        
        # df_average_load_profiles_base enthält bereits die Durchschnittsprofile für alle zu simulierenden Geräte.
        # evaluate_dr_scenario wird intern die Geräte berücksichtigen, für die sowohl Lastprofile
        # als auch Flexibilitätsdaten (in df_respondent_flexibility) vorhanden sind.
        
        current_spot_prices_series = df_spot_prices['price_eur_mwh'] if 'price_eur_mwh' in df_spot_prices else df_spot_prices
        
        results = evaluate_dr_scenario(
            df_respondent_flexibility=df_respondent_flexibility,         # NEU
            df_average_load_profiles=df_average_load_profiles_base.copy(), # Verwende eine Kopie für Sicherheit
            event_parameters=scenario_config["event_params"],
            simulation_assumptions=scenario_config["sim_assumps"],
            df_spot_prices_eur_mwh=current_spot_prices_series, 
            df_reg_original_data=df_reg_data.copy(), # Kopie für Sicherheit
            cost_model_assumptions=scenario_config["cost_assumps"]
        )
        print_scenario_results(scenario_config["name"], results)

if __name__ == "__main__":
    run_analysis()