from __future__ import annotations
import pandas as pd

def csv_bytes(frame: pd.DataFrame) -> bytes:
    """Return a UTF-8 CSV with BOM for spreadsheet compatibility."""
    return frame.to_csv(index=False).encode("utf-8-sig")
