#!/usr/bin/env python3
# PowerE/src/preprocessing/lastprofile/2024/precompute_lastprofile_2024.py

import pandas as pd
from pathlib import Path

BASE = Path("data/processed/lastprofile")
out = BASE/"2024"
out.mkdir(exist_ok=True)

# Gewichtungsfaktor
f = (2024 - 2015) / (2035 - 2015)  # = 0.45

for m in range(1,13):
    df15 = pd.read_csv(BASE/"2015"/f"2015-{m:02d}.csv", parse_dates=["timestamp"])
    df35 = pd.read_csv(BASE/"2035"/f"2035-{m:02d}.csv", parse_dates=["timestamp"])

    # Extrahiere saisonale Schlüssel, z.B. Monat+Stunde
    for df in (df15, df35):
        df["month"] = df["timestamp"].dt.month
        df["hour"]  = df["timestamp"].dt.hour

    # Gruppiere, berechne Mittelwerte
    g15 = df15.groupby(["appliance","month","hour"])["consumption_kW"].mean().rename("c15")
    g35 = df35.groupby(["appliance","month","hour"])["consumption_kW"].mean().rename("c35")

    # Merge und setzt den interpolierten Wert
    g = pd.concat([g15, g35], axis=1).reset_index()
    g["c2024"] = (1-f)*g["c15"] + f*g["c35"]

    # Jetzt rekonstruierst du die vollständigen Time-Series
    # Indem du für jede Zeile in df15 den zugehörigen c2024-Wert nimmst:
    df2024 = df15.merge(
        g[["appliance","month","hour","c2024"]],
        on=["appliance","month","hour"]
    )
    df2024 = df2024[["timestamp","appliance","c2024"]]
    df2024.columns = ["timestamp","appliance","consumption_kW"]

    # Abspeichern
    df2024.to_csv(out/f"2024-{m:02d}.csv", index=False)
    print(f"Wrote 2024-{m:02d}.csv")