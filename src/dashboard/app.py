# src/dashboard/app.py
import dash
from dash import Dash
import dash_bootstrap_components as dbc

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    use_pages=True           # wichtig, falls du dash_pages nutzt
)

server = app.server

app.layout = dbc.Container([
    dbc.NavbarSimple(
        brand="PowerE-Dash",
        color="primary",
        dark=True,
        children=[
            dbc.NavItem(dbc.NavLink("Details", href="/details")),
            # … weitere Seiten
        ]
    ),
    dash.page_container       # hier werden deine pages gerendert
])