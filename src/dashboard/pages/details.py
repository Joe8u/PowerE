# src/dashboard/pages/details.py
import pandas as pd
from datetime import datetime, timedelta
from dash import dcc, html
from dash.dependencies import Input, Output
from dashboard.app import app

# Verfügbare Jahre und Monate
YEARS = [2015, 2035, 2050]
MONTH_OPTIONS = [
    {"label": datetime(1900, m, 1).strftime('%B'), "value": m}
    for m in range(1, 13)
]

# Appliance-Liste aus Januar 2015 laden (Beispiel)
_df0 = pd.read_csv(
    'data/processed/lastprofile/2015/2015-01.csv',
    parse_dates=['timestamp']
)
APPLIANCES = sorted([c for c in _df0.columns if c != 'timestamp'])

# Layout
layout = html.Div([
    html.H2('Detailprofil-Analyse'),
    html.Div([
        html.Label('Appliance:'),
        dcc.Dropdown(
            id='details-appliance-dropdown',
            options=[{'label': a, 'value': a} for a in APPLIANCES],
            value=APPLIANCES[0],
            clearable=False
        )
    ], style={'width': '300px'}),
    html.Div([
        dcc.Tabs(
            id='details-view-tabs',
            value='day',
            children=[
                dcc.Tab(label='Tag', value='day'),
                dcc.Tab(label='Woche', value='week'),
                dcc.Tab(label='Monat', value='month'),
            ]
        )
    ], style={'marginTop': '20px'}),
    html.Div(id='details-date-picker-container', style={'marginTop': '20px'}),
    dcc.Graph(id='details-graph', style={'marginTop': '40px'})
])

# Hilfsfunktion: CSV laden

def load_month_csv(year: int, month: int) -> pd.DataFrame:
    path = f'data/processed/lastprofile/{year}/{year}-{month:02d}.csv'
    df = pd.read_csv(path, parse_dates=['timestamp'])
    df.set_index('timestamp', inplace=True)
    return df

# Callback: Datumsauswahl je Ansicht
@app.callback(
    Output('details-date-picker-container', 'children'),
    Input('details-view-tabs', 'value')
)
def render_date_picker(view):
    today = datetime.today()
    if view == 'day':
        return html.Div([
            html.Label('Wähle Tag:'),
            dcc.DatePickerSingle(
                id='details-daily-picker',
                date=today.date(),
                display_format='YYYY-MM-DD'
            )
        ])
    elif view == 'week':
        monday = today - timedelta(days=today.weekday() + 7)
        sunday = monday + timedelta(days=6)
        return html.Div([
            html.Label('Wähle Woche:'),
            dcc.DatePickerRange(
                id='details-weekly-picker',
                start_date=monday.date(),
                end_date=sunday.date(),
                display_format='YYYY-MM-DD'
            )
        ])
    else:
        return html.Div([
            html.Label('Jahr:'),
            dcc.Dropdown(
                id='details-year-dropdown',
                options=[{'label': y, 'value': y} for y in YEARS],
                value=YEARS[0],
                clearable=False,
                style={'width': '120px', 'display': 'inline-block', 'marginRight': '20px'}
            ),
            html.Label('Monat:'),
            dcc.Dropdown(
                id='details-month-dropdown',
                options=MONTH_OPTIONS,
                value=today.month,
                clearable=False,
                style={'width': '200px', 'display': 'inline-block'}
            )
        ])

# Callback: Graph aktualisieren
@app.callback(
    Output('details-graph', 'figure'),
    Input('details-appliance-dropdown', 'value'),
    Input('details-view-tabs', 'value'),
    Input('details-daily-picker', 'date'),
    Input('details-weekly-picker', 'start_date'),
    Input('details-weekly-picker', 'end_date'),
    Input('details-year-dropdown', 'value'),
    Input('details-month-dropdown', 'value')
)
def update_graph(appliance, view, day_date, week_start, week_end, year, month):
    import plotly.express as px
    # Tagesansicht
    if view == 'day' and day_date:
        dt = datetime.fromisoformat(day_date)
        df = load_month_csv(dt.year, dt.month)
        df_day = df.loc[dt.strftime('%Y-%m-%d')]
        fig = px.line(df_day, y=appliance, labels={'timestamp':'Zeit','value':'Leistung (MW)'})
        fig.update_layout(title=f'{appliance} am {dt.date()}')
        return fig
    # Wochenansicht
    if view == 'week' and week_start and week_end:
        start = datetime.fromisoformat(week_start)
        end = datetime.fromisoformat(week_end) + timedelta(days=1) - timedelta(minutes=15)
        # Lade ggf. zwei Monate
        df = load_month_csv(start.year, start.month)
        if start.month != end.month:
            df = pd.concat([df, load_month_csv(end.year, end.month)])
        df_week = df.loc[start:end]
        fig = px.line(df_week, y=appliance, labels={'timestamp':'Datum/Zeit','value':'Leistung (MW)'})
        fig.update_layout(title=f'{appliance}: Woche {start.date()}–{(end.date())}')
        return fig
    # Monatsansicht
    if view == 'month' and year and month:
        df = load_month_csv(year, month)
        fig = px.line(df, y=appliance, labels={'timestamp':'Datum/Zeit','value':'Leistung (MW)'})
        fig.update_layout(title=f'{appliance}: {year}-{month:02d}')
        return fig
    # Fallback: leere Figure
    return px.line()
