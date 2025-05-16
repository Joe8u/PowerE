# -*- coding: utf-8 -*-
"""
Script to preprocess Question 1 (Age) from the Survey Monkey raw data.

This script reads the raw CSV export, extracts respondent IDs and their age responses,
and writes the result to a separate processed CSV file for Question 1.

Input:
    PowerE/data/raw/survey/Energieverbrauch und Teilnahmebereitschaft an Demand-Response-Programmen in Haushalten.csv
Output:
    PowerE/data/processed/survey/question_1_age.csv

Usage:
    python preprocess_q1_age.py
"""
import os
import pandas as pd

# Define file paths
RAW_DIR = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, 'data', 'raw', 'survey')
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, 'data', 'processed', 'survey')
RAW_FILENAME = 'Energieverbrauch und Teilnahmebereitschaft an Demand-Response-Programmen in Haushalten.csv'
OUTPUT_FILENAME = 'question_1_age.csv'

# Ensure the processed directory exists
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Load the raw data
raw_path = os.path.join(RAW_DIR, RAW_FILENAME)
# KORRIGIERTER AUFRUF:
df_raw = pd.read_csv(raw_path, encoding='utf-8', sep=',', header=0, skiprows=[1])

# Extract respondent_id and the age column
# Note: adjust the column name if it differs
AGE_COL = 'Wie alt sind Sie?'
if AGE_COL not in df_raw.columns:
    raise KeyError(f"Expected column '{AGE_COL}' not found in raw data.")

df_q1 = df_raw[['respondent_id', AGE_COL]].copy()

# Rename columns for clarity
df_q1.columns = ['respondent_id', 'age']

# Save the processed data
output_path = os.path.join(PROCESSED_DIR, OUTPUT_FILENAME)
df_q1.to_csv(output_path, index=False, encoding='utf-8')

print(f"Preprocessed Question 1 data saved to: {output_path}")
