# src/powere/precompute/jasm/precompute_jasm_monthly.py
#!/usr/bin/env python3

from pathlib import Path
import calendar
import pandas as pd

from powere.utils.settings import DATA_PROCESSED_STATIC
from powere.loaders.jasm.jasm_loader import build_month_profile

# Jahresliste (Basisjahre für Simulation)
YEARS = [2015, 2035, 2050]


def precompute_for_year(year: int, appliances=None):
    """
    Generiert die 15‑Minuten‑Monatsprofile für ein Jahr und
    speichert sie in DATA_PROCESSED_STATIC/jasm/{year}/monthly/.
    """
    out_dir = Path(DATA_PROCESSED_STATIC) / "jasm" / str(year) / "monthly"
    out_dir.mkdir(parents=True, exist_ok=True)

    for month in range(1, 13):
        df = build_month_profile(year, month, appliances=appliances)
        fn = out_dir / f"appliance_monthly_{year}_{month:02d}.csv"
        df.to_csv(fn)
        print(f"→ gespeichert: {fn} ({len(df)} Zeilen)")


if __name__ == "__main__":
    APPS = None  # None = alle Geräte; oder Liste z.B. ["Dishwasher","Oven",...]
    for y in YEARS:
        print(f"\n--- Erzeuge monthly für {y} ---")
        precompute_for_year(y, appliances=APPS)


# src/powere/precompute/jasm/precompute_jasm_monthly_2024.py
#!/usr/bin/env python3

import calendar
from datetime import datetime
from pathlib import Path
import pandas as pd

from powere.utils.settings import DATA_RAW_DIR, DATA_PROCESSED_STATIC, TZ

# Zieljahr und Basisszenarien
TARGET_YEAR = 2024
BASE_YEAR1 = 2015
BASE_YEAR2 = 2035
APPS = None  # None = alle Geräte; oder z.B. ["Dishwasher","Oven",...]

# Pfade
RAW_CSV = Path(DATA_RAW_DIR) / "jasm" / "Swiss_load_curves_2015_2035_2050.csv"
OUT_DIR = Path(DATA_PROCESSED_STATIC) / "jasm" / str(TARGET_YEAR) / "monthly"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Einlesen der Rohdaten
raw_df = pd.read_csv(
    RAW_CSV,
    sep=";",
    usecols=["Year", "Month", "Day type", "Time", "Appliances", "Power (MW)"],
)


def get_daily_template(year: int, month: int, day_type: str) -> pd.DataFrame:
    """
    Lädt das stündliche Tagesprofil, skaliert MW→kW,
    interpoliert aufs 15‑Min‑Raster und gibt DataFrame mit time-Index.
    """
    df = raw_df[
        (raw_df["Year"] == year)
        & (raw_df["Month"] == month)
        & (raw_df["Day type"] == day_type)
    ].copy()
    if APPS is not None:
        df = df[df["Appliances"].isin(APPS)]

    # Basis-Datum (Tag 1)
    base = datetime(2000, 1, 1)
    df["timestamp"] = base + pd.to_timedelta(df["Time"])
    df["timestamp"] = df["timestamp"].dt.tz_localize(
        TZ, nonexistent="shift_forward", ambiguous=True
    )

    pivot = df.pivot(
        index="timestamp", columns="Appliances", values="Power (MW)"
    )
    pivot = pivot.mul(1_000)  # kW

    daily_15 = pivot.resample("15T").interpolate(method="linear")
    daily_15.index.freq = "15T"
    return daily_15


def build_2024_daily(month: int, day_type: str) -> pd.DataFrame:
    """
    Interpoliert das Tagesprofil für TARGET_YEAR zwischen BASE_YEAR1 und BASE_YEAR2.
    """
    tpl1 = get_daily_template(BASE_YEAR1, month, day_type)
    tpl2 = get_daily_template(BASE_YEAR2, month, day_type)
    alpha = (TARGET_YEAR - BASE_YEAR1) / (BASE_YEAR2 - BASE_YEAR1)
    return tpl1 + alpha * (tpl2 - tpl1)


