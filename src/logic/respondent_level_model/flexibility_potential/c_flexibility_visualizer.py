# PowerE/src/logic/respondent_level_model/flexibility_potential/c_flexibility_visualizer.py
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import sys
from pathlib import Path

# Importiere die benötigten Funktionen aus den anderen Modulen dieses Pakets
# Relative Imports funktionieren, wenn dieses Skript als Teil des Pakets behandelt wird
# oder wenn der sys.path korrekt für den Projekt-Root gesetzt ist.
try:
    from .a_survey_data_preparer import prepare_survey_flexibility_data
    from .b_participation_calculator import calculate_participation_metrics
except ImportError: # Fallback für standalone Ausführung / wenn sys.path noch nicht korrekt
    module_path = Path(__file__).resolve().parent
    if str(module_path.parent.parent.parent) not in sys.path: # Gehe zum Projekt-Root (src/logic/rm/fp -> src/logic/rm -> src/logic -> src -> PowerE)
         sys.path.insert(0, str(module_path.parent.parent.parent.parent))
    from src.logic.respondent_level_model.flexibility_potential.a_survey_data_preparer import prepare_survey_flexibility_data
    from src.logic.respondent_level_model.flexibility_potential.b_participation_calculator import calculate_participation_metrics

def generate_3d_flexibility_surface_plot(
    target_appliance: str,
    df_survey_flex: pd.DataFrame,
    max_event_duration_h_on_plot: float = 30, # Maximale Dauer auf der Y-Achse des Plots
    incentive_steps: int = 11, # Anzahl der Anreizstufen (z.B. 11 für 0,5,10...50)
    max_incentive_pct_on_plot: float = 65.0
):
    """
    Generiert und zeigt einen 3D-Oberflächenplot der modellierten Teilnahmequote
    für ein Zielgerät in Abhängigkeit von Anreiz und Event-Dauer.

    Args:
        target_appliance (str): Name des Zielgeräts.
        df_survey_flex (pd.DataFrame): Aufbereiteter DataFrame mit Umfragedaten 
                                       (Output von prepare_survey_flexibility_data).
        max_event_duration_h_on_plot (float): Maximale Event-Dauer, die auf der Y-Achse 
                                              des Plots berücksichtigt werden soll.
        incentive_steps (int): Anzahl der zu testenden Anreizstufen (inkl. 0%).
        max_incentive_pct_on_plot (float): Maximaler Anreiz in Prozent auf der X-Achse.
    """
    print(f"\n--- Starte Generierung des 3D-Flexibilitäts-Surface-Plots für: {target_appliance} ---")
    print(f"Verwende max. Event-Dauer für Plot: {max_event_duration_h_on_plot}h")

    # 1. Anreizstufen definieren (X-Achse)
    incentives_range = np.linspace(0, max_incentive_pct_on_plot, incentive_steps)
    print(f"Verwendete Anreizstufen (Kompensation %): {incentives_range}")

    # 2. Dauerstufen definieren (Y-Achse)
    # Basierend auf den einzigartigen 'survey_max_duration_h' Werten aus den Umfragedaten,
    # gefiltert nach max_event_duration_h_on_plot.
    durations_range_final = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0]) # Fallback
    if 'survey_max_duration_h' in df_survey_flex.columns:
        unique_survey_durations = sorted(df_survey_flex['survey_max_duration_h'].dropna().unique())
        durations_range_filtered = [d for d in unique_survey_durations if 0 < d <= max_event_duration_h_on_plot]
        
        if not durations_range_filtered: # Umgang mit dem Fall, dass keine Dauern die Kriterien erfüllen
            all_positive_survey_durations = [d for d in unique_survey_durations if d > 0]
            if all_positive_survey_durations:
                # Nimm die kleinste positive Dauer, wenn alle größer als max_event_duration_h_on_plot sind
                # oder nimm alle bis max_event_duration_h_on_plot
                temp_range = [d for d in all_positive_survey_durations if d <= max_event_duration_h_on_plot]
                if not temp_range: durations_range_final = np.array([min(all_positive_survey_durations)])
                else: durations_range_final = np.array(sorted(list(set(temp_range))))
            else: # Keine positiven Survey-Dauern vorhanden, verwende Fallback bis max_event_duration_h_on_plot
                durations_range_final = np.array([d for d in [0.5, 1.0, 1.5] if d <= max_event_duration_h_on_plot and d > 0])
                if durations_range_final.size == 0: durations_range_final = np.array([0.5])
        else:
            durations_range_final = np.array(sorted(list(set(durations_range_filtered))))
    
    if durations_range_final.size == 0:
        print(f"FEHLER: `durations_range_final` für {target_appliance} ist leer. Plot kann nicht erstellt werden.")
        return
    print(f"Verwendete Event-Dauern für Simulation (basierend auf Q9, max {max_event_duration_h_on_plot}h): {durations_range_final} Stunden")

    # 3. Meshgrid und Z-Matrix initialisieren
    X_incentives, Y_durations = np.meshgrid(incentives_range, durations_range_final)
    Z_raw_participation_rate = np.zeros(X_incentives.shape)

    # 4. Teilnahmequoten berechnen
    print(f"Berechne Teilnahmequoten für {target_appliance}...")
    for i, duration_val in enumerate(durations_range_final):
        # print(f"  Bearbeite Dauer: {duration_val:.1f}h...") # Kann bei vielen Geräten/Dauern verbose sein
        for j, incentive_val in enumerate(incentives_range):
            metrics = calculate_participation_metrics(
                df_survey_flex_input=df_survey_flex,
                target_appliance=target_appliance,
                event_duration_h=float(duration_val), # Sicherstellen, dass es float ist
                offered_incentive_pct=float(incentive_val) # Sicherstellen, dass es float ist
            )
            Z_raw_participation_rate[i, j] = metrics['raw_participation_rate'] * 100 # In Prozent für den Plot

    print(f"Daten für {target_appliance} generiert.")

    # 5. 3D-Visualisierung
    if Z_raw_participation_rate.size > 0 and not np.all(np.isnan(Z_raw_participation_rate)):
        print(f"Erstelle 3D-Plot für Teilnahmequote: {target_appliance}...")

        # NEU: Bestimme globale Min/Max-Werte für die Z-Achse ALLER Geräteplots,
        # wenn du eine einheitliche Skala über mehrere Plots hinweg willst.
        # Für einen einzelnen Plot passt Plotly das automatisch an.
        # Wenn wir es einheitlich wollen, müssten wir z_min und z_max
        # ausserhalb dieser Funktion über alle Z_raw_participation_rate Matrizen
        # bestimmen und dann hier übergeben oder als globale Konstanten definieren.
        # Fürs Erste setzen wir einen sinnvollen festen Bereich, z.B. 0-70%
        # (da 70% ca. der Maximalwert wäre, wenn alle teilnehmen und der Discount 0.7 wäre,
        #  oder eben 100% für die rohe Teilnahme).
        # Da wir jetzt die ROHE Teilnahme plotten, ist der realistische Max-Wert 100%.
        # Um die Unterschiede besser zu sehen, können wir auch erst mal schauen,
        # was die maximalen Werte pro Gerät sind und dann einen gemeinsamen Bereich wählen.
        
        # Für eine GERÄTEÜBERGREIFEND konsistente Farbskala:
        Z_AXIS_MIN = 0
        Z_AXIS_MAX = df_survey_flex['respondent_id'].nunique() * 1 # Max. mögliche Teilnehmer, wenn alle unique IDs teilnehmen, mal 100% für die Rate
                                                               # Oder einfacher: einen festen Wert, der alle erwarteten Raten abdeckt, z.B. 70% oder 100%
        # Realistischer für die aktuelle Darstellung ohne Discount:
        # Nehmen wir an, die höchste beobachtete Rate ist z.B. 65% für Geschirrspüler.
        # Ein guter gemeinsamer Maximalwert könnte 70% oder 75% sein.
        # Für eine dynamische Anpassung müsstest du Z_raw_participation_rate von allen Geräten kennen.
        # Für den Moment setzen wir es für die Demonstration auf 0-75%
        # Diesen Wert müsstest du ggf. anpassen, nachdem du alle Plots gesehen hast,
        # um einen guten gemeinsamen Bereich für ALLE Geräte zu finden.
        COLOR_CMIN = 0 
        COLOR_CMAX = 100 # Beispiel: Setze dies auf den globalen Maximalwert + Puffer yaxis_title zaxis_title xaxis_title
        fig = go.Figure(data=[go.Surface(
            z=Z_raw_participation_rate, 
            x=X_incentives, 
            y=Y_durations, 
            colorscale='Viridis',
            colorbar_title='Teilnahme (%)', # Geändert von 'Rohe Teilnahme (%)'
            name=target_appliance,
            contours = {"z": {"show": True, "highlightcolor":"limegreen", "project":{"z": True}}},
            cmin = COLOR_CMIN, # NEU: Minimalwert für die Farbskala
            cmax = COLOR_CMAX  # NEU: Maximalwert für die Farbskala
        )])
        fig.update_layout(
            title=f'Flexibilitätspotenzial: {target_appliance}<br>Modellierte Teilnahmequote (Umfrage-basiert, %)', # "rein" entfernt
            scene=dict(
                xaxis_title='Anreiz (Kompensation in %)',
                yaxis_title='Event-Dauer (Stunden, aus Q9)',
                zaxis_title='Teilnahmequote (%)', # Geändert von 'Rohe Teilnahmequote (%)'
                zaxis = dict(range=[COLOR_CMIN, COLOR_CMAX]), # NEU: Z-Achsen-Bereich festlegen
                camera=dict(eye=dict(x=-1.8, y=1.8, z=1.5)), 
                aspectmode='cube' 
            ),
            margin=dict(l=10, r=10, b=10, t=80)
        )
        fig.show()
    else:
        print(f"Keine validen Daten für den Plot der Teilnahmequote für {target_appliance} vorhanden.")
    
    print(f"--- Visualisierung für {target_appliance} abgeschlossen ---")


