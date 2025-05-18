# PowerE/src/analysis/srl_evaluation_pipeline/_04_vpp_flex_quantifier.py
import pandas as pd
import numpy as np
from pathlib import Path
import datetime
import sys
# Importiere den Loader relativ zum src-Verzeichnis
from data_loader.lastprofile import load_appliances as load_jasm_profiles

def quantify_vpp_flexibility_at_peaks(
    df_top_srl_periods: pd.DataFrame, # DataFrame mit den Zeitstempeln und Preisen der Spitzen-SRL-Perioden
    target_year_jasm: int,
    appliance_name: str,
    r_participation_peak: float, # Teilnahmequote
    jasm_power_unit_is_mw: bool,
    project_root_path: Path # Wird an load_jasm_profiles weitergegeben
):
    """
    Quantifiziert die VPP-Flexibilitätsleistung während der identifizierten Spitzen-SRL-Perioden
    durch Abgleich mit den JASM-Lastprofildaten.
    """
    print(f"Lade JASM-Lastprofildaten für '{appliance_name}' für das Jahr {target_year_jasm}...")
    jasm_start_date = datetime.datetime(target_year_jasm, 1, 1)
    jasm_end_date = datetime.datetime(target_year_jasm, 12, 31, 23, 59, 59)
    try:
        # load_jasm_profiles (alias für load_appliances) erwartet project_root_path nicht direkt,
        # da es BASE_DIR intern definiert. Dies könnte für Konsistenz angepasst werden.
        # Für jetzt gehen wir davon aus, dass es funktioniert, da PROJECT_ROOT/src im sys.path ist.
        df_jasm_all_year = load_jasm_profiles(
            appliances=[appliance_name], 
            start=jasm_start_date,
            end=jasm_end_date,
            year=target_year_jasm,
            group=True # Annahme: group=True ist für den Appliance-Namen korrekt
        )
        if df_jasm_all_year.empty or appliance_name not in df_jasm_all_year.columns:
            print(f"FEHLER: Keine JASM-Daten für '{appliance_name}' im Jahr {target_year_jasm} geladen.")
            return None
        P_JASM_total_CH_appliance_series = df_jasm_all_year[appliance_name]
        print(f"JASM-Daten für {appliance_name} ({target_year_jasm}) geladen. Durchschnittliche Last: {P_JASM_total_CH_appliance_series.mean():.2f} {'MW' if jasm_power_unit_is_mw else 'kW/W'}")
    except Exception as e:
        print(f"FEHLER beim Laden der JASM-Jahresdaten: {e}")
        return None

    # Stelle sicher, dass Indizes DatetimeIndex sind
    if not isinstance(df_top_srl_periods.index, pd.DatetimeIndex):
        df_top_srl_periods.index = pd.to_datetime(df_top_srl_periods.index)
    if not isinstance(P_JASM_total_CH_appliance_series.index, pd.DatetimeIndex):
        P_JASM_total_CH_appliance_series.index = pd.to_datetime(P_JASM_total_CH_appliance_series.index)

    # Normalisiere die Zeitstempel der Top-SRL-Perioden auf das JASM-Jahr
    df_top_srl_periods_timestamps_normalized = df_top_srl_periods.index.map(
        lambda ts: ts.replace(year=target_year_jasm) 
    )
    
    # Hole die JASM-Last und die SRL-Preise für diese exakten normalisierten Zeitpunkte
    # Annahme: TIME_RESOLUTION_JASM_MINUTES ist global oder wird übergeben (hier hartkodiert für 15min)
    time_resolution_jasm_minutes = 15 
    relevant_jasm_load_series = P_JASM_total_CH_appliance_series.reindex(
        df_top_srl_periods_timestamps_normalized, 
        method='nearest', 
        tolerance=pd.Timedelta(f'{time_resolution_jasm_minutes}min')
    )
    
    # Erstelle den DataFrame für die Analyse der Spitzenperioden
    df_analysis_peaks = pd.DataFrame({
        'srl_original_timestamp': df_top_srl_periods.index,
        'srl_price_chf_kwh': df_top_srl_periods['price_chf_kwh'].values, # Nimm die Preise aus dem übergebenen df
        'jasm_normalized_timestamp': df_top_srl_periods_timestamps_normalized,
        'jasm_load_mw_or_kw': relevant_jasm_load_series.values 
    })
    df_analysis_peaks.dropna(subset=['jasm_load_mw_or_kw'], inplace=True)

    if df_analysis_peaks.empty:
        print("WARNUNG: Konnte keine übereinstimmenden JASM-Lastdaten für die Top-SRL-Perioden finden.")
        return {'df_analysis_peaks': df_analysis_peaks, 'avg_vpp_flex_kw': 0.0}
    
    # Berechne VPP-Flexibilität
    conversion_factor = 1000.0 if jasm_power_unit_is_mw else 1.0
    df_analysis_peaks['vpp_flex_kw'] = df_analysis_peaks['jasm_load_mw_or_kw'] * conversion_factor * r_participation_peak
    
    avg_vpp_flex_kw = df_analysis_peaks['vpp_flex_kw'].mean()
    
    return {
        'df_analysis_peaks': df_analysis_peaks, # Enthält jetzt srl_price, jasm_load, vpp_flex_kw
        'avg_vpp_flex_kw': avg_vpp_flex_kw
    }

if __name__ == '__main__':
    print("Testlauf für _04_vpp_flex_quantifier.py")
    # Dieser Test erfordert Mock-DataFrames oder das Ausführen der vorherigen Schritte
    # Erstelle Dummy df_top_srl_periods für den Test
    test_timestamps = pd.to_datetime([
        '2024-01-19 07:00:00', '2024-01-19 07:15:00', 
        '2024-07-15 18:00:00', '2024-07-15 18:15:00'
    ])
    dummy_top_srl = pd.DataFrame({
        'price_chf_kwh': [0.8, 0.75, 0.9, 0.85]
    }, index=test_timestamps)

    # Bestimme PROJECT_ROOT für den Test
    test_project_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(test_project_root / "src") not in sys.path: # Sicherstellen, dass src im Pfad ist
        sys.path.insert(0, str(test_project_root / "src"))
    try:
        # Erneuter Importversuch für den Fall, dass das Skript standalone ausgeführt wird
        from data_loader.lastprofile import load_appliances as load_jasm_profiles_test

        results = quantify_vpp_flexibility_at_peaks(
            df_top_srl_periods=dummy_top_srl,
            target_year_jasm=2024,
            appliance_name="Geschirrspüler", # Muss mit group_map in lastprofile.py übereinstimmen
            r_participation_peak=0.7246, # Beispielwert
            jasm_power_unit_is_mw=True,
            project_root_path=test_project_root
        )
        if results and not results['df_analysis_peaks'].empty:
            print("\nAnalyse der Spitzen-Perioden (Test):")
            print(results['df_analysis_peaks'].head())
            print(f"Durchschnittliche VPP-Flexibilität (Test): {results['avg_vpp_flex_kw']:.2f} kW")
        elif results:
             print("Testlauf für VPP Flex Quantifier ergab leeren df_analysis_peaks.")
        else:
            print("Testlauf für VPP Flex Quantifier fehlgeschlagen (results is None).")

    except Exception as e:
        print(f"Fehler im Testlauf von _04_vpp_flex_quantifier.py: {e}")
        import traceback
        traceback.print_exc()

