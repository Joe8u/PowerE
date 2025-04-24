# src/dashboard/callbacks.py

from typing import Any, Dict

import pandas as pd
from dash import Input, Output

# Loader-Funktionen importieren (Signaturen siehe unten!)
from src.powere.loaders.jasm.daily import load_jasm_day
from src.powere.loaders.jasm.monthly import load_jasm_month
from src.powere.loaders.jasm.weekly import load_jasm_week
from src.powere.loaders.jasm.yearly import load_jasm_year

# (Analog später für market, tertiary, survey …)


def register_callbacks(app: Any) -> None:
    """
    Registriert alle Dash-Callbacks.
    """

    # Mapping Quelle → Granularität → Loader-Funktion
    # Loader-Signaturen:
    #   - yearly: load_X_year(year: int) -> DataFrame
    #   - others: load_X_day/week/month(year: int, start: str, end: str) -> DataFrame
    loaders: Dict[str, Dict[str, Any]] = {
        "jasm": {
            "daily": load_jasm_day,
            "weekly": load_jasm_week,
            "monthly": load_jasm_month,
            "yearly": load_jasm_year,
        },
        # "market": { ... },
        # "tertiary": { ... },
        # "survey": { ... },
    }

    @app.callback(
        Output("appliance-selector", "options"),
        Input("source-tabs", "value"),
        Input("year-selector", "value"),
        Input("granularity", "value"),
    )
    def update_appliances(source: str, year: int, granularity: str):
        """
        Baut die Dropdown-Options mit allen Spalten (Geräte/Metriken)
        des geladenen DataFrames.
        """
        loader_fn = loaders.get(source, {}).get(granularity)
        if not loader_fn:
            return []

        # nur year
        if granularity == "yearly":
            df = loader_fn(year)
        else:
            # für daily/weekly/monthly: komplette Jahre laden und später slice
            df = loader_fn(year, None, None)  # fallback, erwartet start/end
        return [{"label": c, "value": c} for c in df.columns]

    @app.callback(
        Output("main-graph", "figure"),
        Input("source-tabs", "value"),
        Input("granularity", "value"),
        Input("year-selector", "value"),
        Input("appliance-selector", "value"),
        Input("date-range", "start_date"),
        Input("date-range", "end_date"),
    )
    def update_graph(
        source: str,
        granularity: str,
        year: int,
        selected_apps: list[str],
        start: str,
        end: str,
    ) -> dict:
        """
        Lädt die Daten per Loader, filtert nach Datum & Apps
        und baut die Plotly-Figure auf.
        """
        loader_fn = loaders.get(source, {}).get(granularity)
        if loader_fn is None:
            return {}

        # Jahres-Average
        if granularity == "yearly":
            df = loader_fn(year)

        # Tages-/Wochen-/Monats-Ansicht mit Datumsslice
        else:
            df = loader_fn(year, start, end)

        # nur ausgewählte Spalten
        if selected_apps:
            df = df[selected_apps]

        # einfache Linien-Figure
        fig = {
            "data": [
                {"x": df.index, "y": df[col], "name": col, "mode": "lines"}
                for col in df.columns
            ],
            "layout": {
                "title": f"{source.upper()} | {granularity} | {year}",
                "xaxis": {"title": "Zeit"},
                "yaxis": {"title": "Leistung / Wert"},
            },
        }
        return fig
