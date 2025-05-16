# PowerE/src/analysis/data_check/analyze_q10_incentive_data.py
"""
Skript zur Datenqualitätsanalyse für Frage 10 (Incentives) der Umfrage.
# ... (Rest des Docstrings) ...
"""
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# --- Konfiguration ---
# (Bleibt wie in deiner letzten Version)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROCESSED_SURVEY_DIR_ABS = os.path.abspath(os.path.join(SCRIPT_DIR, '../../../data/processed/survey/'))
RAW_SURVEY_DIR_ABS = os.path.abspath(os.path.join(SCRIPT_DIR, '../../../data/raw/survey/'))
Q10_FILENAME = 'question_10_incentive_wide.csv'
RAW_DATA_WITH_DEVICE_FILENAME = 'Energieverbrauch und Teilnahmebereitschaft an Demand-Response-Programmen in Haushalten.csv'
DEVICES = [
    'Geschirrspüler',
    'Backofen und Herd',
    'Fernseher und Entertainment-Systeme',
    'Bürogeräte',
    'Waschmaschine'
]
OUTPUT_DIR = 'data_check_q10_output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Hilfsfunktionen ---
def clean_pct_based_on_choice(df, choice_col, pct_col):
    df.loc[df[choice_col].isin(['Ja f', 'Nein']), pct_col] = np.nan
    df.loc[df[choice_col].isna() & df[pct_col].notna(), pct_col] = np.nan
    return df

# --- Daten laden ---
q10_path = os.path.join(PROCESSED_SURVEY_DIR_ABS, Q10_FILENAME)
raw_data_path = os.path.join(RAW_SURVEY_DIR_ABS, RAW_DATA_WITH_DEVICE_FILENAME)

try:
    df_q10 = pd.read_csv(q10_path, encoding='utf-8')
    print(f"'{Q10_FILENAME}' erfolgreich geladen.")
    for device_prefix_for_conversion in DEVICES:
        pct_col_to_convert = f'{device_prefix_for_conversion}_pct'
        if pct_col_to_convert in df_q10.columns:
            df_q10[pct_col_to_convert] = pd.to_numeric(df_q10[pct_col_to_convert], errors='coerce')
    print("Prozent-Spalten wurden explizit in numerischen Typ konvertiert (Fehler zu NaN).")
except FileNotFoundError:
    print(f"FEHLER: Datei '{q10_path}' nicht gefunden. Bitte Pfad anpassen.")
    exit()

try:
    df_raw_full = pd.read_csv(raw_data_path, encoding='utf-8', header=0, skiprows=[1])
    if 'respondent_id' not in df_raw_full.columns or 'Device' not in df_raw_full.columns:
        print("FEHLER: 'respondent_id' oder 'Device' Spalte nicht in der Rohdatendatei gefunden.")
        df_device_info = pd.DataFrame(columns=['respondent_id', 'Device'])
    else:
        df_device_info = df_raw_full[['respondent_id', 'Device']].copy()
    print(f"Rohdaten für Geräteinformationen ('{RAW_DATA_WITH_DEVICE_FILENAME}') teilweise geladen.")
except FileNotFoundError:
    print(f"WARNUNG: Rohdatendatei '{raw_data_path}' für Geräteinformationen nicht gefunden.")
    df_device_info = pd.DataFrame(columns=['respondent_id', 'Device'])

# --- Daten zusammenführen ---
if not df_device_info.empty:
    df_q10['respondent_id'] = df_q10['respondent_id'].astype(str)
    df_device_info['respondent_id'] = df_device_info['respondent_id'].astype(str)
    df_analysis = pd.merge(df_q10, df_device_info, on='respondent_id', how='left')
else:
    df_analysis = df_q10.copy()
    if 'Device' not in df_analysis.columns:
         df_analysis['Device'] = np.nan

# --- Leerzeichenbereinigung für _choice Spalten ---


choice_cols_q10 = [f'{dev}_choice' for dev in DEVICES if f'{dev}_choice' in df_analysis.columns]

# Erstellt eine Serie, die für jeden Teilnehmer True ist, wenn mindestens eine _choice-Spalte nicht NA ist
# (und einen der validen Werte enthält, falls du das noch genauer prüfen willst, aber notna() ist oft ausreichend hier)
# df_analysis['q10_hat_geantwortet'] = df_analysis[choice_cols_q10].notna().any(axis=1)

# Genauer: True, wenn mindestens eine _choice-Spalte einen der validen Textwerte enthält
def hat_valide_q10_antwort(row):
    for col in choice_cols_q10:
        if pd.notna(row[col]) and row[col] in ['Ja, +', 'Ja f', 'Nein']:
            return True
    return False

df_analysis['q10_hat_valide_geantwortet'] = df_analysis.apply(hat_valide_q10_antwort, axis=1)
n_mit_valider_q10_antwort = df_analysis['q10_hat_valide_geantwortet'].sum()

