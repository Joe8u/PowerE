# src/dashboard/components/details/graphs/lastprofile_graphs.py

from dash import dcc
import plotly.express as px

def time_series_graph():
    return dcc.Graph(id="time-series-graph")

def make_load_figure(df_load, appliances, start, end, cumulative):
    """
    Erzeugt eine Zeitreihen‐Darstellung des Lastprofils.
    - cumulative=True: kumulierter Verbrauch über alle Appliances
    - sonst eine Linie je Appliance
    """
    if cumulative:
        total = df_load.sum(axis=1)
        total_df = total.reset_index()
        total_df.columns = ["timestamp", "value"]
        fig = px.line(
            total_df,
            x="timestamp",
            y="value",
            title=f"Kumulierte Nachfrage {start} bis {end}",
            labels={"timestamp": "Zeit", "value": "Leistung (kW)"}
        )
    else:
        dfr = df_load.reset_index()
        fig = px.line(
            dfr,
            x="timestamp",
            y=appliances,
            title=f"Verbrauch pro Appliance {start} bis {end}",
            labels={
                "timestamp": "Zeit",
                "value": "Leistung (kW)",
                "variable": "Appliance"
            }
        )

    fig.update_layout(transition_duration=300)
    return fig