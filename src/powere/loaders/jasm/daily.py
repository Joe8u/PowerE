from pathlib import Path

import pandas as pd

from powere.utils.settings import DATA_RAW_DIR


def load_jasm_day(year: int, month: int, day_type: str = "weekday") -> pd.DataFrame:
    """
    Lädt das Appliance-Profil für einen einzigen Kalendertag
    und interpoliert aufs 15-Minuten-Raster. Liefert genau 96 Zeilen,
    freqstr "15T".
    """
    # 1) Rohdaten einlesen
    raw_csv = Path(DATA_RAW_DIR) / "jasm" / "Swiss_load_curves_2015_2035_2050.csv"
    df = pd.read_csv(
        raw_csv,
        sep=";",
        usecols=["Year", "Month", "Day type", "Time", "Appliances", "Power (MW)"],
    )
    df = df[
        (df["Year"] == year)
        & (df["Month"] == month)
        & (df["Day type"] == day_type)
    ].copy()

    # 2) Timestamp für Platzhalter-Tag (1. des Monats) direkt aus Time + Basisdatum
    base = pd.Timestamp(year=year, month=month, day=1)
    df["timestamp"] = base + pd.to_timedelta(df["Time"])

    # 3) tz-lokalisieren
    df["timestamp"] = df["timestamp"].dt.tz_localize(
        "Europe/Zurich", nonexistent="shift_forward", ambiguous="infer"
    )

    # 4) Pivot und MW→kW
    pivot = df.pivot(index="timestamp", columns="Appliances", values="Power (MW)")
    pivot = pivot.mul(1_000)

    # 5) Erste Resample-Stufe (kann Lücken haben)
    day_df = pivot.resample("15T").interpolate(method="linear")

    # 6) Vollständiges 96-Zeilen-Index erzwingen
    start = day_df.index[0].floor("D")
    full_idx = pd.date_range(
        start=start,
        periods=96,
        freq="15T",
        tz=day_df.index.tz
    )
    day_df = day_df.reindex(full_idx).interpolate(method="linear")

    # 7) fertig: full_idx bringt schon freqstr "15T" mit
    return day_df