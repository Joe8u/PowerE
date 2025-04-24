import pandas as pd
from pathlib import Path
from powere.utils.settings import DATA_RAW_DIR

def load_jasm_day(year: int, month: int, day_type: str = "weekday") -> pd.DataFrame:
    """
    Lädt das stündliche Appliance-Profil für den 1. Tag eines gegebenen Monats und 
    interpoliert aufs 15-Minuten-Raster. Liefert genau 96 Zeilen, freqstr "15T".
    """
    # 1) Rohdaten einlesen
    raw_csv = Path(DATA_RAW_DIR) / "jasm" / "Swiss_load_curves_2015_2035_2050.csv"
    df = pd.read_csv(raw_csv, sep=";", usecols=[
        "Year", "Month", "Day type", "Time", "Appliances", "Power (MW)"
    ])
    df = df[
        (df["Year"] == year) &
        (df["Month"] == month) &
        (df["Day type"] == day_type)
    ].copy()

    # 2) Timestamp für einen Platzhalter-Tag erzeugen
    #    wir nehmen den 1. des Monats als Datum, Zeit aus "Time"-Spalte
    df["timestamp"] = pd.to_datetime(df["Time"], format="%H:%M:%S")
    base_date = pd.Timestamp(year=year, month=month, day=1)
    df["timestamp"] = df["timestamp"].dt.time.apply(
        lambda t: pd.Timestamp.combine(base_date, t)
    )
    # 3) tz-lokalisieren (mit DST-Handling)
    df["timestamp"] = df["timestamp"].dt.tz_localize(
        "Europe/Zurich", nonexistent="shift_forward", ambiguous="infer"
    )

    # 4) Pivot und Umrechnung MW→kW
    pivot = df.pivot(index="timestamp", columns="Appliances", values="Power (MW)")
    pivot = pivot.mul(1_000)

    # 5) Auf 15-Minuten-Raster hochrechnen
    day_df = pivot.resample("15T").interpolate(method="linear")

    # 6) Sicherstellen: genau 96 Zeilen, Lücken interpolieren
    start = day_df.index[0].floor("D")
    full_idx = pd.date_range(
        start=start,
        periods=96,
        freq="15T",
        tz=day_df.index.tz
    )
    day_df = day_df.reindex(full_idx).interpolate(method="linear")

    # 7) freq und freqstr setzen
    day_df.index.freq = pd.tseries.frequencies.to_offset("15T")
    day_df.index.freqstr = "15T"

    return day_df