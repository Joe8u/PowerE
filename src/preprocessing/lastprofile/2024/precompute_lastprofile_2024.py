#!/usr/bin/env python3
# PowerE/src/preprocessing/lastprofile/2024/precompute_lastprofile_2024.py

#!/usr/bin/env python3
#!/usr/bin/env python3
# src/preprocessing/lastprofile/2024/precompute_lastprofile_2024.py

import pandas as pd
from pathlib import Path

BASE    = Path("data/processed/lastprofile")
OUT_DIR = BASE / "2024"
OUT_DIR.mkdir(exist_ok=True)

# linearer Gewichtungsfaktor zwischen 2015 ↔ 2035
f = (2024 - 2015) / (2035 - 2015)  # = 0.45

for m in range(1, 13):
    # 1) Lade Wide-CSV für 2015 & 2035
    path15 = BASE / "2015" / f"2015-{m:02d}.csv"
    path35 = BASE / "2035" / f"2035-{m:02d}.csv"
    df15 = pd.read_csv(path15, parse_dates=["timestamp"])
    df35 = pd.read_csv(path35, parse_dates=["timestamp"])

    # 2) normalize column names (strip whitespace, to lowercase)
    for df in (df15, df35):
        df.columns = df.columns.str.strip().str.lower()

    # 3) force timestamp → datetime
    for df in (df15, df35):
        df["timestamp"] = pd.to_datetime(df["timestamp"], infer_datetime_format=True)

    # 4) Melt → long-Format für saisonale Gruppierung
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

    # 5) Saisonale Keys extrahieren
    for df in (df15_long, df35_long):
        df["month"] = df["timestamp"].dt.month
        df["hour"]  = df["timestamp"].dt.hour

    # 6) Gruppenmittelwerte für 2015 & 2035
    g15 = (
        df15_long
        .groupby(["appliance", "month", "hour"])["consumption"]
        .mean()
        .rename("c15")
    )
    g35 = (
        df35_long
        .groupby(["appliance", "month", "hour"])["consumption"]
        .mean()
        .rename("c35")
    )
    g = pd.concat([g15, g35], axis=1).reset_index()

    # 7) Linear interpolieren pro saisonaler Gruppe
    g["c2024"] = (1 - f) * g["c15"] + f * g["c35"]

    # 8) Merge zurück auf jede Timestamp+Appliance
    df2024_long = (
        df15_long[["timestamp", "appliance", "month", "hour"]]
        .merge(
            g[["appliance", "month", "hour", "c2024"]],
            on=["appliance", "month", "hour"]
        )
        .rename(columns={"c2024": "consumption_kW"})
        [["timestamp", "appliance", "consumption_kW"]]
    )

    # 9) Pivot zurück ins Wide-Format
    df2024_wide = (
        df2024_long
        .pivot(index="timestamp", columns="appliance", values="consumption_kW")
        .reset_index()
    )

    # 10) Spalten-Reihenfolge wie im Original (timestamp zuerst)
    original_cols = [c for c in df15.columns]
    # sicherstellen, dass 'timestamp' an erster Stelle steht
    cols = ["timestamp"] + [c for c in original_cols if c != "timestamp"]
    df2024_wide = df2024_wide[cols]

    # 11) CSV schreiben
    out_path = OUT_DIR / f"2024-{m:02d}.csv"
    df2024_wide.to_csv(out_path, index=False)
    print(f"Wrote seasonal‐interpolated (wide) {out_path.name}")