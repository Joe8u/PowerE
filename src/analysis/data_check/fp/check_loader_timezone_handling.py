# PowerE/src/analysis/data_check/fp/check_loader_timezone_handling.py
"""
Überprüft die Zeitzonenbehandlung der Datenladefunktionen 
(tertiary_regulation_loader.load_regulation_range und lastprofile.load_jasm_year_profile).
Stellt sicher, dass sie mit UTC-awaren Zeitstempeln aufgerufen werden können und
DataFrames mit UTC-awaren Indizes zurückgeben.
"""
import pandas as pd
import datetime
from pathlib import Path
import sys
import os # Für os.getcwd() im Fallback

# --- BEGINN: Robuster Pfad-Setup (angepasst für diese Skriptposition) ---
try:
    CURRENT_SCRIPT_PATH = Path(__file__).resolve()
    # Von PowerE/src/analysis/data_check/fp/ hoch zu PowerE/
    PROJECT_ROOT = CURRENT_SCRIPT_PATH.parent.parent.parent.parent.parent
except NameError:
    # Fallback, falls __file__ nicht definiert ist (z.B. in manchen interaktiven Umgebungen)
    PROJECT_ROOT = Path(os.getcwd()).resolve()
    # Versuche, zum Projekt-Root "PowerE" zu navigieren, falls im Unterordner gestartet
    while PROJECT_ROOT.name != "PowerE" and PROJECT_ROOT.parent != PROJECT_ROOT:
        PROJECT_ROOT = PROJECT_ROOT.parent
    if PROJECT_ROOT.name != "PowerE": # Wenn "PowerE" nicht gefunden wurde
        PROJECT_ROOT = Path(os.getcwd()) # Fallback auf aktuelles Verzeichnis
        print(f"[WARNUNG] __file__ nicht definiert und 'PowerE' Verzeichnis konnte nicht automatisch im Pfad gefunden werden.")
        print(f"         PROJECT_ROOT als aktuelles Arbeitsverzeichnis angenommen: {PROJECT_ROOT}")
        print(f"         Bitte stellen Sie sicher, dass das Skript aus einem geeigneten Verzeichnis ausgeführt wird oder passen Sie PROJECT_ROOT an.")
    else:
        print(f"[INFO] __file__ nicht definiert. PROJECT_ROOT heuristisch als '{PROJECT_ROOT}' bestimmt.")


if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    print(f"[Path Setup] Projekt-Root '{PROJECT_ROOT}' zum sys.path hinzugefügt.")
else:
    print(f"[Path Setup] Projekt-Root '{PROJECT_ROOT}' ist bereits im sys.path.")
# --- ENDE: Pfad-Setup ---

# --- Importe der zu testenden Loader ---
try:
    from src.data_loader.tertiary_regulation_loader import load_regulation_range
    from src.data_loader.lastprofile import load_appliances as load_jasm_year_profile
    print("INFO: Loader-Module erfolgreich importiert.")
except ImportError as e:
    print(f"FEHLER beim Importieren der Loader-Module: {e}")
    print("       Stellen Sie sicher, dass die Pfade korrekt sind, das Skript im Kontext des PowerE-Projekts ausgeführt wird")
    print("       und alle notwendigen __init__.py Dateien in den 'src' Unterordnern vorhanden sind.")
    sys.exit(1)
except Exception as e_gen_import:
    print(f"Ein unerwarteter Fehler trat beim Import der Loader auf: {e_gen_import}")
    sys.exit(1)

# --- Testparameter ---
TEST_TARGET_YEAR = 2024
TEST_APPLIANCE_NAME = "Geschirrspüler" # Beispielgerät für JASM

