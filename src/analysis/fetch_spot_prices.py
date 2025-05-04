#!/usr/bin/env python3
"""
fetch_spot_prices.py

Using entsoe-py to download ENTSO-E day-ahead spot prices (A44)
for specified months in years 2015 and 2024,
then save them as 15-minute CSV files in per-year folders.
"""

import os
import pandas as pd
from dotenv import load_dotenv
from pandas.tseries.offsets import MonthEnd
from entsoe import EntsoePandasClient


def load_api_token():
    """
    Load the ENTSOE_API_TOKEN from environment or .env file.
    Raises an error if not found.
    """
    load_dotenv()
    token = os.getenv('ENTSOE_API_TOKEN')
    if not token:
        raise RuntimeError("ENTSOE_API_TOKEN not set in environment or .env")
    return token


def fetch_spot_prices(client: EntsoePandasClient, year: int, month: int, country_code: str) -> pd.Series:
    """
    Query the day-ahead spot prices for the given year/month and country code.

    Returns:
        pandas Series with 15-minute resolution spot prices
    """
    # Define start at month's first day, end at month end
    start = pd.Timestamp(year, month, 1, tz='Europe/Zurich')
    end = start + MonthEnd(1)

    # Query hourly day-ahead prices
    hourly = client.query_day_ahead_prices(country_code, start=start, end=end)

    # Upsample to 15-minute resolution by forward-fill
    spot_15min = hourly.resample('15T').ffill()
    return spot_15min


def main():
    # Load API token and initialize client
    token = load_api_token()
    client = EntsoePandasClient(api_key=token)

    # Base output path (project root)
    base_dir = os.path.join('data', 'raw', 'market', 'spot_prices')

    # Years to fetch and country code
    years = [2015, 2024]
    country_code = 'CH'  # Switzerland

    for year in years:
        # Create per-year directory
        year_dir = os.path.join(base_dir, str(year))
        os.makedirs(year_dir, exist_ok=True)

        for month in range(1, 13):
            print(f"Fetching {year}-{month:02d}...")
            try:
                series = fetch_spot_prices(client, year, month, country_code)
                df = series.reset_index()
                df.columns = ['timestamp', 'price']
                filename = f"{year}-{month:02d}.csv"
                filepath = os.path.join(year_dir, filename)
                df.to_csv(filepath, index=False)
                print(f"Saved {filepath}")
            except Exception as e:
                print(f"Error fetching {year}-{month:02d}: {e}")


if __name__ == '__main__':
    main()