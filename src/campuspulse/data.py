from pathlib import Path
from typing import IO
import logging
import pandas as pd
from .config import REQUIRED_COLUMNS, NUMERIC_RANGES

logger = logging.getLogger(__name__)

class DatasetError(ValueError):
    """Raised when a dataset cannot be safely analysed."""

def validate_dataset(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    if not isinstance(frame, pd.DataFrame) or frame.empty or len(frame.columns) == 0:
        raise DatasetError("Dataset must be a non-empty table.")
    out = frame.copy()
    out.columns = [str(c).strip() for c in out.columns]
    if out.columns.duplicated().any():
        raise DatasetError("Duplicate column names are not allowed.")
    missing = [c for c in REQUIRED_COLUMNS if c not in out.columns]
    if missing:
        raise DatasetError(f"Missing required columns: {', '.join(missing)}")
    notices = []
    out["Name"] = out["Name"].astype("string").str.strip()
    for col, (low, high) in NUMERIC_RANGES.items():
        if col not in out: continue
        before = out[col].notna()
        numeric = pd.to_numeric(out[col], errors="coerce")
        parse_bad = int((before & numeric.isna()).sum())
        range_bad = int((numeric.notna() & ~numeric.between(low, high)).sum())
        numeric = numeric.mask(~numeric.between(low, high))
        out[col] = numeric.astype("float64")
        if parse_bad: notices.append(f"{col}: {parse_bad} non-numeric value(s) converted to missing.")
        if range_bad: notices.append(f"{col}: {range_bad} out-of-range value(s) converted to missing.")
    duplicates = int(out.duplicated().sum())
    if duplicates: notices.append(f"{duplicates} exact duplicate row(s) detected; retained.")
    blank = int((out["Name"].isna() | out["Name"].eq("")).sum())
    if blank: notices.append(f"{blank} row(s) have blank name labels.")
    if out["Marks"].isna().all(): raise DatasetError("Marks has no usable numeric values.")
    return out, notices

def load_dataset(source: str | Path | IO) -> tuple[pd.DataFrame, list[str]]:
    try:
        return validate_dataset(pd.read_csv(source))
    except (UnicodeDecodeError, pd.errors.ParserError, OSError) as exc:
        logger.warning("CSV load failed: %s", exc)
        raise DatasetError(f"Could not read CSV: {exc}") from exc

def quality_report(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([{"Column": c, "Data_Type": str(frame[c].dtype),
        "Missing": int(frame[c].isna().sum()),
        "Missing_Percent": round(float(frame[c].isna().mean()*100), 1),
        "Unique": int(frame[c].nunique(dropna=True))} for c in frame.columns])
