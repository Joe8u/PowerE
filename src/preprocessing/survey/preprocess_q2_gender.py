# -*- coding: utf-8 -*-
"""
Script to preprocess Question 2 (Gender) from the Survey Monkey raw data.

This script reads the raw CSV export, extracts respondent IDs and their gender responses,
and writes the result to a separate processed CSV file for Question 2.

Input:
    PowerE/data/raw/survey/Energieverbrauch und Teilnahmebereitschaft an Demand-Response-Programmen in Haushalten.csv
Output:
    PowerE/data/processed/survey/question_2_gender.csv

Usage:
    python preprocess_q2_gender.py
"""
import os
import pandas as pd

# Define file paths
RAW_DIR = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, 'data', 'raw', 'survey')
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, 'data', 'processed', 'survey')
RAW_FILENAME = 'Energieverbrauch und Teilnahmebereitschaft an Demand-Response-Programmen in Haushalten.csv'
OUTPUT_FILENAME = 'question_2_gender.csv'

# Ensure the processed directory exists
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Load the raw data
raw_path = os.path.join(RAW_DIR, RAW_FILENAME)
# KORRIGIERTER AUFRUF:
df_raw = pd.read_csv(raw_path, encoding='utf-8', sep=',', header=0, skiprows=[1])

# Extract respondent_id and the gender column
GENDER_COL = 'Was ist Ihr Geschlecht?'
if GENDER_COL not in df_raw.columns:
    raise KeyError(f"Expected column '{GENDER_COL}' not found in raw data.")

df_q2 = df_raw[['respondent_id', GENDER_COL]].copy()

# Rename columns for clarity
df_q2.columns = ['respondent_id', 'gender']

# Save the processed data
output_path = os.path.join(PROCESSED_DIR, OUTPUT_FILENAME)
df_q2.to_csv(output_path, index=False, encoding='utf-8')

print(f"Preprocessed Question 2 data saved to: {output_path}")
