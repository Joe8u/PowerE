# src/utils/settings.py
import os
from dotenv import load_dotenv
import yaml

# 1) .env laden
load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))

# 2) Basispfade
DATA_RAW_DIR        = os.getenv("DATA_RAW_DIR")
DATA_PROC_STATIC    = os.getenv("DATA_PROC_STATIC")
DATA_PROC_DYNAMIC   = os.getenv("DATA_PROC_DYNAMIC")
DASH_HOST           = os.getenv("DASH_HOST", "127.0.0.1")
DASH_PORT           = int(os.getenv("DASH_PORT", 8050))
TZ                  = os.getenv("TZ", "Europe/Zurich")
ENTSOE_API_TOKEN    = os.getenv("ENTSOE_API_TOKEN")

# 3) YAML-Config (optional)
def load_config(env: str="default"):
    cfg_dir = os.path.join(os.getcwd(), "config")
    cfg_file = os.path.join(cfg_dir, f"{env}.yaml")
    with open(cfg_file) as f:
        return yaml.safe_load(f)

CONFIG = load_config(os.getenv("APP_ENV", "development"))