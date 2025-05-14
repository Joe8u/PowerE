# PowerE/scripts/visualize_flexibility_surface.py

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os

# === ANFANG: Robuster Pfad-Setup ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
    print(f"Added project root '{PROJECT_ROOT}' to sys.path")
# === ENDE: Robuster Pfad-Setup ===

try:
    from src.logic.respondent_level_model.flexibility_analyzer import get_flexibility_potential
    from src.logic.respondent_level_model.data_transformer import create_respondent_flexibility_df
    # from src.data_loader.lastprofile import load_appliances # Optional
except ModuleNotFoundError as e:
    print(f"FEHLER beim Importieren von Modulen aus 'src': {e}")
    # ... (Fehlermeldungen wie gehabt) ...
    sys.exit(1)

def create_and_show_flexibility_plot(
    target_appliance="Waschmaschine",
    plot_type="energy",
    df_respondent_flex_full_param=None,
    desired_max_duration_h=18.0  # Standardmäßig auf 18h gesetzt
):
    print(f"\nStarte Visualisierung für: {target_appliance} (Plot: {plot_type}, Max-Dauer bis: {desired_max_duration_h}h)")

    print("Lade Basisdaten...")
    if df_respondent_flex_full_param is None:
        try:
            df_respondent_flex_full = create_respondent_flexibility_df()
            print(f"Flexibilitätsdaten geladen. Shape: {df_respondent_flex_full.shape}")
            if df_respondent_flex_full.empty:
                print("WARNUNG: Geladene Flexibilitätsdaten sind leer.")
        # ... (Fehlerbehandlung wie in deinem Code) ...
        except FileNotFoundError as e:
            print(f"FEHLER beim Laden der Umfragedaten für df_respondent_flex_full: {e}")
            return
        except Exception as e:
            print(f"Ein anderer Fehler beim Laden der Flexibilitätsdaten: {e}")
            return
    else:
        df_respondent_flex_full = df_respondent_flex_full_param

    base_sim_assumptions = {
        'reality_discount_factor': 0.7,
        'payback_model': {'type': 'none'}
    }
    print("Basisdaten und Annahmen vorbereitet.")

    # --- Bestimme durations_range basierend auf Survey und desired_max_duration_h ---
    durations_range_final = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0]) # Standard-Fallback
    max_plot_duration_h_final = desired_max_duration_h # Startwert

    if not df_respondent_flex_full.empty and 'max_duration_hours' in df_respondent_flex_full.columns:
        unique_survey_durations = sorted(df_respondent_flex_full['max_duration_hours'].dropna().unique())
        durations_range_filtered = [d for d in unique_survey_durations if 0 < d <= desired_max_duration_h]
        
        if not durations_range_filtered: # Falls keine Survey-Dauer die Bedingung erfüllt
            print(f"WARNUNG: Keine Survey-Dauern <= {desired_max_duration_h}h gefunden. Suche kleinste passende Survey-Dauer oder verwende Fallback.")
            # Nimm alle positiven Survey-Dauern und filtere die, die am nächsten dran sind, oder die kleinste.
            all_positive_survey_durations = [d for d in unique_survey_durations if d > 0]
            if all_positive_survey_durations:
                # Nimm alle, die kleiner oder gleich desired_max sind, oder nur die kleinste, wenn alle größer sind
                temp_range = [d for d in all_positive_survey_durations if d <= desired_max_duration_h]
                if not temp_range: # Wenn alle Survey-Dauern größer als desired_max sind
                    durations_range_final = np.array([min(all_positive_survey_durations)]) # Nimm die kleinste verfügbare Survey-Dauer
                else:
                    durations_range_final = np.array(sorted(list(set(temp_range))))
            else: # Keine positiven Survey-Dauern vorhanden
                durations_range_final = np.array([d for d in [0.5, 1.0, 1.5] if d <= desired_max_duration_h and d > 0])
                if durations_range_final.size == 0: durations_range_final = np.array([0.5])
                print(f"Verwende absoluten Fallback für Dauer (begrenzt durch {desired_max_duration_h}h): {durations_range_final}")
        else:
            durations_range_final = np.array(sorted(list(set(durations_range_filtered))))
        
        print(f"Verwendete Event-Dauern (max {desired_max_duration_h}h, basierend auf Q9): {durations_range_final} Stunden")
    else: # Fallback, wenn Flex-Daten leer sind
        durations_range_final = np.array([d for d in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0] if d <= desired_max_duration_h and d > 0])
        if durations_range_final.size == 0 and desired_max_duration_h > 0: durations_range_final = np.array([min(0.5, desired_max_duration_h)])
        elif durations_range_final.size == 0: durations_range_final = np.array([0.5])
        max_plot_duration_h_final = durations_range_final.max() if durations_range_final.size > 0 else desired_max_duration_h
        print(f"WARNUNG: Flex-Daten leer. Verwende Standard-Range für Dauer (begrenzt durch {desired_max_duration_h}h): {durations_range_final} Stunden")

    if durations_range_final.size == 0:
        print(f"FEHLER: `durations_range_final` ist leer. Plot kann nicht erstellt werden.")
        return
    max_plot_duration_h_final = durations_range_final.max()
    print(f"Finale `max_plot_duration_h` für Profilerstellung: {max_plot_duration_h_final} Stunden")

    # --- Repräsentatives Lastprofil erstellen/laden ---
    num_intervals_profile = int(np.ceil(max_plot_duration_h_final / 0.25))
    if num_intervals_profile == 0: num_intervals_profile = 1
    
    dummy_start_time_profile = datetime(2024, 1, 1, 12, 0, 0)
    plot_profile_index = pd.date_range(start=dummy_start_time_profile, periods=num_intervals_profile, freq="15T")
    
    POWER_KW_TYPICAL_OPERATION = 1.0
    if target_appliance == "Geschirrspüler": POWER_KW_TYPICAL_OPERATION = 1.2
    elif target_appliance == "Backofen und Herd": POWER_KW_TYPICAL_OPERATION = 2.0
    
    representative_profile_one_appliance = pd.DataFrame(
        {target_appliance: POWER_KW_TYPICAL_OPERATION}, index=plot_profile_index
    )
    for col in list(representative_profile_one_appliance.columns):
        if col != target_appliance: del representative_profile_one_appliance[col]

    if representative_profile_one_appliance.empty or target_appliance not in representative_profile_one_appliance.columns:
        print(f"FEHLER: Repräsentatives Profil für {target_appliance} konnte nicht korrekt erstellt werden.")
        return
    print(f"Verwendetes repräsentatives Profil für '{target_appliance}': Konstant {POWER_KW_TYPICAL_OPERATION} kW, Dauer: {len(plot_profile_index)*0.25}h")

    # --- Daten für Plot generieren ---
    print(f"Generiere Daten für 3D-Plot für {target_appliance}...")
    incentives_range = np.linspace(0, 50, 11) # 0, 5, ..., 50 %
    
    X_incentives, Y_durations = np.meshgrid(incentives_range, durations_range_final) # Verwende durations_range_final
    Z_shifted_energy = np.zeros(X_incentives.shape)
    Z_participation_rate = np.zeros(X_incentives.shape)
    # ... (andere Z-Variablen initialisieren) ...

    for i, duration_val in enumerate(durations_range_final):
        print(f"  Bearbeite Dauer: {duration_val:.1f}h...")
        for j, incentive_val in enumerate(incentives_range):
            effective_dummy_start_time = representative_profile_one_appliance.index.min()
            potential_event_end_time = effective_dummy_start_time + timedelta(hours=duration_val)
            
            profile_coverage_ends_at = representative_profile_one_appliance.index.min() + \
                                       timedelta(hours=len(representative_profile_one_appliance.index) * 0.25)

            if potential_event_end_time > profile_coverage_ends_at:
                Z_shifted_energy[i, j] = np.nan; Z_participation_rate[i, j] = np.nan
                # ... (andere Z-Werte auf np.nan) ...
                continue

            metrics = get_flexibility_potential(
                appliance_name=target_appliance, event_duration_hours=duration_val,
                incentive_pct=incentive_val, df_respondent_flexibility=df_respondent_flex_full,
                df_average_load_profile_appliance_only=representative_profile_one_appliance.copy(),
                base_simulation_assumptions=base_sim_assumptions,
                dummy_event_start_time=effective_dummy_start_time
            )
            Z_shifted_energy[i, j] = metrics["shifted_energy_kwh"]
            Z_participation_rate[i, j] = metrics["participation_rate"]
            # ... (andere Z-Werte füllen) ...
    print("Daten für Plot generiert.")

    # --- 3D-Visualisierung ---
    if plot_type == "energy": z_data, z_title_suffix, bar_title = Z_shifted_energy, 'Verschobene Energie (kWh)', 'Energie (kWh)'
    elif plot_type == "participation": z_data, z_title_suffix, bar_title = Z_participation_rate * 100, 'Teilnahmequote (Personen-basiert, %)', 'Teilnahme (%)'
    # ... (andere plot_types) ...
    else: print(f"Unbekannter plot_type: {plot_type}."); return

    if z_data.size > 0 and not np.all(np.isnan(z_data)):
        print(f"Erstelle 3D-Plot für: {z_title_suffix}...")
        fig = go.Figure(data=[go.Surface(
            z=z_data, x=X_incentives, y=Y_durations, colorscale='Viridis',
            colorbar_title=bar_title, name=target_appliance,
            contours = {"z": {"show": True, "highlightcolor":"limegreen", "project":{"z": True}}}
        )])
        fig.update_layout(
            title=f'Flexibilitätspotenzial: {target_appliance}<br>{z_title_suffix}',
            scene=dict(
                xaxis_title='Anreiz (Kompensation in %)',
                yaxis_title='Event-Dauer (Stunden, aus Q9)',
                zaxis_title=z_title_suffix,
                camera=dict(eye=dict(x=1.9, y=-1.2, z=1.2)),
                aspectmode='cube' # NEU: Lässt die Achsen gleich lang erscheinen
            ),
            margin=dict(l=10, r=10, b=10, t=80)
        )
        fig.show()
    else: print(f"Keine validen Daten für den Plot '{plot_type}' vorhanden.")
    print(f"Visualisierung für {target_appliance} ({plot_type}) beendet.")

