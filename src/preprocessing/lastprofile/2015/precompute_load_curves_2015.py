# src/preprocessing/lastprofile/2015/precompute_load_curves_2015.py
import pandas as pd
import os
from calendar import monthrange

RAW_CSV = "/Users/jonathan/Documents/GitHub/PowerE/data/raw/lastprofile/Swiss_load_curves_2015_2035_2050.csv"
OUT_DIR = "/Users/jonathan/Documents/GitHub/PowerE/data/processed/lastprofile/2015"
YEAR = 2015

def upsample_hourly_to_15min(hourly: pd.Series) -> pd.Series:
    """
    Nimmt eine Series mit 24 Werten (Index 0–23)
    und wiederholt jeden Eintrag 4× für 15-Min-Auflösung.
    """
    # repeat each hour 4 times
    vals = hourly.values.repeat(4)
    # Erzeuge einen Datums-Index 00:00–23:45 (96 Werte)
    times = pd.date_range("00:00", "23:45", freq="15T").time
    return pd.Series(vals, index=times)

def make_monthly_profiles(df_year: pd.DataFrame, year:int, month:int) -> pd.DataFrame:
    """
    Für einen Monat: für jede Appliance und day_type (weekday/weekend)
    den 24h-Verlauf auf 15min upsamplen und über alle Kalendertage dieses Typs
    replizieren.
    """
    month_df_list = []
    # Filter nur diesen Monat
    df_m = df_year[df_year["Month"] == month]

    # Gruppe nach „Day type“ + „Appliances“
    for (day_type, appliance), grp in df_m.groupby(["Day type", "Appliances"]):
        # sortiere nach Uhrzeit und hol die stündlichen Leistungswerte
        grp = grp.sort_values("Time")
        hourly = grp["Power (MW)"].reset_index(drop=True)
        prof15 = upsample_hourly_to_15min(hourly)

        # Kalender-Tage dieses Monats erzeugen
        days_in_month = monthrange(year, month)[1]
        alldates = pd.date_range(
            f"{year}-{month:02d}-01",
            f"{year}-{month:02d}-{days_in_month:02d}",
            freq="D",
            tz="Europe/Zurich"
        )

        # Wochentage vs. Wochenende filtern
        if day_type.lower() == "weekday":
            dates = alldates[alldates.weekday < 5]
        else:
            dates = alldates[alldates.weekday >= 5]

        # für jeden Kalendertag den 15-Min-Verlauf klonen
        for d in dates:
            timestamps = [d + pd.Timedelta(minutes=15*i) for i in range(96)]
            df_day = pd.DataFrame({
                "timestamp": timestamps,
                "Appliances": appliance,
                "Power_MW": prof15.values
            })
            month_df_list.append(df_day)

    # alles zusammen
    return pd.concat(month_df_list, ignore_index=True)

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # Rohdaten einlesen (nur Jahr=2015)
    df = pd.read_csv(RAW_CSV, sep=";")
    df2015 = df[df["Year"] == YEAR]

    # pro Monat verarbeiten und abspeichern
    for m in range(1, 13):
        print(f"Processing {YEAR}-{m:02d} …")
        df_month = make_monthly_profiles(df2015, YEAR, m)
        out_file = os.path.join(OUT_DIR, f"{m:02d}.parquet")
        df_month.to_parquet(out_file)
        print(f"  → geschrieben: {out_file}")

if __name__ == "__main__":
    main()