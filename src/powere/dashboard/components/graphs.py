# src/dashboard/components/graphs.py

from dash import Input, Output
from src.dashboard.app import app
# hier weitere Loader importieren:
from src.loaders.jasm.yearly import load_jasm_yearly
# from src.loaders.jasm.monthly import load_jasm_monthly
# from src.loaders.market.yearly import load_market_yearly
# …

@app.callback(
    Output("main-graph", "figure"),
    Input("source-tabs",        "value"),
    Input("granularity",        "value"),
    Input("year-selector",      "value"),
    Input("appliance-selector", "value"),
    Input("date-range",         "start_date"),
    Input("date-range",         "end_date"),
)
def update_graph(source, grit, year, selected_apps, start_date, end_date):
    # 1) Daten laden via den Loader (je nach source+grit)
    #    z.B. if source=="jasm" and grit=="yearly":
    #             df = load_jasm_yearly(year).loc[:, selected_apps]
    # 2) ggf. filtern (Datum nur für daily/weekly/monthly)
    # 3) Plotly-Figure bauen und return fig
    fig = {...}
    return fig