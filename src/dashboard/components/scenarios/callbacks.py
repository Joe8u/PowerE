# src/dashboard/components/scenarios/callbacks.py
from dash import callback, Input, Output, State, no_update, dcc # dcc für Fallback Graph hinzugefügt
import plotly.graph_objects as go
import pandas as pd
import datetime

# Datenlader
from data_loader.lastprofile import load_appliances # Lädt Durchschnitts-Lastprofile pro Gerät
from data_loader.spot_price_loader import load_spot_price_range
from data_loader.tertiary_regulation_loader import load_regulation_range

# NEU: Import für die Transformation der Respondentendaten
from logic.respondent_level_model.data_transformer import create_respondent_flexibility_df

# Die Grafikfunktion für den per-Appliance-Vergleich
from .graphs.per_appliance_comparison_graph import make_per_appliance_comparison_figure

# Import der (überarbeiteten) Haupt-Analysefunktion
from logic.scenario_analyzer import evaluate_dr_scenario

@callback(
    Output("per-appliance-comparison-graph", "figure"),
    Output("scenario-kpi-value-added", "children"),
    Output("scenario-kpi-spot-savings", "children"),
    Output("scenario-kpi-as-savings", "children"),
    Output("scenario-kpi-dr-costs", "children"),
    Output("scenario-kpi-total-shifted-energy", "children"),
    Output("scenario-kpi-avg-payout-rate", "children"),
    Input("scenario-run-button", "n_clicks"),
    State("scenario-appliance-dropdown", "value"),
    State("scenario-date-picker", "start_date"),
    State("scenario-date-picker", "end_date"),
    State("scenario-dr-start-hour", "value"),
    State("scenario-dr-duration-hours", "value"),
    State("scenario-dr-incentive-pct", "value"),
    # Optional: State für 'reality_discount_factor', falls über UI einstellbar
    # State("scenario-reality-discount-factor", "value"), 
)
def update_scenario_simulation_graph(
    n_clicks,
    selected_appliances_from_ui, # Umbenannt für Klarheit
    start_date_str,
    end_date_str,
    dr_start_hour,
    dr_duration_hours,
    dr_incentive_pct
    # reality_discount_factor_ui # Optionaler Parameter
):
    print(f"---- Szenario-Callback GESTARTET, n_clicks: {n_clicks} ----")
    
    # Fallback-Objekte für den Fall eines vorzeitigen Abbruchs
    empty_figure = go.Figure().update_layout(title_text="Keine Daten für Visualisierung verfügbar")
    no_data_text = "N/A"
    # 1 Graph + 6 KPIs
    initial_return_values = [empty_figure] + [no_data_text] * 6 

    if n_clicks == 0 or n_clicks is None:
        print("Button noch nicht geklickt oder n_clicks ist None. Keine Aktualisierung.")
        # no_update für alle Outputs zurückgeben
        return [no_update] * 7 

    # --- 1. Eingaben parsen und vorbereiten ---
    try:
        start_dt = datetime.datetime.fromisoformat(start_date_str)
        end_dt = datetime.datetime.fromisoformat(end_date_str)
        # Stellen Sie sicher, dass end_dt nicht vor start_dt liegt
        if end_dt <= start_dt:
            print("Fehler: End-Datum muss nach Start-Datum liegen.")
            # Hier könnten Sie eine Fehlermeldung an die UI zurückgeben
            return initial_return_values 
    except ValueError as e:
        print(f"Fehler beim Parsen der Datumseingaben: {e}")
        return initial_return_values

    if not selected_appliances_from_ui:
        print("Keine Geräte für Simulation ausgewählt.")
        # Hier könnten Sie eine nutzerfreundliche Meldung ausgeben
        # Für den Graphen eine leere Figur mit Hinweis
        fig_no_appliances = go.Figure().update_layout(title_text="Bitte Geräte für die Simulation auswählen.")
        return [fig_no_appliances] + [no_data_text] * 6


    # --- 2. Basis-DATEN LADEN (Durchschnitts-Lastprofile, Spotpreise, Regelenergie) ---
    # df_load_filt enthält die Durchschnitts-Lastprofile für die ausgewählten Geräte
    print(f"Lade Durchschnitts-Lastprofile für: {selected_appliances_from_ui}")
    df_average_load_profiles_selected = load_appliances(
        appliances=selected_appliances_from_ui, start=start_dt, end=end_dt, year=2024, group=True # group=True, falls gruppierte Profile verwendet werden
    )
    print(f"df_average_load_profiles_selected geladen, leer? {df_average_load_profiles_selected.empty}, Zeilen: {len(df_average_load_profiles_selected)}")
    
    if df_average_load_profiles_selected.empty:
        print("Keine Lastdaten für ausgewählten Zeitraum/Geräte gefunden.")
        fig_no_data = go.Figure().update_layout(title_text="Keine Lastprofildaten für Auswahl gefunden.")
        return [fig_no_data] + [no_data_text] * 6

    df_spot = load_spot_price_range(start_dt, end_dt, as_kwh=False) # Preise als EUR/MWh
    df_reg = load_regulation_range(start_dt, end_dt)
    print("Spot- und Regelenergiedaten geladen.")

    # --- 3. RESPONDENTEN-FLEXIBILITÄTSDATEN für Simulation laden ---
    # ANPASSUNG: Lade df_respondent_flexibility anstelle von shift_metrics und df_participation_curve_q10
    try:
        df_respondent_flexibility = create_respondent_flexibility_df()
        print(f"df_respondent_flexibility geladen, Shape: {df_respondent_flexibility.shape}")
        if df_respondent_flexibility.empty:
            print("WARNUNG: df_respondent_flexibility ist leer. Simulation wird möglicherweise kein Shift-Potenzial ergeben.")
    except Exception as e:
        print(f"FEHLER beim Laden von df_respondent_flexibility: {e}")
        # Fallback, falls das Laden der Flexibilitätsdaten fehlschlägt
        fig_error_flex = go.Figure().update_layout(title_text="Fehler beim Laden der Flexibilitätsdaten.")
        return [fig_error_flex] + [no_data_text] * 6


    # --- 4. EVENT-PARAMETER und SIMULATIONS-/KOSTEN-ANNAHMEN erstellen ---
    try:
        dr_start_hour_int = int(dr_start_hour) if dr_start_hour is not None else 14 # Default 14 Uhr
        dr_duration_float = float(dr_duration_hours) if dr_duration_hours is not None and float(dr_duration_hours) > 0 else 2.0 # Default 2h
        dr_incentive_float = float(dr_incentive_pct) if dr_incentive_pct is not None else 15.0 # Default 15%

        # Event-Zeiten relativ zum Startdatum des ausgewählten Bereichs
        # Sicherstellen, dass event_start_actual_dt innerhalb des ausgewählten Datumsbereichs liegt
        event_start_actual_dt = pd.Timestamp(f"{start_date_str}T{dr_start_hour_int:02d}:00:00")
        if not (start_dt <= event_start_actual_dt < end_dt): # Event muss im Zeitfenster starten
             print(f"WARNUNG: Event-Startzeit {event_start_actual_dt} liegt außerhalb des gewählten Zeitraums {start_dt}-{end_dt}. Justiere auf {start_dt}.")
             event_start_actual_dt = start_dt # Fallback auf Beginn des gewählten Zeitraums

        event_end_actual_dt = event_start_actual_dt + pd.Timedelta(hours=dr_duration_float)
        # Sicherstellen, dass das Event-Ende nicht über das Ende des gewählten Zeitraums hinausragt
        if event_end_actual_dt > end_dt:
            print(f"WARNUNG: Event-Endzeit {event_end_actual_dt} geht über das Ende des gewählten Zeitraums {end_dt} hinaus. Kürze Event-Dauer.")
            event_end_actual_dt = end_dt
            dr_duration_float = (event_end_actual_dt - event_start_actual_dt).total_seconds() / 3600.0
            if dr_duration_float <=0:
                print("FEHLER: Effektive Event-Dauer ist <=0 nach Anpassung an Zeitfenster.")
                return initial_return_values


    except ValueError as e:
        print(f"Fehler bei der Konvertierung der Event-Parameter: {e}. Verwende Fallback-Werte.")
        # Fallback für Parameter, falls Konvertierung fehlschlägt
        event_start_actual_dt = start_dt + pd.Timedelta(hours=14)
        dr_duration_float = 2.0
        event_end_actual_dt = event_start_actual_dt + pd.Timedelta(hours=dr_duration_float)
        dr_incentive_float = 15.0
        # Sicherstellen, dass auch Fallback-Event-Zeiten im gewählten Bereich liegen
        if event_start_actual_dt >= end_dt or event_end_actual_dt > end_dt :
            event_start_actual_dt = start_dt
            event_end_actual_dt = min(end_dt, start_dt + pd.Timedelta(hours=2))
            dr_duration_float = (event_end_actual_dt - event_start_actual_dt).total_seconds() / 3600.0
            if dr_duration_float <=0: return initial_return_values


    event_parameters = {
        'start_time': event_start_actual_dt,
        'end_time': event_end_actual_dt,
        'required_duration_hours': dr_duration_float,
        'incentive_percentage': dr_incentive_float / 100.0 # Umwandlung in 0-1 Wert
    }
    
    # Realitätsabschlag könnte auch aus der UI kommen
    # reality_discount = float(reality_discount_factor_ui) if reality_discount_factor_ui is not None else 0.7
    simulation_assumptions = {
        'reality_discount_factor': 0.7, # Standardwert, kann später UI-gesteuert sein
        'payback_model': {'type': 'uniform_after_event', 'duration_hours': dr_duration_float, 'delay_hours': 0.25}
    }
    
    # Kostenmodell-Annahmen (Beispielwerte)
    avg_household_price_eur_kwh = 0.276 # Beispiel: 0.29 CHF/kWh * 0.95 EUR/CHF (Annahme)
    cost_model_assumptions = {
        'avg_household_electricity_price_eur_kwh': avg_household_price_eur_kwh,
        'assumed_dr_events_per_month': 12,
        'as_displacement_factor': 0.1 # Annahme für Regelenergieverdrängung
    }
    print(f"Finale Event-Parameter: {event_parameters}")
    print(f"Simulationsannahmen: {simulation_assumptions}")
    print(f"Kosten-Annahmen: {cost_model_assumptions}")

    # Die `df_average_load_profiles_selected` enthalten bereits nur die vom Nutzer ausgewählten und im Lastprofil-Loader gefundenen Geräte.
    # Es ist nicht mehr nötig, hier weiter auf `sim_appliances` zu filtern, da `evaluate_dr_scenario`
    # intern mit den Spalten von `df_average_load_profiles` und den Geräten in `df_respondent_flexibility` arbeitet.
    
    # --- 5. SZENARIO-ANALYSE DURCHFÜHREN ---
    analysis_results = {} 
    # df_average_load_profiles_selected enthält die für die Simulation zu verwendenden Durchschnitts-Lastprofile
    if not df_average_load_profiles_selected.empty:
        print(f"Starte evaluate_dr_scenario mit {len(df_average_load_profiles_selected.columns)} Geräten...")
        
        # ANPASSUNG des Aufrufs von evaluate_dr_scenario
        analysis_results = evaluate_dr_scenario(
            df_respondent_flexibility=df_respondent_flexibility,         # NEU
            df_average_load_profiles=df_average_load_profiles_selected,  # UMBENANNT (vorher df_load_to_simulate)
            event_parameters=event_parameters,
            simulation_assumptions=simulation_assumptions,
            df_spot_prices_eur_mwh=df_spot['price_eur_mwh'] if not df_spot.empty else pd.Series(dtype=float), 
            df_reg_original_data=df_reg,
            cost_model_assumptions=cost_model_assumptions
        )
        print(f"Szenario-Analyse Output erhalten: Keys={list(analysis_results.keys())}")
    else:
        print("df_average_load_profiles_selected ist leer, Analyse übersprungen.")
        # Fallback-Struktur für analysis_results, damit .get() unten funktioniert
        analysis_results = {
            "value_added_eur": 0.0, "baseline_spot_costs_eur": 0.0, "scenario_spot_costs_eur": 0.0,
            "dr_program_costs_eur": 0.0, "ancillary_service_savings_eur": 0.0,
            "original_aggregated_load_kw": pd.Series(dtype=float),
            "final_shifted_aggregated_load_kw": pd.Series(dtype=float),
            "df_shiftable_per_appliance": pd.DataFrame(0.0, index=df_average_load_profiles_selected.index, columns=df_average_load_profiles_selected.columns),
            "df_payback_per_appliance": pd.DataFrame(0.0, index=df_average_load_profiles_selected.index, columns=df_average_load_profiles_selected.columns),
            "total_shifted_energy_kwh_event": 0.0, 
            "average_payout_rate_eur_per_kwh_event": 0.0,
            "detailed_participation_for_costing": []
        }

    # --- 6. ERGEBNISSE FÜR GRAFIKEN UND KPIs EXTRAHIEREN ---
    # Verwende .get() mit Fallback-Werten, um Fehler zu vermeiden, falls Schlüssel fehlen
    df_shiftable_res = analysis_results.get("df_shiftable_per_appliance", pd.DataFrame(index=df_average_load_profiles_selected.index))
    df_payback_res = analysis_results.get("df_payback_per_appliance", pd.DataFrame(index=df_average_load_profiles_selected.index))
    
    # Die Geräte für den Plot sind die Spalten der ursprünglichen Auswahl, die auch simuliert wurden.
    # df_average_load_profiles_selected.columns sollte hier korrekt sein.
    appliances_plotted = df_average_load_profiles_selected.columns.tolist()

    fig_per_appliance_comparison = make_per_appliance_comparison_figure(
        df_load_original_disaggregated=df_average_load_profiles_selected, 
        df_shiftable_per_appliance=df_shiftable_res,
        df_payback_per_appliance=df_payback_res,
        appliances_to_plot=appliances_plotted 
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