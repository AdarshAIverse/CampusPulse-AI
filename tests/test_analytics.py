import pandas as pd
from campuspulse.analytics import academic_summary, attendance_summary, correlation_matrix, outlier_summary

def test_academics():
    assert academic_summary(pd.DataFrame({"Marks":[20,40,80]}))["pass_rate"] == 66.7

def test_optional_attendance():
    assert attendance_summary(pd.DataFrame({"Marks":[50]}))["mean"] is None

def test_small_correlation_and_outlier():
    df=pd.DataFrame({"Marks":[70,71,72]})
    assert correlation_matrix(df).empty
    assert outlier_summary(df).empty
