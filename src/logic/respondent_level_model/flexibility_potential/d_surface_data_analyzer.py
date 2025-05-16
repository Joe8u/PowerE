# PowerE/src/logic/respondent_level_model/flexibility_potential/d_surface_data_analyzer.py
import pandas as pd
import numpy as np
import sys
from pathlib import Path
import plotly.express as px # Für optionale einfache 2D-Plots

# Importiere die benötigten Funktionen aus den anderen Modulen dieses Pakets
try:
    from .a_survey_data_preparer import prepare_survey_flexibility_data
    from .b_participation_calculator import calculate_participation_metrics
except ImportError:
    module_path = Path(__file__).resolve().parent
    if str(module_path.parent.parent.parent) not in sys.path: # Gehe zum Projekt-Root (src/logic/rm/fp -> ... -> PowerE)
         sys.path.insert(0, str(module_path.parent.parent.parent.parent))
    from src.logic.respondent_level_model.flexibility_potential.a_survey_data_preparer import prepare_survey_flexibility_data
    from src.logic.respondent_level_model.flexibility_potential.b_participation_calculator import calculate_participation_metrics

# Globale Parameter (können hier für Konsistenz definiert werden)
MAX_EVENT_DURATION_ANALYSIS = 30.0 
INCENTIVE_STEPS_ANALYSIS = 11             
MAX_INCENTIVE_PCT_ANALYSIS = 50.0
incentives_analysis_range = np.linspace(0, MAX_INCENTIVE_PCT_ANALYSIS, INCENTIVE_STEPS_ANALYSIS)

def get_participation_surface_data_for_analysis(
    df_survey_data: pd.DataFrame, 
    target_appliance_name: str, 
    max_duration_axis_param: float = MAX_EVENT_DURATION_ANALYSIS,
    incentives_range_param: np.ndarray = incentives_analysis_range
) -> tuple | None:
    """
    Berechnet die X, Y, Z Datenmatrizen für die Teilnahmequote eines Geräts.
    (Diese Funktion ist im Wesentlichen identisch mit der, die wir im Notebook hatten)
    """
    df_analysis_copy = df_survey_data.copy()
    cols_to_rename = {}
    if 'max_duration_hours_num' in df_analysis_copy.columns: cols_to_rename['max_duration_hours_num'] = 'survey_max_duration_h'
    if 'incentive_choice' in df_analysis_copy.columns: cols_to_rename['incentive_choice'] = 'survey_incentive_choice'
    if 'incentive_pct_required_num' in df_analysis_copy.columns: cols_to_rename['incentive_pct_required_num'] = 'survey_incentive_pct_required'
    if cols_to_rename:
        df_analysis_copy.rename(columns=cols_to_rename, inplace=True)

    expected_cols = ['survey_max_duration_h', 'survey_incentive_choice', 'survey_incentive_pct_required', 'device', 'respondent_id']
    if not all(col in df_analysis_copy.columns for col in expected_cols):
        print(f"FEHLER: Nicht alle erwarteten Spalten in df_analysis_copy für {target_appliance_name}.")
        return None, None, None, None

    appliance_specific_durations = df_analysis_copy[df_analysis_copy['device'] == target_appliance_name]['survey_max_duration_h'].dropna().unique()
    durations_plot_range_output = sorted([d for d in appliance_specific_durations if 0 < d <= max_duration_axis_param])
    
    if not durations_plot_range_output:
        all_positive_dev_durations = sorted([d for d in appliance_specific_durations if d > 0])
        if not all_positive_dev_durations: durations_plot_range_output = np.array([1.5])
        else:
            temp_range_dev = [d for d in all_positive_dev_durations if d <= max_duration_axis_param]
            if not temp_range_dev: durations_plot_range_output = np.array([min(all_positive_dev_durations)])
            else: durations_plot_range_output = np.array(sorted(list(set(temp_range_dev))))
            
    if np.array(durations_plot_range_output).size == 0:
        print(f"FEHLER: durations_plot_range_output für {target_appliance_name} ist leer.")
        return None, None, None, None
        
    X_incentives, Y_durations = np.meshgrid(incentives_range_param, durations_plot_range_output)
    Z_participation = np.zeros(X_incentives.shape)

    for i, duration_val in enumerate(durations_plot_range_output):
        for j, incentive_val in enumerate(incentives_range_param):
            metrics = calculate_participation_metrics(
                df_survey_flex_input=df_analysis_copy, 
                target_appliance=target_appliance_name,
                event_duration_h=float(duration_val),
                offered_incentive_pct=float(incentive_val)
            )
            Z_participation[i, j] = metrics['raw_participation_rate'] * 100
            
    print(f"Analysedaten für {target_appliance_name} (Min/Max Teilnahmequote): {Z_participation.min():.1f}% / {Z_participation.max():.1f}%")
    return X_incentives, Y_durations, Z_participation, durations_plot_range_output

