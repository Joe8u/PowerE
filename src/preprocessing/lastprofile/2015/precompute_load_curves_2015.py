# src/preprocessing/lastprofile/2015/precompute_load_curves_2015.py
import pandas as pd
import os
from calendar import monthrange

# Pfade anpassen
RAW_CSV = "/Users/jonathan/Documents/GitHub/PowerE/data/raw/lastprofile/Swiss_load_curves_2015_2035_2050.csv"
OUT_DIR = "/Users/jonathan/Documents/GitHub/PowerE/data/processed/lastprofile/2015"
YEAR = 2015


def upsample_hourly_to_15min(hourly: pd.Series) -> pd.Series:
    """
    Nimmt eine Series mit 24 Werten (Index 0–23)
    und wiederholt jeden Eintrag 4× für 15-Min-Auflösung.
    """
    vals = hourly.values.repeat(4)
    # Generiere Uhrzeit-Index von 00:00 bis 23:45 in 15-Minuten-Schritten
    times = pd.date_range("00:00", "23:45", freq="15min").time
    return pd.Series(vals, index=times)


def process_month(df_year: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    """
    Erzeugt für einen Monat eine kombinierte 15-Min-CSV mit allen Appliances und Day types.
    """
    df_m = df_year[df_year["Month"] == month]
    month_data = []

    # Für jede Kombination aus Wochentag/WE und Appliance
    for (day_type, appliance), grp in df_m.groupby(["Day type", "Appliances"]):
        grp = grp.sort_values("Time")
        hourly = grp["Power (MW)"].reset_index(drop=True)
        prof15 = upsample_hourly_to_15min(hourly)

        # Kalenderdaten des Monats
        days = monthrange(year, month)[1]
        alldates = pd.date_range(
            f"{year}-{month:02d}-01",
            f"{year}-{month:02d}-{days:02d}",
            freq="D",
            tz="Europe/Zurich"
        )
        if day_type.lower() == "weekday":
            dates = alldates[alldates.weekday < 5]
        else:
            dates = alldates[alldates.weekday >= 5]

        # Pro Tag alle Viertelstunden
        for d in dates:
            timestamps = [d + pd.Timedelta(minutes=15 * i) for i in range(96)]
            df_day = pd.DataFrame({
                "timestamp": timestamps,
                "Appliances": appliance,
                "Day type": day_type,
                "Power_MW": prof15.values
            })
            month_data.append(df_day)

    # Alle Daten des Monats zusammenführen
    return pd.concat(month_data, ignore_index=True)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # Rohdaten einlesen
    df = pd.read_csv(RAW_CSV, sep=";")
    df_year = df[df["Year"] == YEAR]

    # Pro Monat generieren und als CSV speichern
    for m in range(1, 13):
        print(f"Processing {YEAR}-{m:02d} …")
        df_month = process_month(df_year, YEAR, m)
        out_file = os.path.join(OUT_DIR, f"{YEAR}-{m:02d}.csv")
        df_month.to_csv(out_file, index=False)
        print(f"  → geschrieben: {out_file}")


if __name__ == "__main__":
    main()
