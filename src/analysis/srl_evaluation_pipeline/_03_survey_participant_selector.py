# PowerE/src/analysis/srl_evaluation_pipeline/_03_survey_participant_selector.py
import pandas as pd
import numpy as np
import sys
from pathlib import Path
# Importiere die Funktion zum Laden der aufbereiteten Umfragedaten
# Annahme: a_survey_data_preparer.py ist im richtigen Pfad (src/logic/...)
from logic.respondent_level_model.flexibility_potential.a_survey_data_preparer import prepare_survey_flexibility_data

def determine_participating_households(
    max_offerable_incentive_chf_kwh: float,
    price_household_chf_per_kwh: float,
    min_srl_event_duration_h: float,
    appliance_name: str,
    n_survey_base_valid_answers: int,
    project_root_path: Path # Wird an prepare_survey_flexibility_data weitergegeben
):
    """
    Ermittelt die Anzahl der teilnehmenden Haushalte und den durchschnittlichen
    tatsächlich gezahlten Anreiz basierend auf Umfragedaten.
    """
    print("Lade und verarbeite Umfragedaten (Q9 und Q10) für Teilnehmerselektion...")
    try:
        df_survey_flex = prepare_survey_flexibility_data() 
        if df_survey_flex.empty:
            print("FEHLER: Aufbereitete Umfragedaten sind leer in determine_participating_households.")
            return None
    except Exception as e:
        print(f"FEHLER beim Laden der aufbereiteten Umfragedaten in determine_participating_households: {e}")
        return None

    df_appliance_flex = df_survey_flex[df_survey_flex['device'] == appliance_name].copy()
    if df_appliance_flex.empty:
        print(f"Keine Umfragedaten für das Gerät '{appliance_name}' gefunden.")
        return None

    # Stelle sicher, dass relevante Spalten numerisch sind
    df_appliance_flex['survey_incentive_pct_required'] = pd.to_numeric(df_appliance_flex['survey_incentive_pct_required'], errors='coerce')
    df_appliance_flex['survey_max_duration_h'] = pd.to_numeric(df_appliance_flex['survey_max_duration_h'], errors='coerce')

    participating_respondents_details = [] 
    for _, row in df_appliance_flex.iterrows():
        choice = row['survey_incentive_choice']
        required_pct = row['survey_incentive_pct_required']
        max_duration = row['survey_max_duration_h']

        # Bedingung 1: Dauer
        if pd.isna(max_duration) or max_duration < min_srl_event_duration_h:
            continue 

        actual_incentive_for_this_participant_chf_kwh = 0.0
        participant_accepts_incentive = False

        if choice == 'yes_fixed': 
            participant_accepts_incentive = True
            actual_incentive_for_this_participant_chf_kwh = 0.0
        elif choice == 'yes_conditional':
            if not pd.isna(required_pct):
                required_incentive_chf_kwh = (required_pct / 100.0) * price_household_chf_per_kwh
                if max_offerable_incentive_chf_kwh >= required_incentive_chf_kwh:
                    participant_accepts_incentive = True
                    actual_incentive_for_this_participant_chf_kwh = required_incentive_chf_kwh
        
        if participant_accepts_incentive:
            participating_respondents_details.append({
                'respondent_id': row['respondent_id'],
                'actual_incentive_chf_kwh': actual_incentive_for_this_participant_chf_kwh
            })

    df_participating = pd.DataFrame(participating_respondents_details)
    n_market_driven_participants = df_participating['respondent_id'].nunique() # Korrekt mit kleinem 'n' definiert
    
    avg_actual_incentive_paid = 0.0
    # KORRIGIERTE IF-BEDINGUNG: Verwende das korrekt definierte 'n_market_driven_participants'
    if n_market_driven_participants > 0: 
        avg_actual_incentive_paid = df_participating['actual_incentive_chf_kwh'].mean()
    
    participation_rate = 0.0
    if n_survey_base_valid_answers > 0:
        participation_rate = n_market_driven_participants / n_survey_base_valid_answers
    else:
        print("WARNUNG: n_survey_base_valid_answers ist 0. Teilnahmequote kann nicht berechnet werden.")
            
    return {
        'num_participants': n_market_driven_participants,
        'participation_rate': participation_rate,
        'avg_actual_incentive_paid': avg_actual_incentive_paid,
        'df_participating_details': df_participating 
    }

if __name__ == '__main__':
    print("Testlauf für _03_survey_participant_selector.py")
    # Für einen Standalone-Test dieses Moduls müssten wir den PROJECT_ROOT
    # für prepare_survey_flexibility_data() korrekt setzen oder mocken.
    # Der Orchestrator wird project_root_path übergeben.
    
    # Annahmen für den Test:
    # Bestimme PROJECT_ROOT für den Test, falls Loader ihn doch benötigen würden
    # oder wenn die Daten relativ zum Projekt-Root abgelegt sind.
    # Dieser Teil ist für den direkten Test wichtig, um `prepare_survey_flexibility_data` zu finden
    try:
        CURRENT_SCRIPT_PATH_TEST = Path(__file__).resolve()
        test_project_root = CURRENT_SCRIPT_PATH_TEST.parent.parent.parent.parent
        if str(test_project_root / "src") not in sys.path:
            sys.path.insert(0, str(test_project_root / "src"))
        if str(test_project_root) not in sys.path: # Füge auch den Projekt-Root hinzu
            sys.path.insert(0, str(test_project_root))
    except NameError: # Falls __file__ nicht definiert ist (z.B. in einer interaktiven Zelle)
        test_project_root = Path.cwd() # Fallback auf aktuelles Verzeichnis
        if str(test_project_root / "src") not in sys.path:
            sys.path.insert(0, str(test_project_root / "src"))
        if str(test_project_root) not in sys.path:
            sys.path.insert(0, str(test_project_root))
        print(f"[WARNUNG im Testblock] __file__ nicht definiert. test_project_root als CWD angenommen: {test_project_root}")


    try:
        # Erneuter Importversuch, falls der erste try-except Block oben im Skript
        # nicht erfolgreich war (z.B. wenn dieses Modul standalone ausgeführt wird)
        from logic.respondent_level_model.flexibility_potential.a_survey_data_preparer import prepare_survey_flexibility_data
        
        results = determine_participating_households(
            max_offerable_incentive_chf_kwh=0.7270, 
            price_household_chf_per_kwh=0.29,    
            min_srl_event_duration_h=1.0,
            appliance_name="Geschirrspüler",
            n_survey_base_valid_answers=334,     
            project_root_path=test_project_root  
        )
        if results:
            print(f"\nAnzahl Teilnehmer: {results['num_participants']}")
            print(f"Teilnahmequote: {results['participation_rate']:.2%}")
            print(f"Durchschnittlicher tatsächlicher Anreiz: {results['avg_actual_incentive_paid']:.4f} CHF/kWh")
            print("Details der ersten teilnehmenden Personen:")
            print(results['df_participating_details'].head())
    except Exception as e:
        print(f"Fehler im Testlauf von _03_survey_participant_selector.py: {e}")
        import traceback
        traceback.print_exc()
