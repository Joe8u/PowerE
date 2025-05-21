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
import numpy as np

# --- BEGINN: Robuster Pfad-Setup ---
try:
    CURRENT_SCRIPT_PATH = Path(__file__).resolve()
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

DEFAULT_RANK_FOR_PLOTS = 1
DEFAULT_OFFSET_FOR_PLOTS = 2.0
BASE_PRICE_CHF_KWH_COMPENSATION = 0.29
COMP_PERCENT_CAP_ITERATION = 150.0

def load_simulation_results(csv_path: Path) -> pd.DataFrame:
    """Lädt die Simulationsergebnisse aus der CSV-Datei."""
    # ... (Funktion bleibt gleich wie im vorherigen Vorschlag) ...
    if not csv_path.exists():
        print(f"FEHLER: Ergebnis-CSV-Datei nicht gefunden unter {csv_path}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(csv_path, sep=';', decimal='.')
        print(f"Simulationsergebnisse erfolgreich von {csv_path} geladen. Shape: {df.shape}")
        cols_to_numeric = ['avg_srl_price_in_window_chf_kwh', 'konvergierter_komp_prozentsatz',
                           'rohe_teilnahmequote_vor_cap', 'finale_teilnahmequote',
                           'total_srl_wert_chf', 'total_verschobene_energie_mwh',
                           'potenzielle_jasm_last_im_fenster_mwh', 'event_duration_h', 'rank_step4', 'pre_peak_offset_h']
        for col in cols_to_numeric:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
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
        (df_results['pre_peak_offset_h'] == DEFAULT_OFFSET_FOR_PLOTS) &
        (df_results['error_message'].isnull())
    ].copy()

    if not df_filtered_duration.empty:
        plt.figure(figsize=(10, 6))
        # Anpassungen hier: errorbar=None und hue setzen
        sns.barplot(x='event_duration_h', y='total_srl_wert_chf', data=df_filtered_duration,
                    hue='event_duration_h', palette="viridis", errorbar=None, legend=False)
        plt.title(f'Wirtschaftlicher Nutzen (SRL-Wert) vs. Event-Dauer\n(Tag-Rank: {DEFAULT_RANK_FOR_PLOTS}, Pre-Peak-Offset: {DEFAULT_OFFSET_FOR_PLOTS}h)')
        plt.xlabel('Event-Dauer (Stunden)')
        plt.ylabel('Totaler SRL-Wert (CHF)')
        plt.tight_layout()
        plt.savefig(PROJECT_ROOT / "data" / "visualizations" / f"srl_wert_vs_dauer_rank{DEFAULT_RANK_FOR_PLOTS}_offset{DEFAULT_OFFSET_FOR_PLOTS}.png")
        print(f"Plot 'srl_wert_vs_dauer_rank{DEFAULT_RANK_FOR_PLOTS}_offset{DEFAULT_OFFSET_FOR_PLOTS}.png' gespeichert.")
        # plt.show()
    else:
        print(f"Keine Daten für Plot 'SRL-Wert vs. Event-Dauer' mit Rank {DEFAULT_RANK_FOR_PLOTS} und Offset {DEFAULT_OFFSET_FOR_PLOTS}h gefunden.")

    # --- Plot 2: SRL-Wert vs. Top-Ranked-Tage für eine spezifische Dauer & Offset ---
    # --- Plot 2: SRL-Wert vs. Top-Ranked-Tage für eine spezifische Dauer & Offset ---
    representative_duration = 3.0
    available_durations = df_results['event_duration_h'].dropna().unique()
    if not np.any(available_durations): # Prüft, ob das Array leer ist
        print("Keine Event-Dauern in den Daten gefunden für Plot 'SRL-Wert vs. Top-Tage'.")
        return
    # Stelle sicher, dass representative_duration ein Wert ist, der in den Daten vorkommt
    if representative_duration not in available_durations:
        representative_duration = sorted(available_durations)[0] if len(available_durations) > 0 else None
        if representative_duration is None:
            print("Konnte keine repräsentative Dauer für Plot 'SRL-Wert vs. Top-Tage' finden.")
            return


    df_filtered_rank = df_results[
        (df_results['event_duration_h'] == representative_duration) &
        (df_results['pre_peak_offset_h'] == DEFAULT_OFFSET_FOR_PLOTS) &
        (df_results['error_message'].isnull())
    ].copy()

    if not df_filtered_rank.empty:
        plt.figure(figsize=(10, 6))
        # KORRIGIERTER AUFRUF HIER:
        sns.barplot(x='rank_step4', y='total_srl_wert_chf', data=df_filtered_rank,
                    hue='rank_step4', palette="mako", errorbar=None, legend=False) # ci=None -> errorbar=None; hue und legend hinzugefügt
        plt.title(f'Wirtschaftlicher Nutzen (SRL-Wert) vs. Top-Tage\n(Event-Dauer: {representative_duration}h, Pre-Peak-Offset: {DEFAULT_OFFSET_FOR_PLOTS}h)')
        plt.xlabel('Ranking des Tages (aus Step 4)')
        plt.ylabel('Totaler SRL-Wert (CHF)')
        if not df_filtered_rank['rank_step4'].empty:
             plt.xticks(sorted(df_filtered_rank['rank_step4'].unique()))
        plt.tight_layout()
        plt.savefig(PROJECT_ROOT / "data" / "visualizations" / f"srl_wert_vs_top_tage_dauer{representative_duration}_offset{DEFAULT_OFFSET_FOR_PLOTS}.png")
        print(f"Plot 'srl_wert_vs_top_tage_dauer{representative_duration}_offset{DEFAULT_OFFSET_FOR_PLOTS}.png' gespeichert.")
        # plt.show()
    else:
        print(f"Keine Daten für Plot 'SRL-Wert vs. Top-Tage' mit Dauer {representative_duration}h und Offset {DEFAULT_OFFSET_FOR_PLOTS}h gefunden.")

    
    ive_duration = 3.0
    available_durations = df_results['event_duration_h'].dropna().unique()
    if not np.any(available_durations): # Prüft, ob das Array leer ist
        print("Keine Event-Dauern in den Daten gefunden für Plot 'SRL-Wert vs. Top-Tage'.")
        return
    if representative_duration not in available_durations:
        representative_duration = sorted(available_durations)[0]


    df_filtered_rank = df_results[
        (df_results['event_duration_h'] == representative_duration) &
        (df_results['pre_peak_offset_h'] == DEFAULT_OFFSET_FOR_PLOTS) &
        (df_results['error_message'].isnull())
    ].copy()

    if not df_filtered_rank.empty:
        plt.figure(figsize=(10, 6))
        sns.barplot(x='rank_step4', y='total_srl_wert_chf', data=df_filtered_rank, palette="mako", ci=None)
        plt.title(f'Wirtschaftlicher Nutzen (SRL-Wert) vs. Top-Tage\n(Event-Dauer: {representative_duration}h, Pre-Peak-Offset: {DEFAULT_OFFSET_FOR_PLOTS}h)')
        plt.xlabel('Ranking des Tages (aus Step 4)')
        plt.ylabel('Totaler SRL-Wert (CHF)')
        if not df_filtered_rank['rank_step4'].empty:
             plt.xticks(sorted(df_filtered_rank['rank_step4'].unique()))
        plt.tight_layout()
        plt.savefig(PROJECT_ROOT / "data" / "visualizations" / f"srl_wert_vs_top_tage_dauer{representative_duration}_offset{DEFAULT_OFFSET_FOR_PLOTS}.png")
        print(f"Plot 'srl_wert_vs_top_tage_dauer{representative_duration}_offset{DEFAULT_OFFSET_FOR_PLOTS}.png' gespeichert.")
        #plt.show()
    else:
        print(f"Keine Daten für Plot 'SRL-Wert vs. Top-Tage' mit Dauer {representative_duration}h und Offset {DEFAULT_OFFSET_FOR_PLOTS}h gefunden.")


