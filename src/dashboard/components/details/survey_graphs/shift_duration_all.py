# src/dashboard/components/details/survey_graphs/shift_duration_all.py

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.stats import lognorm
from data_loader.survey_loader.nonuse_loader import load_question_9_nonuse

def make_all_shift_distributions() -> go.Figure:
    """
    Für jede Appliance:
      - Frage-9-Antworten in Stunden mappen
      - Nur D>0 verwenden für Log-Normal-Fit (floc=0)
      - PDF über [0, max*1.2]
      - Erwartungswert E[D] berechnen
    Alle Verteilungen in einem gemeinsamen Plot, plus vertikale Linien bei E[D].
    """
    # 1) Daten laden und text → Stunden mappen
    df = load_question_9_nonuse()
    mapping = {
        "Nein, auf keinen Fall":           0.0,
        "Ja, aber maximal für 3 Stunden": 1.5,
        "Ja, für 3 bis 6 Stunden":        4.5,
        "Ja, für 6 bis 12 Stunden":       9.0,
        "Ja, für maximal 24 Stunden":    18.0,
        "Ja, für mehr als 24 Stunden":   30.0
    }
    appliances = [
        "Geschirrspüler",
        "Backofen und Herd",
        "Fernseher und Entertainment-Systeme",
        "Bürogeräte",
        "Waschmaschine",
    ]

    fig = go.Figure()

    for dev in appliances:
        # a) Rohwerte in Stunden, NaNs raus
        durations = df[dev].map(mapping).dropna().astype(float)

        # b) Nur positive Werte für lognorm-Fit
        pos = durations[durations > 0]
        if pos.empty:
            # keine positiven Daten => überspringen
            continue

        # c) Log-Normal anpassen (D>0)
        shape, loc, scale = lognorm.fit(pos, floc=0)

        # d) x‐Raster + PDF
        x_max = pos.max() * 1.2
        x = np.linspace(0, x_max, 300)
        pdf = lognorm.pdf(x, s=shape, loc=loc, scale=scale)

        # e) Erwartungswert
        E = lognorm.mean(s=shape, loc=loc, scale=scale)

        # f) Plotverteilung
        fig.add_trace(go.Scatter(
            x=x, y=pdf,
            mode="lines",
            name=dev
        ))
        # g) vertikale Linie bei E[D]
        fig.add_vline(
            x=E,
            line=dict(color=fig.data[-1].line.color, dash="dash"),
            annotation_text=f"E[{dev}]: {E:.1f} h",
            annotation_position="top right"
        )

    fig.update_layout(
        title="Log-Normal-Verteilungen der max. Verschiebedauer je Appliance",
        xaxis_title="Dauer D (h)",
        yaxis_title="Dichte",
        legend_title="Appliance",
        margin=dict(l=40, r=40, t=60, b=40)
    )
    return fig