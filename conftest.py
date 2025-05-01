# conftest.py  (place in your repo root, alongside pytest.ini)

import sys
import os
from pathlib import Path

# 1) Make sure 'src' is on PYTHONPATH so that `import dashboard.app` works.
ROOT = Path(__file__).parent
SRC  = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 2) Pre‐import the Dash app module under its correct name
#    This ensures that sys.modules["dashboard.app"] exists
import dashboard.app  # noqa: F401