# /Users/jonathan/Documents/GitHub/PowerE/tests/test_loaders_jasm.py
import pytest

from powere.loaders.jasm.daily import load_jasm_day
from powere.loaders.jasm.monthly import load_jasm_month
from powere.loaders.jasm.weekly import load_jasm_week
from powere.loaders.jasm.yearly import load_jasm_year


@pytest.mark.parametrize("year,month", [(2015, 1), (2024, 2)])
def test_load_jasm_day(year, month):
    df = load_jasm_day(year, month)
    # mindestens 96 Zeitpunkte (24 h × 4)
    assert df.shape[0] == 96
    assert df.index.freqstr == "15T"
    assert not df.isna().any().any()


def test_load_jasm_week():
    df = load_jasm_week(2024)
    # eine Woche sollte mindestens 7×96 = 672 Zeilen haben
    assert df.shape[0] >= 672
    assert df.index.freqstr == "15T"


def test_load_jasm_month():
    df = load_jasm_month(2024)
    # Februar 2024 hat 29 Tage, 29×96=2784 Zeilen:
    assert df.shape[0] >= 28 * 96


def test_load_jasm_year():
    df = load_jasm_year(2024)
    # Monats-Index 1–12
    assert list(df.index) == list(range(1, 13))
    assert df.shape[1] > 0  # mindestens eine Appliance
