import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px

sns.set_theme(style="whitegrid")

def marks_histogram(df):
    return px.histogram(df, x="Marks", nbins=15, title="Marks distribution", template="plotly_dark")
def attendance_histogram(df):
    return px.histogram(df.dropna(subset=["Attendance"]), x="Attendance", nbins=12, title="Attendance distribution", template="plotly_dark")
def indicator_bar(df):
    data = df.dropna(subset=["Campus_Indicator"]).nlargest(15,"Campus_Indicator")
    return px.bar(data, x="Name", y="Campus_Indicator", color="Indicator_Band", title="Top descriptive indicator values", template="plotly_dark")
def correlation_heatmap(df):
    cols = [c for c in ["Marks","Attendance","Sleep_Hours","Study_Hours","Screen_Time"] if c in df]
    corr = df[cols].apply(__import__("pandas").to_numeric, errors="coerce").corr()
    fig, ax = plt.subplots(figsize=(7,4.5))
    if corr.empty: ax.text(.5,.5,"Not enough numeric data",ha="center"); ax.axis("off")
    else: sns.heatmap(corr, annot=True, cmap="vlag", center=0, vmin=-1, vmax=1, ax=ax)
    fig.tight_layout()
    return fig
