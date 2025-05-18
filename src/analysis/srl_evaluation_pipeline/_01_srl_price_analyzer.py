# PowerE/src/analysis/srl_evaluation_pipeline/_01_srl_price_analyzer.py
import pandas as pd
import datetime
from pathlib import Path
# Importiere den Loader relativ zum src-Verzeichnis, da PROJECT_ROOT/src im sys.path ist
from data_loader.tertiary_regulation_loader import load_regulation_range

def convert_mwh_to_kwh_price(price_mwh):
    return price_mwh / 1000.0

def analyze_srl_prices(target_year_srl: int, n_top_periods: int, project_root_path: Path):
    """
    Lädt SRL-Preisdaten, identifiziert die N teuersten Perioden und gibt sie zurück.
    """
    print(f"Lade SRL-Preisdaten für {target_year_srl}...")
    srl_start_date = datetime.datetime(target_year_srl, 1, 1)
    srl_end_date = datetime.datetime(target_year_srl, 12, 31, 23, 59, 59)
    try:
        # Der tertiary_regulation_loader erwartet keine project_root_path, da er BASE_DIR intern definiert.
        # Dies könnte angepasst werden für mehr Konsistenz, aber für jetzt belassen wir es.
        df_srl = load_regulation_range(start=srl_start_date, end=srl_end_date)
        if df_srl.empty:
            print(f"FEHLER: Keine SRL-Daten für {target_year_srl} geladen.")
            return None
        if 'avg_price_eur_mwh' in df_srl.columns:
            df_srl['price_chf_kwh'] = convert_mwh_to_kwh_price(df_srl['avg_price_eur_mwh'])
            print("SRL-Preise geladen und zu CHF/kWh konvertiert (Annahme EUR=CHF).")
        else:
            print("FEHLER: Spalte 'avg_price_eur_mwh' nicht in SRL-Daten gefunden.")
            return None
    except Exception as e:
        print(f"FEHLER beim Laden oder Verarbeiten der SRL-Daten: {e}")
        return None

    if df_srl.empty or 'price_chf_kwh' not in df_srl.columns:
        print("Keine gültigen SRL-Preisdaten für die Identifikation von Spitzenpreisen.")
        return None
        
    df_top_srl_periods = df_srl.nlargest(n_top_periods, 'price_chf_kwh').copy()
    if df_top_srl_periods.empty:
        print(f"FEHLER: Konnte keine Top {n_top_periods} Spitzenpreisperioden identifizieren.")
        return None
        
    df_top_srl_periods['weekday'] = df_top_srl_periods.index.day_name()
    df_top_srl_periods['hour'] = df_top_srl_periods.index.hour
    print(f"\nDie {n_top_periods} teuersten SRL-Perioden im Jahr {target_year_srl} (Auszug):")
    print(df_top_srl_periods[['price_chf_kwh', 'weekday', 'hour']].head().to_string())
    
    avg_price_top_periods = df_top_srl_periods['price_chf_kwh'].mean()
    
    return {
        'df_top_srl_periods': df_top_srl_periods,
        'avg_price_top_periods': avg_price_top_periods
    }

if __name__ == '__main__':
    # Testaufruf
    # Um dies standalone zu testen, muss der PROJECT_ROOT für die Loader korrekt sein.
    # Der Loader tertiary_regulation_loader.py verwendet einen relativen Pfad von seinem eigenen Speicherort.
    # Daher ist hier keine explizite project_root_path Übergabe nötig, wenn der Loader so bleibt.
    print("Testlauf für _01_srl_price_analyzer.py")
    # Bestimme PROJECT_ROOT für den Test, falls Loader ihn doch benötigen würden
    # oder wenn die Daten relativ zum Projekt-Root abgelegt sind.
    test_project_root = Path(__file__).resolve().parent.parent.parent.parent
    
    results = analyze_srl_prices(target_year_srl=2024, n_top_periods=24, project_root_path=test_project_root)
    if results:
        print(f"\nDurchschnittspreis der Top-Perioden: {results['avg_price_top_periods']:.4f} CHF/kWh")
        print("\nTop-Perioden DataFrame (erste 5):")
        print(results['df_top_srl_periods'].head())
