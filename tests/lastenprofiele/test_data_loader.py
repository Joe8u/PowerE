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
    # Im grouped-Modus liefern wir die Survey-Gruppennamen
    apps = list_appliances(2024, group=True)
    assert isinstance(apps, list)
    # mindestens eine bekannte Survey-Gruppe
    assert "Geschirrspüler" in apps

def test_load_month_contents():
    # Roh-Modus: alle Original-Spalten werden geladen
    df = load_month(2024, 1)
    assert not df.empty
    # Index muss datetime und ohne tz sein
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.index.tz is None
    # alle Spalten sind numerisch
    for col in df.columns:
        assert pd.api.types.is_numeric_dtype(df[col])

def test_load_range_partial():
    start = datetime.datetime(2024, 1, 1)
    end   = datetime.datetime(2024, 1, 3)
    # Roh-Modus: Bereichsladen funktioniert unverändert
    df = load_range(start, end, year=2024)
    assert df.index.min() >= start
    assert df.index.max() <= end

def test_load_appliances_subset():
    start = datetime.datetime(2024, 1, 1)
    end   = datetime.datetime(2024, 1, 2)
    # grouped-Modus: wir laden zwei Survey-Gruppen
    df = load_appliances(
        ["Bürogeräte", "Fernseher und Entertainment-Systeme"],
        start, end,
        year=2024,
        group=True
    )
    # Nur diese beiden Gruppen
    assert set(df.columns) == {
        "Bürogeräte",
        "Fernseher und Entertainment-Systeme"
    }
    assert df.index.min() >= start
    assert df.index.max() <= end