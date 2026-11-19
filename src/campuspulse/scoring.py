import math
import pandas as pd
from .config import DEFAULT_WEIGHTS

def _components(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Convert raw columns to transparent 0-100 component scores."""
    result = {}
    if "Marks" in df:
        result["Marks"] = pd.to_numeric(df["Marks"], errors="coerce").clip(0, 100)
    if "Attendance" in df:
        result["Attendance"] = pd.to_numeric(df["Attendance"], errors="coerce").clip(0, 100)
    if "Study_Hours" in df:
        result["Study_Hours"] = (pd.to_numeric(df["Study_Hours"], errors="coerce") / 4 * 100).clip(0, 100)
    if "Sleep_Hours" in df:
        hours = pd.to_numeric(df["Sleep_Hours"], errors="coerce")
        result["Sleep_Hours"] = (100 - (hours - 8).abs() * 12.5).clip(0, 100)
    if "Screen_Time" in df:
        hours = pd.to_numeric(df["Screen_Time"], errors="coerce")
        result["Screen_Time"] = (100 - (hours - 2).clip(lower=0) * 12.5).clip(0, 100)
    return result

def calculate_indicator(frame: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.DataFrame:
    """Calculate a weighted descriptive indicator and per-row data coverage.

    The weights are design assumptions, not scientifically validated predictors.
    Missing components are excluded and remaining weights are renormalised per row.
    """
    selected_weights = dict(DEFAULT_WEIGHTS if weights is None else weights)
    if not selected_weights:
        raise ValueError("At least one weight is required.")
    for key, value in selected_weights.items():
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"Weight for {key} must be a finite, non-negative number.")
    total_weight = float(sum(selected_weights.values()))
    if total_weight <= 0:
        raise ValueError("Weights must have a positive total.")

    components = {k: v for k, v in _components(frame).items() if k in selected_weights and selected_weights[k] > 0}
    out = frame.copy()
    weighted = pd.Series(0.0, index=out.index)
    used = pd.Series(0.0, index=out.index)

    for key, values in components.items():
        valid = values.notna()
        out[f"Component_{key}"] = values.round(1)
        weighted += values.fillna(0) * float(selected_weights[key])
        used += valid.astype(float) * float(selected_weights[key])

    out["Campus_Indicator"] = (weighted / used.where(used > 0)).round(1)
    out["Indicator_Coverage"] = (used / total_weight * 100).round(1)
    out["Indicator_Band"] = pd.cut(
        out["Campus_Indicator"], [-0.001, 49.999, 74.999, 100.001],
        labels=["Needs attention", "Developing", "Strong"]
    ).astype("string").fillna("Insufficient data")
    return out
