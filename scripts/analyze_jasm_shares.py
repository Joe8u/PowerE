# PowerE/scripts/analyze_jasm_shares.py

import pandas as pd
import plotly.express as px
from pathlib import Path
import sys
import os # Importiere os für den Pfad-Setup

# --- BEGINN: Robuster Pfad-Setup für Standalone-Ausführung ---
try:
    CURRENT_SCRIPT_PATH = Path(__file__).resolve()
    # Annahme: Dieses Skript liegt in PowerE/scripts/
    # Projekt-Root ist eine Ebene höher
    PROJECT_ROOT = CURRENT_SCRIPT_PATH.parent.parent 
except NameError:
    # Fallback, falls __file__ nicht definiert ist (sollte bei Skriptausführung nicht passieren)
    PROJECT_ROOT = Path(os.getcwd()).resolve() 
    print(f"[WARNUNG] __file__ nicht definiert. PROJECT_ROOT als aktuelles Arbeitsverzeichnis angenommen: {PROJECT_ROOT}")
    # Wenn du das Skript nicht vom PowerE-Ordner aus startest, musst du PROJECT_ROOT ggf. manuell setzen
    # Beispiel: PROJECT_ROOT = Path("/Users/jonathan/Documents/GitHub/PowerE").resolve()


if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    print(f"[Path Setup] Projekt-Root '{PROJECT_ROOT}' zum sys.path hinzugefügt.")
else:
    print(f"[Path Setup] Projekt-Root '{PROJECT_ROOT}' ist bereits im sys.path.")
# --- ENDE: Robuster Pfad-Setup ---

# Importiere deine Ladefunktion aus src
try:
    from src.data_loader.lastprofile import load_month 
except ImportError as e:
    print(f"FEHLER beim Importieren von load_month aus src.data_loader.lastprofile: {e}")
    print("Stelle sicher, dass der PROJECT_ROOT korrekt ist und __init__.py Dateien vorhanden sind.")
    sys.exit(1) # Beende das Skript, wenn der Import fehlschlägt