if __name__ == "__main__":
    df_flex_data_main = None
    try:
        df_flex_data_main = create_respondent_flexibility_df()
    except Exception as e:
        print(f"Konnte Flexibilitätsdaten im Main-Block nicht laden: {e}")

    available_appliances = ["Waschmaschine", "Geschirrspüler", "Backofen und Herd", "Fernseher und Entertainment-Systeme", "Bürogeräte"]
    
    # Setze hier die gewünschte maximale Dauer für die Plots, z.B. 18 Stunden
    MAX_DURATION_FOR_PLOTS = 18.0 

    if df_flex_data_main is not None and not df_flex_data_main.empty:
        for appliance in available_appliances:
            # Du hattest den Energie-Plot auskommentiert, ich lasse es erstmal so:
            # create_and_show_flexibility_plot(
            #     target_appliance=appliance,
            #     plot_type="energy",
            #     df_respondent_flex_full_param=df_flex_data_main,
            #     desired_max_duration_h=MAX_DURATION_FOR_PLOTS
            # )
            create_and_show_flexibility_plot(
                target_appliance=appliance,
                plot_type="participation",
                df_respondent_flex_full_param=df_flex_data_main,
                desired_max_duration_h=MAX_DURATION_FOR_PLOTS
            )
    else:
        print("Flexibilitätsdaten konnten nicht geladen werden oder sind leer, keine Plots werden erstellt.")