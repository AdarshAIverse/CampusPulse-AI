from pathlib import Path
import logging
import sys

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------
# CAMPUSPULSE AI | PREMIUM STREAMLIT APPLICATION
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from campuspulse.pdf_reporting import student_pdf_bytes, campus_pdf_bytes
from campuspulse.data import load_dataset, DatasetError, quality_report
from campuspulse.scoring import calculate_indicator
from campuspulse.analytics import (
    academic_summary,
    attendance_summary,
    correlation_matrix,
    outlier_summary,
    department_summary,
)
from campuspulse.charts import (
    marks_histogram,
    attendance_histogram,
    indicator_bar,
    correlation_heatmap,
)
from campuspulse.reporting import csv_bytes
from campuspulse.interventions import build_support_plan
from campuspulse.config import MAX_UPLOAD_MB

logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title="CampusPulse AI | Smart Campus Intelligence",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------
# PREMIUM UI THEME
# ---------------------------------------------------------------------

st.markdown(
    """
    <style>
    :root {
        --cp-bg: #07111f;
        --cp-panel: #101e33;
        --cp-panel-2: #142640;
        --cp-line: rgba(148, 190, 230, .16);
        --cp-text: #edf6ff;
        --cp-muted: #a9bdd3;
        --cp-cyan: #55d6f5;
        --cp-blue: #5c9dff;
        --cp-violet: #a78bfa;
        --cp-green: #5ee0b5;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background:
          radial-gradient(ellipse at 8% 0%, rgba(28, 107, 164, .19), transparent 34%),
          radial-gradient(ellipse at 95% 8%, rgba(111, 73, 190, .14), transparent 30%),
          var(--cp-bg);
        color: var(--cp-text);
    }

    [data-testid="stHeader"] {
        background: rgba(7,17,31,.72);
    }

    [data-testid="stToolbar"] {
        right: 1rem;
    }

    .block-container {
        max-width: 1500px;
        padding-top: 1.45rem;
        padding-bottom: 3rem;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(
            180deg,
            #0d1a2c 0%,
            #0a1525 100%
        );
        border-right: 1px solid var(--cp-line);
    }

    [data-testid="stSidebar"] * {
        color: var(--cp-text);
    }

    h1, h2, h3, h4 {
        color: var(--cp-text) !important;
        letter-spacing: -.02em;
    }

    p, li, label, .stMarkdown {
        color: #d5e3f2;
    }

    [data-testid="stCaptionContainer"] p,
    .stCaption {
        color: var(--cp-muted) !important;
    }

    /* HERO SECTION */

    .cp-hero {
        position: relative;
        overflow: hidden;
        text-align: center;
        padding: 38px 26px 30px;
        margin: 3px 0 24px;
        border-radius: 26px;
        border: 1px solid rgba(116, 207, 255, .30);
        background:
          radial-gradient(circle at 14% 18%, rgba(76, 202, 255, .23), transparent 31%),
          radial-gradient(circle at 88% 82%, rgba(133, 100, 255, .22), transparent 32%),
          linear-gradient(125deg, #10223e 0%, #12395b 52%, #172b51 100%);
        box-shadow:
          0 18px 55px rgba(0,0,0,.26),
          inset 0 1px 0 rgba(255,255,255,.07);
    }

    .cp-logo {
        width: 82px;
        height: 82px;
        margin: 0 auto 15px;
        display: grid;
        place-items: center;
        border-radius: 24px;
        background: rgba(107, 211, 255, .13);
        border: 1px solid rgba(180, 232, 255, .25);
        box-shadow: 0 10px 28px rgba(0,0,0,.22);
        font-size: 43px;
    }

    .cp-eyebrow {
        color: #8ceaff;
        font-size: 11px;
        font-weight: 850;
        letter-spacing: 4px;
        margin-bottom: 9px;
    }

    .cp-title {
        color: #fff;
        font-size: clamp(34px, 5vw, 54px);
        font-weight: 850;
        letter-spacing: -2px;
        line-height: 1.1;
        margin: 0;
    }

    .cp-title span {
        color: var(--cp-cyan);
    }

    .cp-subtitle {
        color: #d8f2ff;
        font-size: clamp(16px, 2.2vw, 22px);
        font-weight: 600;
        margin-top: 11px;
    }

    .cp-description {
        max-width: 790px;
        margin: 13px auto 0;
        color: #c8dced;
        font-size: 14px;
        line-height: 1.8;
    }

    .cp-tags {
        margin-top: 19px;
    }

    .cp-tag {
        display: inline-block;
        padding: 7px 13px;
        margin: 4px;
        border: 1px solid rgba(126, 217, 255, .25);
        border-radius: 30px;
        background: rgba(255,255,255,.07);
        color: #bdefff;
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 1px;
    }

    .cp-disclaimer {
        text-align: center;
        color: #91a9c2;
        font-size: 11px;
        margin: -10px 0 24px;
    }

    .section-kicker {
        color: var(--cp-cyan);
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 3px;
    }

    .section-title {
        font-size: 22px;
        font-weight: 800;
        color: #f1f7ff;
    }

    /* METRIC CARDS */

    [data-testid="stMetric"] {
        background: linear-gradient(
            145deg,
            rgba(21,42,68,.96),
            rgba(14,30,50,.96)
        );
        border: 1px solid rgba(123,177,225,.19);
        border-radius: 17px;
        padding: 17px 18px;
        box-shadow: 0 8px 24px rgba(0,0,0,.13);
    }

    [data-testid="stMetricLabel"] {
        color: #a9c1d9 !important;
        font-weight: 650;
    }

    [data-testid="stMetricValue"] {
        color: #73dfff !important;
        font-weight: 800;
    }

    [data-testid="stMetricDelta"] {
        color: #79e6bf !important;
    }

    /* TABS */

    button[data-baseweb="tab"] {
        color: #a9bdd3;
        font-weight: 700;
        font-size: 13px;
        min-height: 44px;
        padding-left: 12px;
        padding-right: 12px;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #75e3ff !important;
        border-bottom: 3px solid #65d8f4 !important;
    }

    /* TABLES */

    [data-testid="stDataFrame"],
    [data-testid="stTable"] {
        border: 1px solid rgba(137,180,220,.22);
        border-radius: 12px;
        overflow: hidden;
    }

    /* BUTTONS */

    .stButton button,
    .stDownloadButton button,
    .stFormSubmitButton button {
        min-height: 43px;
        border-radius: 11px !important;
        font-weight: 750 !important;
        border: 1px solid rgba(105,208,245,.45) !important;
        transition: .18s ease;
    }

    .stButton button:hover,
    .stDownloadButton button:hover {
        border-color: #8ceaff !important;
        transform: translateY(-1px);
    }

    .stDownloadButton button {
        background: linear-gradient(
            110deg,
            #126b9b,
            #315db0
        ) !important;
        color: white !important;
    }

    /* INPUTS */

    .stTextInput input,
    .stNumberInput input,
    .stSelectbox div[data-baseweb="select"],
    .stMultiSelect div[data-baseweb="select"] {
        background: #102139 !important;
        color: #eef7ff !important;
        border-color: rgba(139,190,231,.35) !important;
        min-height: 42px;
    }

    [data-testid="stFileUploader"] section {
        background: rgba(17,38,62,.72);
        border: 1px dashed rgba(114,201,238,.4);
        border-radius: 13px;
    }

    [data-testid="stAlert"] {
        border-radius: 12px;
    }

    hr {
        border-color: rgba(148,190,230,.16);
    }

    *:focus-visible {
        outline: 3px solid #ffd166 !important;
        outline-offset: 3px !important;
    }

    /* MOBILE RESPONSIVENESS */

    @media (max-width: 760px) {
        .block-container {
            padding: 1rem .8rem 2rem;
        }

        .cp-hero {
            padding: 27px 14px 23px;
            border-radius: 19px;
        }

        .cp-logo {
            width: 68px;
            height: 68px;
            font-size: 35px;
            border-radius: 20px;
        }

        .cp-description {
            font-size: 13px;
        }

        button[data-baseweb="tab"] {
            font-size: 11px;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            transition-duration: .01ms !important;
            animation-duration: .01ms !important;
        }
    }
    </style>

    <section class="cp-hero">
      <div class="cp-logo" role="img" aria-label="Graduation cap">🎓</div>

      <div class="cp-eyebrow">
        SMART EDUCATION ANALYTICS
      </div>

      <h1 class="cp-title">
        CampusPulse <span>AI</span>
      </h1>

      <div class="cp-subtitle">
        Smart Campus Intelligence System
      </div>

      <div class="cp-description">
        Turn student data into meaningful academic insights.
        Explore performance, attendance, campus indicators,
        data quality and transparent student-support
        recommendations in one unified intelligence workspace.
      </div>

      <div class="cp-tags">
        <span class="cp-tag">DATA-DRIVEN</span>
        <span class="cp-tag">EXPLAINABLE</span>
        <span class="cp-tag">STUDENT-CENTRED</span>
        <span class="cp-tag">PRIVACY-AWARE</span>
      </div>
    </section>

    <div class="cp-disclaimer">
      Explainable educational analytics prototype ·
      Not a predictive or diagnostic system
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# CACHED FUNCTIONS
# ---------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_sample_dataset():
    return load_dataset(
        PROJECT_ROOT / "data" / "sample_students.csv"
    )


@st.cache_data(show_spinner=False)
def cached_indicator(frame):
    return calculate_indicator(frame)


@st.cache_data(show_spinner=False)
def cached_academic_summary(frame):
    return academic_summary(frame)


@st.cache_data(show_spinner=False)
def cached_attendance_summary(frame):
    return attendance_summary(frame)


@st.cache_data(show_spinner=False)
def cached_correlation_matrix(frame):
    return correlation_matrix(frame)


@st.cache_data(show_spinner=False)
def cached_outlier_summary(frame):
    return outlier_summary(frame)


@st.cache_data(show_spinner=False)
def cached_department_summary(frame):
    return department_summary(frame)


@st.cache_data(show_spinner=False)
def cached_support_plan(frame):
    return build_support_plan(frame)


@st.cache_data(show_spinner=False)
def cached_quality_report(frame):
    return quality_report(frame)


def safe_number(value, suffix=""):
    try:
        number = float(value)

        return (
            f"{number:.1f}{suffix}"
            if pd.notna(number)
            else "N/A"
        )

    except (TypeError, ValueError):
        return "N/A"


# ---------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------

with st.sidebar:

    st.markdown("## 🎓 CampusPulse")
    st.caption("INTELLIGENCE CONTROL CENTRE")

    st.divider()

    st.subheader("Data workspace")

    upload = st.file_uploader(
        "Upload student dataset",
        type=["csv"],
        help=(
            f"CSV only · Maximum file size: "
            f"{MAX_UPLOAD_MB} MB"
        ),
    )

    demo = st.checkbox(
        "Use synthetic sample data",
        value=upload is None,
        help=(
            "Use the bundled synthetic dataset "
            "for a safe demonstration."
        ),
    )

    st.divider()

    st.caption(
        "Your data stays within this app session. "
        "Use anonymised or synthetic records for public demos."
    )


# ---------------------------------------------------------------------
# LOAD DATASET
# ---------------------------------------------------------------------

try:

    if upload is not None:

        if upload.size > MAX_UPLOAD_MB * 1024 * 1024:
            st.error(
                f"File exceeds the {MAX_UPLOAD_MB} MB upload limit."
            )
            st.stop()

        raw, notices = load_dataset(upload)
        source = upload.name

    elif demo:

        raw, notices = load_sample_dataset()
        source = "Synthetic sample"

    else:

        st.info(
            "Upload a CSV or enable synthetic sample data "
            "in the sidebar to begin."
        )
        st.stop()

except DatasetError as exc:

    st.error(str(exc))
    st.stop()

except Exception:

    logging.exception("Dataset processing failed")

    st.error(
        "The dataset could not be processed. "
        "Check the CSV format and required columns."
    )

    st.stop()


for message in notices:
    st.warning(message)


if raw is None or raw.empty:
    st.error("The selected dataset contains no student records.")
    st.stop()


# ---------------------------------------------------------------------
# CAMPUS INDICATOR
# ---------------------------------------------------------------------

try:

    scored = cached_indicator(raw)

except Exception:

    logging.exception("Campus Indicator calculation failed")

    st.error(
        "Campus Indicator calculation failed. "
        "Check the dataset columns and scoring module."
    )

    st.stop()


required_columns = {"Marks", "Name"}

if not required_columns.issubset(scored.columns):
    st.error(
        "The processed dataset must contain Name and Marks columns."
    )
    st.stop()


scored["Marks"] = pd.to_numeric(
    scored["Marks"],
    errors="coerce",
)

valid_marks = scored["Marks"].dropna()

if valid_marks.empty:
    st.error(
        "No valid numeric Marks values were found in the dataset."
    )
    st.stop()


# ---------------------------------------------------------------------
# SIDEBAR FILTERS
# ---------------------------------------------------------------------

with st.sidebar:

    st.subheader("Explore & filter")

    mark_range = st.slider(
        "Marks range (%)",
        min_value=0.0,
        max_value=100.0,
        value=(
            float(max(0, valid_marks.min())),
            float(min(100, valid_marks.max())),
        ),
    )

    bands = (
        sorted(
            scored["Indicator_Band"]
            .dropna()
            .astype(str)
            .unique()
        )
        if "Indicator_Band" in scored
        else []
    )

    selected_bands = st.multiselect(
        "Indicator bands",
        bands,
        default=bands,
    )

    departments = (
        sorted(
            scored["Department"]
            .dropna()
            .astype(str)
            .unique()
        )
        if "Department" in scored
        else []
    )

    selected_departments = st.multiselect(
        "Departments",
        departments,
        default=departments,
    )


# ---------------------------------------------------------------------
# APPLY FILTERS
# ---------------------------------------------------------------------

view = scored[
    scored["Marks"].between(*mark_range)
].copy()


if bands:

    if selected_bands:

        view = view[
            view["Indicator_Band"].astype(str).isin(
                selected_bands
            )
        ]

    else:
        view = view.iloc[0:0]


if departments:

    if selected_departments:

        view = view[
            view["Department"].astype(str).isin(
                selected_departments
            )
        ]

    else:
        view = view.iloc[0:0]


if view.empty:

    st.warning(
        "No records match the current filters. "
        "Adjust the filters in the sidebar."
    )

    st.stop()


# ---------------------------------------------------------------------
# SUMMARY CALCULATIONS
# ---------------------------------------------------------------------

try:

    academic = cached_academic_summary(view)

    attendance = cached_attendance_summary(view)

    mean_indicator = pd.to_numeric(
        view.get("Campus_Indicator"),
        errors="coerce",
    ).mean()

except Exception:

    logging.exception("Summary calculation failed")

    st.error(
        "Unable to calculate dashboard summaries "
        "for this dataset."
    )

    st.stop()


# ---------------------------------------------------------------------
# DASHBOARD KPI CARDS
# ---------------------------------------------------------------------

st.markdown(
    '<div class="section-kicker">LIVE CAMPUS SNAPSHOT</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">Your campus at a glance</div>',
    unsafe_allow_html=True,
)


kpis = st.columns(5)

kpis[0].metric(
    "Students",
    f"{len(view):,}",
)

kpis[1].metric(
    "Average marks",
    safe_number(academic.get("mean"), "%"),
)

kpis[2].metric(
    "Pass rate",
    safe_number(academic.get("pass_rate"), "%"),
)

kpis[3].metric(
    "Avg. attendance",
    safe_number(attendance.get("mean"), "%"),
)

kpis[4].metric(
    "Campus indicator",
    safe_number(mean_indicator, "/100"),
)


st.caption(
    f"Source: {source} · "
    f"Showing {len(view):,} of {len(scored):,} "
    f"records after filters"
)

st.divider()


# ---------------------------------------------------------------------
# DASHBOARD NAVIGATION
# ---------------------------------------------------------------------

tabs = st.tabs(
    [
        "✦ Overview",
        "▤ Academics",
        "◷ Attendance",
        "⌁ Insights",
        "✓ Data Quality",
        "♡ Student Support",
        "◎ Student Profile",
        "ⓘ Methodology",
    ]
)


# ---------------------------------------------------------------------
# TAB 1: OVERVIEW
# ---------------------------------------------------------------------

with tabs[0]:

    left, right = st.columns([1.25, 1])

    with left:

        st.subheader("Campus Indicator distribution")

        st.caption(
            "Descriptive distribution of the calculated "
            "indicator bands."
        )

        st.plotly_chart(
            indicator_bar(view),
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
            },
        )

        distribution = (
            view.groupby(
                "Indicator_Band",
                dropna=False,
            )
            .size()
            .reset_index(name="Students")
            .rename(
                columns={
                    "Indicator_Band": "Indicator band"
                }
            )
        ) if "Indicator_Band" in view else pd.DataFrame()

        with st.expander("View distribution as a table"):

            if not distribution.empty:

                st.dataframe(
                    distribution,
                    use_container_width=True,
                    hide_index=True,
                )

            else:

                st.info(
                    "Indicator band data is unavailable."
                )

    with right:

        st.subheader("Department snapshot")

        dept = cached_department_summary(view)

        if dept is not None and not dept.empty:

            st.dataframe(
                dept,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Department data is not available."
            )

        st.info(
            "Indicator bands are descriptive summaries, "
            "not predictions or labels of student ability."
        )


# ---------------------------------------------------------------------
# TAB 2: ACADEMICS
# ---------------------------------------------------------------------

with tabs[1]:

    st.subheader("Academic performance")

    st.caption(
        "Explore the distribution and summary statistics "
        "of student marks."
    )

    st.plotly_chart(
        marks_histogram(view),
        use_container_width=True,
        config={
            "displayModeBar": True,
            "displaylogo": False,
        },
    )

    stat_cols = st.columns(4)

    stat_cols[0].metric(
        "Median",
        safe_number(academic.get("median"), "%"),
    )

    stat_cols[1].metric(
        "Highest",
        safe_number(academic.get("highest"), "%"),
    )

    stat_cols[2].metric(
        "Lowest",
        safe_number(academic.get("lowest"), "%"),
    )

    stat_cols[3].metric(
        "Std. deviation",
        safe_number(academic.get("std")),
    )

    cols = [
        c
        for c in [
            "Name",
            "Department",
            "Year",
            "Marks",
            "Campus_Indicator",
            "Indicator_Coverage",
            "Indicator_Band",
        ]
        if c in view.columns
    ]

    st.subheader("Student academic records")

    st.dataframe(
        view[cols].sort_values(
            "Marks",
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------------------
# TAB 3: ATTENDANCE
# ---------------------------------------------------------------------

with tabs[2]:

    if (
        "Attendance" in view.columns
        and view["Attendance"].notna().any()
    ):

        st.subheader("Attendance intelligence")

        st.caption(
            "Attendance distribution and individual "
            "student records."
        )

        st.plotly_chart(
            attendance_histogram(view),
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
            },
        )

        a, b, c = st.columns(3)

        a.metric(
            "Average attendance",
            safe_number(attendance.get("mean"), "%"),
        )

        b.metric(
            "Below 75% reference",
            int(attendance.get("below_threshold", 0) or 0),
        )

        c.metric(
            "At / above reference",
            int(attendance.get("at_or_above_threshold", 0) or 0),
        )

        cols = [
            c
            for c in [
                "Name",
                "Department",
                "Attendance",
                "Marks",
            ]
            if c in view.columns
        ]

        st.dataframe(
            view[cols].sort_values("Attendance"),
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No usable Attendance values were found. "
            "Add an Attendance column with values from 0 to 100."
        )


# ---------------------------------------------------------------------
# TAB 4: INSIGHTS
# ---------------------------------------------------------------------

with tabs[3]:

    st.subheader("Relationships & unusual values")

    st.caption(
        "Explore associations between numeric fields. "
        "Correlation does not establish causation."
    )

    corr = cached_correlation_matrix(view)

    if corr is not None and not corr.empty:

        st.markdown("**Correlation matrix**")

        st.dataframe(
            corr,
            use_container_width=True,
        )

        st.markdown("**Correlation heatmap**")

        st.pyplot(
            correlation_heatmap(view),
            use_container_width=True,
        )

    else:

        st.info(
            "At least two usable numeric metrics with paired "
            "observations are required for correlation analysis."
        )

    st.divider()

    st.subheader("IQR outlier exploration")

    outliers = cached_outlier_summary(view)

    if outliers is not None and not outliers.empty:

        st.dataframe(
            outliers,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "At least four valid observations per metric "
            "are needed for IQR outlier exploration."
        )

    st.caption(
        "Outlier flags are prompts for data review, "
        "not judgements about students."
    )


# ---------------------------------------------------------------------
# TAB 5: DATA QUALITY
# ---------------------------------------------------------------------

with tabs[4]:

    st.subheader("Dataset inspection")

    st.caption(
        "Review the imported records and the quality checks "
        "generated by CampusPulse."
    )

    st.markdown("**Data preview**")

    st.dataframe(
        raw.head(50),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("**Quality report**")

    quality = cached_quality_report(raw)

    st.dataframe(
        quality,
        use_container_width=True,
        hide_index=True,
    )

    q1, q2, q3 = st.columns(3)

    q1.metric("Rows", f"{len(raw):,}")

    q2.metric("Columns", f"{len(raw.columns):,}")

    q3.metric(
        "Exact duplicate rows",
        f"{int(raw.duplicated().sum()):,}",
    )


# ---------------------------------------------------------------------
# TAB 6: STUDENT SUPPORT
# ---------------------------------------------------------------------

with tabs[5]:

    st.subheader("Student support intelligence")

    st.caption(
        "Transparent support screening based on configured "
        "marks and attendance thresholds."
    )

    support = cached_support_plan(view)

    if support is None or support.empty:

        st.info(
            "No support recommendations are available "
            "for the selected records."
        )

    else:

        counts = (
            support["Support_Status"].value_counts()
            if "Support_Status" in support
            else pd.Series(dtype=int)
        )

        m1, m2, m3 = st.columns(3)

        m1.metric(
            "High support priority",
            int(counts.get("High support priority", 0)),
        )

        m2.metric(
            "Academic support",
            int(counts.get("Needs academic support", 0)),
        )

        m3.metric(
            "Attendance support",
            int(counts.get("Needs attendance support", 0)),
        )

        st.markdown("**Student support plans**")

        support_cols = [
            c
            for c in [
                "Name",
                "Department",
                "Marks",
                "Attendance",
                "Support_Status",
                "Support_Reason",
                "Recommended_Action",
            ]
            if c in support.columns
        ]

        st.dataframe(
            support[support_cols],
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download student support plan (CSV)",
            data=csv_bytes(support[support_cols]),
            file_name="campuspulse_student_support_plan.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.info(
        "Support statuses are review prompts. Do not use them alone "
        "for disciplinary, admission or other high-stakes decisions."
    )


# ---------------------------------------------------------------------
# TAB 7: STUDENT PROFILE
# ---------------------------------------------------------------------

with tabs[6]:

    st.subheader("Individual student profile")

    st.caption(
        "Select a student to inspect their available academic "
        "and attendance information."
    )

    profile_data = view.reset_index(drop=True).copy()

    def student_label(index):

        row = profile_data.iloc[index]

        name = str(
            row.get("Name", "Unknown")
        )

        department = str(
            row.get("Department", "Department unavailable")
        )

        return (
            f"{name} · {department} · Record {index + 1}"
        )

    selected_student = st.selectbox(
        "Choose student",
        options=list(range(len(profile_data))),
        format_func=student_label,
        key="student_profile_selector",
    )

    student = profile_data.iloc[selected_student]

    st.divider()

    st.markdown(
        f"### {student.get('Name', 'Student')}"
    )

    p1, p2, p3 = st.columns(3)

    marks_value = pd.to_numeric(
        pd.Series([student.get("Marks")]),
        errors="coerce",
    ).iloc[0]

    attendance_value = pd.to_numeric(
        pd.Series([student.get("Attendance")]),
        errors="coerce",
    ).iloc[0]

    indicator_value = pd.to_numeric(
        pd.Series([student.get("Campus_Indicator")]),
        errors="coerce",
    ).iloc[0]

    p1.metric(
        "Marks",
        safe_number(marks_value, "%"),
    )

    p2.metric(
        "Attendance",
        safe_number(attendance_value, "%"),
    )

    p3.metric(
        "Campus indicator",
        safe_number(indicator_value, "/100"),
    )

    detail_cols = [
        c
        for c in [
            "Name",
            "Department",
            "Year",
            "Marks",
            "Attendance",
            "Study_Hours",
            "Sleep_Hours",
            "Screen_Time",
            "Campus_Indicator",
            "Indicator_Coverage",
            "Indicator_Band",
        ]
        if c in profile_data.columns
    ]

    st.markdown("**Student information**")

    st.dataframe(
        student[detail_cols].to_frame("Value"),
        use_container_width=True,
    )

    chart_values = {
        "Marks": marks_value,
        "Attendance": attendance_value,
        "Campus Indicator": indicator_value,
    }

    chart_data = pd.DataFrame(
        [
            {
                "Metric": label,
                "Score": value,
            }
            for label, value in chart_values.items()
            if pd.notna(value)
        ]
    )

    if not chart_data.empty:

        st.markdown("**Performance overview**")

        st.bar_chart(
            chart_data.set_index("Metric")
        )

    st.markdown("**Student support assessment**")

    student_support = cached_support_plan(
        profile_data.iloc[[selected_student]].copy()
    )

    support_fields = [
        c
        for c in [
            "Support_Status",
            "Support_Reason",
            "Recommended_Action",
        ]
        if c in student_support.columns
    ]

    if support_fields:

        st.dataframe(
            student_support[support_fields],
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "Support assessment is not available."
        )

    one_student = profile_data.iloc[
        [selected_student]
    ].copy()

    d1, d2 = st.columns(2)

    with d1:

        st.download_button(
            "Download student CSV",
            data=csv_bytes(one_student),
            file_name="campuspulse_individual_student_report.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with d2:

        st.download_button(
            "Download student PDF",
            data=student_pdf_bytes(one_student, source),
            file_name="campuspulse_individual_student_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    st.info(
        "This profile is a descriptive review tool. "
        "Support recommendations require human review "
        "and are not predictions or diagnoses."
    )


# ---------------------------------------------------------------------
# TAB 8: METHODOLOGY
# ---------------------------------------------------------------------

with tabs[7]:

    st.subheader("How the Campus Indicator works")

    st.write(
        "The Campus Indicator is a transparent weighted "
        "descriptive score. It is not a trained machine-learning "
        "model and is not validated for student selection, "
        "diagnosis or prediction."
    )

    weights = pd.DataFrame(
        {
            "Component": [
                "Marks",
                "Attendance",
                "Study hours",
                "Sleep target score",
                "Screen-time target score",
            ],
            "Weight": [
                40,
                25,
                15,
                10,
                10,
            ],
            "Transformation": [
                "Marks as percentage",
                "Attendance as percentage",
                "4 study hours maps to 100; capped at 100",
                "Illustrative target of 8 hours",
                "Illustrative target of 2 hours; penalty above target",
            ],
        }
    )

    st.dataframe(
        weights,
        use_container_width=True,
        hide_index=True,
    )

    st.write(
        "Missing components are excluded from an individual "
        "calculation. Remaining weights are renormalised, "
        "and Indicator_Coverage reports the share of configured "
        "weight represented by available data."
    )

    st.warning(
        "Sleep and screen-time transformations are illustrative "
        "design assumptions, not medical or behavioural guidance."
    )


# ---------------------------------------------------------------------
# EXPORT CENTRE
# ---------------------------------------------------------------------

st.divider()

st.markdown(
    '<div class="section-kicker">TAKE YOUR INSIGHTS WITH YOU</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">Export centre</div>',
    unsafe_allow_html=True,
)

e1, e2, e3 = st.columns(3)

with e1:

    st.download_button(
        "⬇ Campus analytics CSV",
        data=csv_bytes(view),
        file_name="campuspulse_analytics.csv",
        mime="text/csv",
        use_container_width=True,
    )

with e2:

    st.download_button(
        "⬇ Campus analytics PDF",
        data=campus_pdf_bytes(view, source),
        file_name="campuspulse_campus_report.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

with e3:

    st.download_button(
        "⬇ Data quality CSV",
        data=csv_bytes(cached_quality_report(raw)),
        file_name="campuspulse_quality.csv",
        mime="text/csv",
        use_container_width=True,
    )


# ---------------------------------------------------------------------
# FOOTER
# ---------------------------------------------------------------------

st.divider()

st.caption(
    "CampusPulse AI · Smart Campus Intelligence System · "
    "Privacy first: use synthetic data or properly anonymised, "
    "consented records. Do not upload identifiable student "
    "records to a public demo."
)