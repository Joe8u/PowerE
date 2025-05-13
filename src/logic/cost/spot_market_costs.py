# src/logic/cost/spot_market_costs.py
import pandas as pd
import numpy as np # Werden wir für np.nansum oder Fehlerbehandlung brauchen

def calculate_spot_market_costs(
    load_profile_kw: pd.Series,       # Zeitreihe der Last in kW, Index ist Timestamp
    spot_prices_eur_mwh: pd.Series, # Zeitreihe der Spotpreise in EUR/MWh, Index ist Timestamp
) -> float:
    """
    Berechnet die gesamten Energiekosten am Spotmarkt für ein gegebenes Lastprofil.

    Args:
        load_profile_kw: Pandas Series mit Zeitstempel-Index und Lastwerten in kW.
        spot_prices_eur_mwh: Pandas Series mit Zeitstempel-Index und Spotpreisen in EUR/MWh.

    Returns:
        float: Die gesamten Spotmarktkosten in EUR.
               Gibt 0.0 zurück, wenn Inputs leer sind oder keine Überlappung im Index besteht.
    """
    if load_profile_kw is None or load_profile_kw.empty or \
       spot_prices_eur_mwh is None or spot_prices_eur_mwh.empty:
        print("[WARNUNG] calculate_spot_market_costs: Eines der Eingabe-DataFrames ist leer oder None.")
        return 0.0

    # Stelle sicher, dass beide Indizes DatetimeIndizes sind
    if not isinstance(load_profile_kw.index, pd.DatetimeIndex) or \
       not isinstance(spot_prices_eur_mwh.index, pd.DatetimeIndex):
        print("[FEHLER] calculate_spot_market_costs: Indizes müssen DatetimeIndizes sein.")
        # Hier könntest du versuchen, sie zu konvertieren, oder einen Fehler werfen/0.0 zurückgeben
        # Für den Moment geben wir 0.0 zurück und eine Warnung
        try:
            load_profile_kw.index = pd.to_datetime(load_profile_kw.index)
            spot_prices_eur_mwh.index = pd.to_datetime(spot_prices_eur_mwh.index)
        except Exception as e:
            print(f"  Konnte Indizes nicht in DatetimeIndex umwandeln: {e}")
            return 0.0
            
    # 1. Intervalldauer in Stunden ableiten (aus dem Lastprofil-Index)
    #    Annahme: Regelmäßiger Zeitindex
    interval_duration_h = 0.0
    if len(load_profile_kw.index) > 1:
        # Verwende den Median der Differenzen für Robustheit gegenüber einzelnen Ausreißern/Lücken
        # oder pd.infer_freq, wenn der Index eine klare Frequenz hat
        diffs_seconds = load_profile_kw.index.to_series().diff().dropna().dt.total_seconds()
        if not diffs_seconds.empty:
            interval_duration_h = diffs_seconds.median() / 3600.0
    elif len(load_profile_kw.index) == 1:
        # Annahme für einen einzelnen Datenpunkt (z.B. 15 Minuten oder 1 Stunde)
        # Für eine einzelne Zeile ist die Energieberechnung so nicht direkt möglich,
        # es sei denn, man nimmt eine Standard-Intervalldauer an.
        # Hier nehmen wir an, dass der Preis für diese eine Laststufe für 1h gilt, wenn nicht anders bekannt.
        # Besser wäre es, wenn dies als Parameter übergeben wird, oder die Frequenz bekannt ist.
        # Für den Moment nehmen wir 0.25h (15min) als Default, wenn nur eine Zeile da ist.
        # print("[WARNUNG] calculate_spot_market_costs: Nur ein Datenpunkt im Lastprofil. Intervalldauer unklar. Nehme 0.25h an.")
        # dt_series = pd.Series(load_profile_kw.index)
        # freq = pd.infer_freq(dt_series)
        # if freq:
        #     interval_duration_h = pd.Timedelta(pd.tseries.frequencies.to_offset(freq)).total_seconds() / 3600
        # else:
        #     print("[WARNUNG] ... konnte Frequenz nicht ableiten, nehme 0.25h an.")
        #     interval_duration_h = 0.25 # Standardannahme: 15 Minuten für einen einzelnen Punkt
        #     (Dieser Teil ist tricky, wenn die Frequenz nicht bekannt ist. Die Median-Methode ist besser für >1 Punkt)
        print("[WARNUNG] calculate_spot_market_costs: Nur ein Datenpunkt im Lastprofil. Energieberechnung basiert auf Annahme oder ist ungenau.")
        # Fallback, falls die Frequenz nicht ableitbar ist / Median nicht funktioniert
        if interval_duration_h == 0.0:
             # Dies kann passieren, wenn die Frequenz des Index nicht ermittelt werden kann
             # oder wenn der Index nicht regelmäßig ist. Für eine robustere Lösung
             # wäre es besser, die Intervalldauer explizit zu übergeben oder aus der Quelle zu kennen.
             # Hier eine Notlösung, um einen Fehler zu vermeiden, aber das Ergebnis ist dann ungenau.
            print("[WARNUNG] ... konnte Intervalldauer nicht ableiten, setze auf 0.25h als Annahme.")
            interval_duration_h = 0.25


    if interval_duration_h <= 0:
        print("[WARNUNG] calculate_spot_market_costs: Intervalldauer ist 0 oder negativ. Kosten werden 0 sein.")
        return 0.0

    # 2. Spotpreise an den Index des Lastprofils anpassen (falls nötig, z.B. stündliche Preise auf 15-Min-Last)
    #    Wir verwenden 'ffill' (forward fill), um den letzten bekannten Preis für Intervalle zu nehmen,
    #    für die kein exakter Preisstempel existiert.
    aligned_spot_prices_eur_mwh = spot_prices_eur_mwh.reindex(load_profile_kw.index, method='ffill')
    
    # Fülle verbleibende NaNs am Anfang, falls das Lastprofil vor den Preisen beginnt
    aligned_spot_prices_eur_mwh = aligned_spot_prices_eur_mwh.bfill()

    # Wenn immer noch NaNs vorhanden sind (z.B. wenn beide Series komplett disjunkt sind oder nur NaNs enthalten),
    # können keine Kosten berechnet werden.
    if aligned_spot_prices_eur_mwh.isnull().all() or load_profile_kw.isnull().all():
        print("[WARNUNG] calculate_spot_market_costs: Nach Index-Angleichung keine gültigen Preis- oder Lastdaten.")
        return 0.0

    # 3. Energie pro Intervall in kWh berechnen
    #    load_profile_kw (kW) * interval_duration_h (h) = energy_kwh_interval (kWh)
    energy_kwh_interval = load_profile_kw * interval_duration_h

    # 4. Spotpreise von EUR/MWh in EUR/kWh umrechnen
    aligned_spot_prices_eur_kwh = aligned_spot_prices_eur_mwh / 1000.0

    # 5. Kosten pro Intervall berechnen
    #    energy_kwh_interval (kWh) * aligned_spot_prices_eur_kwh (EUR/kWh) = cost_eur_interval (EUR)
    cost_eur_interval = energy_kwh_interval * aligned_spot_prices_eur_kwh

    # 6. Gesamtkosten berechnen
    #    np.nansum summiert und behandelt NaNs als 0, was hier sinnvoll ist,
    #    falls einzelne Intervalle keine Kosten verursachen oder Daten fehlen.
    total_spot_cost_eur = np.nansum(cost_eur_interval)
    
    print(f"[INFO] calculate_spot_market_costs: Berechnete Gesamtkosten = {total_spot_cost_eur:.2f} EUR")
    return total_spot_cost_eur