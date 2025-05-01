# src/dashboard/app.py
import dash
from dash import Dash
import dash_bootstrap_components as dbc

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    use_pages=True,
    pages_folder="pages",
    suppress_callback_exceptions=True   # ← ADD THIS
)

server = app.server

app.layout = dbc.Container([
    dbc.NavbarSimple(
        brand="PowerE-Dash",
        color="primary",
        dark=True,
        children=[
            dbc.NavItem(dbc.NavLink("Summary",    href="/")),
            dbc.NavItem(dbc.NavLink("Details",    href="/details")),
            dbc.NavItem(dbc.NavLink("Scenarios",  href="/scenarios")),
        ]
    ),
    dash.page_container       # hier werden deine pages gerendert
])