# -*- coding: utf-8 -*-
"""
Script to preprocess Question 1 (Age) from the Survey Monkey raw data.

This script reads the raw CSV export, extracts respondent IDs and their age responses,
specifically recodes 'unter 18' to 17 and 'über 95' to 96,
then converts age to a numeric type (other non-numeric entries become NaN),
and writes the result to a separate processed CSV file for Question 1.
"""
import os
import pandas as pd
import numpy as np # Für np.nan, falls explizit benötigt

# Define file paths
RAW_DIR = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, 'data', 'raw', 'survey')
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, 'data', 'processed', 'survey')
RAW_FILENAME = 'Energieverbrauch und Teilnahmebereitschaft an Demand-Response-Programmen in Haushalten.csv'
OUTPUT_FILENAME = 'question_1_age.csv'

# Ensure the processed directory exists
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Load the raw data
raw_path = os.path.join(RAW_DIR, RAW_FILENAME)
df_raw = pd.read_csv(raw_path, encoding='utf-8', sep=',', header=0, skiprows=[1])

# Extract respondent_id and the age column
AGE_COL_ORIGINAL = 'Wie alt sind Sie?' # Name der Spalte in der Rohdatei
if AGE_COL_ORIGINAL not in df_raw.columns:
    raise KeyError(f"Expected column '{AGE_COL_ORIGINAL}' not found in raw data.")

df_q1 = df_raw[['respondent_id', AGE_COL_ORIGINAL]].copy()

# Umbenennen der Spalte VOR der Konvertierung, um Klarheit zu schaffen
df_q1.rename(columns={AGE_COL_ORIGINAL: 'age'}, inplace=True)

# Spezifische textuelle Altersangaben vor der numerischen Konvertierung ersetzen
# Wichtig: .astype(str) um sicherzustellen, dass .replace auf Strings operiert, falls die Spalte gemischte Typen hat
df_q1['age'] = df_q1['age'].astype(str).str.lower().str.strip() # Normalisieren zu Kleinbuchstaben und Leerzeichen entfernen
df_q1['age'] = df_q1['age'].replace('unter 18', '17')
df_q1['age'] = df_q1['age'].replace('über 95', '96')
# Du könntest hier weitere spezifische Ersetzungen hinzufügen, falls nötig

# Konvertiere die 'age'-Spalte zu numerisch.
# Andere Texte, die nicht explizit ersetzt wurden, werden zu NaN.
df_q1['age'] = pd.to_numeric(df_q1['age'], errors='coerce')

# Die Spaltennamen sind jetzt 'respondent_id' und 'age'

# Save the processed data
output_path = os.path.join(PROCESSED_DIR, OUTPUT_FILENAME)
df_q1.to_csv(output_path, index=False, encoding='utf-8')

print(f"Preprocessed Question 1 data saved to: {output_path}")