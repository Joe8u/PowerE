# src/dashboard/components/details/survey_graphs/shift_duration_all.py

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.stats import lognorm
from data_loader.survey_loader.nonuse_loader import load_question_9_nonuse

def calculate_shift_potential_data() -> dict:
    """
    Für jede Appliance:
      - Frage-9-Antworten in Stunden mappen.
      - Partizipationsrate berechnen (Anteil derer, die > 0h verschieben würden).
      - Für positive Dauern (D>0) eine Log-Normal-Verteilung anpassen (floc=0).
      - PDF über einen sinnvollen Bereich erstellen.
      - Erwartungswert E[D] und Median P50[D] für D>0 berechnen.
    Gibt ein Dictionary zurück, das die Plotly-Figur und ein Dictionary
    mit den berechneten Metriken pro Appliance enthält.
    """
    # 1) Daten laden und text → Stunden mappen
    df = load_question_9_nonuse()
    mapping = {
        "Nein, auf keinen Fall":           0.0,
        "Ja, aber maximal für 3 Stunden": 1.5,
        "Ja, für 3 bis 6 Stunden":        4.5,
        "Ja, für 6 bis 12 Stunden":       9.0,
        "Ja, für maximal 24 Stunden":    18.0,
        "Ja, für mehr als 24 Stunden":   30.0  # Annahme für ">24h"
    }
    appliances = [
        "Geschirrspüler",
        "Backofen und Herd",
        "Fernseher und Entertainment-Systeme",
        "Bürogeräte",
        "Waschmaschine",
    ]

    fig = go.Figure()
    appliance_metrics = {}

    for dev in appliances:
        # a) Rohwerte in Stunden, NaNs raus (repräsentiert alle gültigen Antworten)
        all_valid_responses = df[dev].map(mapping).dropna().astype(float)

        if all_valid_responses.empty:
            appliance_metrics[dev] = {
                "participation_rate": 0,
                "lognorm_shape": np.nan,
                "lognorm_loc": 0, # da floc=0
                "lognorm_scale": np.nan,
                "expected_duration_willing": np.nan,
                "median_duration_willing": np.nan
            }
            continue

        # b) Partizipationsrate berechnen
        # Anzahl derer, die bereit sind zu verschieben (Dauer > 0)
        willing_responses_count = (all_valid_responses > 0).sum()
        total_responses_count = len(all_valid_responses)
        participation_rate = willing_responses_count / total_responses_count if total_responses_count > 0 else 0

        # c) Nur positive Werte für lognorm-Fit
        positive_durations = all_valid_responses[all_valid_responses > 0]

        if positive_durations.empty:
            # Es gibt Antworten, aber keine positive Bereitschaft
            appliance_metrics[dev] = {
                "participation_rate": participation_rate, # wird 0 sein
                "lognorm_shape": np.nan,
                "lognorm_loc": 0,
                "lognorm_scale": np.nan,
                "expected_duration_willing": np.nan,
                "median_duration_willing": np.nan
            }
            # Optional: Man könnte eine Linie bei 0h für diese Geräte anzeigen,
            # aber für die Verteilungsanpassung ist hier Schluss.
            fig.add_trace(go.Scatter(
                x=[0], y=[0], # Platzhalter für Legende
                mode="lines",
                name=f"{dev} (Part.: {participation_rate:.0%}, keine pos. Dauer)"
            ))
            continue

        # d) Log-Normal anpassen (D>0)
        shape, loc, scale = lognorm.fit(positive_durations, floc=0) # loc wird 0 sein

        # e) x‐Raster + PDF
        x_max = positive_durations.max() * 1.3 # Etwas mehr Raum für Visualisierung
        if x_max == 0: x_max = 1 # Falls max doch 0 ist (sollte durch positive_durations.empty abgefangen sein)
        x = np.linspace(0.001, x_max, 300) # Start bei >0 für PDF
        pdf = lognorm.pdf(x, s=shape, loc=loc, scale=scale)

        # f) Erwartungswert und Median für D>0
        E_D_willing = lognorm.mean(s=shape, loc=loc, scale=scale)
        P50_D_willing = lognorm.median(s=shape, loc=loc, scale=scale)

        appliance_metrics[dev] = {
            "participation_rate": participation_rate,
            "lognorm_shape": shape,
            "lognorm_loc": loc,
            "lognorm_scale": scale,
            "expected_duration_willing": E_D_willing,
            "median_duration_willing": P50_D_willing
        }

        # g) Plotverteilung mit Hover-Info
        trace_color = fig.layout.template.layout.colorway[len(fig.data) % len(fig.layout.template.layout.colorway)]

        # Hover-Text definieren
        hover_text = (f"<b>{dev}</b><br>"
                      f"Partizipation: {participation_rate:.0%}<br>"
                      f"E[Max Dauer | D>0]: {E_D_willing:.1f}h<br>"
                      f"Median[Max Dauer | D>0]: {P50_D_willing:.1f}h<extra></extra>") # <extra></extra> entfernt zusätzliche Trace-Infos

        fig.add_trace(go.Scatter(
            x=x, y=pdf,
            mode="lines",
            name=f"{dev} (Part.: {participation_rate:.0%})", # Part. Rate bleibt in Legende sichtbar
            line=dict(color=trace_color),
            hovertemplate=hover_text  # *** HIER NEU: Hover-Text zugewiesen ***
        ))

        # h) Vertikale Linien OHNE Annotationen
        fig.add_vline(
            x=E_D_willing,
            line=dict(color=trace_color, dash="dash", width=1),
            # annotation_text=f"E: {E_D_willing:.1f}h", # *** DIESE ZEILE ENTFERNEN/AUSKOMMENTIEREN ***
            # annotation_position="top" # Kann auch entfernt werden
        )
        fig.add_vline(
            x=P50_D_willing,
            line=dict(color=trace_color, dash="dot", width=1),
            # annotation_text=f"P50: {P50_D_willing:.1f}h", # *** DIESE ZEILE ENTFERNEN/AUSKOMMENTIEREN ***
            # annotation_position="bottom" # Kann auch entfernt werden
        )

    fig.update_layout(
        title="Log-Normal-Verteilungen der max. Verschiebedauer (für D>0) und Partizipationsrate",
        xaxis_title="Maximale Verschiebedauer D (Stunden)",
        yaxis_title="Dichte der Wahrscheinlichkeitsverteilung (für D>0)",
        legend_title="Gerät (Partizipationsrate)",
        margin=dict(l=40, r=40, t=80, b=40) # Mehr Platz für längeren Titel
    )
    return {"figure": fig, "metrics": appliance_metrics}