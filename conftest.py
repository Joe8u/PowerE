# conftest.py  (place in your repo root, alongside pytest.ini)

import sys
import os
from pathlib import Path

# 1) Make sure 'src' is on PYTHONPATH so that `import dashboard.app` works.
root = Path(__file__).parent
src  = root / "src"
sys.path.insert(0, src)
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

# 2) Pre‐import the Dash app module under its correct name
#    This ensures that sys.modules["dashboard.app"] exists
import dashboard.app  # noqa: F401