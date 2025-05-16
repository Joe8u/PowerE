# PowerE/src/logic/respondent_level_model/flexibility_potential/b_participation_calculator.py
import pandas as pd
import numpy as np
import sys # Für den Testblock unten
from pathlib import Path # Für den Testblock unten

# Importiere die Datenaufbereitungsfunktion für den Testblock
# Dies erfordert, dass das Skript entweder aus dem Projekt-Root ausgeführt wird
# oder der sys.path korrekt gesetzt ist.
try:
    from src.logic.respondent_level_model.flexibility_potential.a_survey_data_preparer import prepare_survey_flexibility_data
except ImportError:
    if str(Path.cwd().parent.parent.parent.parent) not in sys.path:
         sys.path.insert(0, str(Path.cwd().parent.parent.parent.parent))
    from src.logic.respondent_level_model.flexibility_potential.a_survey_data_preparer import prepare_survey_flexibility_data


def calculate_participation_metrics(
    df_survey_flex_input: pd.DataFrame,
    target_appliance: str,
    event_duration_h: float,
    offered_incentive_pct: float
) -> dict:
    """
    Berechnet die "rohe" Teilnahmequote und zugehörige Metriken basierend 
    auf den Umfrageantworten für ein gegebenes Gerät, eine Event-Dauer 
    und einen angebotenen Anreiz.

    Args:
        df_survey_flex_input (pd.DataFrame): Der aufbereitete DataFrame von 
                                             a_survey_data_preparer.prepare_survey_flexibility_data().
                                             Erwartete Spalten: 'respondent_id', 'device', 
                                                              'survey_max_duration_h', 
                                                              'survey_incentive_choice', 
                                                              'survey_incentive_pct_required'.
        target_appliance (str): Das zu analysierende Haushaltsgerät.
        event_duration_h (float): Die Dauer des hypothetischen DR-Events in Stunden.
        offered_incentive_pct (float): Der für die Teilnahme angebotene Anreiz in Prozent (z.B. 10.0 für 10%).

    Returns:
        dict: Ein Dictionary mit den Ergebnissen:
              'target_appliance': Name des Geräts.
              'event_duration_h': Verwendete Event-Dauer.
              'offered_incentive_pct': Verwendeter Anreiz.
              'base_population': Anzahl der Befragten, die Angaben für dieses Gerät gemacht haben.
              'num_participants': Anzahl der Befragten, die unter den gegebenen Bedingungen teilnehmen würden.
              'raw_participation_rate': Rohe Teilnahmequote (num_participants / base_population), oder 0.0.
    """

    if df_survey_flex_input.empty:
        print(f"[WARNUNG] calculate_participation_metrics: df_survey_flex_input ist leer für {target_appliance}.")
        return {
            'target_appliance': target_appliance, 'event_duration_h': event_duration_h, 
            'offered_incentive_pct': offered_incentive_pct, 'base_population': 0,
            'num_participants': 0, 'raw_participation_rate': 0.0
        }

    # Filtere für das spezifische Gerät
    df_device_flex = df_survey_flex_input[df_survey_flex_input['device'] == target_appliance].copy()

    if df_device_flex.empty:
        # print(f"[INFO] calculate_participation_metrics: Keine Umfragedaten für Gerät '{target_appliance}' gefunden.")
        return {
            'target_appliance': target_appliance, 'event_duration_h': event_duration_h,
            'offered_incentive_pct': offered_incentive_pct, 'base_population': 0,
            'num_participants': 0, 'raw_participation_rate': 0.0
        }

    # Basispopulation: Anzahl der einzigartigen Teilnehmer, die für dieses Gerät geantwortet haben
    base_population = df_device_flex['respondent_id'].nunique()
    
    if base_population == 0:
        # Sollte durch den df_device_flex.empty Check oben abgedeckt sein, aber zur Sicherheit
        return {
            'target_appliance': target_appliance, 'event_duration_h': event_duration_h,
            'offered_incentive_pct': offered_incentive_pct, 'base_population': 0,
            'num_participants': 0, 'raw_participation_rate': 0.0
        }

    num_participants = 0
    participating_respondent_ids = set() # Um sicherzustellen, dass jeder Respondent nur einmal pro Szenario zählt

    for _, row in df_device_flex.iterrows():
        # Bedingung 1: Akzeptierte Dauer der Nichtnutzung ist ausreichend
        survey_max_duration = row['survey_max_duration_h']
        # Wenn survey_max_duration 0.0 ist ("Nein, auf keinen Fall"), dann ist duration_met nur True, wenn event_duration_h auch 0 ist.
        # Für positive event_duration_h muss survey_max_duration >= event_duration_h sein.
        # Und 0.0 (aus "Nein, auf keinen Fall") ist NICHT >= einer positiven Event-Dauer.
        duration_met = (not pd.isna(survey_max_duration)) and \
                       (survey_max_duration >= event_duration_h)
        
        # Sonderfall: Wenn Eventdauer 0 ist, nehmen wir an, jeder, der nicht "Nein, auf keinen Fall" gesagt hat, "erfüllt" die Dauer.
        # Oder wir sagen, ein Event mit Dauer 0 macht keinen Sinn und `duration_met` bleibt wie oben.
        # Für DR-Events > 0h ist die obige Logik korrekt.
        # Wenn event_duration_h == 0 ist, und survey_max_duration == 0 (also "Nein, auf keinen Fall"),
        # wäre 0 >= 0 -> duration_met = True. Das wollen wir nicht für "Nein, auf keinen Fall".
        # Daher eine zusätzliche Bedingung: Wenn survey_max_duration == 0.0, ist duration_met nur True, wenn event_duration_h auch exakt 0.0 ist.
        # Aber ein Event mit Dauer 0.0 ist meist nicht sinnvoll. Sicherer:
        if survey_max_duration == 0.0 and event_duration_h > 0:
            duration_met = False
        elif survey_max_duration == 0.0 and event_duration_h == 0: # Ein "Event" der Dauer Null
             duration_met = True # Man "kann" ein 0h Event halten, wenn man 0h Abschaltung akzeptiert
                                 # (Dies ist ein Randfall, der selten relevant sein wird)


        # Bedingung 2: Anreizbedingung ist erfüllt
        incentive_choice = row['survey_incentive_choice']
        survey_pct_required = row['survey_incentive_pct_required'] # Kann NaN sein
        
        incentive_condition_met = False
        if incentive_choice == 'yes_fixed':
            incentive_condition_met = True
        elif incentive_choice == 'yes_conditional':
            if not pd.isna(survey_pct_required) and survey_pct_required <= offered_incentive_pct:
                incentive_condition_met = True
        # Bei 'no' oder 'unknown_choice' bleibt incentive_condition_met False

        if duration_met and incentive_condition_met:
            participating_respondent_ids.add(row['respondent_id'])
            # print(f"  Debug: {row['respondent_id']} für {target_appliance} nimmt teil. Dauer ok: {row['survey_max_duration_h']}>={event_duration_h}. Anreiz ok: choice={incentive_choice}, req={survey_pct_required}<={offered_incentive_pct}")


    num_participants = len(participating_respondent_ids)
    raw_participation_rate = (num_participants / base_population) if base_population > 0 else 0.0
    
    return {
        'target_appliance': target_appliance,
        'event_duration_h': event_duration_h,
        'offered_incentive_pct': offered_incentive_pct,
        'base_population': base_population,
        'num_participants': num_participants,
        'raw_participation_rate': raw_participation_rate
    }