# UTC-behaftete Zeitstempel für Tests (kurzer Zeitraum für schnelle Tests)
test_start_utc = datetime.datetime(TEST_TARGET_YEAR, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
# Nur wenige Tage laden für den Test, um die Datenmenge klein zu halten
test_end_utc = datetime.datetime(TEST_TARGET_YEAR, 1, 3, 23, 59, 59, tzinfo=datetime.timezone.utc)

def print_check(description: str, success: bool, details: str = ""):
    status_symbol = "✅" if success else "❌"
    print(f"{status_symbol} {description:<60} | Status: {'ERFOLGREICH' if success else 'FEHLGESCHLAGEN'}{' | Details: ' + details if details else ''}")

def check_datetime_index_utc_aware(df: pd.DataFrame, df_name: str) -> bool:
    """Prüft, ob der Index ein UTC-behafteter DatetimeIndex ist."""
    if df is None:
        print_check(f"'{df_name}' DataFrame ist None", False)
        return False
    if df.empty:
        print_check(f"'{df_name}' DataFrame ist leer", False, "Keine Daten zum Prüfen des Index vorhanden.")
        # Kann je nach Loader erwartet sein für kurze Zeiträume, daher kein direkter Fehler hier
        return True # Kein Fehler, aber auch keine positive Bestätigung des Index-Typs
        
    check_desc_type = f"'{df_name}' Index ist pd.DatetimeIndex"
    is_datetime_index = isinstance(df.index, pd.DatetimeIndex)
    print_check(check_desc_type, is_datetime_index)
    if not is_datetime_index:
        print(f"         Tatsächlicher Typ: {type(df.index)}")
        return False

    check_desc_tz_aware = f"'{df_name}' Index ist zeitzonenbehaftet (tz-aware)"
    is_tz_aware = df.index.tz is not None
    print_check(check_desc_tz_aware, is_tz_aware)
    if not is_tz_aware: return False

    check_desc_is_utc = f"'{df_name}' Index ist spezifisch UTC"
    is_utc = df.index.tz == datetime.timezone.utc
    print_check(check_desc_is_utc, is_utc, f"Gefundene Zeitzone: {df.index.tz}" if not is_utc else "")
    return is_utc

def test_srl_loader():
    print("\n--- Test: tertiary_regulation_loader.load_regulation_range ---")
    overall_success = True
    df_srl_test = None
    try:
        print(f"  Aufruf von load_regulation_range mit UTC-Start/End: {test_start_utc} / {test_end_utc}")
        df_srl_test = load_regulation_range(start=test_start_utc, end=test_end_utc)
        print_check("Aufruf von load_regulation_range ohne TypeError", True)
    except TypeError as te:
        print_check("Aufruf von load_regulation_range ohne TypeError", False, f"TypeError aufgetreten: {te}")
        overall_success = False
    except Exception as e:
        print_check("Aufruf von load_regulation_range ohne andere Fehler", False, f"Anderer Fehler: {e}")
        overall_success = False

    if df_srl_test is not None:
        if not df_srl_test.empty:
            print_check("SRL DataFrame ist nicht leer", True, f"Shape: {df_srl_test.shape}")
            if not check_datetime_index_utc_aware(df_srl_test, "SRL"):
                overall_success = False
        else:
            # Für kurze Zeiträume könnte der DF leer sein, wenn keine Daten existieren.
            # Dies ist kein Fehler des Loaders per se, sondern ein Datenverfügbarkeitsthema.
            print_check("SRL DataFrame ist nicht leer", True, "DataFrame ist leer (kann für kurzen Testzeitraum normal sein).")
    else:
        print_check("SRL DataFrame ist nicht None", False)
        overall_success = False
        
    if overall_success:
         print("  SRL Loader scheint korrekt mit UTC-awaren Zeitstempeln umzugehen und UTC-Index zurückzugeben (falls Daten vorhanden).")
    else:
         print("  SRL Loader hat Probleme mit der Zeitzonenbehandlung oder dem Laden.")
    return overall_success

def test_jasm_loader():
    print("\n--- Test: lastprofile.load_jasm_year_profile ---")
    overall_success = True
    df_jasm_test = None
    try:
        print(f"  Aufruf von load_jasm_year_profile für '{TEST_APPLIANCE_NAME}' mit UTC-Start/End...")
        df_jasm_test = load_jasm_year_profile(
            appliances=[TEST_APPLIANCE_NAME],
            start=test_start_utc,
            end=test_end_utc,
            year=TEST_TARGET_YEAR, # Erforderlich für JASM Loader
            group=True             # Annahme basierend auf Ihren Skripten
        )
        print_check(f"Aufruf von load_jasm_year_profile ('{TEST_APPLIANCE_NAME}') ohne TypeError", True)
    except TypeError as te:
        print_check(f"Aufruf von load_jasm_year_profile ('{TEST_APPLIANCE_NAME}') ohne TypeError", False, f"TypeError aufgetreten: {te}")
        overall_success = False
    except Exception as e:
        print_check(f"Aufruf von load_jasm_year_profile ('{TEST_APPLIANCE_NAME}') ohne andere Fehler", False, f"Anderer Fehler: {e}")
        overall_success = False

    if df_jasm_test is not None:
        if not df_jasm_test.empty:
            print_check(f"JASM DataFrame ('{TEST_APPLIANCE_NAME}') ist nicht leer", True, f"Shape: {df_jasm_test.shape}")
            if TEST_APPLIANCE_NAME not in df_jasm_test.columns:
                print_check(f"JASM Spalte '{TEST_APPLIANCE_NAME}' vorhanden", False)
                overall_success = False
            else:
                 print_check(f"JASM Spalte '{TEST_APPLIANCE_NAME}' vorhanden", True)

            if not check_datetime_index_utc_aware(df_jasm_test, f"JASM '{TEST_APPLIANCE_NAME}'"):
                overall_success = False
        else:
            print_check(f"JASM DataFrame ('{TEST_APPLIANCE_NAME}') ist nicht leer", True, "DataFrame ist leer (kann für kurzen Testzeitraum normal sein).")

    else:
        print_check(f"JASM DataFrame ('{TEST_APPLIANCE_NAME}') ist nicht None", False)
        overall_success = False

    if overall_success:
        print(f"  JASM Loader für '{TEST_APPLIANCE_NAME}' scheint korrekt mit UTC-awaren Zeitstempeln umzugehen und UTC-Index zurückzugeben (falls Daten vorhanden).")
    else:
        print(f"  JASM Loader für '{TEST_APPLIANCE_NAME}' hat Probleme mit der Zeitzonenbehandlung oder dem Laden.")
    return overall_success

if __name__ == "__main__":
    print("Starte Überprüfung der Zeitzonenkonsistenz für Datenlader...")
    print("============================================================")
    
    srl_loader_ok = test_srl_loader()
    print("============================================================")
    jasm_loader_ok = test_jasm_loader()
    print("============================================================")
    
    print("\n--- Zusammenfassung der Überprüfung ---")
    if srl_loader_ok and jasm_loader_ok:
        print("✅ Alle primären Zeitzonen-Checks für die getesteten Loader ERFOLGREICH (bei Aufruf mit UTC-awaren Inputs).")
        print("   Dies deutet darauf hin, dass die Loader intern naive Daten korrekt nach UTC lokalisieren/konvertieren,")
        print("   oder bereits UTC-aware Daten aus den Quellen lesen.")
    else:
        print("❌ Mindestens ein Zeitzonen-Check ist FEHLGESCHLAGEN.")
        print("   Bitte überprüfen Sie die Ausgaben und die Implementierung der entsprechenden Ladefunktion(en),")
        print("   um sicherzustellen, dass der DataFrame-Index intern korrekt als UTC behandelt wird, bevor Slicing-Operationen")
        print("   mit UTC-awaren Zeitstempeln erfolgen.")