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
    if any(not c for c in out.columns):
        raise DatasetError("Column names cannot be blank.")
    if out.columns.duplicated().any():
        raise DatasetError("Duplicate column names are not allowed.")
    missing = [c for c in REQUIRED_COLUMNS if c not in out.columns]
    if missing:
        raise DatasetError(f"Missing required columns: {', '.join(missing)}")

    notices: list[str] = []
    out["Name"] = out["Name"].astype("string").str.strip()
    blank_names = out["Name"].isna() | out["Name"].eq("")
    if blank_names.any():
        notices.append(f"{int(blank_names.sum())} row(s) have blank name labels.")
        out.loc[blank_names, "Name"] = "Unknown"

    for col, (low, high) in NUMERIC_RANGES.items():
        if col not in out:
            continue
        before = out[col].notna()
        numeric = pd.to_numeric(out[col], errors="coerce")
        parse_bad = int((before & numeric.isna()).sum())
        range_bad = int((numeric.notna() & ~numeric.between(low, high)).sum())
        numeric = numeric.mask(~numeric.between(low, high))
        out[col] = numeric.astype("float64")
        if parse_bad:
            notices.append(f"{col}: {parse_bad} non-numeric value(s) converted to missing.")
        if range_bad:
            notices.append(f"{col}: {range_bad} out-of-range value(s) converted to missing.")

    duplicates = int(out.duplicated().sum())
    if duplicates:
        notices.append(f"{duplicates} exact duplicate row(s) detected; retained.")
    if out["Marks"].isna().all():
        raise DatasetError("Marks has no usable numeric values between 0 and 100.")
    return out, notices

def load_dataset(source: str | Path | IO) -> tuple[pd.DataFrame, list[str]]:
    try:
        try:
            frame = pd.read_csv(source, encoding="utf-8-sig")
        except UnicodeDecodeError:
            if hasattr(source, "seek"):
                source.seek(0)
            frame = pd.read_csv(source, encoding="latin-1")
        return validate_dataset(frame)
    except DatasetError:
        raise
    except (UnicodeDecodeError, pd.errors.ParserError, OSError, ValueError) as exc:
        logger.warning("CSV load failed: %s", exc)
        raise DatasetError("Could not read this CSV. Check that it is a valid, comma-separated file.") from exc

def quality_report(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in frame.columns:
        values = frame[col]
        rows.append({
            "Column": str(col),
            "Data_Type": str(values.dtype),
            "Missing": int(values.isna().sum()),
            "Missing_Percent": round(float(values.isna().mean() * 100), 1),
            "Unique": int(values.nunique(dropna=True)),
            "Duplicate_Values": int(values.duplicated().sum()),
        })
    return pd.DataFrame(rows)
