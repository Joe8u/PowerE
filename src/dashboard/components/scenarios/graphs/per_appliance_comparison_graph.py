# src/dashboard/components/scenarios/graphs/per_appliance_comparison_graph.py
from dash import dcc
import plotly.graph_objects as go
import pandas as pd
from typing import List, Optional

def per_appliance_comparison_graph_component():
    return dcc.Graph(id="per-appliance-comparison-graph")

def make_per_appliance_comparison_figure(
    df_load_original_disaggregated: pd.DataFrame, # Index=Timestamp, Spalten=Geräte (Original-Last)
    df_shiftable_per_appliance: Optional[pd.DataFrame], # Index=Timestamp, Spalten=Geräte (Reduktions-Last)
    df_payback_per_appliance: Optional[pd.DataFrame],   # Index=Timestamp, Spalten=Geräte (Payback-Last)
    appliances_to_plot: List[str] # Die Geräte, die tatsächlich geplottet werden sollen
) -> go.Figure:
    fig = go.Figure()

    # Farben-Management für Konsistenz zwischen Original und Simuliert
    # Plotly's Standardfarben oder definiere eigene
    colors = fig.layout.template.layout.colorway 
    color_idx = 0

    for dev in appliances_to_plot:
        if dev not in df_load_original_disaggregated.columns:
            continue

        original_load_dev = df_load_original_disaggregated[dev]

        # Standardmäßig ist das verschobene Profil gleich dem Original
        shifted_load_dev = original_load_dev.copy()

        if df_shiftable_per_appliance is not None and dev in df_shiftable_per_appliance.columns:
            # Stelle sicher, dass die Indizes übereinstimmen und fülle fehlende Werte mit 0
            reduction_dev = df_shiftable_per_appliance[dev].reindex(original_load_dev.index, fill_value=0.0)
            shifted_load_dev -= reduction_dev

        if df_payback_per_appliance is not None and dev in df_payback_per_appliance.columns:
            # Stelle sicher, dass die Indizes übereinstimmen und fülle fehlende Werte mit 0
            payback_dev = df_payback_per_appliance[dev].reindex(original_load_dev.index, fill_value=0.0)
            shifted_load_dev += payback_dev

        current_color = colors[color_idx % len(colors)]
        color_idx += 1

        fig.add_trace(go.Scatter(
            x=original_load_dev.index,
            y=original_load_dev,
            name=f"{dev} Original",
            mode='lines',
            line=dict(color=current_color)
        ))

        fig.add_trace(go.Scatter(
            x=shifted_load_dev.index,
            y=shifted_load_dev,
            name=f"{dev} Simuliert",
            mode='lines',
            line=dict(color=current_color, dash='dash') # Gleiche Farbe, anderer Stil
        ))

    fig.update_layout(
        title_text="Geräte-Lastprofile: Original vs. Simuliert nach DR",
        xaxis_title="Zeit",
        yaxis_title="Leistung (kW)",
        legend_title_text="Geräteprofile"
    )
    return fig