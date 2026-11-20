import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import pandas as pd


# Consistent chart styling
sns.set_theme(
    style="whitegrid",
    context="notebook",
    font_scale=1.0
)


def marks_histogram(df):
    """Create an interactive distribution chart for student marks."""
    if "Marks" not in df.columns:
        return px.histogram(
            title="Marks data is unavailable",
            template="plotly_dark"
        )

    data = df.dropna(subset=["Marks"]).copy()
    data["Marks"] = pd.to_numeric(data["Marks"], errors="coerce")
    data = data.dropna(subset=["Marks"])

    return px.histogram(
        data,
        x="Marks",
        nbins=15,
        title="Marks distribution",
        template="plotly_dark",
        labels={
            "Marks": "Marks (%)",
            "count": "Number of students"
        }
    )


def attendance_histogram(df):
    """Create an interactive attendance distribution chart."""
    if "Attendance" not in df.columns:
        return px.histogram(
            title="Attendance data is unavailable",
            template="plotly_dark"
        )

    data = df.dropna(subset=["Attendance"]).copy()
    data["Attendance"] = pd.to_numeric(
        data["Attendance"], errors="coerce"
    )
    data = data.dropna(subset=["Attendance"])

    return px.histogram(
        data,
        x="Attendance",
        nbins=12,
        title="Attendance distribution",
        template="plotly_dark",
        labels={
            "Attendance": "Attendance (%)",
            "count": "Number of students"
        }
    )


def indicator_bar(df):
    """Display the top 15 descriptive Campus Indicator values."""
    required = ["Name", "Campus_Indicator", "Indicator_Band"]

    if not all(col in df.columns for col in required):
        return px.bar(
            title="Campus Indicator data is unavailable",
            template="plotly_dark"
        )

    data = df.copy()
    data["Campus_Indicator"] = pd.to_numeric(
        data["Campus_Indicator"], errors="coerce"
    )
    data = data.dropna(subset=["Campus_Indicator"])
    data = data.nlargest(15, "Campus_Indicator")

    return px.bar(
        data,
        x="Name",
        y="Campus_Indicator",
        color="Indicator_Band",
        title="Top descriptive indicator values",
        template="plotly_dark",
        labels={
            "Name": "Student label",
            "Campus_Indicator": "Indicator (0-100)",
            "Indicator_Band": "Indicator category"
        }
    )


def correlation_heatmap(df):
    """
    Generate a Matplotlib correlation heatmap.

    Uses available numeric student metrics and handles
    missing or insufficient data safely.
    """
    cols = [
        col for col in [
            "Marks",
            "Attendance",
            "Sleep_Hours",
            "Study_Hours",
            "Screen_Time"
        ]
        if col in df.columns
    ]

    # Convert available columns to numeric values
    if cols:
        numeric = df[cols].apply(
            pd.to_numeric,
            errors="coerce"
        )
    else:
        numeric = pd.DataFrame()

    # Calculate correlation only when numeric data exists
    if not numeric.empty:
        corr = numeric.corr(min_periods=2)
        corr = corr.dropna(axis=0, how="all")
        corr = corr.dropna(axis=1, how="all")
    else:
        corr = pd.DataFrame()

    # Create a Matplotlib figure
    fig, ax = plt.subplots(figsize=(8, 5))

    if corr.empty or corr.shape[1] < 2:
        ax.text(
            0.5,
            0.5,
            "Not enough paired numeric data",
            ha="center",
            va="center",
            fontsize=12,
            transform=ax.transAxes
        )
        ax.set_title("Metric correlation analysis")
        ax.axis("off")

    else:
        sns.heatmap(
            corr,
            annot=True,
            fmt=".2f",
            cmap="vlag",
            center=0,
            vmin=-1,
            vmax=1,
            linewidths=0.5,
            square=True,
            ax=ax,
            cbar_kws={
                "label": "Correlation coefficient"
            }
        )

        ax.set_title(
            "Relationships between available metrics",
            fontsize=13,
            fontweight="bold",
            pad=12
        )
        ax.set_xlabel("Student metrics")
        ax.set_ylabel("Student metrics")

        ax.tick_params(
            axis="x",
            labelrotation=30,
            labelsize=9
        )
        ax.tick_params(
            axis="y",
            labelrotation=0,
            labelsize=9
        )

    # Matplotlib uses tight_layout(), not Plotly's update_layout()
    fig.tight_layout()

    return fig