def analyze_device_participation_slices(X_data, Y_data, Z_data, durations_list, incentives_list, device_name):
    """Analysiert und druckt Slices aus den 3D-Daten."""
    if Z_data is None:
        print(f"Keine Daten für {device_name} zum Analysieren vorhanden.")
        return

    print(f"\n--- Detailanalyse für: {device_name} ---")
    print(f"Simulierte Dauern (Y-Achse): {durations_list}")
    print(f"Simulierte Anreize (X-Achse): {incentives_list}")

    # Beispiel: Teilnahmequote bei einem bestimmten Anreiz (z.B. 15%) für verschiedene Dauern
    target_incentive = 15.0
    if target_incentive in incentives_list:
        idx_incentive = np.where(incentives_list == target_incentive)[0][0]
        df_slice_by_duration = pd.DataFrame({
            'Dauer (h)': Y_data[:, idx_incentive],
            f'Teilnahmequote (%) bei {target_incentive}% Anreiz': Z_data[:, idx_incentive]
        })
        print(f"\n{device_name}: Teilnahmequoten bei {target_incentive}% Anreiz:")
        print(df_slice_by_duration)
    else:
        print(f"Anreiz {target_incentive}% nicht in incentives_list gefunden.")

    # Beispiel: Teilnahmequote bei einer bestimmten Dauer (z.B. 4.5h) für verschiedene Anreize
    target_duration = 4.5
    if target_duration in durations_list:
        idx_duration = durations_list.index(target_duration) # list.index()
        df_slice_by_incentive = pd.DataFrame({
            'Anreiz (%)': X_data[idx_duration, :],
            f'Teilnahmequote (%) bei {target_duration}h Dauer': Z_data[idx_duration, :]
        })
        print(f"\n{device_name}: Teilnahmequoten bei {target_duration}h Dauer:")
        print(df_slice_by_incentive)
        
        # Optionaler einfacher 2D Plot für diesen Slice
        # fig_slice = px.line(df_slice_by_incentive, x='Anreiz (%)', y=f'Teilnahmequote (%) bei {target_duration}h Dauer',
        #                             title=f'{device_name}: Teilnahme vs. Anreiz (bei {target_duration}h Dauer)', markers=True)
        # fig_slice.show() 
    else:
        print(f"Dauer {target_duration}h nicht in den simulierten Dauern für {device_name} enthalten.")


if __name__ == '__main__':
    print("--- Starte Analyse der Flexibilitätspotenzial-Daten (d_surface_data_analyzer.py) ---")
    
    # Pfad-Setup für Standalone-Ausführung (wie in a_survey_data_preparer.py)
    current_script_path_main = Path(__file__).resolve()
    project_root_main = current_script_path_main.parent.parent.parent.parent # PowerE Ordner
    if str(project_root_main) not in sys.path:
        sys.path.insert(0, str(project_root_main))
        print(f"Standalone-Modus: '{project_root_main}' zu sys.path hinzugefügt.")

    try:
        print("Lade und bereite Umfragedaten vor...")
        df_survey_flex_main = prepare_survey_flexibility_data()

        if not df_survey_flex_main.empty:
            # Analysiere für ausgewählte Geräte
            devices_to_analyze = ["Geschirrspüler", "Waschmaschine", "Backofen und Herd", "Bürogeräte", "Fernseher und Entertainment-Systeme"] 
            # devices_to_analyze = [dev for dev in df_survey_flex_main['device'].unique().tolist() if pd.notna(dev)] # Alle Geräte

            for device in devices_to_analyze:
                X_data, Y_data, Z_data, durations_list = get_participation_surface_data_for_analysis(
                    df_survey_flex_main, device
                )
                analyze_device_participation_slices(X_data, Y_data, Z_data, durations_list, incentives_analysis_range, device)
        else:
            print("Aufbereitete Umfragedaten sind leer. Keine Analyse möglich.")
    
    except Exception as e:
        print(f"Ein Fehler ist im Hauptteil von d_surface_data_analyzer.py aufgetreten: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n--- Analyse der Flexibilitätspotenzial-Daten beendet ---")