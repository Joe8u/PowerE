# src/preprocessing/lastprofile/2015/precompute_load_curves_2015.py
import pandas as pd
import os
from calendar import monthrange

# Pfade anpassen
def get_paths():
    raw = "/Users/jonathan/Documents/GitHub/PowerE/data/raw/lastprofile/Swiss_load_curves_2015_2035_2050.csv"
    out_base = "/Users/jonathan/Documents/GitHub/PowerE/data/processed/lastprofile/2015"
    return raw, out_base


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
    Erzeugt für einen Monat eine CSV mit Spalten:
    timestamp, Appliance1, Appliance2, ..., ApplianceN
    Werte für jede Appliance basierend auf weekday- oder weekend-Profil und Kalenderdatum.
    """
    df_m = df_year[df_year["Month"] == month]
    # Profile pro Appliance und Day type sammeln
    profiles = {}
    for (day_type, appliance), grp in df_m.groupby(["Day type", "Appliances"]):
        # sortieren, stündliche Werte
        grp = grp.sort_values("Time")
        hourly = grp["Power (MW)"].reset_index(drop=True)
        prof15 = upsample_hourly_to_15min(hourly)
        profiles.setdefault(appliance, {})[day_type.lower()] = prof15

    # Vollständiger Zeitindex für den Monat
    start = pd.Timestamp(year=year, month=month, day=1, tz="Europe/Zurich")
    days_in_month = monthrange(year, month)[1]
    end = pd.Timestamp(year=year, month=month, day=days_in_month, hour=23, minute=45, tz="Europe/Zurich")
    full_index = pd.date_range(start, end, freq="15min")

    df_out = pd.DataFrame(index=full_index)

    # Für jede Appliance eine Spalte erzeugen
    for appliance, profs in profiles.items():
        # Profibus weekday und weekend
        prof_weekday = profs.get("weekday")
        prof_weekend = profs.get("weekend")
        # Werte entsprechend Tagestyp zuweisen
        # Tageszeit extrahieren
        times = full_index.time
        # Vektor aus weekday- und weekend-Profilen
        vals_weekday = [prof_weekday[t] for t in times]
        vals_weekend = [prof_weekend[t] for t in times]
        # Maske für Wochentage
        mask_weekday = full_index.weekday < 5
        # Serie initialisieren
        series = pd.Series(index=full_index, dtype=float)
        series[mask_weekday] = pd.Series(vals_weekday, index=full_index)[mask_weekday]
        series[~mask_weekday] = pd.Series(vals_weekend, index=full_index)[~mask_weekday]
        df_out[appliance] = series

    # Ausgabe
    os.makedirs(out_base, exist_ok=True)
    out_file = os.path.join(out_base, f"{year}-{month:02d}.csv")
        # 1) Reset index und Spalte umbenennen

    df_export = df_out.reset_index().rename(columns={"index": "timestamp"})
    # 2) Timestamp von tz-aware auf tz-naiv zurücksetzen,
    #    ohne die angezeigte Uhrzeit zu verändern
   # Da timestamp schon tz-aware ist, nur noch konvertieren und dann naiv machen:
    df_export["timestamp"] = (
       df_export["timestamp"]
           .dt.tz_convert("Europe/Zurich")  # in lokale Zeit wandeln
           .dt.tz_localize(None)            # Zeitzone wieder abziehen (Uhrzeit bleibt stehen)
   )

    # 3) CSV schreiben – jetzt stehen nur noch naive Zeiten in der Datei
    df_export.to_csv(out_file, index=False)
    print(f"  → geschrieben: {out_file}")


def main():
    raw, out_base = get_paths()
    os.makedirs(out_base, exist_ok=True)
    df = pd.read_csv(raw, sep=";")
    df_year = df[df["Year"] == 2015]
    for m in range(1, 13):
        print(f"Processing 2015-{m:02d} …")
        process_month(df_year, 2015, m, out_base)

if __name__ == "__main__":
    main()
