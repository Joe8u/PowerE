# PowerE/conftest.py
# conftest.py  (place this at your repo root, alongside pytest.ini)
import sys
from pathlib import Path
import pytest

# ----------------------
# 1) Monkey-patch FirefoxOptions to drop unsupported capabilities
from selenium.webdriver.firefox.options import Options as FirefoxOptions
# backup original
_orig_set_capability = FirefoxOptions.set_capability

def _patched_set_capability(self, name, value):
    # ignore legacy or unsupported capabilities
    if name in ("loggingPrefs", "goog:loggingPrefs", "marionette"):
        return
    # forward all others
    return _orig_set_capability(self, name, value)

# apply patch
FirefoxOptions.set_capability = _patched_set_capability
# ----------------------

# 2) Make sure src/ is on PYTHONPATH so `import dashboard.app` works
root = Path(__file__).parent
src  = root / "src"
sys.path.insert(0, str(src))

# 3) Pre-import your Dash app so import_app("dashboard.app") will find it
import dashboard.app  # noqa: F401

# 4) Expose a fixture that just returns your real app
from dash.testing.application_runners import import_app

@pytest.fixture
def dash_app():
    # import_app("dashboard.app") returns the Dash() you defined in src/dashboard/app.py
    return import_app("dashboard.app")
