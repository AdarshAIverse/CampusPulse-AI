import pandas as pd
from campuspulse.interventions import build_support_plan


def test_low_marks_and_attendance_get_high_priority():
    df = pd.DataFrame({
        "Name": ["Student A"],
        "Marks": [30],
        "Attendance": [50],
    })
    result = build_support_plan(df)
    assert result.iloc[0]["Support_Status"] == "High support priority"


def test_good_performance_is_on_track():
    df = pd.DataFrame({
        "Name": ["Student B"],
        "Marks": [85],
        "Attendance": [90],
    })
    result = build_support_plan(df)
    assert result.iloc[0]["Support_Status"] == "On track"


def test_missing_data_is_not_marked_on_track():
    df = pd.DataFrame({
        "Name": ["Student C"],
        "Marks": [None],
        "Attendance": [None],
    })
    result = build_support_plan(df)
    assert result.iloc[0]["Support_Status"] == "Insufficient data"


def test_academic_support_recommendation():
    df = pd.DataFrame({
        "Name": ["Student D"],
        "Marks": [30],
        "Attendance": [90],
    })
    result = build_support_plan(df)
    assert result.iloc[0]["Support_Status"] == "Needs academic support"
    assert result.iloc[0]["Recommended_Action"]


def test_original_data_is_not_modified():
    df = pd.DataFrame({
        "Name": ["Student E"],
        "Marks": [80],
        "Attendance": [85],
    })
    original_columns = list(df.columns)
    build_support_plan(df)
    assert list(df.columns) == original_columns
