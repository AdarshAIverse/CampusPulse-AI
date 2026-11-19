import pandas as pd
from campuspulse.analytics import academic_summary, attendance_summary, correlation_matrix, outlier_summary, department_summary

def test_academics():
    result = academic_summary(pd.DataFrame({"Marks":[20,40,80]}))
    assert result["pass_rate"] == 66.7
    assert result["lowest"] == 20

def test_optional_attendance():
    assert attendance_summary(pd.DataFrame({"Marks":[50]}))["mean"] is None

def test_small_correlation_and_outlier():
    df = pd.DataFrame({"Marks":[70,71,72]})
    assert correlation_matrix(df).empty
    assert outlier_summary(df).empty

def test_department_summary():
    df = pd.DataFrame({"Department":["CSE","ECE"],"Marks":[80,60]})
    result = department_summary(df)
    assert len(result) == 2
