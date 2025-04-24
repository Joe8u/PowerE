# /Users/jonathan/Documents/GitHub/PowerE/src/powere/precompute/jasm/precompute_jasm_monthly_2024.py
"""
precompute_jasm_monthly_2024.py

Interpoliert das Appliance-Lastprofil für TARGET_YEAR=2024 zwischen den Basis-Jahren
BASE_YEAR1=2015 und BASE_YEAR2=2035 und speichert je Monat eine 15-Minuten-CSV
in data/processed/static/jasm/2024/monthly/.
"""

import calendar
from datetime import datetime
from pathlib import Path

import pandas as pd

# === 1) Konfiguration ===
TARGET_YEAR = 2024
BASE_YEAR1 = 2015
BASE_YEAR2 = 2035
APPS = None  # None = alle Geräte; oder z.B. ["Dishwasher","Oven",...]

# Pfad zum Projekt-Root (hebt 3 Ebenen ab src/precompute/jasm)
PROJECT_ROOT = Path(__file__).resolve().parents[3]

RAW_CSV = (
    PROJECT_ROOT / "data" / "raw" / "jasm" / "Swiss_load_curves_2015_2035_2050.csv"
)
OUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "static"
    / "jasm"
    / str(TARGET_YEAR)
    / "monthly"
)
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Einmaliges Einlesen des Roh-DataFrames
raw_df = pd.read_csv(
    RAW_CSV,
    sep=";",
    usecols=["Year", "Month", "Day type", "Time", "Appliances", "Power (MW)"],
)


def get_daily_template(year: int, month: int, day_type: str) -> pd.DataFrame:
    """
    Lädt das stündliche Tagesprofil für (year, month, day_type),
    skaliert MW→kW, interpoliert aufs 15-Min-Raster und gibt einen
    DataFrame zurück, dessen Index reine Uhrzeiten (time) sind.
    """
    df = raw_df[
        (raw_df["Year"] == year)
        & (raw_df["Month"] == month)
        & (raw_df["Day type"] == day_type)
    ].copy()
    if APPS is not None:
        df = df[df["Appliances"].isin(APPS)]

    # 1) Basis-Datum zum Umwandeln (Tag 1 als Platzhalter)
    base_date = datetime(2000, 1, 1)

    # 2) Time-Strings in Timedelta umwandeln und zum base_date addieren
    df["timestamp"] = base_date + pd.to_timedelta(df["Time"])

    # 3) tz-lokalisieren mit DST-Handling
    df["timestamp"] = df["timestamp"].dt.tz_localize(
        "Europe/Zurich", nonexistent="shift_forward", ambiguous=True
    )

    # 4) Pivot: index=timestamp, columns=Appliances, Werte=Power (MW)
    pivot = df.pivot(index="timestamp", columns="Appliances", values="Power (MW)")

    # 5) MW → kW
    pivot = pivot.mul(1_000)

    # 6) Auf 15-Minuten-Raster hochrechnen
    daily_15 = pivot.resample("15min").interpolate(method="linear")

    # 7) Index auf time-of-day reduzieren
    daily_15.index = daily_15.index.time

    return daily_15


def build_2024_daily(month: int, day_type: str) -> pd.DataFrame:
    """
    Interpoliert das Tagesprofil für TARGET_YEAR zwischen BASE_YEAR1 und BASE_YEAR2.
    """
    tpl1 = get_daily_template(BASE_YEAR1, month, day_type)
    tpl2 = get_daily_template(BASE_YEAR2, month, day_type)
    alpha = (TARGET_YEAR - BASE_YEAR1) / (BASE_YEAR2 - BASE_YEAR1)
    return tpl1 + alpha * (tpl2 - tpl1)


# === 2) Hauptschleife: pro Monat vollständiges Profil bauen und speichern ===
if __name__ == "__main__":
    for month in range(1, 13):
        print(f"⏳ Erzeuge Monatsprofil 2024-{month:02d} …", end=" ")

        # Tages-Templates für Werktag und Wochenende
        tpl_wd = build_2024_daily(month, "weekday")
        tpl_we = build_2024_daily(month, "weekend")

        days_in_month = calendar.monthrange(TARGET_YEAR, month)[1]
        frames = []

        for day in range(1, days_in_month + 1):
            date = pd.Timestamp(TARGET_YEAR, month, day)
            is_weekend = date.dayofweek >= 5  # Sa=5, So=6

            tpl = tpl_we if is_weekend else tpl_wd

            # Vollständige Timestamps mit DST-Handling
            idx = pd.DatetimeIndex(
                [
                    pd.Timestamp.combine(date.date(), t).tz_localize(
                        "Europe/Zurich", nonexistent="shift_forward", ambiguous=True
                    )
                    for t in tpl.index
                ]
            )

            df_day = pd.DataFrame(tpl.values, index=idx, columns=tpl.columns)
            frames.append(df_day)

        # Alle Tage zusammensetzen
        df_month = pd.concat(frames)

        # CSV schreiben
        out_file = OUT_DIR / f"appliance_monthly_{TARGET_YEAR}_{month:02d}.csv"
        df_month.to_csv(out_file)

        print(f" fertig → {out_file.name} ({len(df_month)} Zeilen)")
