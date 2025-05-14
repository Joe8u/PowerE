import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Stelle sicher, dass du deine Kernsimulationsfunktion importieren kannst
# Der genaue Pfad hängt davon ab, wo simulate_respondent_level_load_shift jetzt genau liegt.
# Basierend auf deinem Dump ist es in src/logic/load_shifting_simulation.py
from logic.load_shifting_simulation import simulate_respondent_level_load_shift

def get_flexibility_potential(
    appliance_name: str,
    event_duration_hours: float,
    incentive_pct: float,
    df_respondent_flexibility: pd.DataFrame,
    df_average_load_profile_appliance_only: pd.DataFrame,
    base_simulation_assumptions: dict,
    dummy_event_start_time: datetime = datetime(2024, 1, 1, 12, 0, 0)
):
    """
    Berechnet die Teilnahmequote (approximiert) und die verschiebbare Energie 
    für ein Gerät, eine gegebene Event-Dauer und einen Anreiz.
    (Implementierung wie im vorherigen Vorschlag)
    """
    df_flex_device = df_respondent_flexibility[df_respondent_flexibility['device'] == appliance_name].copy()
    if df_flex_device.empty:
        return {"participation_rate": 0.0, "shifted_energy_kwh": 0.0, "avg_shifted_power_kw": 0.0, "num_participants": 0}

    event_params = {
        'start_time': dummy_event_start_time,
        'end_time': dummy_event_start_time + timedelta(hours=event_duration_hours),
        'required_duration_hours': event_duration_hours,
        'incentive_percentage': incentive_pct / 100.0
    }

    # Sicherstellen, dass das Lastprofil nur die eine Spalte für das Gerät enthält und das Fenster abdeckt
    if appliance_name not in df_average_load_profile_appliance_only.columns or \
       len(df_average_load_profile_appliance_only.columns) > 1:
        # print(f"Warnung: Das übergebene Lastprofil für {appliance_name} ist nicht korrekt formatiert.")
        return {"participation_rate": 0.0, "shifted_energy_kwh": 0.0, "avg_shifted_power_kw": 0.0, "num_participants": 0}

    if df_average_load_profile_appliance_only.index.min() > event_params['start_time'] or \
       df_average_load_profile_appliance_only.index.max() < (event_params['end_time'] - timedelta(minutes=1)): # Ende exklusiv
        # print(f"Warnung: Lastprofil für {appliance_name} deckt das Event-Fenster nicht ab. Profil: {df_average_load_profile_appliance_only.index.min()} - {df_average_load_profile_appliance_only.index.max()}, Event: {event_params['start_time']} - {event_params['end_time']}")
        return {"participation_rate": 0.0, "shifted_energy_kwh": 0.0, "avg_shifted_power_kw": 0.0, "num_participants": 0}

    sim_assumptions = {
        **base_simulation_assumptions,
        'payback_model': base_simulation_assumptions.get('payback_model', {'type': 'none'})
    }

    sim_output = simulate_respondent_level_load_shift(
        df_respondent_flexibility=df_flex_device,
        df_average_load_profiles=df_average_load_profile_appliance_only,
        event_parameters=event_params,
        simulation_assumptions=sim_assumptions
    )

    shifted_energy_kwh = sim_output.get("total_shifted_energy_kwh", 0.0)
    avg_shifted_power_kw = (shifted_energy_kwh / event_duration_hours) if event_duration_hours > 0 else 0.0

    # Teilnahmequote und Teilnehmerzahl
    num_participants = len(sim_output.get("detailed_participation_for_costing", []))
    num_survey_base_for_dev = df_flex_device['respondent_id'].nunique()
    participation_rate_person_based = (num_participants / num_survey_base_for_dev) * base_simulation_assumptions.get('reality_discount_factor', 1.0) if num_survey_base_for_dev > 0 else 0.0

    return {
        "participation_rate": participation_rate_person_based, # Personen-basierte Teilnahmequote
        "shifted_energy_kwh": shifted_energy_kwh,
        "avg_shifted_power_kw": avg_shifted_power_kw,
        "num_participants": num_participants # Absolute Anzahl der (simulierten) Teilnehmer
    }

# Du könntest hier auch Hilfsfunktionen unterbringen,
# um z.B. das repräsentative Einzelgeräte-Lastprofil vorzubereiten.