# PowerE/tests/conftest.py
import sys
from pathlib import Path

# Füge das 'src'-Verzeichnis zum Python-Pfad hinzu
# Dies geht davon aus, dass diese conftest.py Datei im Ordner 'PowerE/tests/' liegt.
# Path(__file__) ist der Pfad zu dieser conftest.py Datei.
# .resolve() macht den Pfad absolut.
# .parent ist der Ordner 'tests/'.
# .parent ist dann der Projekt-Root 'PowerE/'.
# Anschließend wird '/src' angehängt.
src_path = Path(__file__).resolve().parent.parent / "src"

if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
    print(f"Added to sys.path for testing: {src_path}") # Für Debugging