# Die Gesamtzahl der Teilnehmer im df_analysis (sollte 372 sein, wenn alle IDs gematcht wurden)
n_gesamt_in_q10_datensatz = df_analysis.shape[0]

print(f"\nAnzahl Teilnehmer im Q10-Datensatz: {n_gesamt_in_q10_datensatz}")
print(f"Anzahl Teilnehmer mit mindestens einer validen Antwort in Frage 10: {n_mit_valider_q10_antwort}")
if n_gesamt_in_q10_datensatz > 0:
    prozent_mit_valider_q10_antwort = (n_mit_valider_q10_antwort / n_gesamt_in_q10_datensatz) * 100
    print(f"Dies entspricht {prozent_mit_valider_q10_antwort:.1f}% der Teilnehmer im Q10-Datensatz.")


print("\nBereinige Leerzeichen in allen '_choice'-Spalten von df_analysis...")
for device_to_clean in DEVICES:
    choice_col_to_clean = f'{device_to_clean}_choice'
    if choice_col_to_clean in df_analysis.columns:
        df_analysis[choice_col_to_clean] = df_analysis[choice_col_to_clean].astype(str).str.strip()
        df_analysis.loc[df_analysis[choice_col_to_clean].str.lower() == 'nan', choice_col_to_clean] = np.nan
print("Leerzeichenbereinigung für '_choice'-Spalten in df_analysis abgeschlossen.")

# +++ NEU: Liste zum Sammeln der Ergebnisse für die Zusammenfassung +++
summary_for_thesis = []
total_respondents = df_analysis.shape[0]
print(f"\nGesamtzahl der Teilnehmer im Datensatz (df_analysis): {total_respondents}")


print("\n--- Analyse für Frage 10 ---")
for device in DEVICES:
    choice_col = f'{device}_choice'
    pct_col = f'{device}_pct'
    print(f"\n--- Gerät: {device} ---")
    if choice_col not in df_analysis.columns or pct_col not in df_analysis.columns:
        print(f"WARNUNG: Spalten für {device} nicht im DataFrame gefunden. Überspringe.")
        continue

    df_analysis_cleaned_for_device = clean_pct_based_on_choice(df_analysis.copy(), choice_col, pct_col)
    
    print("\n1. Häufigkeit der 'Choice'-Antworten:")
    choice_counts = df_analysis_cleaned_for_device[choice_col].value_counts(dropna=False)
    print(choice_counts)

    # Hole N_GESAMT_JA_PLUS aus den (bereinigten für Leerzeichen) Choice-Counts von df_analysis
    # (Nicht aus df_analysis_cleaned_for_device, da clean_pct_based_on_choice nichts an den Choice-Labels ändert)
    n_gesamt_ja_plus = df_analysis[df_analysis[choice_col] == 'Ja, +'].shape[0]

    valid_pct_series = df_analysis_cleaned_for_device.loc[df_analysis_cleaned_for_device[choice_col] == 'Ja, +', pct_col].dropna()
    print("\n2. Deskriptive Statistiken für 'Prozent'-Angaben (nur wenn Choice='Ja +'):")
    if not valid_pct_series.empty:
        print(valid_pct_series.describe())
        # ... (Plotting Code bleibt gleich) ...
        plt.figure(figsize=(8, 5)); sns.histplot(valid_pct_series, kde=False, bins=10); plt.title(f'Verteilung Prozent für {device} (Choice="Ja +")'); plt.xlabel('Prozent Rabatt'); plt.ylabel('Anzahl'); plt.savefig(os.path.join(OUTPUT_DIR, f'{device}_pct_histogram.png')); plt.close()
        plt.figure(figsize=(6, 4)); sns.boxplot(y=valid_pct_series); plt.title(f'Boxplot Prozent für {device} (Choice="Ja +")'); plt.ylabel('Prozent Rabatt'); plt.savefig(os.path.join(OUTPUT_DIR, f'{device}_pct_boxplot.png')); plt.close()
    else:
        print("Keine validen Prozentangaben für 'Ja +' bei diesem Gerät vorhanden oder nach Bereinigung keine übrig.")

    print("\n3. Prüfung auf Inkonsistenzen (basierend auf df_analysis nach Leerzeichen- und Num-Konvertierung):")
    n_ja_plus_ohne_prozent = df_analysis.loc[(df_analysis[choice_col] == 'Ja, +') & (df_analysis[pct_col].isna())].shape[0]
    print(f"   Anzahl 'Ja, +' ohne Prozentangabe: {n_ja_plus_ohne_prozent}")

    choice_nein_oder_jaf_mit_pct = df_analysis.loc[
        (df_analysis[choice_col].isin(['Ja f', 'Nein'])) & (df_analysis[pct_col].notna())
    ].shape[0]
    print(f"   Anzahl 'Ja f'/'Nein' MIT Prozentangabe (sollte 0 sein nach Preprocessing): {choice_nein_oder_jaf_mit_pct}")

    choice_fehlt_mit_pct = df_analysis.loc[
        (df_analysis[choice_col].isna()) & (df_analysis[pct_col].notna())
    ].shape[0]
    print(f"   Anzahl fehlende 'Choice' MIT Prozentangabe (sollte 0 sein nach Preprocessing): {choice_fehlt_mit_pct}")

    # +++ NEU: Daten für Zusammenfassung sammeln +++
    prozent_ja_plus_ohne_pct_value = 0
    if n_gesamt_ja_plus > 0:
        prozent_ja_plus_ohne_pct_value = (n_ja_plus_ohne_prozent / n_gesamt_ja_plus) * 100
    
    summary_for_thesis.append({
        'Gerät': device,
        'N_Gesamt_Ja_Plus': n_gesamt_ja_plus,
        'N_Ja_Plus_ohne_Prozent': n_ja_plus_ohne_prozent,
        'Prozentsatz_Ja_Plus_ohne_Prozent': round(prozent_ja_plus_ohne_pct_value, 1)
    })

