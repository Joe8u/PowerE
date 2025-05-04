#!/usr/bin/env python3
"""
explore_regelenergie.py

Explores available ENTSO-E balancing and market data (aFRR, mFRR, spot prices) for a specified period
using entsoe-py. Prints a summary of available data (columns, resolution, sample data)
to help determine usable endpoints for PowerE-Dash.
"""

import os
import pandas as pd
from dotenv import load_dotenv
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


def explore_endpoint(client: EntsoePandasClient, endpoint_name: str, query_func, start: pd.Timestamp, end: pd.Timestamp, country_code: str) -> dict:
    """
    Explore a specific ENTSO-E API endpoint and return a summary of available data.

    Args:
        client: EntsoePandasClient instance
        endpoint_name: Name of the endpoint (e.g., 'imbalance_volumes')
        query_func: Function to query the endpoint (e.g., client.query_imbalance_volumes)
        start: Start timestamp
        end: End timestamp
        country_code: Country code (e.g., 'CH')

    Returns:
        dict: Summary including columns, resolution, sample data, and errors
    """
    summary = {
        'endpoint': endpoint_name,
        'status': 'success',
        'columns': [],
        'resolution': None,
        'sample_data': None,
        'error': None
    }

    try:
        # Query the endpoint
        data = query_func(start=start, end=end, country_code=country_code)

        # Handle different data types (Series or DataFrame)
        if isinstance(data, pd.Series):
            df = data.to_frame(name=endpoint_name)
        elif isinstance(data, pd.DataFrame):
            df = data
        else:
            raise ValueError(f"Unexpected data type: {type(data)}")

        # Extract summary information
        summary['columns'] = list(df.columns)
        if not df.empty:
            # Determine resolution (difference between consecutive timestamps)
            if df.index.is_monotonic_increasing and len(df.index) > 1:
                resolution = (df.index[1] - df.index[0]).total_seconds() / 60
                summary['resolution'] = f"{int(resolution)} minutes"
            else:
                summary['resolution'] = "Irregular or insufficient data"
            # Sample data (first 5 rows)
            summary['sample_data'] = df.head().to_dict()
        else:
            summary['status'] = 'empty'
            summary['error'] = "No data returned"

    except Exception as e:
        summary['status'] = 'error'
        summary['error'] = str(e)

    return summary


def print_summary(summaries: list):
    """
    Print a formatted summary of explored endpoints.

    Args:
        summaries: List of summary dictionaries
    """
    print("\n=== ENTSO-E API Data Exploration Summary ===")
    for summary in summaries:
        print(f"\nEndpoint: {summary['endpoint']}")
        print(f"Status: {summary['status']}")
        if summary['status'] == 'error':
            print(f"Error: {summary['error']}")
        else:
            print(f"Columns: {summary['columns']}")
            print(f"Resolution: {summary['resolution']}")
            print("Sample Data:")
            if summary['sample_data']:
                for idx, row in summary['sample_data'].items():
                    print(f"  {idx}: {row}")
            else:
                print("  No sample data available")
        print("-" * 50)


def main():
    # Load API token and initialize client
    token = load_api_token()
    client = EntsoePandasClient(api_key=token)

    # Define test period (short period to explore available data)
    start = pd.Timestamp("2024-01-01", tz="Europe/Zurich")
    end = pd.Timestamp("2024-01-07", tz="Europe/Zurich")  # One week
    country_code = "CH"  # Switzerland

    # Define endpoints to explore
    endpoints = [
        {
            'name': 'imbalance_volumes',
            'func': client.query_imbalance_volumes,
            'description': 'Imbalance volumes (aFRR/mFRR activation quantities, MW)'
        },
        {
            'name': 'imbalance_prices',
            'func': client.query_imbalance_prices,
            'description': 'Imbalance prices (potentially aFRR/mFRR, CHF/MWh)'
        },
        {
            'name': 'day_ahead_prices',
            'func': client.query_day_ahead_prices,
            'description': 'Day-ahead spot market prices (CHF/MWh)'
        }
    ]

    # Explore each endpoint
    summaries = []
    for endpoint in endpoints:
        print(f"Exploring {endpoint['name']}...")
        summary = explore_endpoint(
            client=client,
            endpoint_name=endpoint['name'],
            query_func=endpoint['func'],
            start=start,
            end=end,
            country_code=country_code
        )
        summaries.append(summary)

    # Print summary
    print_summary(summaries)


if __name__ == '__main__':
    main()