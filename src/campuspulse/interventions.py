import pandas as pd
from .config import PASS_MARK, ATTENDANCE_THRESHOLD


def build_support_plan(df: pd.DataFrame) -> pd.DataFrame:
    """Create transparent, rule-based student support suggestions.

    This is a support-screening tool, not a validated predictive model.
    """
    result = df.copy()

    marks = (
        pd.to_numeric(result["Marks"], errors="coerce")
        if "Marks" in result
        else pd.Series(float("nan"), index=result.index)
    )
    attendance = (
        pd.to_numeric(result["Attendance"], errors="coerce")
        if "Attendance" in result
        else pd.Series(float("nan"), index=result.index)
    )

    statuses = []
    reasons = []
    actions = []

    for mark, attend in zip(marks, attendance):
        marks_valid = pd.notna(mark)
        attendance_valid = pd.notna(attend)

        low_marks = marks_valid and mark < PASS_MARK
        low_attendance = (
            attendance_valid and attend < ATTENDANCE_THRESHOLD
        )

        if not marks_valid and not attendance_valid:
            status = "Insufficient data"
            reason = "Marks and attendance are unavailable."
            action = "Review and complete the student record."

        elif low_marks and low_attendance:
            status = "High support priority"
            reason = "Marks and attendance are both below reference thresholds."
            action = "Arrange an academic review and attendance support meeting."

        elif low_marks:
            status = "Needs academic support"
            reason = "Marks are below the configured pass mark."
            action = "Offer subject-level tutoring and review learning progress."

        elif low_attendance:
            status = "Needs attendance support"
            reason = "Attendance is below the configured threshold."
            action = "Discuss attendance barriers and agree on a support plan."

        elif not marks_valid or not attendance_valid:
            status = "Partial data"
            reason = "Only one of marks or attendance is available."
            action = "Complete the missing information before reviewing progress."

        else:
            status = "On track"
            reason = "Marks and attendance meet the configured reference thresholds."
            action = "Continue monitoring and provide regular feedback."

        statuses.append(status)
        reasons.append(reason)
        actions.append(action)

    result["Support_Status"] = statuses
    result["Support_Reason"] = reasons
    result["Recommended_Action"] = actions

    return result
