#!/usr/bin/env python3
# src/preprocessing/lastprofile/2035/precompute_load_curves_2035.py

import pandas as pd
import os
from calendar import monthrange

# 1) Pfade definieren
def get_paths():
    raw      = "data/raw/lastprofile/Swiss_load_curves_2015_2035_2050.csv"
    out_base = "data/processed/lastprofile/2035"
    return raw, out_base

YEAR = 2035

# 2) Hilfsfunktion: Stündliche Daten auf 15-Min-Intervalle aufteilen
def upsample_hourly_to_15min(hourly: pd.Series) -> pd.Series:
    vals  = hourly.values.repeat(4)
    times = pd.date_range("00:00", "23:45", freq="15min").time
    return pd.Series(vals, index=times)

# 3) Pro Monat: Profil zusammenbauen und ausgeben
def process_month(df_year: pd.DataFrame, year: int, month: int, out_base: str):
    df_m = df_year[df_year["Month"] == month]

    # a) Profile für jede Appliance & Day type sammeln
    profiles = {}
    for (day_type, appliance), grp in df_m.groupby(["Day type", "Appliances"]):
        grp     = grp.sort_values("Time")
        hourly  = grp["Power (MW)"].reset_index(drop=True)
        prof15  = upsample_hourly_to_15min(hourly)
        profiles.setdefault(appliance, {})[day_type.lower()] = prof15

    # b) tz-aware Zeitindex in Europe/Zurich (automatisch +1/+2 Std)
    start      = pd.Timestamp(year=year, month=month, day=1, tz="Europe/Zurich")
    days       = monthrange(year, month)[1]
    end        = pd.Timestamp(year=year, month=month, day=days, hour=23, minute=45, tz="Europe/Zurich")
    full_index = pd.date_range(start, end, freq="15min")

    df_out = pd.DataFrame(index=full_index)

    # c) Verbrauchswerte je Appliance je nach Weekday/Weekend zuweisen
    for appliance, profs in profiles.items():
        wd = profs["weekday"]
        we = profs["weekend"]
        times = full_index.time
        vals_wd = [wd[t] for t in times]
        vals_we = [we[t] for t in times]
        mask_wd = full_index.weekday < 5

        series = pd.Series(index=full_index, dtype=float)
        series[mask_wd]   = pd.Series(vals_wd, index=full_index)[mask_wd]
        series[~mask_wd]  = pd.Series(vals_we, index=full_index)[~mask_wd]
        df_out[appliance] = series

    # d) Index zurück in Spalte, Zeitzone entfernen, CSV schreiben
    os.makedirs(out_base, exist_ok=True)
    out_file = os.path.join(out_base, f"{year}-{month:02d}.csv")

    df_export = df_out.reset_index().rename(columns={"index": "timestamp"})
    df_export["timestamp"] = (
        df_export["timestamp"]
            .dt.tz_convert("Europe/Zurich")  # stellt lokale Zeit sicher
            .dt.tz_localize(None)            # hebt Zeitzone auf, Uhrzeit bleibt gleich
    )

    df_export.to_csv(out_file, index=False)
    print(f"  → geschrieben: {out_file}")

def main():
    raw, out_base = get_paths()
    os.makedirs(out_base, exist_ok=True)

    df = pd.read_csv(raw, sep=";")
    df_year = df[df["Year"] == YEAR]

    for m in range(1, 13):
        print(f"Processing {YEAR}-{m:02d} …")
        process_month(df_year, YEAR, m, out_base)

if __name__ == "__main__":
    main()