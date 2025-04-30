# src/dashboard/app.py
from dash import Dash, html, dcc, Input, Output
import dash_bootstrap_components as dbc

from dashboard.pages.summary   import layout as summary_layout
from dashboard.pages.details   import layout as details_layout
from dashboard.pages.scenarios import layout as scenarios_layout

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="PowerE-Dash Prototype"
)

app.layout = html.Div([
    # URL-Leiste überwachen
    dcc.Location(id='url', refresh=False),
    # Navigation
    html.Nav([
        dcc.Link("1 – Summary",   href='/',         style={'margin':'10px'}),
        dcc.Link("2 – Details",   href='/details',  style={'margin':'10px'}),
        dcc.Link("3 – Scenarios", href='/scenarios',style={'margin':'10px'}),
    ], style={'padding':'20px','backgroundColor':'#f8f9fa'}),
    # Hier rendern wir die Seite
    html.Div(id='page-content', style={'padding':'20px'})
])

@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/':
        return summary_layout
    elif pathname == '/details':
        return details_layout
    elif pathname == '/scenarios':
        return scenarios_layout
    else:
        return html.H1("404: Seite nicht gefunden")