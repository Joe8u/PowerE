# demand_response.py

import os
import pandas as pd

# Directory where all the processed survey CSVs live
BASE_DIR     = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, 'data', 'processed', 'survey'))
    
# Mapping of logical names to filenames
_FILES = {
    'importance':  'question_8_importance_wide.csv',   # Q8: Importance of appliances (wide format)
    'curtailment': 'question_9_curtailment.csv',       # Q9: Willingness to curtail use
    'incentives':  'question_10_incentives.csv',       # Q10: Incentive dropdowns + rebate %
    'notification': 'question_11_notification.csv',    # Q11: Notify when grid is stressed
    'smart_plug':   'question_12_smart_plug.csv',      # Q12: Smart-plug install willingness
}

def _load_csv(name: str) -> pd.DataFrame:
    """
    Helper to load a single CSV by its logical name.
    Raises FileNotFoundError if the file does not exist.
    """
    fname = _FILES.get(name)
    if fname is None:
        raise KeyError(f"No such survey component: {name}")
    path = os.path.join(BASE_DIR, fname)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Processed file not found: {path}")
    return pd.read_csv(path, dtype=str)

def load_demand_response() -> dict[str, pd.DataFrame]:
    """
    Load all demand-response survey tables (Q8–Q12).

    Returns
    -------
    dict[str, DataFrame]
        A dict with keys ['importance', 'curtailment', 'incentives',
        'notification', 'smart_plug'] mapping to the corresponding DataFrame.
    """
    return { name: _load_csv(name) for name in _FILES }

# Optional convenience functions:
def load_importance() -> pd.DataFrame:
    return _load_csv('importance')

def load_curtailment() -> pd.DataFrame:
    return _load_csv('curtailment')

def load_incentives() -> pd.DataFrame:
    return _load_csv('incentives')

def load_notification() -> pd.DataFrame:
    return _load_csv('notification')

def load_smart_plug() -> pd.DataFrame:
    return _load_csv('smart_plug')