# src/dashboard/app.py
import dash
from dash import Dash
from pathlib import Path
import dash_bootstrap_components as dbc

# 1) Tell Dash where to look for your page modules
PAGES_FOLDER = str(Path(__file__).parent / "pages")

# 2) Create the app, pointing at that folder
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    use_pages=True,
    pages_folder=PAGES_FOLDER,
    suppress_callback_exceptions=True,
)

server = app.server

app.layout = dbc.Container([
    dbc.NavbarSimple(
        brand="PowerE-Dash",
        color="primary",
        dark=True,
        children=[
            dbc.NavItem(dbc.NavLink("Summary",   href="/")),
            dbc.NavItem(dbc.NavLink("Details",   href="/details")),
            dbc.NavItem(dbc.NavLink("Scenarios", href="/scenarios")),
        ]
    ),
    dash.page_container
])