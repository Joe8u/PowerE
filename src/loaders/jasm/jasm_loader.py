import pandas as pd
import calendar
from pathlib import Path
from src.utils.settings import DATA_RAW_DIR


def load_jasm_day(year: int, month: int, day_type: str = "weekday") -> pd.DataFrame:
    """
    Lädt das stündliche Appliance‑Profil für den 1. Tag eines gegebenen Monats und 
    interpoliert linear auf ein 15‑Minuten‑Raster.
    day_type in {"weekday","weekend"}.
    """
    # Pfad zur Rohdatei
    # lade aus Deinem zentralen raw-Verzeichnis:
    path = Path(DATA_RAW_DIR) / "jasm" / "Swiss_load_curves_2015_2035_2050.csv"

    # 1) CSV einlesen und nach Jahr, Monat & Tagtyp filtern
    df = pd.read_csv(
        path,
        sep=";",
        usecols=["Year", "Month", "Day type", "Time", "Appliances", "Power (MW)"]
    )
    df = df[
        (df["Year"] == year) &
        (df["Month"] == month) &
        (df["Day type"] == day_type)
    ]

    # 2) Timestamp bauen (Tag=1 als Platzhalter) und tz‑lokalisieren
    base = pd.to_datetime({
        "year":  df["Year"],
        "month": df["Month"],
        "day":   1
    })
    df["timestamp"] = (
        base + pd.to_timedelta(df["Time"])
    ).dt.tz_localize("Europe/Zurich")

    # 3) Pivot: index=timestamp, columns=Appliances, Werte=Power (MW)
    pivot = df.pivot(
        index="timestamp",
        columns="Appliances",
        values="Power (MW)"
    )

    # 4) MW → kW und auf 15‑Minuten‑Raster hochrechnen (verwende "min" statt veraltetem "T")
    pivot = pivot.mul(1_000).resample("15min").interpolate(method="linear")

    return pivot


def build_month_profile(year: int, month: int, appliances: list[str] = None) -> pd.DataFrame:
    """
    Erzeugt ein vollständiges Monats‑Profil für jeden Kalendertag:
      – Unterscheidung Werktag (weekday) vs. Wochenende (weekend)
      – Interpolation auf 15‑Minuten-Raster
      – Optional auf eine Liste von Geräten beschränken
    """
    # Tagesprofile für Woche/Weekend laden
    df_wd = load_jasm_day(year, month, day_type="weekday")
    df_we = load_jasm_day(year, month, day_type="weekend")
    if appliances is not None:
        df_wd = df_wd[appliances]
        df_we = df_we[appliances]

    # Für jeden Tag im Monat das passende Template kopieren und Datum setzen
    num_days = calendar.monthrange(year, month)[1]
    frames = []
    for day in range(1, num_days + 1):
        is_weekend = calendar.weekday(year, month, day) >= 5
        template = df_we if is_weekend else df_wd
        tmp = template.copy()
        tmp.index = tmp.index.map(lambda ts: ts.replace(day=day))
        frames.append(tmp)

    # Alles zusammenfügen und nach Index sortieren
    return pd.concat(frames).sort_index()

