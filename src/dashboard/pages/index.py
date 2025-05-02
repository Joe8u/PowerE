# src/dashboard/pages/index.py
from dash import register_page, html, dcc, callback, Input, Output
import pandas as pd
import plotly.express as px

# 1) register this as the root page
register_page(__name__,
    path="/",
    title="Executive Summary",
    name="Summary"       # optional but gives you a default nav label
)

DF_DUMMY = pd.DataFrame({
    "Kategorie": ["Spot Einsparung", "Kompensation"],
    "Wert":      [1000, 300]
})

layout = html.Div([
    dcc.Interval(id="summary-trigger", interval=1, max_intervals=1),
    html.H2("Executive Summary"),              # ← this is the <h2> your test is looking for
    html.Div([
        html.H4("Netto-Mehrwert (CHF)"),
        html.Div(id="summary-net-value")
    ], className="card", style={"marginBottom": "20px"}),
    dcc.Graph(id="summary-kpi-graph")
])

@callback(
    Output("summary-net-value", "children"),
    Input("summary-trigger", "n_intervals"),
)
def update_net_value(_):
    total = (
        DF_DUMMY.loc[DF_DUMMY.Kategorie=="Spot Einsparung", "Wert"].sum()
      - DF_DUMMY.loc[DF_DUMMY.Kategorie=="Kompensation",   "Wert"].sum()
    )
    return f"{total} CHF"

@callback(
    Output("summary-kpi-graph", "figure"),
    Input("summary-trigger", "n_intervals"),
)
def update_kpi_graph(_):
    return px.bar(DF_DUMMY, x="Kategorie", y="Wert", title="Kosten vs. Kompensation")