if __name__ == "__main__":
    for month in range(1, 13):
        print(f"⏳ Erzeuge Monatsprofil 2024-{month:02d} …", end=" ")
        tpl_wd = build_2024_daily(month, "weekday")
        tpl_we = build_2024_daily(month, "weekend")
        days = calendar.monthrange(TARGET_YEAR, month)[1]
        frames = []
        for day in range(1, days + 1):
            date = pd.Timestamp(TARGET_YEAR, month, day)
            is_we = date.weekday() >= 5
            tpl = tpl_we if is_we else tpl_wd
            idx = pd.DatetimeIndex([
                pd.Timestamp.combine(date.date(), t).tz_localize(TZ)
                for t in tpl.index
            ])
            df_day = pd.DataFrame(tpl.values, index=idx, columns=tpl.columns)
            frames.append(df_day)
        df_month = pd.concat(frames)
        out_file = OUT_DIR / f"appliance_monthly_{TARGET_YEAR}_{month:02d}.csv"
        df_month.to_csv(out_file)
        print(f"fertig → {out_file.name} ({len(df_month)} Zeilen)")


# src/powere/precompute/jasm/precompute_jasm_yearly.py
#!/usr/bin/env python3

from pathlib import Path
import pandas as pd

from powere.utils.settings import DATA_PROCESSED_STATIC, TZ

TARGET_YEAR = 2024
IN_DIR = Path(DATA_PROCESSED_STATIC) / "jasm" / str(TARGET_YEAR) / "monthly"
OUT_DIR = Path(DATA_PROCESSED_STATIC) / "jasm" / str(TARGET_YEAR) / "yearly"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    records = []
    for m in range(1, 13):
        csv_file = IN_DIR / f"appliance_monthly_{TARGET_YEAR}_{m:02d}.csv"
        df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
        if df.index.tz is None:
            df.index = df.index.tz_localize(TZ)
        else:
            df.index = df.index.tz_convert(TZ)
        avg = df.mean()
        avg.name = m
        records.append(avg)

    yearly = pd.DataFrame(records)
    yearly.index.name = "month"

    out_file = OUT_DIR / f"appliance_yearly_avg_{TARGET_YEAR}.csv"
    yearly.to_csv(out_file)
    print(
        f"✅ Gespeichert: {out_file} "
        f"({yearly.shape[0]} Monate × {yearly.shape[1]} Appliances)"
    )


if __name__ == "__main__":
    main()


# src/powere/precompute/jasm/precompute_jasm_yearly_2024.py
#!/usr/bin/env python3

from pathlib import Path
import pandas as pd

from powere.utils.settings import DATA_PROCESSED_STATIC, TZ

TARGET_YEAR = 2024
IN_DIR = Path(DATA_PROCESSED_STATIC) / "jasm" / str(TARGET_YEAR) / "monthly"
OUT_DIR = Path(DATA_PROCESSED_STATIC) / "jasm" / str(TARGET_YEAR) / "yearly"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 1) Monatsprofile einlesen
frames = []
for m in range(1, 13):
    csv_file = IN_DIR / f"appliance_monthly_{TARGET_YEAR}_{m:02d}.csv"
    df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
    if df.index.tz is None:
        df.index = df.index.tz_localize(TZ)
    else:
        df.index = df.index.tz_convert(TZ)
    frames.append(df)

# 2) Zusammenführen und nach Monat mitteln
full = pd.concat(frames)
yearly = full.groupby(full.index.month).mean()
yearly.index.name = "month"

# 3) Speichern
out_file = OUT_DIR / f"appliance_yearly_avg_{TARGET_YEAR}.csv"
yearly.to_csv(out_file)
print(
    f"✅ Jahres‑Durchschnitt {TARGET_YEAR} gespeichert in {out_file} "
    f"({yearly.shape[0]} Monate × {yearly.shape[1]} Appliances)"
)
