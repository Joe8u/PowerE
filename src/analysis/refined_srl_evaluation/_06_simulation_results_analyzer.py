# PowerE/src/analysis/refined_srl_evaluation/_06_simulation_results_analyzer.py
"""
Analysiert und visualisiert die Ergebnisse der Flexibilitätspotenzial-Simulation
aus _05_simulation_results_MWh_NetBenefitCH.csv.
Fokus auf Identifikation von Szenarien mit maximal verschobenem Strom (Energie/Leistung).
"""
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns # Für ansprechendere Grafiken
from pathlib import Path
import sys
import datetime # Für Zeitstempel im Output-Ordnernamen
from typing import Optional # Importiert für Type Hinting

# --- Pfad-Setup ---
try:
    CURRENT_SCRIPT_PATH = Path(__file__).resolve()
    PROJECT_ROOT = CURRENT_SCRIPT_PATH.parent.parent.parent.parent
except NameError:
    PROJECT_ROOT = Path.cwd()
    print(f"[WARNUNG] _06_ __file__ nicht definiert. PROJECT_ROOT: {PROJECT_ROOT}")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    print(f"[Path Setup _06_] Projekt-Root '{PROJECT_ROOT}' zum sys.path hinzugefügt.")

# Definiere einen Basis-Ausgabeordner für Grafiken etc.
REPORTS_DIR = PROJECT_ROOT / "reports" / "figures" / "step_06_simulation_analysis"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def load_simulation_results(csv_file_path: Path) -> Optional[pd.DataFrame]:
    """Lädt die Simulationsergebnisse aus der CSV-Datei."""
    if not csv_file_path.is_file():
        print(f"FEHLER: Ergebnisdatei nicht gefunden: {csv_file_path}")
        return None
    try:
        df = pd.read_csv(csv_file_path, sep=';', decimal='.')
        df['date'] = pd.to_datetime(df['date']).dt.date
        df['event_start_utc'] = pd.to_datetime(df['event_start_utc'])
        numeric_cols = [
            'rank_step4', 'event_duration_h', 'pre_peak_offset_h',
            'offered_compensation_pct', 'final_participation_rate_pct',
            'total_jasm_load_in_event_mwh', 'total_dispatched_energy_mwh',
            'avg_dispatched_power_mw', 'avg_srl_price_in_event_chf_kwh',
            'avoided_srl_costs_chf', 'compensation_chf_per_hh_simulated',
            'total_compensation_ch_estimate', 'net_benefit_chf_total_ch_estimate'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        print(f"Simulationsergebnisse geladen. Shape: {df.shape}")
        return df
    except Exception as e:
        print(f"Fehler beim Laden der CSV-Datei '{csv_file_path}': {e}")
        return None

def plot_sensitivity_to_incentive(df: pd.DataFrame, output_path: Path):
    if df is None or df.empty:
        print("Keine Daten für Anreiz-Sensitivitätsanalyse (plot_sensitivity_to_incentive).")
        return
    agg_by_incentive = df.groupby('offered_compensation_pct').agg(
        avg_participation_pct=('final_participation_rate_pct', 'mean'),
        avg_dispatched_mwh=('total_dispatched_energy_mwh', 'mean'),
        avg_dispatched_mw=('avg_dispatched_power_mw', 'mean'),
        avg_net_benefit_chf=('net_benefit_chf_total_ch_estimate', 'mean'),
        avg_avoided_costs_chf=('avoided_srl_costs_chf', 'mean'),
        avg_total_compensation_chf=('total_compensation_ch_estimate', 'mean')
    ).reset_index()
    fig, axes = plt.subplots(3, 1, figsize=(12, 18), sharex=True)
    fig.suptitle('Sensitivität auf Anreizlevel (Ø über alle Szenarien)', fontsize=16)
    sns.lineplot(ax=axes[0], data=agg_by_incentive, x='offered_compensation_pct', y='avg_participation_pct', marker='o', label='Ø Teilnahme (%)')
    axes[0].set_ylabel('Teilnahmequote (%)'); axes[0].grid(True); axes[0].legend()
    ax1_twin = axes[1].twinx()
    sns.lineplot(ax=axes[1], data=agg_by_incentive, x='offered_compensation_pct', y='avg_dispatched_mwh', marker='o', color='blue', label='Ø Versch. Energie (MWh)')
    sns.lineplot(ax=ax1_twin, data=agg_by_incentive, x='offered_compensation_pct', y='avg_dispatched_mw', marker='s', color='green', label='Ø Versch. Leistung (MW)')
    axes[1].set_ylabel('Ø Verschobene Energie (MWh)', color='blue'); ax1_twin.set_ylabel('Ø Verschobene Leistung (MW)', color='green')
    axes[1].tick_params(axis='y', labelcolor='blue'); ax1_twin.tick_params(axis='y', labelcolor='green'); axes[1].grid(True)
    lines, labels = axes[1].get_legend_handles_labels(); lines2, labels2 = ax1_twin.get_legend_handles_labels()
    axes[1].legend(lines + lines2, labels + labels2, loc='best')
    sns.lineplot(ax=axes[2], data=agg_by_incentive, x='offered_compensation_pct', y='avg_avoided_costs_chf', marker='o', label='Ø Vermiedene SRL-Kosten (CHF)')
    sns.lineplot(ax=axes[2], data=agg_by_incentive, x='offered_compensation_pct', y='avg_total_compensation_chf', marker='s', label='Ø Gesamtkosten Komp. (CHF)')
    sns.lineplot(ax=axes[2], data=agg_by_incentive, x='offered_compensation_pct', y='avg_net_benefit_chf', marker='D', label='Ø Netto-Nutzen CH (CHF)')
    axes[2].set_ylabel('Betrag (CHF)'); axes[2].axhline(0, color='red', linestyle='--', linewidth=0.8, label='Break-Even Netto-Nutzen')
    axes[2].set_xlabel('Angebotene Kompensation (% der Monatskosten)'); axes[2].grid(True); axes[2].legend()
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    filepath = output_path / "sensitivity_analysis_by_incentive.png"
    try: plt.savefig(filepath); print(f"Sensitivitätsanalyse (Anreiz) gespeichert: {filepath}")
    except Exception as e: print(f"  Fehler beim Speichern der Grafik 'sensitivity_analysis_by_incentive.png': {e}")
    plt.close()

def analyze_event_duration_effect(df: pd.DataFrame, output_dir: Path):
    if df is None or df.empty: print("Keine Daten für Event-Dauer-Analyse."); return
    print("\n--- Analyse: Einfluss der Event-Dauer ---")
    df_agg_duration = df.groupby(['event_duration_h', 'offered_compensation_pct']).agg(
        avg_participation_rate=('final_participation_rate_pct', 'mean'),
        avg_dispatched_mwh=('total_dispatched_energy_mwh', 'mean'),
        avg_dispatched_mw=('avg_dispatched_power_mw', 'mean'),
        avg_net_benefit_chf=('net_benefit_chf_total_ch_estimate', 'mean')
    ).reset_index()
    print("\nDurchschnittliche Metriken pro Event-Dauer und Anreizlevel (Auszug):"); print(df_agg_duration.head())
    plt.figure(figsize=(12, 8))
    sns.lineplot(data=df_agg_duration, x='event_duration_h', y='avg_participation_rate', hue='offered_compensation_pct', marker='o', palette='viridis')
    plt.title('Einfluss der Event-Dauer auf die Ø Teilnahmequote (pro Anreizlevel)'); plt.xlabel('Event-Dauer (Stunden)'); plt.ylabel('Durchschnittliche finale Teilnahmequote (%)')
    if not df_agg_duration.empty: plt.xticks(df_agg_duration['event_duration_h'].unique())
    plt.grid(True); plt.legend(title='Anreiz (%)'); filepath_participation = output_dir / "effect_participation_vs_duration.png"
    try: plt.savefig(filepath_participation); print(f"Grafik gespeichert: {filepath_participation}")
    except Exception as e: print(f"  Fehler beim Speichern der Grafik 'effect_participation_vs_duration.png': {e}")
    plt.close()
    plt.figure(figsize=(12, 8))
    sns.lineplot(data=df_agg_duration, x='event_duration_h', y='avg_net_benefit_chf', hue='offered_compensation_pct', marker='o', palette='viridis')
    plt.title('Einfluss der Event-Dauer auf den Ø Netto-Nutzen CH (pro Anreizlevel)'); plt.xlabel('Event-Dauer (Stunden)'); plt.ylabel('Durchschnittlicher Netto-Nutzen CH (CHF)')
    if not df_agg_duration.empty: plt.xticks(df_agg_duration['event_duration_h'].unique())
    plt.axhline(0, color='red', linestyle='--', linewidth=0.8, label='Break-Even'); plt.grid(True); plt.legend(title='Anreiz (%)')
    filepath_netbenefit = output_dir / "effect_netbenefit_vs_duration.png"
    try: plt.savefig(filepath_netbenefit); print(f"Grafik gespeichert: {filepath_netbenefit}")
    except Exception as e: print(f"  Fehler beim Speichern der Grafik 'effect_netbenefit_vs_duration.png': {e}")
    plt.close()

def find_optimal_scenarios(df: pd.DataFrame, output_dir: Path):
    if df is None or df.empty: print("Keine Daten für die Identifikation optimaler Szenarien (Netto-Nutzen Fokus)."); return
    print("\n--- Analyse: Optimale Szenarien (Fokus: Netto-Nutzen) ---")
    cols_to_show_optimal = ['date', 'event_start_utc', 'event_duration_h', 'pre_peak_offset_h', 'offered_compensation_pct', 'final_participation_rate_pct', 'total_dispatched_energy_mwh','avg_dispatched_power_mw', 'avoided_srl_costs_chf', 'net_benefit_chf_total_ch_estimate']
    cols_to_show_optimal = [col for col in cols_to_show_optimal if col in df.columns]
    top_net_benefit_scenarios = df.nlargest(10, 'net_benefit_chf_total_ch_estimate')
    print("\nTop 10 Szenarien nach höchstem Netto-Nutzen (CH Estimate):"); print(top_net_benefit_scenarios[cols_to_show_optimal])
    try: top_net_benefit_scenarios.to_csv(output_dir / "top_10_net_benefit_scenarios.csv", index=False, sep=';', decimal='.'); print(f"Top Netto-Nutzen Szenarien gespeichert: {output_dir / 'top_10_net_benefit_scenarios.csv'}")
    except Exception as e: print(f"  Fehler beim Speichern von 'top_10_net_benefit_scenarios.csv': {e}")
    if 'avg_dispatched_power_mw' in df.columns:
        marketable_srl_scenarios = df[df['avg_dispatched_power_mw'] >= 1.0].copy()
        if not marketable_srl_scenarios.empty:
            srl_marketable_scenarios_sorted = marketable_srl_scenarios.sort_values(by='net_benefit_chf_total_ch_estimate', ascending=False)
            print("\nSzenarien, die >= 1MW verschobene Leistung erreichen (Top 10 nach bestem Netto-Nutzen):"); print(srl_marketable_scenarios_sorted[cols_to_show_optimal].head(10))
            try: srl_marketable_scenarios_sorted.to_csv(output_dir / "srl_marketable_scenarios_top_net_benefit.csv", index=False, sep=';', decimal='.'); print(f"SRL-vermarktbare Szenarien gespeichert: {output_dir / 'srl_marketable_scenarios_top_net_benefit.csv'}")
            except Exception as e: print(f"  Fehler beim Speichern von 'srl_marketable_scenarios_top_net_benefit.csv': {e}")
        else: print("\nKeine simulierten Szenarien erreichen die 1MW-Schwelle für die durchschnittlich verschobene Leistung (Netto-Nutzen Fokus).")
    else: print("\nSpalte 'avg_dispatched_power_mw' nicht in den Ergebnissen gefunden, 1MW-Analyse (Netto-Nutzen Fokus) übersprungen.")

def analyze_srl_price_vs_net_benefit(df: pd.DataFrame, output_path: Path):
    if df is None or df.empty: print("Keine Daten für SRL Preis vs. Netto-Nutzen Analyse."); return
    required_cols_plot = ['avg_srl_price_in_event_chf_kwh', 'net_benefit_chf_total_ch_estimate', 'offered_compensation_pct', 'avg_dispatched_power_mw']
    if not all(col in df.columns for col in required_cols_plot): print(f"FEHLER: Nicht alle benötigten Spalten für 'analyze_srl_price_vs_net_benefit' vorhanden. Benötigt: {required_cols_plot}"); return
    plt.figure(figsize=(12, 7))
    try:
        sns.scatterplot(data=df, x='avg_srl_price_in_event_chf_kwh', y='net_benefit_chf_total_ch_estimate', hue='offered_compensation_pct', size='avg_dispatched_power_mw', palette='coolwarm', sizes=(30, 250), alpha=0.7)
        plt.title('Netto-Nutzen vs. Ø SRL-Preis im Event'); plt.xlabel('Durchschnittlicher SRL-Preis im Event (CHF/kWh)'); plt.ylabel('Geschätzter Netto-Nutzen CH (CHF)')
        plt.axhline(0, color='red', linestyle='--', linewidth=0.8, label='Break-Even'); plt.grid(True)
        plt.legend(title='Anreiz (%) / Leistung (MW)', bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0.)
        plt.tight_layout(rect=[0, 0, 0.85, 1]); filepath = output_path / "net_benefit_vs_srl_price.png"
        plt.savefig(filepath); print(f"Grafik Netto-Nutzen vs. SRL Preis gespeichert: {filepath}")
    except Exception as e: print(f"  Fehler beim Erstellen der Grafik 'net_benefit_vs_srl_price.png': {e}")
    finally: plt.close()

# --- KORRIGIERTE FUNKTION ---
def find_max_impact_with_profitability(
    df: pd.DataFrame,
    output_path: Path,
    impact_metric: str = 'avg_dispatched_power_mw',
    min_power_mw_threshold: Optional[float] = None,
    consider_profitability: bool = True
):
    """
    Filtert Szenarien optional nach Netto-Nutzen >= 0 und/oder Leistungsschwelle
    und findet diejenigen, die die gewählte Impact-Metrik maximieren.
    """
    if df is None or df.empty:
        print("Keine Daten für 'Maximaler Impact'-Analyse.")
        return

    profitability_status_msg = "bei Profitabilität (Netto-Nutzen >= 0)" if consider_profitability else "unabhängig von Profitabilität"
    threshold_msg = f"und >= {min_power_mw_threshold} MW" if min_power_mw_threshold is not None else ""
    print(f"\n--- Analyse: Maximaler Impact ({impact_metric}) {profitability_status_msg} {threshold_msg} ---")

    target_df_for_max_impact = df.copy()

    if consider_profitability:
        target_df_for_max_impact = target_df_for_max_impact[target_df_for_max_impact['net_benefit_chf_total_ch_estimate'] >= 0].copy()
        if target_df_for_max_impact.empty:
            print(f"Keine Szenarien mit Netto-Nutzen >= 0 gefunden für Impact-Metrik '{impact_metric}'.")
            return

    if min_power_mw_threshold is not None:
        if 'avg_dispatched_power_mw' in target_df_for_max_impact.columns:
            # KORREKTE STATUSMELDUNG FÜR LEISTUNGSSCHWELLE
            base_scenario_count_for_threshold_msg = len(target_df_for_max_impact)
            status_msg_addon = "(aus den profitablen Szenarien)" if consider_profitability and base_scenario_count_for_threshold_msg != len(df) else "(aus allen Szenarien)"
            if not consider_profitability and base_scenario_count_for_threshold_msg == len(df) : status_msg_addon = "(aus allen Szenarien)"


            marketable_scenarios = target_df_for_max_impact[target_df_for_max_impact['avg_dispatched_power_mw'] >= min_power_mw_threshold].copy()

            if marketable_scenarios.empty:
                print(f"WARNUNG: Von den {base_scenario_count_for_threshold_msg} Szenarien {status_msg_addon} erreicht keines die {min_power_mw_threshold}MW-Schwelle.")
                target_df_for_max_impact = marketable_scenarios # Wird leer sein
            else:
                target_df_for_max_impact = marketable_scenarios
                print(f"{len(target_df_for_max_impact)} der {base_scenario_count_for_threshold_msg} Szenarien {status_msg_addon} erreichen die {min_power_mw_threshold}MW-Schwelle.")
        else:
            print("WARNUNG: Spalte 'avg_dispatched_power_mw' nicht gefunden. Leistungsschwellen-Filter kann nicht angewendet werden.")

    if impact_metric not in target_df_for_max_impact.columns:
        print(f"FEHLER: Impact-Metrik '{impact_metric}' nicht in den Daten vorhanden.")
        return

    if target_df_for_max_impact.empty:
        print(f"Keine Szenarien erfüllen die Kriterien für die Suche nach maximalem Impact ({impact_metric}).")
        return

    best_impact_scenarios = target_df_for_max_impact.sort_values(
        by=[impact_metric, 'net_benefit_chf_total_ch_estimate'],
        ascending=[False, False]
    )

    print(f"\nTop 10 Szenarien (sortiert nach höchstem '{impact_metric}'):")
    cols_to_show = [
        'date', 'event_start_utc', 'event_duration_h', 'pre_peak_offset_h',
        'offered_compensation_pct', 'final_participation_rate_pct',
        'total_dispatched_energy_mwh', 'avg_dispatched_power_mw',
        'avoided_srl_costs_chf', 'total_compensation_ch_estimate',
        'net_benefit_chf_total_ch_estimate'
    ]
    cols_to_show = [col for col in cols_to_show if col in best_impact_scenarios.columns]
    print(best_impact_scenarios[cols_to_show].head(10))

    try:
        profit_str = "profitable" if consider_profitability else "all_scenarios"
        thresh_str = f"_min{str(min_power_mw_threshold).replace('.', '_')}MW" if min_power_mw_threshold is not None else ""
        filename = f"max_impact_{profit_str}_{impact_metric.replace('.', '_')}{thresh_str}.csv"
        filepath = output_path / filename
        best_impact_scenarios.head(50).to_csv(filepath, index=False, sep=';', decimal='.')
        print(f"Ergebnisse für '{filename}' gespeichert: {filepath}")
    except Exception as e:
        print(f"  Fehler beim Speichern der Ergebnisse für '{filename}': {e}")


if __name__ == '__main__':
    if '__file__' in locals():
        RESULTS_CSV_FILE = Path(__file__).resolve().parent / "_05_simulation_results_MWh_NetBenefitCH.csv"
    else:
        RESULTS_CSV_FILE = Path.cwd() / "_05_simulation_results_MWh_NetBenefitCH.csv"
        if not RESULTS_CSV_FILE.exists():
             project_root_candidate = Path.cwd()
             alt_path = project_root_candidate / "src" / "analysis" / "refined_srl_evaluation" / "_05_simulation_results_MWh_NetBenefitCH.csv"
             if alt_path.exists(): RESULTS_CSV_FILE = alt_path
             else:
                 alt_path_src = project_root_candidate / "src" / "_05_simulation_results_MWh_NetBenefitCH.csv"
                 if alt_path_src.exists(): RESULTS_CSV_FILE = alt_path_src

    print(f"Lade Simulationsergebnisse von: {RESULTS_CSV_FILE}")
    df_simulation_output = load_simulation_results(RESULTS_CSV_FILE)

    if df_simulation_output is not None and not df_simulation_output.empty:
        current_timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_output_dir = REPORTS_DIR / f"analysis_run_{current_timestamp_str}"
        run_output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Analyse-Ausgaben werden gespeichert in: {run_output_dir}")

        # --- Bestehende Analysen ---
        plot_sensitivity_to_incentive(df_simulation_output.copy(), run_output_dir)
        analyze_event_duration_effect(df_simulation_output.copy(), run_output_dir)
        find_optimal_scenarios(df_simulation_output.copy(), run_output_dir)
        analyze_srl_price_vs_net_benefit(df_simulation_output.copy(), run_output_dir)

        # --- KORRIGIERTE NEUE ANALYSEN: FOKUS AUF MAXIMAL VERSCHOBENEN STROM ---

        # 1. Maximale verschobene Energie (MWh) - WETTBEWERBSFÄHIG (Netto-Nutzen >= 0)
        find_max_impact_with_profitability(
            df=df_simulation_output.copy(),
            output_path=run_output_dir,
            impact_metric='total_dispatched_energy_mwh',
            consider_profitability=True,
            min_power_mw_threshold=None
        )

        # 2. Maximale verschobene Energie (MWh) - rein technisch, UNABHÄNGIG von Profitabilität
        find_max_impact_with_profitability(
            df=df_simulation_output.copy(),
            output_path=run_output_dir,
            impact_metric='total_dispatched_energy_mwh',
            consider_profitability=False, # HIER IST DER UNTERSCHIED
            min_power_mw_threshold=None
        )

        # 3. Maximale verschobene Leistung (MW) - WETTBEWERBSFÄHIG (Netto-Nutzen >= 0) und z.B. >= 1 MW
        find_max_impact_with_profitability(
            df=df_simulation_output.copy(),
            output_path=run_output_dir,
            impact_metric='avg_dispatched_power_mw',
            consider_profitability=True,
            min_power_mw_threshold=1.0
        )

        # 4. Maximale verschobene Leistung (MW) - rein technisch, UNABHÄNGIG von Profitabilität, und z.B. >= 1 MW
        find_max_impact_with_profitability(
            df=df_simulation_output.copy(),
            output_path=run_output_dir,
            impact_metric='avg_dispatched_power_mw',
            consider_profitability=False, # HIER IST DER UNTERSCHIED
            min_power_mw_threshold=1.0
        )

        # 5. Maximale verschobene Leistung (MW) - rein technisch, UNABHÄNGIG von Profitabilität, KEINE Leistungsschwelle
        find_max_impact_with_profitability(
            df=df_simulation_output.copy(),
            output_path=run_output_dir,
            impact_metric='avg_dispatched_power_mw',
            consider_profitability=False, # HIER IST DER UNTERSCHIED
            min_power_mw_threshold=None
        )

        print("\n\n--- Analyse der Simulationsergebnisse (Step 6) abgeschlossen. ---")
        print(f"Alle Berichte und CSVs dieses Laufs sind in: {run_output_dir}")
    else:
        print("Keine Simulationsergebnisse zum Analysieren geladen.")