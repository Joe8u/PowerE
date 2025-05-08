# -*- coding: utf-8 -*-
"""
Script to preprocess Question 3 (Household Size) from the Survey Monkey raw data.

This script reads the raw CSV export, extracts respondent IDs and their household size responses,
and writes the result to a separate processed CSV file for Question 3.

Input:
    PowerE/data/raw/survey/Energieverbrauch und Teilnahmebereitschaft an Demand-Response-Programmen in Haushalten.csv
Output:
    PowerE/data/processed/survey/python preprocess_q4_accommodation.py

Usage:
    python preprocess_q3_household_size.py
"""
import os
import pandas as pd

# Define file paths
RAW_DIR = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, 'data', 'raw', 'survey')
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, 'data', 'processed', 'survey')
RAW_FILENAME = 'Energieverbrauch und Teilnahmebereitschaft an Demand-Response-Programmen in Haushalten.csv'
OUTPUT_FILENAME = 'python preprocess_q4_accommodation.py'

# Ensure the processed directory exists
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Load the raw data
raw_path = os.path.join(RAW_DIR, RAW_FILENAME)
df_raw = pd.read_csv(raw_path, encoding='utf-8', sep=',')

# Extract respondent_id and the household size column
SIZE_COL = 'Wie viele Personen leben in Ihrem Haushalt?'
if SIZE_COL not in df_raw.columns:
    raise KeyError(f"Expected column '{SIZE_COL}' not found in raw data.")

df_q3 = df_raw[['respondent_id', SIZE_COL]].copy()

# Rename columns for clarity
df_q3.columns = ['respondent_id', 'household_size']

# Save the processed data
output_path = os.path.join(PROCESSED_DIR, OUTPUT_FILENAME)
df_q3.to_csv(output_path, index=False, encoding='utf-8')

print(f"Preprocessed Question 3 data saved to: {output_path}")