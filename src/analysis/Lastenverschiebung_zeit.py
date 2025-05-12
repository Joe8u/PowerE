import pandas as pd
import os
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

# 1) Laden der Wide-CSV
HERE = os.path.dirname(__file__)                   # .../src/analysis
ROOT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))  # .../PowerE
csv_path = os.path.join(ROOT, "data", "processed", "survey", "question_9_nonuse_wide.csv")

df = pd.read_csv(csv_path, dtype=str)

# 2) Mapping Kategorien → Stunden
mapping = {
    "Nein, auf keinen Fall": 0,
    "Ja, aber maximal für 3 Stunden": 3,
    "Ja, für 3 bis 6 Stunden": 4.5,
    "Ja, für 6 bis 12 Stunden": 9,
    "Ja, für maximal 24 Stunden": 24,
    "Ja, für mehr als 24 Stunden": 30
}
appliances = ["Geschirrspüler",
              "Backofen und Herd",
              "Fernseher und Entertainment-Systeme",
              "Bürogeräte",
              "Waschmaschine"]

# 3) Numerische Serie pro Appliance erzeugen
numeric = {}
for dev in appliances:
    numeric[dev] = df[dev].map(mapping).dropna().astype(float)

# 4) Explorative Plots
for dev, series in numeric.items():
    plt.figure(figsize=(6,4))
    plt.hist(series, bins=10, density=True, alpha=0.5, label="Histogramm")
    series.plot.kde(label="KDE")
    plt.title(f"{dev}")
    plt.xlabel("Max Shift Duration (h)")
    plt.ylabel("Density")
    plt.legend()
    plt.show()

# 5) Verteilungen fitten + AIC vergleichen
def fit_and_aic(data, dist_name):
    dist = getattr(stats, dist_name)
    params = dist.fit(data, floc=0)
    loglik = np.sum(dist.logpdf(data, *params))
    k = len(params)
    return 2*k - 2*loglik  # AIC

dists = ["lognorm", "gamma", "weibull_min", "norm"]
aic_table = pd.DataFrame(index=appliances, columns=dists)

for dev in appliances:
    for d in dists:
        aic_table.loc[dev, d] = fit_and_aic(numeric[dev], d)

print("AIC-Vergleich pro Appliance:\n", aic_table)