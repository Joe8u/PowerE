from pathlib import Path
from dotenv import load_dotenv
import os

# Pfad zur Projekt-Root und zur .env-Datei
ROOT = Path(__file__).parent.parent.parent
load_dotenv(ROOT / ".env")

# Umgebungsvariablen
APP_ENV = os.getenv("APP_ENV", "production")
DATA_RAW_DIR = Path(os.getenv("DATA_RAW_DIR", "./data/raw"))
DATA_PROCESSED_STATIC = Path(os.getenv("DATA_PROCESSED_STATIC", "./data/processed/static"))
DATA_PROCESSED_DYNAMIC = Path(os.getenv("DATA_PROCESSED_DYNAMIC", "./data/processed/dynamic"))
DASH_HOST = os.getenv("DASH_HOST", "127.0.0.1")
DASH_PORT = int(os.getenv("DASH_PORT", 8050))
TZ = os.getenv("TZ", "Europe/Zurich")

# API Token (z.B. ENTSOE)
ENTSOE_API_TOKEN = os.getenv("ENTSOE_API_TOKEN")