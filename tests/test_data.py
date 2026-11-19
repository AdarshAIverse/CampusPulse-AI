import pandas as pd
import pytest
from campuspulse.data import validate_dataset, DatasetError, quality_report

def test_numeric_validation():
    df, notes = validate_dataset(pd.DataFrame({"Name":["A","B"],"Marks":[80,"bad"],"Attendance":[101,75]}))
    assert pd.isna(df.loc[1,"Marks"]) and pd.isna(df.loc[0,"Attendance"])
    assert len(notes) >= 2

def test_required_columns():
    with pytest.raises(DatasetError): validate_dataset(pd.DataFrame({"Name":["A"]}))

def test_quality_report():
    report=quality_report(pd.DataFrame({"Name":["A",None],"Marks":[1,2]}))
    assert report.loc[report.Column=="Name","Missing_Percent"].iloc[0] == 50
