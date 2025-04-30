# src/dashboard/pages/details.py

from dash import html, dcc
import plotly.express as px
import pandas as pd
import os

def load_month_profile(year: int, appliance: str, day_type: str, month: int):
    """
    Liest die Parquet-Datei für die gegebene Kombination
    und gibt ein DataFrame mit Zeitindex und power_mw zurück.
    """
    base = os.path.join('data', 'processed', 'lastprofile', str(year),
                        appliance.replace(' ', '_'), day_type)
    path = os.path.join(base, f'month_{month:02d}.parquet')
    df = pd.read_parquet(path)
    # sicherstellen, dass der Index datetime ist
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    return df

# Beispiel: 2015, Geschirrspüler (Dishwasher), Wochentag, Januar
df_example = load_month_profile(2015, 'Dishwasher', 'weekday', 1)

# Erzeuge die Plotly-Figur
fig = px.line(
    df_example,
    x=df_example.index,
    y='power_mw',
    title="2015 – Dishwasher (weekday), Januar (15-Minuten-Auflösung)",
    labels={'x': 'Zeit', 'power_mw': 'Leistung (MW)'}
)

# Dash-Layout
layout = html.Div([
    html.H1("Seite 2 – Detailanalyse"),
    html.P("Beispiel: 15-Minuten-Lastprofil für Dishwasher im Januar 2015 (Wochentag)."),
    dcc.Graph(figure=fig)
])