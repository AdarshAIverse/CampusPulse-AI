import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import pandas as pd

sns.set_theme(style="whitegrid")

def marks_histogram(df):
    data = df.dropna(subset=["Marks"])
    return px.histogram(data, x="Marks", nbins=15, title="Marks distribution", template="plotly_dark", labels={"Marks": "Marks (%)", "count": "Students"})

def attendance_histogram(df):
    data = df.dropna(subset=["Attendance"]) if "Attendance" in df else pd.DataFrame(columns=["Attendance"])
    return px.histogram(data, x="Attendance", nbins=12, title="Attendance distribution", template="plotly_dark", labels={"Attendance": "Attendance (%)", "count": "Students"})

def indicator_bar(df):
    data = df.dropna(subset=["Campus_Indicator"]).nlargest(15, "Campus_Indicator")
    return px.bar(data, x="Name", y="Campus_Indicator", color="Indicator_Band", title="Top descriptive indicator values", template="plotly_dark", labels={"Name": "Student label", "Campus_Indicator": "Indicator (0-100)"})

def correlation_heatmap(df):
    cols = [c for c in ["Marks", "Attendance", "Sleep_Hours", "Study_Hours", "Screen_Time"] if c in df]
    numeric = df[cols].apply(pd.to_numeric, errors="coerce") if cols else pd.DataFrame()
    corr = numeric.corr(min_periods=2).dropna(axis=0, how="all").dropna(axis=1, how="all") if not numeric.empty else pd.DataFrame()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    if corr.empty or corr.shape[1] < 2:
        ax.text(.5, .5, "Not enough paired numeric data", ha="center", va="center")
        ax.axis("off")
    else:
        sns.heatmap(corr, annot=True, cmap="vlag", center=0, vmin=-1, vmax=1, ax=ax)
        ax.set_title("Relationships between available metrics")
    fig.tight_layout()
    return fig
