# src/dashboard/components/details/survey_graphs/participation_graphs.py

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_loader.survey_loader.incentive_loader import load_question_10_incentives

def get_participation_df() -> pd.DataFrame:
    df = load_question_10_incentives()
    devices = [
        "Geschirrspüler",
        "Backofen und Herd",
        "Fernseher und Entertainment-Systeme",
        "Bürogeräte",
        "Waschmaschine",
    ]
    rows = []
    for dev in devices:
        rows.append(
            df[["respondent_id", f"{dev}_choice", f"{dev}_pct"]]
              .rename(columns={f"{dev}_choice": "choice", f"{dev}_pct": "pct"})
              .assign(device=dev)
        )
    df_long = pd.concat(rows, ignore_index=True)
    df_long["pct"] = pd.to_numeric(df_long["pct"], errors="coerce").fillna(0)

    levels = sorted(df_long["pct"].unique())
    data = []
    for dev in devices:
        sub = df_long[df_long["device"] == dev]
        total = len(sub)
        for c in levels:
            accepted = (
                (sub["choice"] == "Ja, f")
                | ((sub["choice"] == "Ja, +") & (sub["pct"] <= c))
            )
            data.append({
                "device": dev,
                "comp_pct": c,
                "participation_pct": accepted.sum() / total * 100
            })
    return pd.DataFrame(data)

def make_participation_curve() -> go.Figure:
    df_curve = get_participation_df()
    fig = px.line(
        df_curve,
        x="comp_pct",
        y="participation_pct",
        color="device",
        markers=True,
        labels={
            "comp_pct": "Angebotene Kompensation (%)",
            "participation_pct": "Teilnahmequote (%)"
        },
        title="Teilnahmequote vs. Kompensationslevel pro Gerät"
    )
    fig.update_layout(margin=dict(l=40, r=40, t=60, b=40))
    return fig