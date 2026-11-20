CampusPulse AI — Smart Campus Intelligence System

CampusPulse AI is a privacy-aware, explainable campus analytics prototype designed to explore academic performance, attendance patterns, and student-support indicators through an interactive dashboard.

It helps users understand campus-level trends and identify records that may benefit from further review using transparent, rule-based analytics.

«Important: CampusPulse AI is an educational analytics prototype. It is not a validated AI prediction system, medical tool, diagnostic system, or measure of student potential. Its indicators are descriptive and rule-based, not trained machine-learning predictions.»

---

Key Features

1. Interactive Dashboard

- Dark-themed Streamlit interface.
- Campus-level academic and attendance summaries.
- Interactive charts and department comparisons.
- Filters for exploring uploaded datasets.

2. Data Upload and Quality Analysis

- CSV file upload and schema validation.
- Missing-value and duplicate reporting.
- Numeric and range validation.
- Data quality summaries and warnings.

3. Academic and Attendance Analytics

- Marks and attendance summaries.
- Correlation analysis.
- IQR-based outlier exploration.
- Department-level comparisons and insights.

4. Explainable Campus Indicator

- Transparent weighted scoring methodology.
- Per-record indicator coverage.
- Visible scoring transformations.
- Weights are adjusted according to available input values.

5. Student Support

- Rule-based student-support screening.
- Identifies records that may need further review.
- Provides explainable support indicators.
- Does not make automated academic or personal decisions.

6. Individual Student Profile

- Individual student information and analytics.
- Student-level academic and attendance details.
- Individual CSV and PDF report downloads.

7. Reports and Exports

- Campus analytics CSV export.
- Campus analytics PDF report.
- Individual student CSV and PDF reports.
- Data quality reporting.

8. Testing and Modular Architecture

- Modular Python package.
- Automated unit tests using pytest.
- CLI demonstration through "main.py".

---

Technology Stack

Technology| Purpose
Python| Core programming language
Streamlit| Interactive dashboard
Pandas| Data processing
NumPy| Numerical operations
Plotly| Interactive charts
Seaborn| Data visualization
Matplotlib| Data visualization
ReportLab| PDF report generation
Pytest| Automated testing

---

Installation and Setup

Windows

Open PowerShell in the project directory.

py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

Run the application

python -m streamlit run app.py

Run automated tests

python -m pytest -v

Run the CLI demo

python main.py

macOS / Linux

python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m streamlit run app.py

---

CSV Input Schema

The application accepts CSV datasets.

Required columns:

- "Name"
- "Marks"

Optional columns:

- "Attendance"
- "Sleep_Hours"
- "Study_Hours"
- "Screen_Time"
- "Department"
- "Year"
- "Student_ID"

Validation Rules

- Marks: 0–100.
- Attendance: 0–100.
- Hour-based values: 0–24.
- Invalid numeric cells and out-of-range values are converted to missing values and reported.
- Extra columns are retained.

The built-in demonstration dataset contains synthetic, pseudonymous data.

---

Campus Indicator Methodology

The Campus Indicator is a transparent weighted score based on available input values.

Component| Default Weight
Marks| 40%
Attendance| 25%
Study Hours| 15%
Sleep Target Score| 10%
Screen-Time Target Score| 10%

How it works

1. Each available component is transformed into a score.
2. Configured weights are renormalised over the available values for each record.
3. The final indicator is calculated using the available weighted components.
4. "Indicator_Coverage" reports the percentage of configured weight represented by available inputs.

The transformations are implemented in:

"src/campuspulse/scoring.py"

Sleep and screen-time targets are illustrative design assumptions, not health guidance.

---

Student Support Methodology

The Student Support feature uses transparent, rule-based screening.

It highlights records that may deserve further attention based on available academic and attendance information.

- Screening rules are not trained machine-learning models.
- A flagged record does not establish that a student is facing a problem.
- Results should be reviewed by authorised people and interpreted with context.
- The system must not be used as the sole basis for decisions about students.

---

Project Structure

CampusPulse_AI_Hackathon/
│
├── app.py
├── main.py
├── requirements.txt
├── pyproject.toml
├── README.md
│
├── .streamlit/
│   └── config.toml
│
├── data/
│
├── src/
│   └── campuspulse/
│       ├── analytics.py
│       ├── charts.py
│       ├── config.py
│       ├── data.py
│       ├── scoring.py
│       ├── reporting.py
│       ├── interventions.py
│       └── pdf_reporting.py
│
└── tests/
    ├── test_analytics.py
    ├── test_data.py
    ├── test_scoring.py
    └── test_interventions.py

---

Hackathon Demonstration Flow

A suggested demonstration sequence:

1. Open the CampusPulse AI dashboard.
2. Upload a sample CSV dataset.
3. Demonstrate validation warnings and data quality reporting.
4. Explore academic and attendance analytics.
5. Show department comparisons and correlation analysis.
6. Explain the Campus Indicator weights and coverage.
7. Demonstrate Student Support screening.
8. Open an individual Student Profile.
9. Download campus-level and individual PDF reports.
10. Explain privacy safeguards, limitations, and future improvements.

---

Privacy and Responsible Use

CampusPulse AI is designed as a privacy-aware educational prototype.

- Use synthetic, anonymised, or properly consented data.
- Do not upload identifiable student information to a public deployment.
- Restrict access to sensitive datasets.
- Follow institutional data-protection requirements.

Before production use, additional safeguards would be required, including institutional authentication, role-based access control, encrypted storage, audit logs, retention controls, and security reviews.

---

Limitations

- The Campus Indicator is a heuristic, not a validated predictive model.
- Student Support uses predefined rules rather than trained AI.
- Correlation does not establish causation.
- Outlier detection identifies records for review, not necessarily errors.
- Sleep and screen-time targets are illustrative assumptions.
- Results depend on the quality and completeness of uploaded data.

---

Future Scope

Potential improvements include:

- Role-based access for students, faculty, and administrators.
- More advanced data-quality diagnostics.
- Configurable indicator weights.
- Additional explainability and reporting features.
- Improved accessibility and dashboard usability.
- Security, privacy, and institutional validation before real-world deployment.

---

Project Status

CampusPulse AI is an educational hackathon prototype with an interactive Streamlit dashboard, modular analytics, explainable scoring, rule-based student-support screening, individual student profiles, PDF/CSV reporting, and automated tests.

Built with Python and Streamlit.