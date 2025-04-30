# run.py
import sys
# Damit Python unsere src/-Module findet:
sys.path.append('src')

from dashboard.app import app

if __name__ == '__main__':
    # im Debug-Modus, öffnet localhost:8050
    app.run_server(debug=True)