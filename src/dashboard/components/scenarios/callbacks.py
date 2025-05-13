# src/dashboard/components/scenarios/callbacks.py
from dash import callback, Input, Output, State, no_update
import plotly.graph_objects as go # Für go.Figure() als leere Figur
import pandas as pd
import datetime

# Datenlader
from data_loader.lastprofile import load_appliances
from data_loader.spot_price_loader import load_spot_price_range
from data_loader.tertiary_regulation_loader import load_regulation_range

# Umfragedaten-Verarbeitung
from dashboard.components.details.survey_graphs.participation_graphs import get_participation_df
from dashboard.components.details.survey_graphs.shift_duration_all import calculate_shift_potential_data

# Die Grafikfunktion für den per-Appliance-Vergleich
# Stelle sicher, dass der Pfad korrekt ist, wenn du per_appliance_comparison_graph.py verschoben hast:
# z.B. from .graphs.per_appliance_comparison_graph import make_per_appliance_comparison_figure
# Wenn es in components/scenarios/graphs/ liegt:
from .graphs.per_appliance_comparison_graph import make_per_appliance_comparison_figure

# Import der Haupt-Analysefunktion
from logic.scenario_analyzer import evaluate_dr_scenario

@callback(
    # Bestehendes Output für die Grafik
    Output("per-appliance-comparison-graph", "figure"),
    # NEUE Outputs für die KPI-Karten
    Output("scenario-kpi-value-added", "children"),
    Output("scenario-kpi-spot-savings", "children"),
    Output("scenario-kpi-as-savings", "children"),
    Output("scenario-kpi-dr-costs", "children"),
    Output("scenario-kpi-total-shifted-energy", "children"),
    Output("scenario-kpi-avg-payout-rate", "children"),
    # Haupt-Trigger
    Input("scenario-run-button", "n_clicks"),
    # States für alle anderen Controls auf der Szenario-Seite
    State("scenario-appliance-dropdown", "value"),
    State("scenario-date-picker", "start_date"),
    State("scenario-date-picker", "end_date"),
    State("scenario-dr-start-hour", "value"),
    State("scenario-dr-duration-hours", "value"),
    State("scenario-dr-incentive-pct", "value"),
    # Hier könntest du später States für Simulationsannahmen (z.B. Reality Discount Factor) hinzufügen,
    # falls diese per UI einstellbar werden sollen.
)
def update_scenario_simulation_graph(
    n_clicks,
    selected_appliances,
    start_date_str,
    end_date_str,
    dr_start_hour,
    dr_duration_hours,
    dr_incentive_pct
):
    print(f"---- Szenario-Callback GESTARTET, n_clicks: {n_clicks} ----")
    print(f"Ausgewählte Geräte: {selected_appliances}")
    print(f"Datum: {start_date_str} bis {end_date_str}")
    print(f"DR-Parameter Input: StartStd={dr_start_hour}, Dauer={dr_duration_hours}, Anreiz={dr_incentive_pct}%")

    if n_clicks == 0 or n_clicks is None:
        print("Button noch nicht geklickt oder n_clicks ist None. Keine Aktualisierung.")
        # Für mehrere Outputs müssen wir eine Liste von no_update zurückgeben,
        # die der Anzahl der Outputs entspricht.
        return [no_update] * 7 # 1 Grafik + 6 KPIs = 7 Outputs

    # --- 1. Eingaben parsen und vorbereiten ---
    start_dt = datetime.datetime.fromisoformat(start_date_str)
    end_dt = datetime.datetime.fromisoformat(end_date_str)
    
    # Erstelle eine leere Standardfigur für den Fehlerfall
    empty_figure = go.Figure()
    # Default-Texte für KPIs im Fehlerfall oder wenn keine Daten
    no_data_text = "N/A"
    default_kpi_outputs = [no_data_text] * 6 # Für die 6 KPI-Outputs

    if not selected_appliances:
        print("Keine Geräte für Simulation ausgewählt.")
        return [empty_figure] + default_kpi_outputs

    # --- 2. Basis-DATEN LADEN (Lastprofile, Spotpreise, Regelenergie) ---
    df_load_filt = load_appliances(
        appliances=selected_appliances, start=start_dt, end=end_dt, year=2024
    )
    print(f"df_load_filt geladen, leer? {df_load_filt.empty}, Zeilen: {len(df_load_filt)}")
    if df_load_filt.empty:
        print("Keine Lastdaten für ausgewählten Zeitraum/Geräte gefunden.")
        return [empty_figure] + default_kpi_outputs

    df_spot = load_spot_price_range(start_dt, end_dt, as_kwh=False) # Preise als EUR/MWh lassen für evaluate_dr_scenario
    df_reg = load_regulation_range(start_dt, end_dt)
    print("Spot- und Regelenergiedaten geladen.")

    # --- 3. UMFRAGEDATEN für Simulation laden ---
    shift_data_results = calculate_shift_potential_data() # Diese Funktion lädt Q9-Daten
    shift_metrics = shift_data_results["metrics"]
    df_participation_curve_q10 = get_participation_df() # Diese Funktion lädt Q10-Daten
    print("Umfragedaten (shift_metrics, df_participation_curve_q10) geladen.")

    # --- 4. EVENT-PARAMETER und SIMULATIONS-/KOSTEN-ANNAHMEN erstellen ---
    try:
        dr_start_hour_int = int(dr_start_hour) if dr_start_hour is not None else 14
        dr_duration_float = float(dr_duration_hours) if dr_duration_hours is not None else 2.0
        dr_incentive_float = float(dr_incentive_pct) if dr_incentive_pct is not None else 15.0

        event_start_actual_dt = pd.Timestamp(f"{start_date_str} {dr_start_hour_int:02d}:00:00")
        event_end_actual_dt = event_start_actual_dt + pd.Timedelta(hours=dr_duration_float)
    except Exception as e:
        print(f"Fehler beim Erstellen der Event-Zeiten: {e}. Verwende Fallback-Zeiten.")
        event_start_actual_dt = start_dt + pd.Timedelta(hours=14) # start_dt ist bereits datetime
        event_end_actual_dt = event_start_actual_dt + pd.Timedelta(hours=2.0)

    event_parameters = {
        'start_time': event_start_actual_dt,
        'end_time': event_end_actual_dt,
        'required_duration_hours': dr_duration_float,
        'incentive_percentage': dr_incentive_float / 100.0 # als 0-1 Wert
    }
    simulation_assumptions = {
        'reality_discount_factor': 0.7,
        'payback_model': {'type': 'uniform_after_event', 'duration_hours': dr_duration_float, 'delay_hours': 0.25}
    }
    
    haushalts_strompreis_chf_kwh = 0.29
    chf_to_eur_conversion_factor = 1.05 # Dein angenommener Kurs (1 CHF = 1.05 EUR)
    avg_household_price_eur_kwh = haushalts_strompreis_chf_kwh * chf_to_eur_conversion_factor

    cost_model_assumptions = {
        'avg_household_electricity_price_eur_kwh': avg_household_price_eur_kwh,
        'assumed_dr_events_per_month': 12,
        'as_displacement_factor': 0.1 # Beispiel Startwert
    }
    print(f"Erstellte Event-Parameter: {event_parameters}")
    print(f"Erstellte Simulationsannahmen: {simulation_assumptions}")
    print(f"Verwendete Kosten-Annahmen: {cost_model_assumptions}")

    # Geräte für Simulation auswählen
    sim_appliances = [a for a in selected_appliances if a in shift_metrics and a in df_load_filt.columns]
    df_load_for_simulation_input = df_load_filt[sim_appliances].copy() if sim_appliances else pd.DataFrame()
    print(f"df_load_for_simulation_input leer? {df_load_for_simulation_input.empty}, Geräte für Sim: {sim_appliances}")

    # --- 5. SZENARIO-ANALYSE DURCHFÜHREN ---
    analysis_results = {} 
    if not df_load_for_simulation_input.empty:
        print("Starte evaluate_dr_scenario...")
        analysis_results = evaluate_dr_scenario(
            df_load_to_simulate=df_load_for_simulation_input,
            # appliances_for_simulation parameter wird in evaluate_dr_scenario nicht mehr erwartet, wenn df_load_to_simulate bereits gefiltert ist
            shift_metrics=shift_metrics,
            df_participation_curve_q10=df_participation_curve_q10,
            event_parameters=event_parameters,
            simulation_assumptions=simulation_assumptions,
            df_spot_prices_eur_mwh=df_spot['price_eur_mwh'], 
            df_reg_original_data=df_reg,
            cost_model_assumptions=cost_model_assumptions
        )
        print(f"Szenario-Analyse Output erhalten: Keys={analysis_results.keys()}")
    else:
        print("df_load_for_simulation_input ist leer, Analyse übersprungen.")
        # Fülle analysis_results mit Default-Werten, damit .get() unten funktioniert
        analysis_results = {
            "value_added_eur": 0.0, "baseline_spot_costs_eur": 0.0, "scenario_spot_costs_eur": 0.0,
            "dr_program_costs_eur": 0.0, "ancillary_service_savings_eur": 0.0,
            "total_shifted_energy_kwh_event": 0.0, "average_payout_rate_eur_per_kwh_event": 0.0,
            "df_shiftable_per_appliance": pd.DataFrame(0.0, index=df_load_filt.index, columns=sim_appliances if sim_appliances else df_load_filt.columns),
            "df_payback_per_appliance": pd.DataFrame(0.0, index=df_load_filt.index, columns=sim_appliances if sim_appliances else df_load_filt.columns)
        }


    # --- 6. ERGEBNISSE FÜR GRAFIKEN UND KPIs EXTRAHIEREN ---
    df_shiftable_res = analysis_results.get("df_shiftable_per_appliance")
    df_payback_res = analysis_results.get("df_payback_per_appliance")
    
    fig_per_appliance_comparison = make_per_appliance_comparison_figure(
        df_load_original_disaggregated=df_load_filt, 
        df_shiftable_per_appliance=df_shiftable_res,
        df_payback_per_appliance=df_payback_res,
        appliances_to_plot=sim_appliances
    )
    
    value_added = analysis_results.get("value_added_eur", 0.0)
    baseline_spot_costs = analysis_results.get("baseline_spot_costs_eur", 0.0)
    scenario_spot_costs = analysis_results.get("scenario_spot_costs_eur", 0.0)
    spot_savings = baseline_spot_costs - scenario_spot_costs
    as_savings = analysis_results.get("ancillary_service_savings_eur", 0.0)
    dr_costs = analysis_results.get("dr_program_costs_eur", 0.0)
    total_shifted_kwh = analysis_results.get("total_shifted_energy_kwh_event", 0.0)
    avg_payout_kwh = analysis_results.get("average_payout_rate_eur_per_kwh_event", 0.0)

    # Formatierung für die Anzeige
    kpi_value_added_text = f"{value_added:.2f} EUR"
    kpi_spot_savings_text = f"{spot_savings:.2f} EUR"
    kpi_as_savings_text = f"{as_savings:.2f} EUR"
    kpi_dr_costs_text = f"{dr_costs:.2f} EUR"
    kpi_total_shifted_text = f"{total_shifted_kwh:.2f} kWh"
    kpi_avg_payout_text = f"{avg_payout_kwh:.4f} EUR/kWh"

    print("Callback beendet, gebe Figur und KPI-Texte zurück.")
    return (
        fig_per_appliance_comparison,
        kpi_value_added_text,
        kpi_spot_savings_text,
        kpi_as_savings_text,
        kpi_dr_costs_text,
        kpi_total_shifted_text,
        kpi_avg_payout_text
    )