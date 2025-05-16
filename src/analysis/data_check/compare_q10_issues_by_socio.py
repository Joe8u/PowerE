# PowerE/src/analysis/data_check/compare_q10_issues_by_age.py
"""
Skript zum Vergleich von Teilnehmern mit vs. ohne "Probleme" bei Frage 10
(definiert als "Ja, +" gewählt, aber keinen Prozentwert angegeben)
hinsichtlich des Alters.
"""
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Füge das 'src'-Verzeichnis zum Python-Pfad hinzu für Loader-Importe
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "src"))

try:
    from data_loader.survey_loader.incentive_loader import load_question_10_incentives
    from data_loader.survey_loader.demographics import load_demographics
    print("Loader-Module erfolgreich importiert.\n")
except ImportError as e:
    print(f"FEHLER beim Importieren der Loader-Module: {e}")
    exit()

# Geräte-Liste
DEVICES = [
    'Geschirrspüler',
    'Backofen und Herd',
    'Fernseher und Entertainment-Systeme',
    'Bürogeräte',
    'Waschmaschine'
]

OUTPUT_DIR = 'data_check_q10_age_output' # Eigener Ordner für diese Analyse-Ausgaben
os.makedirs(OUTPUT_DIR, exist_ok=True)


def main():
    print("=== Starte Vergleichsanalyse für Frage 10-Probleme vs. Alter ===")

    # 1. Daten laden
    try:
        df_q10_wide = load_question_10_incentives()
        demographics_data = load_demographics(PROJECT_ROOT) # Lade Demographie-Daten
        df_age = demographics_data.get('age') # Hole Alters-DataFrame

        if df_q10_wide.empty or df_age is None or df_age.empty:
            print("FEHLER: Q10-Daten oder Altersdaten sind leer oder konnten nicht geladen werden.")
            return
    except Exception as e:
        print(f"FEHLER beim Laden der Daten: {e}")
        return

    # Bereinigung und Typkonvertierung für Q10-Daten
    df_q10_wide['respondent_id'] = df_q10_wide['respondent_id'].astype(str)
    issue_columns_bool = []
    for device in DEVICES:
        choice_col = f'{device}_choice'
        pct_col = f'{device}_pct'
        issue_indicator_col = f'{device}_had_issue'

        if choice_col in df_q10_wide.columns:
            df_q10_wide[choice_col] = df_q10_wide[choice_col].astype(str).str.strip()
            df_q10_wide.loc[df_q10_wide[choice_col].str.lower() == 'nan', choice_col] = np.nan
        else:
            df_q10_wide[issue_indicator_col] = False
            issue_columns_bool.append(issue_indicator_col)
            continue
        if pct_col in df_q10_wide.columns:
            df_q10_wide[pct_col] = pd.to_numeric(df_q10_wide[pct_col], errors='coerce')
        else:
            df_q10_wide[issue_indicator_col] = False
            issue_columns_bool.append(issue_indicator_col)
            continue
        df_q10_wide[issue_indicator_col] = (df_q10_wide[choice_col] == 'Ja, +') & (df_q10_wide[pct_col].isna())
        issue_columns_bool.append(issue_indicator_col)

    if issue_columns_bool:
        df_q10_wide['had_q10_issue_overall'] = df_q10_wide[issue_columns_bool].any(axis=1)
    else:
        df_q10_wide['had_q10_issue_overall'] = False

    df_q10_issue_summary = df_q10_wide[['respondent_id', 'had_q10_issue_overall']].copy()

    # 2. Altersdaten vorbereiten und mergen
    df_age['respondent_id'] = df_age['respondent_id'].astype(str)
    if 'age' in df_age.columns: # Sicherstellen, dass die 'age'-Spalte existiert
        df_age['age'] = pd.to_numeric(df_age['age'], errors='coerce')
    else:
        print("FEHLER: 'age'-Spalte nicht im Demographics-DataFrame gefunden.")
        return

    df_merged = pd.merge(df_q10_issue_summary, df_age[['respondent_id', 'age']], on='respondent_id', how='left')

    if df_merged.empty:
        print("FEHLER: DataFrame ist nach dem Mergen leer.")
        return
        
    print(f"\nGesamtzahl der Teilnehmer für den Vergleich: {len(df_merged)}")
    print("Verteilung der 'Problemfälle' bei Frage 10:")
    print(df_merged['had_q10_issue_overall'].value_counts(dropna=False))

    # 3. Vergleich nach Alter
    print("\n--- Vergleich nach Alter (age) ---")
    if 'age' in df_merged.columns and df_merged['age'].notna().any(): # Prüfen ob Altersdaten vorhanden sind
        print("\nDeskriptive Statistiken für Alter, gruppiert nach 'Problemfall bei Q10':")
        age_stats_by_issue = df_merged.groupby('had_q10_issue_overall')['age'].describe()
        print(age_stats_by_issue.to_string())

        # Boxplot (bleibt nützlich für den Gesamtvergleich)
        plt.figure(figsize=(8, 6))
        sns.boxplot(x='had_q10_issue_overall', y='age', data=df_merged)
        plt.title('Altersverteilung nach "Problemfall bei Frage 10"')
        plt.xlabel('Hatte Problem bei Frage 10 (Ja+/ohne %)?')
        plt.ylabel('Alter')
        plt.xticks([False, True], ['Nein (Kein Problem)', 'Ja (Problemfall)'])
        plot_path_box = os.path.join(OUTPUT_DIR, 'age_vs_q10_issue_boxplot.png')
        try:
            plt.savefig(plot_path_box)
            print(f"\nBoxplot für Alter gespeichert unter: {plot_path_box}")
        except Exception as e_plot:
            print(f"FEHLER beim Speichern des Alter-Boxplots: {e_plot}")
        plt.close()
        
        # Histogramm (bleibt nützlich)
        plt.figure(figsize=(10, 6))
        sns.histplot(data=df_merged, x='age', hue='had_q10_issue_overall', kde=True, element="step", stat="density", common_norm=False)
        plt.title('Altersverteilung nach "Problemfall bei Frage 10" (Histogramm)')
        plt.xlabel('Alter')
        plt.ylabel('Dichte')
        plot_path_hist = os.path.join(OUTPUT_DIR, 'age_vs_q10_issue_histogram.png')
        try:
            plt.savefig(plot_path_hist)
            print(f"Histogramm für Alter gespeichert unter: {plot_path_hist}")
        except Exception as e_plot:
            print(f"FEHLER beim Speichern des Alter-Histogramms: {e_plot}")
        plt.close()

        # Erstelle Altersgruppen
        # Du kannst die Grenzen und Labels anpassen, wie es für deine Analyse am sinnvollsten ist.
        # Deine Altersdaten gehen von min 17 bis max 96.
        age_bins = [16, 29, 39, 49, 59, 69, 97] # Obere Grenze +1 oder eine sehr hohe Zahl
        age_labels = ['17-29', '30-39', '40-49', '50-59', '60-69', '70+'] # Max war 96, also 70+ passt
        
        df_merged['age_group'] = pd.cut(df_merged['age'], bins=age_bins, labels=age_labels, right=True)

        print("\n--- Analyse 'Problemfall bei Q10' nach Altersgruppen ---")
        if 'age_group' in df_merged.columns and df_merged['age_group'].notna().any():
            # Absolute Häufigkeiten
            age_group_crosstab_abs = pd.crosstab(df_merged['age_group'], df_merged['had_q10_issue_overall'], dropna=False)
            print("\nAbsolute Häufigkeiten (Altersgruppe vs. Problemfall):")
            print(age_group_crosstab_abs.to_string())

            # Prozentsatz der "Problemfälle" INNERHALB jeder Altersgruppe
            # normalize='index' würde den Anteil der Problemfälle/Nicht-Problemfälle pro Altersgruppe zeigen
            # Wir wollen aber den Anteil der Problemfälle *an allen Personen in der Altersgruppe*
            # Daher berechnen wir es etwas anders:
            
            # Gesamtzahl pro Altersgruppe
            total_in_age_group = df_merged['age_group'].value_counts(dropna=False).sort_index()
            # Anzahl Problemfälle pro Altersgruppe
            issues_in_age_group = df_merged[df_merged['had_q10_issue_overall'] == True]['age_group'].value_counts(dropna=False).sort_index()

            # Stelle sicher, dass alle Altersgruppen in 'issues_in_age_group' vorhanden sind, auch wenn sie 0 Probleme hatten
            issues_in_age_group = issues_in_age_group.reindex(total_in_age_group.index, fill_value=0)

            percentage_issue_in_age_group = (issues_in_age_group / total_in_age_group * 100).round(1)
            
            summary_table = pd.DataFrame({
                'Gesamt pro Altersgruppe': total_in_age_group,
                'Anzahl Problemfälle': issues_in_age_group,
                'Prozent Problemfälle in Gruppe (%)': percentage_issue_in_age_group
            })
            print("\nZusammenfassung: Problemfälle nach Altersgruppe:")
            print(summary_table.to_string())
            
            # Optional: Barplot für den Prozentsatz der Problemfälle pro Altersgruppe
            plt.figure(figsize=(10, 6))
            percentage_issue_in_age_group.plot(kind='bar')
            plt.title('Prozentsatz der Teilnehmer mit "Q10-Problem" nach Altersgruppe')
            plt.xlabel('Altersgruppe')
            plt.ylabel('Prozent mit Problem (%)')
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plot_path_age_group_bar = os.path.join(OUTPUT_DIR, 'q10_issue_by_age_group_barplot.png')
            try:
                plt.savefig(plot_path_age_group_bar)
                print(f"\nBalkendiagramm für Problemfälle nach Altersgruppe gespeichert unter: {plot_path_age_group_bar}")
            except Exception as e_plot:
                print(f"FEHLER beim Speichern des Balkendiagramms: {e_plot}")
            plt.close()

        else:
            print("Keine Altersgruppen für die Analyse vorhanden.")
    else:
        print("Altersspalte ('age') nicht im gemergten DataFrame oder keine validen Altersdaten vorhanden.")

    print("\n\n=== Vergleichsanalyse abgeschlossen ===")

if __name__ == "__main__":
    main()