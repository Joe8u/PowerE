# PowerE/src/analysis/simulation_visualizer/_07_simulation_results_visualizer.py
"""
Visualisiert die Simulationsergebnisse aus der Output-CSV von 
_05_flex_potential_simulation.py.
"""
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
import os

# --- BEGINN: Robuster Pfad-Setup ---
try:
    CURRENT_SCRIPT_PATH = Path(__file__).resolve()
    # Annahme: Dieses Skript liegt in src/analysis/simulation_visualizer/
    # Vier .parent Aufrufe zum Projekt-Root (PowerE)
    PROJECT_ROOT = CURRENT_SCRIPT_PATH.parent.parent.parent.parent
except NameError:
    PROJECT_ROOT = Path(os.getcwd()).resolve()
    print(f"[WARNUNG] __file__ nicht definiert. PROJECT_ROOT als aktuelles Arbeitsverzeichnis angenommen: {PROJECT_ROOT}")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    print(f"[Path Setup] Projekt-Root '{PROJECT_ROOT}' zum sys.path hinzugefügt.")
# --- ENDE: Robuster Pfad-Setup ---

# --- Konfigurationen ---
RESULTS_CSV_FILENAME = "simulation_results_Geschirrspüler_2024_erweitert.csv"
RESULTS_CSV_PATH = PROJECT_ROOT / "data" / "results" / RESULTS_CSV_FILENAME

# Standardfilter für repräsentative Plots (kann angepasst werden)
DEFAULT_RANK_FOR_PLOTS = 1
DEFAULT_OFFSET_FOR_PLOTS = 2.0 # z.B. 2.0h pre_peak_offset_h

