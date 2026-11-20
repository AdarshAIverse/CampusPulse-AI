from pathlib import Path
import logging
import sys
import pandas as pd

# Ensure the src-layout package is importable locally and on Streamlit Community Cloud.
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
import streamlit as st
from campuspulse.pdf_reporting import student_pdf_bytes, campus_pdf_bytes
from campuspulse.data import load_dataset, DatasetError, quality_report
from campuspulse.scoring import calculate_indicator
from campuspulse.analytics import (academic_summary, attendance_summary, correlation_matrix,
                                   outlier_summary, department_summary)
from campuspulse.charts import marks_histogram, attendance_histogram, indicator_bar, correlation_heatmap
from campuspulse.reporting import csv_bytes
from campuspulse.interventions import build_support_plan
from campuspulse.config import MAX_UPLOAD_MB

logging.basicConfig(level=logging.INFO)
st.set_page_config(page_title="CampusPulse AI", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")
# --------------------------------------------------
# CAMPUSPULSE AI - PROFESSIONAL DASHBOARD THEME
# --------------------------------------------------

st.markdown("""
<style>
.stApp {
    background-color: #0B1220;
    color: #E5EDF8;
}

.block-container {
    padding-top: 2rem;
    max-width: 1450px;
}

h1, h2, h3 {
    color: #E5EDF8 !important;
}

[data-testid="stSidebar"] {
    background-color: #111C30;
    border-right: 1px solid #263750;
}

[data-testid="stMetric"] {
    background-color: #16243A;
    border: 1px solid #263D5C;
    border-radius: 14px;
    padding: 18px;
}

[data-testid="stMetricLabel"] {
    color: #A9BED8 !important;
}

[data-testid="stMetricValue"] {
    color: #54B8FF !important;
}

button[data-baseweb="tab"] {
    color: #A9BED8;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #54B8FF !important;
}

[data-testid="stDataFrame"] {
    border: 1px solid #263D5C;
    border-radius: 12px;
}

.stDownloadButton button {
    background-color: #1769AA;
    color: white;
    border-radius: 9px;
    border: none;
}

hr {
    border-color: #263750;
}

</style>
""", unsafe_allow_html=True)
st.title("🎓 CampusPulse AI")
st.subheader("Smart Campus Intelligence System")

st.markdown(
    """
    <div style="
        background: linear-gradient(110deg, #17365D, #2476B9);
        padding: 20px 24px;
        border-radius: 14px;
        color: white;
        margin-bottom: 18px;
    ">
        <h3 style="color:white !important; margin:0;">
            Welcome to Campus Intelligence
        </h3>
        <p style="color:#E7F1FC; margin:8px 0 0 0;">
            Explore student performance, attendance, academic insights
            and transparent student support recommendations.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

st.caption(
    "Explainable educational analytics prototype · "
    "Not a predictive or diagnostic system"
)
with st.sidebar:
    st.header("Control centre")
    upload = st.file_uploader("Upload student CSV", type=["csv"], help=f"Maximum recommended upload size: {MAX_UPLOAD_MB} MB")
    demo = st.checkbox("Use synthetic sample data", value=upload is None)

try:
    if upload is not None:
        if upload.size > MAX_UPLOAD_MB * 1024 * 1024:
            st.error(f"File is too large. Please upload a CSV smaller than {MAX_UPLOAD_MB} MB.")
            st.stop()
        raw, notices = load_dataset(upload)
        source = upload.name
    elif demo:
        raw, notices = load_dataset(Path(__file__).parent / "data" / "sample_students.csv")
        source = "Synthetic sample"
    else:
        st.info("Upload a CSV or enable synthetic sample data to begin.")
        st.stop()
except DatasetError as exc:
    st.error(str(exc))
    st.stop()
except Exception:
    logging.exception("Dataset processing failed")
    st.error("Unable to process this CSV. Check the file format and required Name and Marks columns.")
    st.stop()

for message in notices:
    st.warning(message)

scored = calculate_indicator(raw)
with st.sidebar:
    st.divider()
    st.subheader("Filters")
    marks_values = pd.to_numeric(scored["Marks"], errors="coerce").dropna()
    if marks_values.empty:
        st.error("No valid marks available for filtering.")
        st.stop()
    mark_range = st.slider("Marks range", 0.0, 100.0, (float(marks_values.min()), float(marks_values.max())))
    bands = sorted(scored["Indicator_Band"].astype(str).unique().tolist())
    selected_bands = st.multiselect("Indicator band", bands, default=bands)
    departments = sorted(scored["Department"].dropna().astype(str).unique().tolist()) if "Department" in scored else []
    selected_departments = st.multiselect("Department", departments, default=departments) if departments else []

view = scored[scored["Marks"].between(*mark_range)].copy()
if selected_bands:
    view = view[view["Indicator_Band"].astype(str).isin(selected_bands)]
if departments and selected_departments:
    view = view[view["Department"].astype(str).isin(selected_departments)]
if view.empty:
    st.warning("No rows match the selected filters. Adjust the filters in the sidebar.")
    st.stop()

academic = academic_summary(view)
attendance = attendance_summary(view)
mean_indicator = view["Campus_Indicator"].mean()
metrics = st.columns(5)
metrics[0].metric("Students", f"{len(view):,}")
metrics[1].metric("Average marks", f"{academic['mean']:.1f}%" if academic["mean"] is not None else "N/A")
metrics[2].metric("Pass rate", f"{academic['pass_rate']:.1f}%" if academic["pass_rate"] is not None else "N/A")
metrics[3].metric("Avg attendance", f"{attendance['mean']:.1f}%" if attendance["mean"] is not None else "N/A")
metrics[4].metric("Avg indicator", f"{mean_indicator:.1f}/100" if pd.notna(mean_indicator) else "N/A")
st.caption(f"Data source: {source} · Showing {len(view):,} of {len(scored):,} rows")

tabs = st.tabs(["Overview", "Academics", "Attendance", "Insights", "Data quality", "Student Support", "Student Profile", "Methodology"])
with tabs[0]:
    left, right = st.columns([1.3, 1])
    left.plotly_chart(indicator_bar(view), use_container_width=True)
    right.subheader("Indicator band distribution")
    right.bar_chart(view["Indicator_Band"].astype(str).value_counts())
    st.info("Indicator groups are descriptive summaries, not predictions or labels of student ability.")
    dept = department_summary(view)
    if not dept.empty:
        st.subheader("Department comparison")
        st.dataframe(dept, use_container_width=True, hide_index=True)
with tabs[1]:
    st.plotly_chart(marks_histogram(view), use_container_width=True)
    st.write({"Median marks": academic["median"], "Highest marks": academic["highest"], "Lowest marks": academic["lowest"], "Standard deviation": academic["std"]})
    cols = [c for c in ["Name", "Department", "Year", "Marks", "Campus_Indicator", "Indicator_Coverage", "Indicator_Band"] if c in view]
    st.dataframe(view[cols].sort_values("Marks", ascending=False), use_container_width=True, hide_index=True)
with tabs[2]:
    if "Attendance" in view and view["Attendance"].notna().any():
        st.plotly_chart(attendance_histogram(view), use_container_width=True)
        st.write(f"Below 75% reference: {attendance['below_threshold']} · At/above: {attendance['at_or_above_threshold']}")
        cols = [c for c in ["Name", "Department", "Attendance", "Marks"] if c in view]
        st.dataframe(view[cols].sort_values("Attendance"), use_container_width=True, hide_index=True)
    else:
        st.info("No usable Attendance values. Add an Attendance column from 0–100.")
with tabs[3]:
    corr = correlation_matrix(view)
    if not corr.empty:
        st.subheader("Correlation matrix")
        st.dataframe(corr, use_container_width=True)
        st.pyplot(correlation_heatmap(view), use_container_width=True)
        st.caption("Correlation describes association; it does not establish causation.")
    else:
        st.info("At least two usable numeric metrics with paired observations are needed for correlation analysis.")
    st.subheader("IQR outlier exploration")
    outliers = outlier_summary(view)
    if outliers.empty:
        st.info("At least four valid observations per metric are needed for IQR outlier exploration.")
    else:
        st.dataframe(outliers, use_container_width=True, hide_index=True)
    st.caption("Outlier flags are prompts for data review, not judgements about students.")
with tabs[4]:
    st.subheader("Data preview")
    st.dataframe(raw.head(50), use_container_width=True, hide_index=True)
    st.subheader("Quality report")
    quality = quality_report(raw)
    st.dataframe(quality, use_container_width=True, hide_index=True)
    q1, q2, q3 = st.columns(3)
    q1.metric("Rows", len(raw))
    q2.metric("Columns", len(raw.columns))
    q3.metric("Exact duplicate rows", int(raw.duplicated().sum()))
with tabs[5]:
    st.subheader("Student Support Intelligence")
    st.caption("Transparent support screening based on configured marks and attendance thresholds. Not a predictive diagnosis.")

    support = build_support_plan(view)
    counts = support["Support_Status"].value_counts()

    m1, m2, m3 = st.columns(3)
    m1.metric("High support priority", int(counts.get("High support priority", 0)))
    m2.metric("Academic support", int(counts.get("Needs academic support", 0)))
    m3.metric("Attendance support", int(counts.get("Needs attendance support", 0)))

    st.subheader("Student support plans")
    support_columns = [
        c for c in [
            "Name", "Department", "Marks", "Attendance",
            "Support_Status", "Support_Reason", "Recommended_Action"
        ] if c in support.columns
    ]
    st.dataframe(
        support[support_columns],
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "Download student support plan",
        csv_bytes(support[support_columns]),
        "campuspulse_student_support_plan.csv",
        "text/csv",
        use_container_width=True
    )

    st.info("Support statuses are review prompts. They should not be used alone for disciplinary, admission, or other high-stakes decisions.")

with tabs[6]:
    st.subheader("Individual Student Profile")
    st.caption("A student-level view of the available academic and attendance data.")

    profile_data = view.reset_index(drop=True).copy()

    def student_label(i):
        row = profile_data.iloc[i]
        name = str(row.get("Name", "Unknown"))
        department = str(row.get("Department", "Department not available"))
        return f"{name} | {department} | Record {i + 1}"

    selected_student = st.selectbox(
        "Select a student",
        options=list(range(len(profile_data))),
        format_func=student_label,
        key="student_profile_selector"
    )

    student = profile_data.iloc[selected_student]
    st.divider()

    st.subheader(str(student.get("Name", "Student")))

    metric_columns = st.columns(3)

    marks_value = pd.to_numeric(
        pd.Series([student.get("Marks")]), errors="coerce"
    ).iloc[0]

    attendance_value = pd.to_numeric(
        pd.Series([student.get("Attendance")]), errors="coerce"
    ).iloc[0]

    indicator_value = pd.to_numeric(
        pd.Series([student.get("Campus_Indicator")]), errors="coerce"
    ).iloc[0]

    metric_columns[0].metric(
        "Marks",
        f"{marks_value:.1f}%" if pd.notna(marks_value) else "N/A"
    )
    metric_columns[1].metric(
        "Attendance",
        f"{attendance_value:.1f}%" if pd.notna(attendance_value) else "N/A"
    )
    metric_columns[2].metric(
        "Campus Indicator",
        f"{indicator_value:.1f}/100" if pd.notna(indicator_value) else "N/A"
    )

    st.subheader("Student information")
    detail_columns = [
        c for c in [
            "Name", "Department", "Year", "Marks", "Attendance",
            "Study_Hours", "Sleep_Hours", "Screen_Time",
            "Campus_Indicator", "Indicator_Coverage", "Indicator_Band"
        ] if c in profile_data.columns
    ]

    st.dataframe(
        student[detail_columns].to_frame("Value"),
        use_container_width=True
    )

    st.subheader("Performance overview")
    chart_values = {
        "Marks": marks_value,
        "Attendance": attendance_value,
        "Campus Indicator": indicator_value
    }
    chart_data = pd.DataFrame([
        {"Metric": name, "Score": value}
        for name, value in chart_values.items()
        if pd.notna(value)
    ])

    if not chart_data.empty:
        st.bar_chart(chart_data.set_index("Metric"))
    else:
        st.info("No numeric performance values are available for this student.")

    st.subheader("Student support assessment")
    student_support = build_support_plan(
        profile_data.iloc[[selected_student]].copy()
    )

    support_fields = [
        c for c in [
            "Support_Status", "Support_Reason", "Recommended_Action"
        ] if c in student_support.columns
    ]

    if support_fields:
        st.dataframe(
            student_support[support_fields],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Support assessment is not available.")

    st.download_button(
        "Download individual student report",
        csv_bytes(profile_data.iloc[[selected_student]]),
        "campuspulse_individual_student_report.csv",
        "text/csv",
        use_container_width=True
    )
    st.download_button(
        "Download individual student PDF",
        student_pdf_bytes(
            profile_data.iloc[[selected_student]].copy(),
            source
        ),
        "campuspulse_individual_student_report.pdf",
        "application/pdf",
        use_container_width=True
    )

    st.info(
        "This profile is a descriptive review tool. Support recommendations "
        "require human review and must not be treated as predictions or diagnoses."
    )

with tabs[7]:
    st.subheader("Campus Indicator methodology")
    st.write("The Campus Indicator is a transparent weighted descriptive score. It is not a trained machine-learning model and is not validated for student selection, diagnosis, or prediction.")
    weights = pd.DataFrame({"Component": ["Marks", "Attendance", "Study hours", "Sleep target score", "Screen-time target score"], "Weight": [40, 25, 15, 10, 10], "Transformation": ["Marks as percentage", "Attendance as percentage", "4 study hours maps to 100; capped at 100", "Illustrative target of 8 hours", "Illustrative target of 2 hours; penalty above target"]})
    st.dataframe(weights, use_container_width=True, hide_index=True)
    st.write("Missing components are excluded from an individual calculation. Remaining weights are renormalised, and Indicator_Coverage reports the share of configured weight represented by available data.")
    st.warning("Sleep and screen-time transformations are illustrative design assumptions, not medical or behavioural guidance.")

st.divider()
st.subheader("Export reports")
col_a, col_b = st.columns(2)
with col_a:
    st.download_button("Download filtered analytics CSV", csv_bytes(view), "campuspulse_analytics.csv", "text/csv", use_container_width=True)
with col_b:
    st.download_button("Download data quality CSV", csv_bytes(quality_report(raw)), "campuspulse_quality.csv", "text/csv", use_container_width=True)
st.caption("Privacy first: use synthetic data or properly anonymised, consented data. Do not upload identifiable student records to a public demo.")