def calculate_and_plot_appliance_shares_from_jasm(year: int = 2024, output_dir: Path = None):
    """
    Lädt JASM-Daten für ein gegebenes Jahr, berechnet die Energieanteile der
    vordefinierten Gerätegruppen und erstellt ein Tortendiagramm.
    """
    print(f"\nStarte Analyse der JASM-Energieanteile für das Jahr {year}...")

    # --- 1. Jahresdaten für deine 5 Gruppen laden ---
    # Das group_map in src.data_loader.lastprofile.load_month muss korrekt sein!
    print(f"Lade JASM-Lastprofildaten für {year} (gruppiert)...")
    all_months_data_grouped = []
    try:
        for month_num in range(1, 13):
            df_month = load_month(year=year, month=month_num, group=True) 
            all_months_data_grouped.append(df_month)
        
        df_yearly_survey_groups = pd.concat(all_months_data_grouped)
        print(f"Jahresdaten für {year} geladen. Shape: {df_yearly_survey_groups.shape}")
        if df_yearly_survey_groups.empty:
            print(f"FEHLER: Keine Daten für das Jahr {year} geladen. Überprüfe die Quelldateien und das group_map in lastprofile.py.")
            return
        print("Geladene Spalten (Gerätegruppen): ", df_yearly_survey_groups.columns.tolist())

    except FileNotFoundError as e:
        print(f"\nFEHLER: Mindestens eine Monatsdatei für {year} konnte nicht gefunden werden.")
        print("Stelle sicher, dass das Skript 'src/preprocessing/lastprofile/{year}/precompute_lastprofile_{year}.py' erfolgreich gelaufen ist.")
        print(f"Details: {e}")
        return
    except KeyError as e:
        print(f"\nFEHLER: Eine erwartete Spalte (Gerätegruppe) wurde in den geladenen Daten nicht gefunden.")
        print("Überprüfe das `group_map` in `src.data_loader.lastprofile.py` und die Spaltennamen in deinen Monats-CSVs.")
        print(f"Details: {e}")
        return
    except Exception as e:
        print(f"\nEin unerwarteter Fehler beim Laden der Monatsdaten ist aufgetreten: {e}")
        return

    # --- 2. Jährlichen Energieverbrauch pro Gruppe berechnen ---
    interval_duration_h = 0.25 # 15-Minuten-Intervalle
    df_energy_kwh = df_yearly_survey_groups * interval_duration_h
    yearly_energy_kwh_per_group = df_energy_kwh.sum()
    
    print(f"\nJährlicher Energieverbrauch pro Gerätegruppe (kWh) in {year}:")
    print(yearly_energy_kwh_per_group.round(0))

    # --- 3. Gesamtenergieverbrauch dieser Gruppen berechnen ---
    total_yearly_energy_selected_groups_kwh = yearly_energy_kwh_per_group.sum()
    if total_yearly_energy_selected_groups_kwh == 0:
        print("FEHLER: Gesamtenergieverbrauch der ausgewählten Gruppen ist 0. Anteile können nicht berechnet werden.")
        return
        
    print(f"\nGesamter jährlicher Energieverbrauch der ausgewählten Gruppen: {total_yearly_energy_selected_groups_kwh:,.0f} kWh")

    # --- 4. Prozentuale Anteile berechnen ---
    percentage_share_per_group = (yearly_energy_kwh_per_group / total_yearly_energy_selected_groups_kwh) * 100
    print("\nProzentualer Anteil am Gesamtenergieverbrauch dieser Gruppen (%):")
    print(percentage_share_per_group.round(1))

   # --- 5. Tortendiagramm erstellen und speichern/anzeigen ---
    df_pie_data = percentage_share_per_group.reset_index()
    df_pie_data.columns = ['Gerätegruppe', 'Prozentualer Anteil']

    # +++ BEGINN NEUER CODE FÜR LABEL-ANPASSUNG +++
    # Ersetze den langen Namen durch einen mit Zeilenumbruch
    # Du kannst dies für alle langen Namen tun oder nur für spezifische
    long_name = "Fernseher und Entertainment-Systeme"
    short_name_with_break = "Fernseher und<br>Entertainment-Systeme" 
    # Oder eine allgemeinere Logik, um nach einer bestimmten Wortanzahl umzubrechen:
    # def add_line_breaks(label, words_per_line=2):
    #     words = label.split()
    #     new_label_parts = []
    #     for i in range(0, len(words), words_per_line):
    #         new_label_parts.append(" ".join(words[i:i+words_per_line]))
    #     return "<br>".join(new_label_parts)
    #
    # df_pie_data['Gerätegruppe_Angepasst'] = df_pie_data['Gerätegruppe'].apply(lambda x: add_line_breaks(x, 2) if len(x.split()) > 3 else x)


    # Spezifische Ersetzung für das lange Label:
    df_pie_data['Gerätegruppe_Angepasst'] = df_pie_data['Gerätegruppe'].replace(
        {long_name: short_name_with_break}
    )
    # +++ ENDE NEUER CODE FÜR LABEL-ANPASSUNG +++

    fig_energy_shares_pie = px.pie(df_pie_data, 
                                   values='Prozentualer Anteil', 
                                   names='Gerätegruppe_Angepasst', # Deine Spalte mit ggf. <br> Tags
                                   title=f'Anteile der Gerätegruppen am gemeinsamen Jahresenergieverbrauch ({year}, Basis: JASM)',
                                   hole=0.3) 
    
    fig_energy_shares_pie.update_traces(
        textposition='inside', 
        textinfo='percent',  # GEÄNDERT: Nur 'percent' anzeigen (statt 'percent+label')
        hoverinfo='label+percent+value', # Beim Hovern weiterhin alles anzeigen
        textfont_size=19  # Ggf. die Schriftgröße der Prozente anpassen, damit sie gut sichtbar sind
    )
    
    fig_energy_shares_pie.update_layout(
        title_font_size=19,      
        legend_title_text='Gerätegruppen',
        legend_title_font_size=14, 
        legend_font_size=19,       # Stelle sicher, dass die Legende gut lesbar ist
        uniformtext_minsize=12, # Sorgt dafür, dass Text nicht zu klein wird
        uniformtext_mode='hide'   # Versteckt Text, wenn er nicht passt (statt ihn zu überlappen)
    )
    
    if output_dir:
        # ... (HTML speichern bleibt gut für Interaktivität) ...
        plot_path_html = output_dir / f"jasm_anteile_geraetegruppen_{year}.html"
        fig_energy_shares_pie.write_html(plot_path_html)
        print(f"\nTortendiagramm HTML gespeichert unter: {plot_path_html}")

        # NEU: Als PNG mit höherer Auflösung/Skalierung speichern
        plot_path_png = output_dir / f"jasm_anteile_geraetegruppen_{year}.png"
        try:
            fig_energy_shares_pie.write_image(plot_path_png, scale=3, width=800, height=600) # Experimentiere mit scale, width, height
            print(f"Tortendiagramm als PNG gespeichert unter: {plot_path_png}")
        except Exception as img_e:
            print(f"Konnte PNG nicht speichern (kaleido installiert und im Pfad?): {img_e}")

        # Optional: Als SVG (vektorbasiert, ideal für LaTeX, skaliert perfekt)
        # plot_path_svg = output_dir / f"jasm_anteile_geraetegruppen_{year}.svg"
        # try:
        #     fig_energy_shares_pie.write_image(plot_path_svg, width=800, height=600)
        #     print(f"Tortendiagramm als SVG gespeichert unter: {plot_path_svg}")
        # except Exception as img_e:
        #     print(f"Konnte SVG nicht speichern: {img_e}")
    else:
        fig_energy_shares_pie.show

if __name__ == '__main__':
    # Definiere, wohin die Plots gespeichert werden sollen
    # Passt zum output_dir_f1_v2 aus deinem Notebook
    output_directory_for_plots = PROJECT_ROOT / "scripts" / "F1_Analyse_Kompensationsforderungen" / "outputs_f1_v2"
    calculate_and_plot_appliance_shares_from_jasm(year=2024, output_dir=output_directory_for_plots)
    
    print("\n--- Analyse der JASM-Energieanteile beendet ---")