# --- Analyse nach Gerätetyp (Device) - Punkt 4 ---
# (Dieser Teil bleibt wie in deiner letzten Version, er liefert die Prozentsätze für iOS etc.)
# ... (Code für Punkt 4 wie gehabt) ...
if 'Device' in df_analysis.columns and df_analysis['Device'].notna().any():
    print("\n\n--- Analyse der Datenqualität von Frage 10 nach Gerätetyp (Device) ---")
    # ... (Rest des Codes für Device-Analyse wie in deiner Version) ...
    # Die Logik hier sollte jetzt mit den bereinigten 'Ja, +'-Werten funktionieren
    # df_analysis['temp_is_ja_plus'] = False # Diese Zeile kann weg, wenn nicht weiter verwendet
    for device_loop_var in DEVICES:
        choice_col_inner = f'{device_loop_var}_choice'
        pct_col_inner = f'{device_loop_var}_pct'
        if choice_col_inner not in df_analysis.columns: continue
        df_analysis[f'{device_loop_var}_pct_missing_for_ja_plus'] = \
            (df_analysis[choice_col_inner] == 'Ja, +') & (df_analysis[pct_col_inner].isna())
    print("\nVerteilung der genutzten Geräte (Device):")
    print(df_analysis['Device'].value_counts(dropna=False))
    for device_item_analyse in DEVICES:
        col_to_check_pct_missing = f'{device_item_analyse}_pct_missing_for_ja_plus'
        choice_col_for_subset = f'{device_item_analyse}_choice'
        if col_to_check_pct_missing not in df_analysis.columns: continue
        print(f"\nAnalyse für Haushaltsgerät: {device_item_analyse}")
        ja_plus_subset = df_analysis[df_analysis[choice_col_for_subset] == 'Ja, +']
        if not ja_plus_subset.empty:
            print(f"   Prozentsatz fehlender Prozentangaben (wenn 'Ja, +' gewählt wurde für {device_item_analyse}) nach Gerätetyp (Device):")
            summary = ja_plus_subset.groupby('Device', dropna=False)[col_to_check_pct_missing].value_counts(normalize=True, dropna=False).mul(100).round(1).astype(str) + '%'
            print(summary)
        else:
            print(f"   Keine 'Ja, +'-Antworten für {device_item_analyse} gefunden (nach Leerzeichenbereinigung und für Device-Analyse).")
    cols_to_drop_temp = [f'{d}_pct_missing_for_ja_plus' for d in DEVICES if f'{d}_pct_missing_for_ja_plus' in df_analysis.columns]
    df_analysis.drop(columns=cols_to_drop_temp, inplace=True, errors='ignore')
else:
    print("\nKeine 'Device'-Informationen für gerätespezifische Analyse der Datenqualität verfügbar.")


# +++ NEU: Ausgabe der Zusammenfassung für die Masterarbeit +++
print("\n\n--- Zusammenfassung der relevanten Zahlen für die Masterarbeit (Frage 10) ---")
print(f"Gesamtzahl der ausgewerteten Teilnehmer: {total_respondents}")
# Anzahl Teilnehmer ohne Geräteinfo:
device_nan_count = df_analysis['Device'].isna().sum()
print(f"Anzahl Teilnehmer ohne Geräteinformation: {device_nan_count} (von {total_respondents})")

print("\nDetails pro Gerät ('Ja, +' Fälle):")
summary_df = pd.DataFrame(summary_for_thesis)
print(summary_df.to_string()) # .to_string() für schönere Konsolenausgabe

print("\n--- Analyse abgeschlossen ---")
print(f"Eventuell erstellte Plots wurden im Ordner '{OUTPUT_DIR}' gespeichert.")