def plot_participation_vs_duration(df_results: pd.DataFrame):
    """ Erstellt ein Liniendiagramm: Rohe und finale Teilnahmequote vs. Event-Dauer. """
    # ... (Funktion bleibt gleich wie im vorherigen Vorschlag) ...
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
        df_filtered['rohe_tq_pct'] = df_filtered['rohe_teilnahmequote_vor_cap'] * 100
        df_filtered['finale_tq_pct'] = df_filtered['finale_teilnahmequote'] * 100

        plt.figure(figsize=(10, 6))
        sns.lineplot(x='event_duration_h', y='rohe_tq_pct', data=df_filtered, marker='o', label='Rohe Teilnahmequote (vor Cap)')
        sns.lineplot(x='event_duration_h', y='finale_tq_pct', data=df_filtered, marker='x', label='Finale Teilnahmequote (nach Cap)')
        
        max_cap_defined = 0.629 # MAX_PARTICIPATION_CAP from _05_ script
        plt.axhline(y=max_cap_defined * 100, color='r', linestyle='--', label=f'Max. Teilnahme Cap ({max_cap_defined*100:.1f}%)')

        plt.title(f'Teilnahmequoten vs. Event-Dauer\n(Tag-Rank: {DEFAULT_RANK_FOR_PLOTS}, Pre-Peak-Offset: {DEFAULT_OFFSET_FOR_PLOTS}h)')
        plt.xlabel('Event-Dauer (Stunden)')
        plt.ylabel('Teilnahmequote (%)')
        plt.legend()
        plot_y_max = 105
        if not df_filtered['rohe_tq_pct'].empty:
            current_max_rohe_tq = df_filtered['rohe_tq_pct'].max()
            if pd.notna(current_max_rohe_tq):
                 if current_max_rohe_tq < 95 :
                     plot_y_max = current_max_rohe_tq + 10
                 else:
                     plot_y_max = min(current_max_rohe_tq + 10, 105)
        plt.ylim(0, plot_y_max)
        plt.grid(True, which='both', linestyle='-', linewidth=0.5)
        plt.tight_layout()
        plt.savefig(PROJECT_ROOT / "data" / "visualizations" / f"teilnahme_vs_dauer_rank{DEFAULT_RANK_FOR_PLOTS}_offset{DEFAULT_OFFSET_FOR_PLOTS}.png")
        print(f"Plot 'teilnahme_vs_dauer_rank{DEFAULT_RANK_FOR_PLOTS}_offset{DEFAULT_OFFSET_FOR_PLOTS}.png' gespeichert.")
        #plt.show()
    else:
        print(f"Keine Daten für Plot 'Teilnahmequoten vs. Event-Dauer' mit Rank {DEFAULT_RANK_FOR_PLOTS} und Offset {DEFAULT_OFFSET_FOR_PLOTS}h gefunden.")

