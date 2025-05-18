import os

# Der RIS-Eintrag als mehrzeiliger String
# BITTE ERSETZEN SIE "[Ihr Zugriffsdatum hier einfügen]" mit dem tatsächlichen Datum
ris_entry = """TY  - RPRT
AU  - ENTSO-E
PY  - 2024
DA  - 2024/09/25
TI  - 2023 Annual Load-Frequency Control Report
PB  - ENTSO-E aisbl
CY  - Brussels
N1  - Authoring body: System Operations Committee. Corrected with editorial changes on October 14, 2024. Report date: September 25, 2024. Accessed on [Ihr Zugriffsdatum hier einfügen]
UR  - https://eepublicdownloads.entsoe.eu/clean-documents/SOC%20documents/LFC/ALFC_report_2023_Update_14102024.pdf
ER  -
"""

# Der von Ihnen gewünschte Speicherort (Verzeichnis)
desired_directory = "/Users/jonathan/Documents/GitHub/PowerE/src/data/referenz"

# Der gewünschte Dateiname mit .ris Endung
desired_filename = "entsoe_bericht.ris" # Geändert auf .ris

# Kombiniere Verzeichnis und Dateinamen zum vollständigen Pfad
file_path = os.path.join(desired_directory, desired_filename)

try:
    # Stelle sicher, dass das Verzeichnis existiert.
    os.makedirs(desired_directory, exist_ok=True)

    # Schreibe den RIS-Eintrag in die Datei
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(ris_entry)
    
    print(f"RIS-Datei erfolgreich erstellt unter: {file_path}")

except PermissionError:
    print(f"Fehler: Keine Schreibrechte für den Pfad {file_path}. Bitte überprüfen Sie die Berechtigungen.")
except Exception as e:
    print(f"Ein Fehler ist aufgetreten: {e}")