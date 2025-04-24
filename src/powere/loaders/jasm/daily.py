from pathlib import Path

import pandas as pd

from powere.utils.settings import DATA_RAW_DIR


def load_jasm_day(year: int, month: int, day_type: str = "weekday") -> pd.DataFrame:
    """
    Lädt ein 15-Min-Raster für einen einzigen Kalendertag:
      – year, month, day_type in {"weekday","weekend"}.
      – Index: tz-aware Timestamp über den ganzen Tag.
      – Spalten: Appliances.
      – Werte: Leistung in kW.
    """
    csv_path = Path(DATA_RAW_DIR) / "jasm" / "Swiss_load_curves_2015_2035_2050.csv"

    df = pd.read_csv(
        csv_path,
        sep=";",
        usecols=["Year", "Month", "Day type", "Time", "Appliances", "Power (MW)"],
    )
    df = df[
        (df["Year"] == year) & (df["Month"] == month) & (df["Day type"] == day_type)
    ].copy()

    # Basis-Zeitstempel (Tag 1 als Platzhalter)
    base = pd.to_datetime({"year": df["Year"], "month": df["Month"], "day": 1})
    df["timestamp"] = (base + pd.to_timedelta(df["Time"])).dt.tz_localize(
        "Europe/Zurich"
    )

    # Pivot und Umrechnung MW→kW
    pivot = df.pivot(index="timestamp", columns="Appliances", values="Power (MW)").mul(
        1_000
    )

    # — hier neu: stündliche Vollständigkeit erzwingen —
    tz = pivot.index.tz
    day0 = pivot.index[0].normalize()  # 2000-01-01 00:00 CET
    full_hours = pd.date_range(start=day0, periods=24, freq="H", tz=tz)
    pivot = pivot.reindex(full_hours)

    # auf 15 Min-Raster hochrechnen
    daily_15 = pivot.resample("15min").interpolate(method="linear")

    # Frequenz-Info setzen (für df.index.freqstr)
    daily_15.index.freq = pd.tseries.frequencies.to_offset("15T")

    return daily_15
