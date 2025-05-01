import datetime
import pandas as pd
import pytest
from pathlib import Path
from data_loader.lastprofile import (
    list_appliances,
    load_month,
    load_range,
    load_appliances
)

BASE = Path("data/processed/lastprofile")

def test_list_appliances():
    apps = list_appliances(2024)
    assert isinstance(apps, list)
    assert "Computer" in apps  # mindestens eine bekannte Spalte

def test_load_month_contents():
    df = load_month(2024, 1)
    assert not df.empty
    # Index muss datetime und ohne tz sein
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.index.tz is None
    # alle Spalten außer timestamp sind numerisch
    for col in df.columns:
        assert pd.api.types.is_numeric_dtype(df[col])

def test_load_range_partial():
    start = datetime.datetime(2024,1,1)
    end   = datetime.datetime(2024,1,3)
    df = load_range(start, end, year=2024)
    assert df.index.min() >= start
    assert df.index.max() <= end

def test_load_appliances_subset():
    start = datetime.datetime(2024,1,1)
    end   = datetime.datetime(2024,1,2)
    df = load_appliances(["Computer","TV"], start, end, year=2024)
    # Nur die beiden Spalten
    assert set(df.columns) == {"Computer","TV"}
    assert df.index.min() >= start
    assert df.index.max() <= end