if __name__ == '__main__':
    print("--- Starte Testlauf für c_flexibility_visualizer.py ---")
    
    # Stelle sicher, dass der Projekt-Root im sys.path ist für die src-Importe
    # (wie im try-except Block oben im Skript)
    # Dieser Teil ist wichtig, wenn das Skript direkt ausgeführt wird
    current_script_path_main = Path(__file__).resolve()
    project_root_main = current_script_path_main.parent.parent.parent.parent # PowerE Ordner
    if str(project_root_main) not in sys.path:
        sys.path.insert(0, str(project_root_main))
        print(f"Test-Modus: '{project_root_main}' zu sys.path hinzugefügt.")

    try:
        print("Lade und bereite Umfragedaten vor...")
        df_survey_flex_main = prepare_survey_flexibility_data()

        if not df_survey_flex_main.empty:
            available_appliances = [dev for dev in df_survey_flex_main['device'].unique().tolist() if pd.notna(dev)]
            
            # --- NEU: Globales Maximum der Teilnahmequote für einheitliche Skala finden ---
            all_z_rates_max = []
            temp_incentives_range = np.linspace(0, 50, 11) # Beispiel, wie im Plot-Funktion
            temp_max_event_duration = 30.0 # Beispiel, wie im Plot-Funktion

            print("\nErmittle maximale Teilnahmequoten für Skalierung...")
            for appliance_for_max in available_appliances:
                # Dauerstufen für dieses Gerät bestimmen (wie in der Plot-Funktion)
                unique_survey_durations_temp = sorted(df_survey_flex_main[df_survey_flex_main['device'] == appliance_for_max]['survey_max_duration_h'].dropna().unique())
                durations_range_filtered_temp = [d for d in unique_survey_durations_temp if 0 < d <= temp_max_event_duration]
                if not durations_range_filtered_temp: # Fallback, falls keine Dauern passen
                    all_positive_temp = [d for d in unique_survey_durations_temp if d > 0]
                    if not all_positive_temp: current_durations_for_calc = np.array([1.5]) # Absoluter Fallback
                    else: current_durations_for_calc = np.array([min(all_positive_temp)])
                else: current_durations_for_calc = np.array(sorted(list(set(durations_range_filtered_temp))))

                if current_durations_for_calc.size == 0: continue # Überspringe, falls keine Dauern

                max_rate_for_device = 0
                for duration_val_temp in current_durations_for_calc:
                    for incentive_val_temp in temp_incentives_range:
                        metrics_temp = calculate_participation_metrics(
                            df_survey_flex_main, appliance_for_max, float(duration_val_temp), float(incentive_val_temp)
                        )
                        if metrics_temp['raw_participation_rate'] * 100 > max_rate_for_device:
                            max_rate_for_device = metrics_temp['raw_participation_rate'] * 100
                all_z_rates_max.append(max_rate_for_device)
                print(f"  Max. Teilnahmequote für {appliance_for_max}: {max_rate_for_device:.1f}%")

            GLOBAL_CMAX = max(all_z_rates_max) if all_z_rates_max else 75 # Fallback auf 75%
            GLOBAL_CMAX = np.ceil(GLOBAL_CMAX / 5) * 5 # Runde auf nächste 5er-Stufe auf
            GLOBAL_CMAX = max(GLOBAL_CMAX, 10) # Mindestens 10%
            print(f"Globaler Maximalwert für Farbskala (COLOR_CMAX) gesetzt auf: {GLOBAL_CMAX}%")
            # --- ENDE NEU ---

            test_appliances = available_appliances
            for appliance in test_appliances:
                generate_3d_flexibility_surface_plot(
                    target_appliance=appliance,
                    df_survey_flex=df_survey_flex_main,
                    max_event_duration_h_on_plot=30.0, # Oder dein gewünschter oberer Wert für Y-Achse
                    # Übergebe GLOBAL_CMAX an die Funktion, dafür muss die Funktion angepasst werden
                    # oder setze COLOR_CMAX in der Funktion direkt auf diesen globalen Wert.
                    # Für jetzt: Passe COLOR_CMAX in der Funktion manuell an, nachdem du GLOBAL_CMAX kennst.
                )
    
    except Exception as e:
        print(f"Ein Fehler ist im Testlauf von c_flexibility_visualizer.py aufgetreten: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n--- Testlauf für c_flexibility_visualizer.py beendet ---")