def load_simulation_results(csv_path: Path) -> pd.DataFrame:
    """Lädt die Simulationsergebnisse aus der CSV-Datei."""
    if not csv_path.exists():
        print(f"FEHLER: Ergebnis-CSV-Datei nicht gefunden unter {csv_path}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(csv_path, sep=';', decimal='.')
        print(f"Simulationsergebnisse erfolgreich von {csv_path} geladen. Shape: {df.shape}")
        # Konvertiere relevante Spalten falls nötig (sollten schon numerisch sein)
        # Prozentwerte sind als float (z.B. 0.6290) gespeichert und werden für Plots ggf. *100 genommen
        return df
    except Exception as e:
        print(f"FEHLER beim Laden der CSV-Datei {csv_path}: {e}")
        return pd.DataFrame()

def plot_srl_value_comparison(df_results: pd.DataFrame):
    """
    Erstellt Balkendiagramme zum Vergleich des total_srl_wert_chf.
    1. Vergleich über verschiedene Event-Dauern (für einen Top-Tag und Offset).
    2. Vergleich über die Top-Ranked-Tage (für eine feste Dauer und Offset).
    """
    if df_results.empty:
        print("Keine Daten zum Plotten für SRL-Wert vorhanden.")
        return

    sns.set_theme(style="whitegrid")

    # --- Plot 1: SRL-Wert vs. Event-Dauer für einen spezifischen Tag & Offset ---
    df_filtered_duration = df_results[
        (df_results['rank_step4'] == DEFAULT_RANK_FOR_PLOTS) &
        (df_results['pre_peak_offset_h'] == DEFAULT_OFFSET_FOR_PLOTS) & # Filtern nach spezifischem Offset
        (df_results['error_message'].isnull()) # Nur erfolgreiche Simulationen
    ].copy() # .copy() um SettingWithCopyWarning zu vermeiden

    if not df_filtered_duration.empty:
        plt.figure(figsize=(10, 6))
        sns.barplot(x='event_duration_h', y='total_srl_wert_chf', data=df_filtered_duration, palette="viridis", ci=None) # ci=None entfernt Fehlerbalken falls Daten aggregiert wären
        plt.title(f'Wirtschaftlicher Nutzen (SRL-Wert) vs. Event-Dauer\n(Tag-Rank: {DEFAULT_RANK_FOR_PLOTS}, Pre-Peak-Offset: {DEFAULT_OFFSET_FOR_PLOTS}h)')
        plt.xlabel('Event-Dauer (Stunden)')
        plt.ylabel('Totaler SRL-Wert (CHF)')
        plt.tight_layout()
        plt.savefig(PROJECT_ROOT / "data" / "visualizations" / f"srl_wert_vs_dauer_rank{DEFAULT_RANK_FOR_PLOTS}_offset{DEFAULT_OFFSET_FOR_PLOTS}.png")
        print(f"Plot 'srl_wert_vs_dauer_rank{DEFAULT_RANK_FOR_PLOTS}_offset{DEFAULT_OFFSET_FOR_PLOTS}.png' gespeichert.")
        plt.show()
    else:
        print(f"Keine Daten für Plot 'SRL-Wert vs. Event-Dauer' mit Rank {DEFAULT_RANK_FOR_PLOTS} und Offset {DEFAULT_OFFSET_FOR_PLOTS}h gefunden.")

    # --- Plot 2: SRL-Wert vs. Top-Ranked-Tage für eine spezifische Dauer & Offset ---
    # Wähle eine repräsentative Dauer, z.B. die mittlere oder eine, die gute Ergebnisse liefert
    # Aus deinen Ergebnissen scheint 3.0h eine interessante Dauer zu sein.
    representative_duration = 3.0
    if representative_duration not in df_results['event_duration_h'].unique():
        # Fallback, falls 3.0h nicht in den Daten ist, nimm die erste verfügbare Dauer
        if len(df_results['event_duration_h'].unique()) > 0:
            representative_duration = sorted(df_results['event_duration_h'].unique())[0]
        else:
            print("Keine Event-Dauern in den Daten gefunden für Plot 'SRL-Wert vs. Top-Tage'.")
            return


    df_filtered_rank = df_results[
        (df_results['event_duration_h'] == representative_duration) &
        (df_results['pre_peak_offset_h'] == DEFAULT_OFFSET_FOR_PLOTS) & # Filtern nach spezifischem Offset
        (df_results['error_message'].isnull()) # Nur erfolgreiche Simulationen
    ].copy()

    if not df_filtered_rank.empty:
        plt.figure(figsize=(10, 6))
        sns.barplot(x='rank_step4', y='total_srl_wert_chf', data=df_filtered_rank, palette="mako", ci=None)
        plt.title(f'Wirtschaftlicher Nutzen (SRL-Wert) vs. Top-Tage\n(Event-Dauer: {representative_duration}h, Pre-Peak-Offset: {DEFAULT_OFFSET_FOR_PLOTS}h)')
        plt.xlabel('Ranking des Tages (aus Step 4)')
        plt.ylabel('Totaler SRL-Wert (CHF)')
        plt.xticks(sorted(df_filtered_rank['rank_step4'].unique())) # Stellt sicher, dass alle Ranks angezeigt werden
        plt.tight_layout()
        plt.savefig(PROJECT_ROOT / "data" / "visualizations" / f"srl_wert_vs_top_tage_dauer{representative_duration}_offset{DEFAULT_OFFSET_FOR_PLOTS}.png")
        print(f"Plot 'srl_wert_vs_top_tage_dauer{representative_duration}_offset{DEFAULT_OFFSET_FOR_PLOTS}.png' gespeichert.")
        plt.show()
    else:
        print(f"Keine Daten für Plot 'SRL-Wert vs. Top-Tage' mit Dauer {representative_duration}h und Offset {DEFAULT_OFFSET_FOR_PLOTS}h gefunden.")


def plot_participation_vs_duration(df_results: pd.DataFrame):
    """
    Erstellt ein Liniendiagramm: Rohe und finale Teilnahmequote vs. Event-Dauer
    (für einen Top-Tag und einen festen Offset).
    """
    if df_results.empty:
        print("Keine Daten zum Plotten für Teilnahmequoten vorhanden.")
        return

    sns.set_theme(style="whitegrid")

    df_filtered = df_results[
        (df_results['rank_step4'] == DEFAULT_RANK_FOR_PLOTS) &
        (df_results['pre_peak_offset_h'] == DEFAULT_OFFSET_FOR_PLOTS) &
        (df_results['error_message'].isnull())
    ].copy()

    if 'rohe_teilnahmequote_vor_cap' not in df_filtered.columns or \
       'finale_teilnahmequote' not in df_filtered.columns:
        print("FEHLER: Benötigte Spalten 'rohe_teilnahmequote_vor_cap' oder 'finale_teilnahmequote' nicht im DataFrame.")
        return

    if not df_filtered.empty:
        # Konvertiere Raten in Prozent für die Darstellung
        df_filtered['rohe_tq_pct'] = df_filtered['rohe_teilnahmequote_vor_cap'] * 100
        df_filtered['finale_tq_pct'] = df_filtered['finale_teilnahmequote'] * 100

        plt.figure(figsize=(10, 6))
        sns.lineplot(x='event_duration_h', y='rohe_tq_pct', data=df_filtered, marker='o', label='Rohe Teilnahmequote (vor Cap)')
        sns.lineplot(x='event_duration_h', y='finale_tq_pct', data=df_filtered, marker='x', label='Finale Teilnahmequote (nach Cap)')
        
        # Horizontale Linie für den Cap-Wert
        max_cap_pct = df_results['finale_teilnahmequote'][df_results['finale_teilnahmequote'] < 1.0].max() * 100 # Nimmt den Cap-Wert dynamisch
        if pd.isna(max_cap_pct) and 'MAX_PARTICIPATION_CAP' in globals(): # Fallback falls Cap nie erreicht wurde aber definiert ist
             max_cap_pct = MAX_PARTICIPATION_CAP * 100 # MAX_PARTICIPATION_CAP aus _05_ verwenden, wenn verfügbar. Für jetzt fix:
        if pd.isna(max_cap_pct) or max_cap_pct == 0: max_cap_pct = 0.629 * 100 # Fallback auf 62.9%

        plt.axhline(y=max_cap_pct, color='r', linestyle='--', label=f'Max. Teilnahme Cap ({max_cap_pct:.1f}%)')

        plt.title(f'Teilnahmequoten vs. Event-Dauer\n(Tag-Rank: {DEFAULT_RANK_FOR_PLOTS}, Pre-Peak-Offset: {DEFAULT_OFFSET_FOR_PLOTS}h)')
        plt.xlabel('Event-Dauer (Stunden)')
        plt.ylabel('Teilnahmequote (%)')
        plt.legend()
        plt.ylim(0, max(100, df_filtered['rohe_tq_pct'].max() * 1.1 if not df_filtered['rohe_tq_pct'].empty else 100) ) # Y-Achse bis 100% oder etwas mehr
        plt.grid(True, which='both', linestyle='-', linewidth=0.5)
        plt.tight_layout()
        plt.savefig(PROJECT_ROOT / "data" / "visualizations" / f"teilnahme_vs_dauer_rank{DEFAULT_RANK_FOR_PLOTS}_offset{DEFAULT_OFFSET_FOR_PLOTS}.png")
        print(f"Plot 'teilnahme_vs_dauer_rank{DEFAULT_RANK_FOR_PLOTS}_offset{DEFAULT_OFFSET_FOR_PLOTS}.png' gespeichert.")
        plt.show()
    else:
        print(f"Keine Daten für Plot 'Teilnahmequoten vs. Event-Dauer' mit Rank {DEFAULT_RANK_FOR_PLOTS} und Offset {DEFAULT_OFFSET_FOR_PLOTS}h gefunden.")


if __name__ == "__main__":
    print(f"--- Starte Visualisierung der Simulationsergebnisse aus: {RESULTS_CSV_PATH} ---")
    
    # Erstelle den Visualisierungsordner, falls er nicht existiert
    vis_folder = PROJECT_ROOT / "data" / "visualizations"
    vis_folder.mkdir(parents=True, exist_ok=True)
    print(f"Speichere Plots in: {vis_folder}")

    df_sim_results = load_simulation_results(RESULTS_CSV_PATH)

    if not df_sim_results.empty:
        # Überprüfe, ob die erwarteten Spalten vorhanden sind
        required_cols = [
            'rank_step4', 'pre_peak_offset_h', 'event_duration_h', 'total_srl_wert_chf',
            'rohe_teilnahmequote_vor_cap', 'finale_teilnahmequote', 'error_message'
        ]
        missing_cols = [col for col in required_cols if col not in df_sim_results.columns]
        if missing_cols:
            print(f"FEHLER: Folgende Spalten fehlen in der CSV-Datei: {missing_cols}")
            sys.exit("Bitte stelle sicher, dass die CSV-Datei alle benötigten Spalten enthält.")

        # Filtere NaN error_message, da diese sonst die Plots stören könnten, wenn sie als Kategorie interpretiert werden
        # Stattdessen werden sie in den Plotfunktionen gefiltert.
        # df_sim_results_cleaned = df_sim_results[df_sim_results['error_message'].isnull()].copy()
        # Es ist besser, die Filterung in den Plotfunktionen zu belassen,
        # um auch mit fehlerhaften Zeilen im df umgehen zu können (z.B. für eine Fehleranalyse)


        plot_srl_value_comparison(df_sim_results.copy()) # .copy() um Original-DataFrame nicht zu verändern
        plot_participation_vs_duration(df_sim_results.copy())
    else:
        print("Keine Simulationsergebnisse zum Visualisieren geladen.")
    
    print("\n--- Visualisierungsskript beendet. ---")