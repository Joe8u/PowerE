#!/usr/bin/env python3
# PowerE/src/preprocessing/lastprofile/2024/precompute_lastprofile_2024.py

#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

BASE    = Path("data/processed/lastprofile")
OUT_DIR = BASE/"2024"
OUT_DIR.mkdir(exist_ok=True)

# linearer Gewichtungsfaktor zwischen 2015 ↔ 2035
f = (2024 - 2015) / (2035 - 2015)  # = 0.45

for m in range(1, 13):
    # 1) Lade Wide-CSV für 2015 & 2035
    df15 = pd.read_csv(
        BASE/"2015"/f"2015-{m:02d}.csv",
        parse_dates=["timestamp"]
    )
    df35 = pd.read_csv(
        BASE/"2035"/f"2035-{m:02d}.csv",
        parse_dates=["timestamp"]
    )

    # 2) Melt → long-Format
    df15_long = df15.melt(
        id_vars=["timestamp"],
        var_name="appliance",
        value_name="consumption"
    )
    df35_long = df35.melt(
        id_vars=["timestamp"],
        var_name="appliance",
        value_name="consumption"
    )

    # 3) Saisonale Keys extrahieren
    for df in (df15_long, df35_long):
        df["month"] = df["timestamp"].dt.month
        df["hour"]  = df["timestamp"].dt.hour

    # 4) Gruppenmittelwerte für 2015 & 2035
    g15 = (
        df15_long
        .groupby(["appliance","month","hour"])["consumption"]
        .mean()
        .rename("c15")
    )
    g35 = (
        df35_long
        .groupby(["appliance","month","hour"])["consumption"]
        .mean()
        .rename("c35")
    )
    g = pd.concat([g15, g35], axis=1).reset_index()
    # 5) Linear interpolieren pro saisonaler Gruppe
    g["c2024"] = (1 - f) * g["c15"] + f * g["c35"]

    # 6) Merge zurück auf jede Timestamp+Appliance
    df2024_long = (
        df15_long[["timestamp","appliance","month","hour"]]
        .merge(
            g[["appliance","month","hour","c2024"]],
            on=["appliance","month","hour"]
        )
        .rename(columns={"c2024":"consumption_kW"})
        [["timestamp","appliance","consumption_kW"]]
    )

    # 7) Pivot zurück ins Wide-Format
    df2024_wide = df2024_long.pivot(
        index="timestamp",
        columns="appliance",
        values="consumption_kW"
    ).reset_index()

    # 8) Spalten-Reihenfolge wie im Original (Timestamp zuerst)
    cols = ["timestamp"] + [c for c in df15.columns if c != "timestamp"]
    df2024_wide = df2024_wide[cols]

    # 9) CSV schreiben
    df2024_wide.to_csv(OUT_DIR/f"2024-{m:02d}.csv", index=False)
    print(f"Wrote seasonal‐interpolated (wide) 2024-{m:02d}.csv")