def plot_srl_price_vs_compensation_percentage(df_results: pd.DataFrame):
    """ Erstellt ein Streudiagramm: Durchschnittlicher SRL-Preis im Fenster vs. Konvergierter Kompensationsprozentsatz. """
    # ... (Funktion bleibt gleich wie im vorherigen Vorschlag) ...
    if df_results.empty:
        print("Keine Daten zum Plotten für SRL-Preis vs. Kompensation vorhanden.")
        return

    sns.set_theme(style="whitegrid")
    
    df_plot = df_results[
        df_results['error_message'].isnull() &
        df_results['avg_srl_price_in_window_chf_kwh'].notna() &
        df_results['konvergierter_komp_prozentsatz'].notna()
    ].copy()

    if df_plot.empty:
        print("Keine validen Daten nach Filterung für SRL-Preis vs. Kompensation Plot.")
        return

    plt.figure(figsize=(12, 7))
    
    scatter = sns.scatterplot(
        x='avg_srl_price_in_window_chf_kwh',
        y='konvergierter_komp_prozentsatz',
        hue='event_duration_h',
        size='total_srl_wert_chf',
        sizes=(50, 500),
        alpha=0.7,
        palette='coolwarm',
        data=df_plot
    )
    
    min_srl_price = df_plot['avg_srl_price_in_window_chf_kwh'].min()
    max_srl_price = df_plot['avg_srl_price_in_window_chf_kwh'].max()
    if pd.notna(min_srl_price) and pd.notna(max_srl_price) and min_srl_price < max_srl_price:
        x_line = np.linspace(min_srl_price, max_srl_price, 100)
        y_line_uncapped = (x_line / BASE_PRICE_CHF_KWH_COMPENSATION) * 100
        y_line_capped = np.minimum(y_line_uncapped, COMP_PERCENT_CAP_ITERATION)
        plt.plot(x_line, y_line_capped, color='gray', linestyle=':', linewidth=2, label=f'Theoret. KKP (gecapped bei {COMP_PERCENT_CAP_ITERATION}%)')

    plt.axhline(y=COMP_PERCENT_CAP_ITERATION, color='darkred', linestyle='--', linewidth=1, label=f'Max. Komp.-Prozentsatz Cap (Iteration)')

    plt.title('Durchschnittlicher SRL-Preis vs. Konvergierter Kompensationsprozentsatz')
    plt.xlabel('Durchschnittlicher SRL-Preis im Event-Fenster (CHF/kWh)')
    plt.ylabel('Konvergierter Kompensationsprozentsatz (%)')
    plt.legend(title='Parameter', loc='center left', bbox_to_anchor=(1, 0.5))
    plt.grid(True, which='both', linestyle='-', linewidth=0.5)
    plt.tight_layout(rect=[0, 0, 0.85, 1])
    
    filename = "srl_preis_vs_komp_prozentsatz.png"
    plt.savefig(PROJECT_ROOT / "data" / "visualizations" / filename)
    print(f"Plot '{filename}' gespeichert.")
    #plt.show()

