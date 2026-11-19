import pandas as pd
from .config import DEFAULT_WEIGHTS

def _components(df: pd.DataFrame) -> dict[str, pd.Series]:
    result = {}
    if "Marks" in df: result["Marks"] = pd.to_numeric(df["Marks"], errors="coerce")
    if "Attendance" in df: result["Attendance"] = pd.to_numeric(df["Attendance"], errors="coerce")
    if "Study_Hours" in df: result["Study_Hours"] = (pd.to_numeric(df["Study_Hours"], errors="coerce") / 4 * 100).clip(0, 100)
    if "Sleep_Hours" in df: result["Sleep_Hours"] = (100 - (pd.to_numeric(df["Sleep_Hours"], errors="coerce") - 8).abs()*12.5).clip(0, 100)
    if "Screen_Time" in df: result["Screen_Time"] = (100 - (pd.to_numeric(df["Screen_Time"], errors="coerce") - 2).clip(lower=0)*12.5).clip(0, 100)
    return result

def calculate_indicator(frame: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.DataFrame:
    weights = dict(weights or DEFAULT_WEIGHTS)
    if not weights or any(v < 0 for v in weights.values()) or sum(weights.values()) <= 0:
        raise ValueError("Weights must be non-negative and have a positive total.")
    components = {k:v for k,v in _components(frame).items() if k in weights and weights[k] > 0}
    out = frame.copy()
    if not components:
        out["Campus_Indicator"] = float("nan")
        out["Indicator_Coverage"] = 0.0
        out["Indicator_Band"] = "Insufficient data"
        return out
    weighted = pd.Series(0.0, index=out.index)
    used = pd.Series(0.0, index=out.index)
    for key, values in components.items():
        valid = values.notna()
        weighted += values.fillna(0) * weights[key]
        used += valid.astype(float) * weights[key]
    out["Campus_Indicator"] = (weighted / used.where(used > 0)).round(1)
    out["Indicator_Coverage"] = (used / sum(weights.values()) * 100).round(1)
    out["Indicator_Band"] = pd.cut(out["Campus_Indicator"], [-.001, 49.999, 74.999, 100.001],
        labels=["Needs attention", "Developing", "Strong"]).astype("string").fillna("Insufficient data")
    return out
