#!/usr/bin/env bash

# 1) Ordner anlegen
mkdir -p \
  docker \
  config \
  data/raw/lastprofile/{2015,2024,2035,2050} \
  data/raw/survey \
  data/raw/market/spot_prices/{2015,2024,2035,2050} \
  data/raw/market/regelenergie/fcr/{2015,2024,2035,2050} \
  data/raw/market/regelenergie/afrr/{2015,2024,2035,2050} \
  data/raw/market/regelenergie/mfrR/{2015,2024,2035,2050} \
  data/processed/lastprofile \
  data/processed/survey/{full,cleaned,imputed,normalized,segments} \
  data/processed/market/spot_prices \
  data/processed/market/aggregated_regelleistung_costs \
  notebooks \
  src/preprocessing/lastprofile/{2015,2024,2035,2050} \
  src/preprocessing/survey \
  src/preprocessing/market/spot_prices \
  src/preprocessing/market/aggregated_regelleistung_costs \
  src/analysis \
  src/dashboard/assets \
  src/dashboard/components \
  src/dashboard/pages \
  src/utils/api \
  tests \
  scripts \
  docs/architecture \
  docs/survey \
  .github/workflows

# 2) Leere Platzhalterdateien anlegen
declare -a files=(
  .gitignore CHANGELOG.md CONTRIBUTING.md README.md LICENSE \
  pyproject.toml requirements.txt .env.example \
  docker/Dockerfile docker/docker-compose.yml \
  config/default.yaml config/logging.yaml config/years.yaml \
  data/raw/survey/survey.csv \
  src/__init__.py \
  src/preprocessing/__init__.py src/preprocessing/preprocess.py \
  src/preprocessing/lastprofile/preprocess_lastprofile.py \
  src/preprocessing/survey/preprocess_survey_full.py \
  src/preprocessing/survey/preprocess_survey_cleaned.py \
  src/preprocessing/survey/preprocess_survey_imputed.py \
  src/preprocessing/survey/preprocess_survey_normalize.py \
  src/preprocessing/survey/preprocess_survey_segments.py \
  src/preprocessing/market/spot_prices/preprocess_spot_prices.py \
  src/preprocessing/market/aggregated_regelleistung_costs/preprocess_regelleistung.py \
  src/analysis/__init__.py src/analysis/cost_saving.py \
  src/dashboard/__init__.py src/dashboard/app.py src/dashboard/layout.py src/dashboard/callbacks.py \
  src/dashboard/assets/custom.css src/dashboard/assets/logo.png \
  src/dashboard/components/__init__.py src/dashboard/components/slider.py \
  src/dashboard/pages/__init__.py src/dashboard/pages/summary.py src/dashboard/pages/details.py src/dashboard/pages/scenarios.py \
  src/utils/__init__.py src/utils/api/__init__.py \
  tests/__init__.py tests/test_placeholder.py \
  scripts/fetch_market_data.py \
  docs/architecture/.gitkeep docs/survey/.gitkeep \
  .github/workflows/ci.yml
)

for f in "${files[@]}"; do
  touch "$f"
done

# 3) Script ausführbar machen
chmod +x setup_structure.sh
