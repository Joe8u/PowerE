# src/dashboard/app.py
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
from dash.dependencies import Input, Output

# Layout imports (only layouts and callback registration functions)
from dashboard.pages.summary   import layout as summary_layout,   register_callbacks as register_summary
from dashboard.pages.details   import layout as details_layout,   register_callbacks as register_details
from dashboard.pages.scenarios import layout as scenarios_layout, register_callbacks as register_scenarios

# Create Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)
server = app.server

# Main layout with URL routing
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content")
])

# Page switcher
@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def display_page(pathname):
    if pathname == "/details":
        return details_layout
    elif pathname == "/scenarios":
        return scenarios_layout
    else:
        return summary_layout

# Register callbacks after app and server are defined
register_summary(app)
register_details(app)
register_scenarios(app)