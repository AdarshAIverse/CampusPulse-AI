import pandas as pd
from .config import PASS_MARK, ATTENDANCE_THRESHOLD

NUMERIC_FIELDS = ["Marks", "Attendance", "Sleep_Hours", "Study_Hours", "Screen_Time"]

def academic_summary(df: pd.DataFrame) -> dict:
    marks = pd.to_numeric(df.get("Marks", pd.Series(dtype=float)), errors="coerce").dropna()
    if marks.empty:
        return {"count": 0, "mean": None, "median": None, "highest": None, "lowest": None, "pass_rate": None, "std": None}
    return {
        "count": int(len(marks)), "mean": round(float(marks.mean()), 2),
        "median": round(float(marks.median()), 2), "highest": round(float(marks.max()), 2),
        "lowest": round(float(marks.min()), 2),
        "pass_rate": round(float((marks >= PASS_MARK).mean() * 100), 1),
        "std": round(float(marks.std(ddof=0)), 2),
    }

def attendance_summary(df: pd.DataFrame) -> dict:
    if "Attendance" not in df:
        return {"mean": None, "below_threshold": 0, "at_or_above_threshold": 0, "count": 0}
    values = pd.to_numeric(df["Attendance"], errors="coerce").dropna()
    if values.empty:
        return {"mean": None, "below_threshold": 0, "at_or_above_threshold": 0, "count": 0}
    return {
        "mean": round(float(values.mean()), 2),
        "below_threshold": int((values < ATTENDANCE_THRESHOLD).sum()),
        "at_or_above_threshold": int((values >= ATTENDANCE_THRESHOLD).sum()),
        "count": int(values.size),
    }

def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in NUMERIC_FIELDS if c in df and pd.to_numeric(df[c], errors="coerce").notna().sum() >= 2]
    if len(cols) < 2:
        return pd.DataFrame()
    numeric = df[cols].apply(pd.to_numeric, errors="coerce")
    corr = numeric.corr(min_periods=2).round(2)
    return corr.dropna(axis=0, how="all").dropna(axis=1, how="all")

def outlier_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in NUMERIC_FIELDS:
        if col not in df:
            continue
        values = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(values) < 4:
            continue
        q1, q3 = values.quantile([0.25, 0.75])
        iqr = q3 - q1
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        flagged = int(((values < low) | (values > high)).sum())
        rows.append({"Metric": col, "Lower_Fence": round(float(low), 2), "Upper_Fence": round(float(high), 2), "Flagged_Count": flagged, "Valid_Count": int(len(values))})
    return pd.DataFrame(rows)

def department_summary(df: pd.DataFrame) -> pd.DataFrame:
    if "Department" not in df or "Marks" not in df:
        return pd.DataFrame()
    work = df.assign(Marks=pd.to_numeric(df["Marks"], errors="coerce")).dropna(subset=["Marks"])
    if work.empty:
        return pd.DataFrame()
    return work.groupby("Department", dropna=False).agg(
        Students=("Marks", "size"), Average_Marks=("Marks", "mean"), Median_Marks=("Marks", "median")
    ).round(2).reset_index()
