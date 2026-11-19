# CampusPulse AI — Smart Campus Intelligence System

A privacy-aware, explainable **data analytics prototype** for academic, attendance and student-experience trends.

## Features
- CSV upload, schema validation, numeric/range checks, missing-value and duplicate reporting
- Academic and attendance summaries, interactive charts, correlation and IQR outlier exploration
- Transparent weighted Campus Indicator with per-record input coverage
- Streamlit dashboard, CSV exports, CLI summary, modular package and automated tests
- Uses Python, Pandas, NumPy, Plotly, Seaborn and Matplotlib
- No API keys, external calls, or hidden data collection

> This is an educational prototype, not a validated AI prediction system. The indicator is a transparent heuristic, not a diagnosis or measure of student potential. Use synthetic or consented, anonymised data only.

## Run (Windows)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```
## Run (macOS/Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
Tests: `python -m pytest -q`  
CLI: `python main.py`

## CSV schema
Required: `Name`, `Marks`. Optional: `Attendance`, `Sleep_Hours`, `Study_Hours`, `Screen_Time`, `Department`, `Year`, `Student_ID`.
Marks/Attendance must be 0–100; hour values 0–24. Bad numeric cells and out-of-range values are converted to missing and reported. Extra columns are retained. Demo data is synthetic and pseudonymous.

## Indicator methodology
Default weights: Marks 40%, Attendance 25%, Study Hours 15%, Sleep target score 10%, Screen-time target score 10%. Weights are renormalised over available values for each row and `Indicator_Coverage` exposes the percentage of configured weight represented. Transformations are visible in `src/campuspulse/scoring.py`. Targets are illustrative design assumptions, not health guidance.

## Structure
- `app.py`: Streamlit interface
- `main.py`: command-line demo
- `src/campuspulse/data.py`: validation and quality report
- `analytics.py`: descriptive statistics
- `scoring.py`: explainable indicator
- `charts.py`: Plotly, Seaborn and Matplotlib charts
- `reporting.py`: export helpers
- `tests/`: automated unit tests

## Hackathon demo checklist
1. Show data upload, validation warnings, dashboard filters and exports.
2. Explain the indicator weights, transformations and coverage.
3. Test malformed CSV, missing optional columns, invalid ranges and tiny datasets.
4. Explain that correlation is not causation and outlier flags are review prompts.
5. Discuss consent, anonymisation, access control, retention and limitations.

## Security / production roadmap
Uploads are processed in memory and not persisted by default. Do not publicly deploy identifiable student data. Production needs institutional SSO/RBAC, encrypted storage, audit logs, retention controls, rate limiting, dependency scanning and formal model validation. Keep dependencies updated.


## Upgrade notes
- Expanded data validation and quality reporting.
- Added component-level indicator transparency and explicit methodology tab.
- Added optional department filtering and department summary.
- Added stronger edge-case tests and CSV spreadsheet compatibility.