# --- NEUE PLOTTING-FUNKTION FÜR "LOHNENSWERTE" VERSCHOBENE LEISTUNG ---
def plot_worthwhile_shifted_power(df_results: pd.DataFrame):
    """
    Erstellt ein Streudiagramm der durchschnittlich verschobenen Leistung (MW)
    für Szenarien, die sich "lohnen" (Kompensationsprozentsatz >= 100%).
    """
    if df_results.empty:
        print("Keine Daten zum Plotten für lohnenswerte verschobene Leistung vorhanden.")
        return

    sns.set_theme(style="whitegrid")

    # 1. Filtern nach "lohnenswerten" Szenarien
    df_worthwhile = df_results[
        (df_results['konvergierter_komp_prozentsatz'] >= 100.0) &
        (df_results['error_message'].isnull()) &
        (df_results['total_verschobene_energie_mwh'].notna()) &
        (df_results['event_duration_h'].notna()) &
        (df_results['event_duration_h'] > 0) # Division durch Null vermeiden
    ].copy() # .copy() um SettingWithCopyWarning zu vermeiden

    if df_worthwhile.empty:
        print("Keine 'lohnenswerten' Szenarien (Komp.Proz. >= 100%) für den Plot gefunden.")
        return

    # 2. Berechnung der durchschnittlich verschobenen Leistung
    df_worthwhile['avg_shifted_power_mw'] = df_worthwhile['total_verschobene_energie_mwh'] / df_worthwhile['event_duration_h']

    # 3. Erstellung des Streudiagramms
    plt.figure(figsize=(12, 7))
    scatter = sns.scatterplot(
        x='event_duration_h',
        y='avg_shifted_power_mw',
        hue='rank_step4', # Farbe nach Ranking des Tages
        size='konvergierter_komp_prozentsatz', # Grösse nach Höhe des "Lohnens"
        sizes=(50, 500),
        alpha=0.8,
        palette='Spectral', # Andere Farbpalette zur Abwechslung
        data=df_worthwhile
    )

    plt.title('Durchschnittlich verschobene Leistung für "lohnenswerte" Events\n(Kompensationsprozentsatz >= 100%)')
    plt.xlabel('Event-Dauer (Stunden)')
    plt.ylabel('Durchschnittlich verschobene Leistung (MW)')
    plt.legend(title='Parameter', loc='center left', bbox_to_anchor=(1, 0.5))
    plt.grid(True, which='both', linestyle='-', linewidth=0.5)
    plt.tight_layout(rect=[0, 0, 0.85, 1]) # Platz für Legende

    filename = "lohnenswerte_verschobene_leistung.png"
    plt.savefig(PROJECT_ROOT / "data" / "visualizations" / filename)
    print(f"Plot '{filename}' gespeichert.")
    #plt.show()


if __name__ == "__main__":
    print(f"--- Starte Visualisierung der Simulationsergebnisse aus: {RESULTS_CSV_PATH} ---")
    
    vis_folder = PROJECT_ROOT / "data" / "visualizations"
    vis_folder.mkdir(parents=True, exist_ok=True)
    print(f"Speichere Plots in: {vis_folder}")

    df_sim_results = load_simulation_results(RESULTS_CSV_PATH)

    if not df_sim_results.empty:
        required_cols = [
            'rank_step4', 'pre_peak_offset_h', 'event_duration_h', 'total_srl_wert_chf',
            'rohe_teilnahmequote_vor_cap', 'finale_teilnahmequote', 'error_message',
            'avg_srl_price_in_window_chf_kwh', 'konvergierter_komp_prozentsatz',
            'total_verschobene_energie_mwh' # Für die neue Funktion benötigt
        ]
        missing_cols = [col for col in required_cols if col not in df_sim_results.columns]
        if missing_cols:
            print(f"FEHLER: Folgende Spalten fehlen in der CSV-Datei: {missing_cols}")
            sys.exit("Bitte stelle sicher, dass die CSV-Datei alle benötigten Spalten enthält.")

        plot_srl_value_comparison(df_sim_results.copy())
        plot_participation_vs_duration(df_sim_results.copy())
        plot_srl_price_vs_compensation_percentage(df_sim_results.copy())
        
        # Rufe die neue Plotfunktion auf
        plot_worthwhile_shifted_power(df_sim_results.copy())
        
        print("\nAlle Plots wurden erstellt und gespeichert (falls Daten vorhanden). Um sie anzuzeigen, entferne die Auskommentierung von 'plt.show()' in den Funktionen.")
    else:
        print("Keine Simulationsergebnisse zum Visualisieren geladen.")
    
    print("\n--- Visualisierungsskript beendet. ---")