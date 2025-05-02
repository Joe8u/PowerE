#!/usr/bin/env python3
# src/preprocessing/lastprofile/2050/precompute_load_curves_2050.py

import pandas as pd
import os
from calendar import monthrange

# 1) Pfade definieren
def get_paths():
    raw      = "data/raw/lastprofile/Swiss_load_curves_2015_2035_2050.csv"
    out_base = "data/processed/lastprofile/2050"
    return raw, out_base

# 2) Zieljahr
YEAR = 2050

# 3) Hilfsfunktion: Stündliche Daten auf 15-Min-Intervalle aufteilen
def upsample_hourly_to_15min(hourly: pd.Series) -> pd.Series:
    vals  = hourly.values.repeat(4)
    times = pd.date_range("00:00", "23:45", freq="15min").time
    return pd.Series(vals, index=times)

# 4) Monatsweise Verarbeitung und CSV-Ausgabe
def process_month(df_year: pd.DataFrame, year: int, month: int, out_base: str):
    # a) Rohdaten für den Monat filtern
    df_m = df_year[df_year["Month"] == month]

    # b) Profile pro Appliance & Day type sammeln
    profiles = {}
    for (day_type, appliance), grp in df_m.groupby(["Day type", "Appliances"]):
        grp     = grp.sort_values("Time")
        hourly  = grp["Power (MW)"].reset_index(drop=True)
        prof15  = upsample_hourly_to_15min(hourly)
        profiles.setdefault(appliance, {})[day_type.lower()] = prof15

    # c) tz-aware Zeitindex in Europe/Zurich erzeugen
    start      = pd.Timestamp(year=year, month=month, day=1, tz="Europe/Zurich")
    days       = monthrange(year, month)[1]
    end        = pd.Timestamp(year=year, month=month, day=days, hour=23, minute=45, tz="Europe/Zurich")
    full_index = pd.date_range(start, end, freq="15min")

    df_out = pd.DataFrame(index=full_index)

    # d) Verbrauchswerte zuweisen (weekday vs weekend)
    for appliance, profs in profiles.items():
        wd = profs.get("weekday")
        we = profs.get("weekend")
        times   = full_index.time
        vals_wd = [wd[t] for t in times]
        vals_we = [we[t] for t in times]
        mask_wd = full_index.weekday < 5

        series = pd.Series(index=full_index, dtype=float)
        series[mask_wd]  = pd.Series(vals_wd, index=full_index)[mask_wd]
        series[~mask_wd] = pd.Series(vals_we, index=full_index)[~mask_wd]
        df_out[appliance] = series

    # e) Verzeichnis & Dateinamen
    os.makedirs(out_base, exist_ok=True)
    out_file = os.path.join(out_base, f"{year}-{month:02d}.csv")

    # f) Index zurück in Spalte, Zeitzone entfernen, CSV schreiben
    df_export = df_out.reset_index().rename(columns={"index": "timestamp"})
    df_export["timestamp"] = (
        df_export["timestamp"]
            .dt.tz_convert("Europe/Zurich")  # in lokale Zeit wandeln
            .dt.tz_localize(None)            # Offset entfernen, Uhrzeit bleibt
    )

    df_export.to_csv(out_file, index=False)
    print(f"  → geschrieben: {out_file}")

# 5) Hauptfunktion

def main():
    raw, out_base = get_paths()
    os.makedirs(out_base, exist_ok=True)

    df       = pd.read_csv(raw, sep=";")
    df_year  = df[df["Year"] == YEAR]

    for m in range(1, 13):
        print(f"Processing {YEAR}-{m:02d} …")
        process_month(df_year, YEAR, m, out_base)

if __name__ == "__main__":
    main()