if __name__ == '__main__':
    print("\n--- Starte Testlauf für b_participation_calculator.py ---")
    
    # 1. Lade Beispieldaten (aufbereitet durch den Preparer)
    try:
        # Hier müssen wir sicherstellen, dass der PROJECT_ROOT für die Loader in prepare_survey_flexibility_data korrekt ist,
        # wenn dieses Skript standalone ausgeführt wird.
        # Die try-except Logik am Anfang von a_survey_data_preparer.py sollte dies für standalone Tests ermöglichen.
        df_test_flex_data = prepare_survey_flexibility_data()
        
        if df_test_flex_data.empty:
            print("Test-Flexibilitätsdaten sind leer, Test kann nicht durchgeführt werden.")
        else:
            print(f"\nTest-Flexibilitätsdaten geladen (Shape: {df_test_flex_data.shape}). Erste Zeilen:")
            print(df_test_flex_data.head())

            # 2. Definiere einige Test-Szenarien
            test_scenarios = [
                {"appliance": "Geschirrspüler", "duration": 1.5, "incentive": 0},    # Erwarte Teilnehmer, die 'yes_fixed' und Dauer >= 1.5h haben
                {"appliance": "Geschirrspüler", "duration": 1.5, "incentive": 10},   # Erwarte 'yes_fixed' ODER 'yes_conditional' mit <=10% Forderung
                {"appliance": "Waschmaschine", "duration": 4.5, "incentive": 20},
                {"appliance": "Backofen und Herd", "duration": 1.5, "incentive": 5}, # Kaum Teilnahme erwartet basierend auf Q9/Q10
                {"appliance": "Geschirrspüler", "duration": 30.0, "incentive": 50}, # Test mit langer Dauer
            ]

            print("\n--- Teste calculate_participation_metrics für verschiedene Szenarien ---")
            for scenario in test_scenarios:
                metrics = calculate_participation_metrics(
                    df_survey_flex_input=df_test_flex_data,
                    target_appliance=scenario["appliance"],
                    event_duration_h=scenario["duration"],
                    offered_incentive_pct=scenario["incentive"]
                )
                print(
                    f"Szenario: Gerät={metrics['target_appliance']}, Dauer={metrics['event_duration_h']}h, Anreiz={metrics['offered_incentive_pct']}% "
                    f"-> Basispop: {metrics['base_population']}, Teilnehmer: {metrics['num_participants']}, "
                    f"Rohe Teilnahmequote: {metrics['raw_participation_rate']:.2%}"
                )
            
            # Spezifischer Testfall, um die Logik genauer zu prüfen:
            print("\nSpezifischer Testfall für Geschirrspüler (Q9: 1.5h, Q10: 'yes_fixed'):")
            # Annahme: Es gibt mindestens einen Respondent für Geschirrspüler mit diesen genauen Werten
            # Erstelle einen Mini-DataFrame für diesen Testfall
            sample_data_gs_fixed = pd.DataFrame({
                'respondent_id': ['TestR1'], 'device': ['Geschirrspüler'], 
                'survey_max_duration_h': [1.5], 
                'survey_incentive_choice': ['yes_fixed'], 
                'survey_incentive_pct_required': [0.0]
            })
            metrics_gs_fixed = calculate_participation_metrics(sample_data_gs_fixed, "Geschirrspüler", 1.5, 0)
            print(
                 f"Szenario: Gerät={metrics_gs_fixed['target_appliance']}, Dauer={metrics_gs_fixed['event_duration_h']}h, Anreiz={metrics_gs_fixed['offered_incentive_pct']}% "
                 f"-> Basispop: {metrics_gs_fixed['base_population']}, Teilnehmer: {metrics_gs_fixed['num_participants']}, "
                 f"Rohe Teilnahmequote: {metrics_gs_fixed['raw_participation_rate']:.2%}"
            )
            assert metrics_gs_fixed['num_participants'] == 1, "Fehler im Testfall Geschirrspüler 'yes_fixed'"


            print("\nSpezifischer Testfall für Geschirrspüler (Q9: 0.0h 'Nein', Q10: 'yes_fixed'):")
            sample_data_gs_q9no_q10yes = pd.DataFrame({
                'respondent_id': ['TestR2'], 'device': ['Geschirrspüler'], 
                'survey_max_duration_h': [0.0], # Sagt Nein in Q9
                'survey_incentive_choice': ['yes_fixed'], 
                'survey_incentive_pct_required': [0.0]
            })
            metrics_gs_q9no_q10yes = calculate_participation_metrics(sample_data_gs_q9no_q10yes, "Geschirrspüler", 1.5, 0) # Event-Dauer 1.5h
            print(
                 f"Szenario: Gerät={metrics_gs_q9no_q10yes['target_appliance']}, Dauer={metrics_gs_q9no_q10yes['event_duration_h']}h, Anreiz={metrics_gs_q9no_q10yes['offered_incentive_pct']}% "
                 f"-> Basispop: {metrics_gs_q9no_q10yes['base_population']}, Teilnehmer: {metrics_gs_q9no_q10yes['num_participants']}, "
                 f"Rohe Teilnahmequote: {metrics_gs_q9no_q10yes['raw_participation_rate']:.2%}"
            )
            assert metrics_gs_q9no_q10yes['num_participants'] == 0, "Fehler im Testfall Geschirrspüler Q9='Nein', sollte nicht teilnehmen bei Event-Dauer > 0"


    except Exception as e:
        print(f"Ein Fehler ist im Testlauf aufgetreten: {e}")
        import traceback
        traceback.print_exc()
    print("\n--- Testlauf für b_participation_calculator.py beendet ---")