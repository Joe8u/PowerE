# PowerE/conftest.py
# conftest.py  (place this at your repo root, alongside pytest.ini)
import sys
from pathlib import Path
import pytest

# 1) Make sure src/ is on PYTHONPATH so `import dashboard.app` works
root = Path(__file__).parent
src  = root / "src"
sys.path.insert(0, str(src))

# 2) Pre-import your Dash app so import_app("dashboard.app") will find it
import dashboard.app  # noqa: F401

# 3) Expose a fixture that just returns your real app
from dash.testing.application_runners import import_app

@pytest.fixture
def dash_app():
    # import_app("dashboard.app") returns the Dash() you defined in src/dashboard/app.py
    return import_app("dashboard.app")