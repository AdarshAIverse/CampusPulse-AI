from io import BytesIO
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak
)

from campuspulse.interventions import build_support_plan


def _value(value):
    if pd.isna(value):
        return "N/A"
    return str(value)


def _number(value, suffix=""):
    number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return f"{number:.1f}{suffix}" if pd.notna(number) else "N/A"


def _make_pdf(title, subtitle, sections):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#17365D"),
        fontSize=21,
        spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        name="ReportSubtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        textColor=colors.grey,
        fontSize=9,
        spaceAfter=18
    ))

    story = [
        Paragraph(escape(title), styles["ReportTitle"]),
        Paragraph(escape(subtitle), styles["ReportSubtitle"])
    ]

    for heading, rows in sections:
        story.append(Paragraph(escape(heading), styles["Heading2"]))
        story.append(Spacer(1, 5))

        table = Table(rows, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5DDE5")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#F1F5F9")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.extend([table, Spacer(1, 14)])

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "CampusPulse AI | Explainable educational analytics prototype. "
        "This report is descriptive, not predictive or diagnostic. "
        "Human review is required before acting on support recommendations.",
        styles["Italic"]
    ))

    doc.build(story)
    return buffer.getvalue()


def student_pdf_bytes(student_df, source=""):
    if student_df.empty:
        raise ValueError("No student record is available.")

    student = student_df.iloc[0]
    sections = []

    details = [["Field", "Value"]]
    for column in [
        "Name", "Department", "Year", "Marks", "Attendance",
        "Study_Hours", "Sleep_Hours", "Screen_Time",
        "Campus_Indicator", "Indicator_Coverage", "Indicator_Band"
    ]:
        if column in student_df.columns:
            details.append([column, _value(student[column])])

    sections.append(("Student information", details))

    support = build_support_plan(student_df.copy())
    support_row = support.iloc[0]
    support_rows = [["Support field", "Assessment"]]

    for column in [
        "Support_Status", "Support_Reason", "Recommended_Action"
    ]:
        if column in support.columns:
            support_rows.append([column, _value(support_row[column])])

    sections.append(("Student support assessment", support_rows))

    return _make_pdf(
        "Individual Student Report",
        f"CampusPulse AI | Data source: {source or 'Not specified'}",
        sections
    )


def campus_pdf_bytes(df, source=""):
    if df.empty:
        raise ValueError("No student data is available.")

    marks = pd.to_numeric(df["Marks"], errors="coerce")
    sections = []

    academic_rows = [
        ["Academic metric", "Value"],
        ["Total student records", str(len(df))],
        ["Average marks", _number(marks.mean(), "%")],
        ["Median marks", _number(marks.median(), "%")],
        ["Highest marks", _number(marks.max(), "%")],
        ["Lowest marks", _number(marks.min(), "%")]
    ]

    sections.append(("Academic summary", academic_rows))

    attendance_rows = [["Attendance metric", "Value"]]
    if "Attendance" in df.columns:
        attendance = pd.to_numeric(df["Attendance"], errors="coerce")
        attendance_rows.extend([
            ["Average attendance", _number(attendance.mean(), "%")],
            ["Below 75% reference", str(int((attendance < 75).sum()))],
            ["At or above 75% reference", str(int((attendance >= 75).sum()))],
            ["Records with attendance data", str(int(attendance.notna().sum()))]
        ])
    else:
        attendance_rows.append(["Attendance", "Column not available"])

    sections.append(("Attendance summary", attendance_rows))

    indicator_rows = [["Indicator metric", "Value"]]
    if "Campus_Indicator" in df.columns:
        indicator = pd.to_numeric(df["Campus_Indicator"], errors="coerce")
        indicator_rows.extend([
            ["Average Campus Indicator", _number(indicator.mean(), "/100")],
            ["Records with indicator data", str(int(indicator.notna().sum()))]
        ])
    else:
        indicator_rows.append(["Campus Indicator", "Not available"])

    sections.append(("Campus Indicator summary", indicator_rows))

    support = build_support_plan(df.copy())
    counts = support["Support_Status"].value_counts()
    support_rows = [["Support status", "Student count"]]

    for status in [
        "High support priority",
        "Needs academic support",
        "Needs attendance support",
        "Partial data",
        "Insufficient data",
        "On track"
    ]:
        support_rows.append([status, str(int(counts.get(status, 0)))])

    sections.append(("Student support summary", support_rows))

    return _make_pdf(
        "Campus Analytics Report",
        f"CampusPulse AI | Data source: {source or 'Not specified'}",
        sections
    )