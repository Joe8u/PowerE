# src/dashboard/pages/summary.py
import pandas as pd
from dash import dcc, html
from dash.dependencies import Input, Output

def layout():
    return html.Div([
        html.H2('Executive Summary'),
        html.Div([
            html.H4('Netto-Mehrwert (CHF)'),
            html.Div(id='summary-net-value')
        ], className='card', style={'marginBottom':'20px'}),
        dcc.Graph(id='summary-kpi-graph')
    ])

# Beispiel-Daten
DF_DUMMY = pd.DataFrame({
    'Kategorie': ['Spot Einsparung', 'Kompensation'],
    'Wert': [1000, 300]
})

# Callback-Registrierung
def register_callbacks(app):
    @app.callback(
        Output('summary-net-value', 'children'),
        []
    )
    def update_net_value():
        total = DF_DUMMY.loc[DF_DUMMY['Kategorie']=='Spot Einsparung', 'Wert'].sum() \
              - DF_DUMMY.loc[DF_DUMMY['Kategorie']=='Kompensation', 'Wert'].sum()
        return f"{total} CHF"

    @app.callback(
        Output('summary-kpi-graph', 'figure'),
        []
    )
    def update_kpi_graph():
        import plotly.express as px
        fig = px.bar(DF_DUMMY, x='Kategorie', y='Wert', title='Kosten vs. Kompensation')
        return fig