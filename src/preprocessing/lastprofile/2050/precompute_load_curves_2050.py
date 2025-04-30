# src/preprocessing/lastprofile/2050/precompute_load_curves_2050.py
import pandas as pd
import os
from calendar import monthrange

# Pfade anpassen
def get_paths():
    raw = "/Users/jonathan/Documents/GitHub/PowerE/data/raw/lastprofile/Swiss_load_curves_2015_2035_2050.csv"
    out_base = "/Users/jonathan/Documents/GitHub/PowerE/data/processed/lastprofile/2050"
    return raw, out_base

YEAR = 2050


def upsample_hourly_to_15min(hourly: pd.Series) -> pd.Series:
    """
    Wandelt eine Series mit 24 stündlichen Werten in eine mit 96 Viertelstunden-Werten um.
    Index: time (hh:mm:ss)
    """
    vals = hourly.values.repeat(4)
    times = pd.date_range("00:00", "23:45", freq="15min").time
    return pd.Series(vals, index=times)


def process_month(df_year: pd.DataFrame, year: int, month: int, out_base: str):
    """
    Erzeugt für einen Monat eine CSV mit:
    timestamp, Appliance1, Appliance2, ..., ApplianceN
    basierend auf weekday/weekend-Profil und Kalenderdatum.
    """
    df_m = df_year[df_year["Month"] == month]
    profiles = {}
    # Profile pro Appliance und Day type sammeln
    for (day_type, appliance), grp in df_m.groupby(["Day type", "Appliances"]):
        grp = grp.sort_values("Time")
        hourly = grp["Power (MW)"].reset_index(drop=True)
        prof15 = upsample_hourly_to_15min(hourly)
        profiles.setdefault(appliance, {})[day_type.lower()] = prof15

    # Zeitindex für den Monat
    start = pd.Timestamp(year=year, month=month, day=1, tz="Europe/Zurich")
    days_in_month = monthrange(year, month)[1]
    end = pd.Timestamp(year=year, month=month, day=days_in_month, hour=23, minute=45, tz="Europe/Zurich")
    full_index = pd.date_range(start, end, freq="15min")

    df_out = pd.DataFrame(index=full_index)

    # Werte zuweisen basierend auf Wochentag/Weekend
    for appliance, profs in profiles.items():
        prof_weekday = profs.get("weekday")
        prof_weekend = profs.get("weekend")
        times = full_index.time
        vals_wd = [prof_weekday[t] for t in times]
        vals_we = [prof_weekend[t] for t in times]
        mask_wd = full_index.weekday < 5
        series = pd.Series(index=full_index, dtype=float)
        series[mask_wd] = pd.Series(vals_wd, index=full_index)[mask_wd]
        series[~mask_wd] = pd.Series(vals_we, index=full_index)[~mask_wd]
        df_out[appliance] = series

    os.makedirs(out_base, exist_ok=True)
    out_file = os.path.join(out_base, f"{year}-{month:02d}.csv")
    df_out.reset_index().rename(columns={"index": "timestamp"}).to_csv(out_file, index=False)
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
