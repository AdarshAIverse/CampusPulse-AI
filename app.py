from pathlib import Path
import logging
import pandas as pd
import streamlit as st
from campuspulse.data import load_dataset, DatasetError, quality_report
from campuspulse.scoring import calculate_indicator
from campuspulse.analytics import academic_summary, attendance_summary, correlation_matrix, outlier_summary
from campuspulse.charts import marks_histogram, attendance_histogram, indicator_bar, correlation_heatmap
from campuspulse.reporting import csv_bytes

logging.basicConfig(level=logging.INFO)
st.set_page_config(page_title="CampusPulse AI", page_icon="🎓", layout="wide")
st.title("🎓 CampusPulse AI")
st.subheader("Smart Campus Intelligence System")
st.caption("Educational analytics prototype · Synthetic demo data · Not a predictive or diagnostic system")
with st.sidebar:
    st.header("Control centre")
    upload = st.file_uploader("Upload student CSV", type=["csv"])
    demo = st.checkbox("Use synthetic sample data", value=upload is None)
try:
    if upload is not None:
        raw, notices = load_dataset(upload); source = upload.name
    elif demo:
        raw, notices = load_dataset(Path(__file__).parent/"data"/"sample_students.csv"); source = "Synthetic sample"
    else:
        st.info("Upload a CSV or enable sample data."); st.stop()
except DatasetError as exc:
    st.error(str(exc)); st.stop()
except Exception:
    logging.exception("Dataset processing failed")
    st.error("Unable to process this CSV. Confirm it has Name and Marks columns."); st.stop()
for message in notices: st.warning(message)
scored = calculate_indicator(raw)
with st.sidebar:
    lo, hi = float(scored.Marks.min()), float(scored.Marks.max())
    mark_range = st.slider("Marks range", 0.0, 100.0, (max(0.0,lo), min(100.0,hi)))
    bands = sorted(scored.Indicator_Band.astype(str).unique().tolist())
    selected = st.multiselect("Indicator band", bands, default=bands)
view = scored[scored.Marks.between(*mark_range)].copy()
if selected: view = view[view.Indicator_Band.astype(str).isin(selected)]
if view.empty: st.warning("No rows match the selected filters."); st.stop()
a, t = academic_summary(view), attendance_summary(view)
m = st.columns(5)
m[0].metric("Students",len(view))
m[1].metric("Average marks",f"{a['mean']:.1f}%" if a["mean"] is not None else "N/A")
m[2].metric("Pass rate",f"{a['pass_rate']:.1f}%" if a["pass_rate"] is not None else "N/A")
m[3].metric("Avg attendance",f"{t['mean']:.1f}%" if t["mean"] is not None else "N/A")
mean_i = view.Campus_Indicator.mean()
m[4].metric("Avg indicator",f"{mean_i:.1f}/100" if pd.notna(mean_i) else "N/A")
st.caption(f"Data source: {source} · Showing {len(view)} of {len(scored)} rows")
tabs = st.tabs(["Overview","Academics","Attendance","Insights","Data quality"])
with tabs[0]:
    x,y=st.columns([1.3,1])
    x.plotly_chart(indicator_bar(view),use_container_width=True)
    y.subheader("Indicator band distribution"); y.bar_chart(view.Indicator_Band.astype(str).value_counts())
    st.info("Indicator groups are descriptive summaries, not predictions or labels of student ability.")
with tabs[1]:
    st.plotly_chart(marks_histogram(view),use_container_width=True)
    st.dataframe(view[["Name","Marks","Campus_Indicator","Indicator_Coverage","Indicator_Band"]].sort_values("Marks",ascending=False),use_container_width=True,hide_index=True)
with tabs[2]:
    if "Attendance" in view and view.Attendance.notna().any():
        st.plotly_chart(attendance_histogram(view),use_container_width=True)
        st.write(f"Below 75% reference: {t['below_threshold']} · At/above: {t['at_or_above_threshold']}")
        st.dataframe(view[["Name","Attendance","Marks"]].sort_values("Attendance"),use_container_width=True,hide_index=True)
    else: st.info("No usable Attendance values. Add an Attendance column from 0–100.")
with tabs[3]:
    corr=correlation_matrix(view)
    if not corr.empty:
        st.subheader("Correlation matrix"); st.dataframe(corr,use_container_width=True)
        st.pyplot(correlation_heatmap(view),use_container_width=True)
        st.caption("Correlation is association, not proof of causation.")
    st.subheader("IQR outlier exploration"); st.dataframe(outlier_summary(view),use_container_width=True,hide_index=True)
    st.caption("Outlier flags prompt data review; they are not judgements about people.")
with tabs[4]:
    st.subheader("Data preview"); st.dataframe(raw.head(30),use_container_width=True,hide_index=True)
    st.subheader("Quality report"); st.dataframe(quality_report(raw),use_container_width=True,hide_index=True)
    st.write(f"Rows: {len(raw)} · Columns: {len(raw.columns)} · Exact duplicate rows: {raw.duplicated().sum()}")
st.divider()
st.download_button("Download filtered analytics CSV",csv_bytes(view),"campuspulse_analytics.csv","text/csv")
st.download_button("Download data quality CSV",csv_bytes(quality_report(raw)),"campuspulse_quality.csv","text/csv")
st.caption("Privacy first: use synthetic or properly anonymised, consented data.")
