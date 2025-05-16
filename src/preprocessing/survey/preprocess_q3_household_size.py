# -*- coding: utf-8 -*-
"""
Script to preprocess Question 3 (Household Size) from the Survey Monkey raw data.

This script reads the raw CSV export, extracts respondent IDs and their household size responses,
specifically recodes 'über 6' to 7, then converts household size to a numeric type
(other non-numeric entries become NaN), and writes the result to a separate
processed CSV file for Question 3.

Input:
    PowerE/data/raw/survey/Energieverbrauch und Teilnahmebereitschaft an Demand-Response-Programmen in Haushalten.csv
Output:
    PowerE/data/processed/survey/question_3_household_size.csv

Usage:
    python preprocess_q3_household_size.py
"""
import os
import pandas as pd
import numpy as np # Für np.nan, falls explizit benötigt

# Define file paths
RAW_DIR = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, 'data', 'raw', 'survey')
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, 'data', 'processed', 'survey')
RAW_FILENAME = 'Energieverbrauch und Teilnahmebereitschaft an Demand-Response-Programmen in Haushalten.csv'
OUTPUT_FILENAME = 'question_3_household_size.csv'

# Ensure the processed directory exists
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Load the raw data, skipping the second row (artefact row)
raw_path = os.path.join(RAW_DIR, RAW_FILENAME)
df_raw = pd.read_csv(raw_path, encoding='utf-8', sep=',', header=0, skiprows=[1])

# Extract respondent_id and the household size column
SIZE_COL_ORIGINAL = 'Wie viele Personen leben in Ihrem Haushalt?' # Name der Spalte in der Rohdatei
if SIZE_COL_ORIGINAL not in df_raw.columns:
    raise KeyError(f"Expected column '{SIZE_COL_ORIGINAL}' not found in raw data.")

df_q3 = df_raw[['respondent_id', SIZE_COL_ORIGINAL]].copy()

# Umbenennen der Spalte VOR der Konvertierung, um Klarheit zu schaffen
df_q3.rename(columns={SIZE_COL_ORIGINAL: 'household_size'}, inplace=True)

# Spezifische textuelle Angaben zur Haushaltsgröße vor der numerischen Konvertierung ersetzen
# Wichtig: .astype(str) um sicherzustellen, dass .replace auf Strings operiert
df_q3['household_size'] = df_q3['household_size'].astype(str).str.lower().str.strip() # Normalisieren
df_q3['household_size'] = df_q3['household_size'].replace('über 6', '7')
# Du könntest hier weitere spezifische Ersetzungen hinzufügen, falls es andere Textantworten gab

# Konvertiere die 'household_size'-Spalte zu numerisch.
# Andere Texte, die nicht explizit ersetzt wurden (und keine Zahlen sind), werden zu NaN.
df_q3['household_size'] = pd.to_numeric(df_q3['household_size'], errors='coerce')

# Die Spaltennamen sind jetzt 'respondent_id' und 'household_size'

# Save the processed data
output_path = os.path.join(PROCESSED_DIR, OUTPUT_FILENAME)
df_q3.to_csv(output_path, index=False, encoding='utf-8')

print(f"Preprocessed Question 3 data saved to: {output_path}")