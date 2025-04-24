from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException

router = APIRouter()

BASE = Path(__file__).resolve().parents[3] / "data" / "processed" / "static" / "jasm"


@router.get("/monthly/{year}")
def get_jasm_monthly(year: int):
    path = BASE / str(year) / "monthly" / f"appliance_monthly_{year}_01.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Year not found")
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    # Im JSON-Response konvertieren wir TimeIndex zu ISO-Strings
    data = {
        "index": [t.isoformat() for t in df.index],
        "columns": df.columns.tolist(),
        "values": df.values.tolist(),
    }
    return data
