import pandas as pd
from .config import PASS_MARK, ATTENDANCE_THRESHOLD

def academic_summary(df: pd.DataFrame) -> dict:
    marks = pd.to_numeric(df.get("Marks", pd.Series(dtype=float)), errors="coerce").dropna()
    if marks.empty: return {"count": 0, "mean": None, "median": None, "highest": None, "pass_rate": None}
    return {"count": int(len(marks)), "mean": round(float(marks.mean()),2),
        "median": round(float(marks.median()),2), "highest": round(float(marks.max()),2),
        "pass_rate": round(float((marks >= PASS_MARK).mean()*100),1)}

def attendance_summary(df: pd.DataFrame) -> dict:
    if "Attendance" not in df: return {"mean": None, "below_threshold": 0, "at_or_above_threshold": 0}
    values = pd.to_numeric(df["Attendance"], errors="coerce").dropna()
    if values.empty: return {"mean": None, "below_threshold": 0, "at_or_above_threshold": 0}
    return {"mean": round(float(values.mean()),2), "below_threshold": int((values < ATTENDANCE_THRESHOLD).sum()),
        "at_or_above_threshold": int((values >= ATTENDANCE_THRESHOLD).sum())}

def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in ["Marks","Attendance","Sleep_Hours","Study_Hours","Screen_Time"]
            if c in df and pd.to_numeric(df[c], errors="coerce").notna().sum() >= 2]
    return df[cols].apply(pd.to_numeric, errors="coerce").corr().round(2) if len(cols) >= 2 else pd.DataFrame()

def outlier_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in ["Marks","Attendance","Sleep_Hours","Study_Hours","Screen_Time"]:
        if col not in df: continue
        x = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(x) < 4: continue
        q1, q3 = x.quantile([.25,.75]); iqr = q3-q1
        rows.append({"Metric":col,"Lower_Fence":round(float(q1-1.5*iqr),2),
            "Upper_Fence":round(float(q3+1.5*iqr),2),"Flagged_Count":int(((x<q1-1.5*iqr)|(x>q3+1.5*iqr)).sum())})
    return pd.DataFrame(rows)
