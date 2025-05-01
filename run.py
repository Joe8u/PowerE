# run.py
import sys
import os

# Füge das src-Verzeichnis zum Python-Pfad hinzu
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from dashboard.app import app

if __name__ == "__main__":
    app.run(debug=True)