from __future__ import annotations

"""
CampusPulse AI — redesigned single-file Streamlit application.

Features:
- Existing academic, attendance, support, quality, profile and export workflows
- Model comparison (Logistic Regression, Random Forest, Gradient Boosting)
- Held-out evaluation, cross-validation, permutation importance and explanations
- Dataset-aware Q&A assistant (local, deterministic; optional OpenAI API integration)
- PDF/CSV reporting
- SQLite by default; PostgreSQL when DATABASE_URL + SQLAlchemy/psycopg are configured
- Admin, faculty and student roles with scoped views
- Notification centre and optional SMTP email
- Input validation, audit metadata, safer password hashing and deployment guidance

Important:
- Predictions require a genuine historical target column. Never fabricate labels from the
  Campus Indicator or use protected/sensitive attributes as predictors.
- PostgreSQL is enabled by DATABASE_URL. SQLite is for local development.
- Configure secrets with environment variables or Streamlit secrets, never in source code.
"""

from pathlib import Path
from datetime import datetime, timezone
from io import BytesIO
from typing import Any
import hashlib
import hmac
import logging
import os
import re
import secrets
import sqlite3
import sys
import smtplib
from email.message import EmailMessage

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from campuspulse.pdf_reporting import student_pdf_bytes, campus_pdf_bytes
from campuspulse.data import load_dataset, DatasetError, quality_report
from campuspulse.scoring import calculate_indicator
from campuspulse.analytics import (
    academic_summary, attendance_summary, correlation_matrix,
    outlier_summary, department_summary,
)
from campuspulse.charts import (
    marks_histogram, attendance_histogram, indicator_bar, correlation_heatmap,
)
from campuspulse.reporting import csv_bytes
from campuspulse.interventions import build_support_plan
from campuspulse.config import MAX_UPLOAD_MB

from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score,
)

try:
    from sqlalchemy import create_engine, text as sql_text
    from sqlalchemy.exc import SQLAlchemyError
except Exception:
    create_engine = None
    sql_text = None
    SQLAlchemyError = Exception

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("campuspulse")

st.set_page_config(
    page_title="CampusPulse AI | Campus Intelligence",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Configuration and database
# ---------------------------------------------------------------------------

def secret(name: str, default: str = "") -> str:
    value = os.getenv(name, "")
    if value:
        return value
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return default


DATABASE_URL = secret("DATABASE_URL")
OPENAI_API_KEY = secret("OPENAI_API_KEY")
OPENAI_MODEL = secret("OPENAI_MODEL", "gpt-4o-mini")
SMTP_HOST = secret("SMTP_HOST")
SMTP_PORT = int(secret("SMTP_PORT", "587") or "587")
SMTP_USER = secret("SMTP_USER")
SMTP_PASSWORD = secret("SMTP_PASSWORD")
SMTP_FROM = secret("SMTP_FROM", SMTP_USER)


def db_kind() -> str:
    return "PostgreSQL" if DATABASE_URL.startswith(("postgres://", "postgresql://")) else "SQLite"


@st.cache_resource
def get_engine():
    if DATABASE_URL.startswith(("postgres://", "postgresql://")):
        if create_engine is None:
            raise RuntimeError("Install SQLAlchemy and psycopg[binary] to use PostgreSQL.")
        url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return create_engine(url, pool_pre_ping=True, pool_recycle=1800)
    return None


def db_execute(query: str, params: dict[str, Any] | None = None, fetch: bool = False):
    params = params or {}
    engine = get_engine()
    if engine is not None:
        with engine.begin() as conn:
            result = conn.execute(sql_text(query), params)
            return result.mappings().all() if fetch else result.rowcount
    conn = sqlite3.connect(ROOT / "data" / "campuspulse.db", timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(query, params)
        rows = [dict(r) for r in cur.fetchall()] if fetch else cur.rowcount
        conn.commit()
        return rows
    finally:
        conn.close()


def init_db():
    if get_engine() is not None:
        statements = [
            """CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(100) PRIMARY KEY, password_hash TEXT NOT NULL,
                salt TEXT NOT NULL, role VARCHAR(20) NOT NULL,
                student_key TEXT, email TEXT, created_at TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS activity (
                id SERIAL PRIMARY KEY, username TEXT NOT NULL, event TEXT NOT NULL,
                details TEXT, created_at TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY, recipient TEXT, title TEXT NOT NULL,
                message TEXT NOT NULL, severity TEXT NOT NULL DEFAULT 'info',
                is_read INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS interventions (
                id SERIAL PRIMARY KEY, student_key TEXT NOT NULL, owner TEXT NOT NULL,
                action TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Open',
                follow_up TEXT, created_at TEXT NOT NULL)""",
        ]
    else:
        statements = [
            """CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY, password_hash TEXT NOT NULL,
                salt TEXT NOT NULL, role TEXT NOT NULL,
                student_key TEXT, email TEXT, created_at TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL,
                event TEXT NOT NULL, details TEXT, created_at TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT, recipient TEXT,
                title TEXT NOT NULL, message TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'info', is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS interventions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, student_key TEXT NOT NULL,
                owner TEXT NOT NULL, action TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open', follow_up TEXT, created_at TEXT NOT NULL)""",
        ]
    for statement in statements:
        db_execute(statement)


def log_activity(username: str, event: str, details: str = ""):
    db_execute(
        "INSERT INTO activity(username,event,details,created_at) VALUES(:u,:e,:d,:t)",
        {"u": username, "e": event, "d": details[:500],
         "t": datetime.now(timezone.utc).isoformat()},
    )


def digest_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 420_000).hex()


def create_account(username: str, password: str, role: str, student_key: str = "", email: str = ""):
    username = username.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,40}", username):
        return False, "Username must be 3–40 characters: letters, numbers, dot, dash or underscore."
    if len(password) < 12:
        return False, "Use a password with at least 12 characters."
    if role not in {"admin", "faculty", "student"}:
        return False, "Invalid role."
    salt = secrets.token_bytes(16)
    try:
        db_execute(
            """INSERT INTO users(username,password_hash,salt,role,student_key,email,created_at)
               VALUES(:u,:p,:s,:r,:k,:m,:t)""",
            {"u": username, "p": digest_password(password, salt), "s": salt.hex(),
             "r": role, "k": student_key.strip(), "m": email.strip(),
             "t": datetime.now(timezone.utc).isoformat()},
        )
        return True, "Account created."
    except Exception:
        LOG.exception("Account creation failed")
        return False, "Could not create account. The username may already exist."


def authenticate(username: str, password: str):
    rows = db_execute(
        "SELECT username,password_hash,salt,role,student_key,email FROM users WHERE username=:u",
        {"u": username.strip()}, fetch=True,
    )
    if not rows:
        # Constant-ish work for unknown users
        digest_password(password, b"campuspulse-dummy")
        return None
    row = rows[0]
    candidate = digest_password(password, bytes.fromhex(row["salt"]))
    if hmac.compare_digest(candidate, row["password_hash"]):
        return {k: row[k] for k in ("username", "role", "student_key", "email")}
    return None


def count_users() -> int:
    return len(db_execute("SELECT username FROM users", fetch=True))


def add_notification(recipient: str | None, title: str, message: str, severity: str = "info"):
    db_execute(
        """INSERT INTO notifications(recipient,title,message,severity,is_read,created_at)
           VALUES(:r,:t,:m,:s,0,:d)""",
        {"r": recipient, "t": title[:150], "m": message[:1000],
         "s": severity, "d": datetime.now(timezone.utc).isoformat()},
    )


def send_email(to_email: str, subject: str, body: str) -> tuple[bool, str]:
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMTP_FROM]):
        return False, "SMTP is not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD and SMTP_FROM."
    try:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = SMTP_FROM, to_email, subject
        msg.set_content(body)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True, "Email sent."
    except Exception:
        LOG.exception("Email send failed")
        return False, "Email could not be sent. Check SMTP configuration."


# ---------------------------------------------------------------------------
# Authentication and roles
# ---------------------------------------------------------------------------

def auth_ui():
    st.markdown('<div class="auth-shell">', unsafe_allow_html=True)
    st.title("🎓 CampusPulse AI")
    st.caption("Secure campus intelligence workspace")
    if count_users() == 0:
        st.info("First launch: create the initial administrator account.")
        with st.form("bootstrap_admin"):
            u = st.text_input("Administrator username")
            p = st.text_input("Password (12+ characters)", type="password")
            p2 = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create administrator", width="stretch")
        if submitted:
            if p != p2:
                st.error("Passwords do not match.")
            else:
                ok, msg = create_account(u, p, "admin")
                (st.success if ok else st.error)(msg)
                if ok:
                    st.rerun()
    login_tab, register_tab = st.tabs(["Sign in", "Request / create student account"])
    with login_tab:
        with st.form("login"):
            u = st.text_input("Username", key="login_u")
            p = st.text_input("Password", type="password", key="login_p")
            go = st.form_submit_button("Sign in", width="stretch")
        if go:
            account = authenticate(u, p)
            if account:
                st.session_state.account = account
                log_activity(account["username"], "login")
                st.rerun()
            else:
                st.error("Incorrect username or password.")
    with register_tab:
        st.caption("Self-registration creates a student account. Faculty/admin accounts must be provisioned by an administrator.")
        with st.form("student_register"):
            u = st.text_input("Choose username", key="reg_u")
            p = st.text_input("Choose password (12+ characters)", type="password", key="reg_p")
            p2 = st.text_input("Confirm password", type="password", key="reg_p2")
            student_key = st.text_input("Student ID / roll number")
            email = st.text_input("Email (optional)")
            go = st.form_submit_button("Create student account", width="stretch")
        if go:
            if p != p2:
                st.error("Passwords do not match.")
            elif not student_key.strip():
                st.error("Student ID is required for a student account.")
            else:
                ok, msg = create_account(u, p, "student", student_key, email)
                (st.success if ok else st.error)(msg)
    st.markdown("</div>", unsafe_allow_html=True)


init_db()
if "account" not in st.session_state:
    st.session_state.account = None
if st.session_state.account is None:
    auth_ui()
    st.stop()

USER = st.session_state.account
ROLE = USER["role"]
USERNAME = USER["username"]

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

st.markdown("""
<style>
:root{color-scheme:dark}
.stApp{background:#09111f;color:#e8f0fb}
.block-container{max-width:1540px;padding-top:1.2rem;padding-bottom:3rem}
[data-testid="stSidebar"]{background:#101c30;border-right:1px solid #263b59}
h1,h2,h3{color:#f2f7ff!important;letter-spacing:-.025em}
p,li,label{color:#c9d7e9}
[data-testid="stMetric"]{background:linear-gradient(145deg,#14243b,#102038);border:1px solid #294362;border-radius:16px;padding:16px}
[data-testid="stMetricValue"]{color:#65c5ff}
.hero{padding:28px 30px;border-radius:22px;background:linear-gradient(115deg,#142c4d,#12679a 58%,#51418b);border:1px solid #72c8ff55;box-shadow:0 18px 50px #0003}
.hero h1{font-size:2.2rem;margin:0;color:white!important}
.hero p{font-size:1rem;margin:.45rem 0 0;color:#e3f2ff}
.panel{background:#111f33;border:1px solid #293e5a;border-radius:16px;padding:18px}
.stButton button,.stDownloadButton button{border-radius:10px;min-height:42px;font-weight:650}
*:focus-visible{outline:3px solid #ffd166!important;outline-offset:3px!important}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Dataset helpers
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_sample():
    return load_dataset(ROOT / "data" / "sample_students.csv")


@st.cache_data(show_spinner=False)
def cached_indicator(df):
    return calculate_indicator(df)


def recommendations(row: pd.Series) -> list[str]:
    actions = []
    marks = pd.to_numeric(pd.Series([row.get("Marks")]), errors="coerce").iloc[0]
    att = pd.to_numeric(pd.Series([row.get("Attendance")]), errors="coerce").iloc[0]
    hours = pd.to_numeric(pd.Series([row.get("Study_Hours")]), errors="coerce").iloc[0]
    if pd.notna(marks) and marks < 40:
        actions.append("Offer a supportive academic check-in and a focused subject-wise recovery plan.")
    elif pd.notna(marks) and marks < 60:
        actions.append("Provide targeted practice, faculty office hours and a two-week progress review.")
    if pd.notna(att) and att < 75:
        actions.append("Privately discuss attendance barriers and agree a supportive attendance plan.")
    elif pd.notna(att) and att < 85:
        actions.append("Monitor attendance weekly and check for timetable or travel barriers.")
    if pd.notna(hours) and hours < 2:
        actions.append("Help the student build a realistic, consistent weekly study routine.")
    return actions or ["No immediate rule-based support flag. Continue routine mentoring and review new data."]


def make_features(df: pd.DataFrame, target: str):
    y = df[target]
    X = df.drop(columns=[target]).copy()
    excluded = {
        "Student_ID", "Name", "Email", "Phone", "Address",
        "Gender", "Date_of_Birth", "DOB", "Caste", "Religion",
    }
    X = X.drop(columns=[c for c in X.columns if c in excluded], errors="ignore")
    return X, y
def make_features(df: pd.DataFrame, target: str):
    y = df[target]
    valid = y.notna()
    data = df.loc[valid].copy()
    y = y.loc[valid].astype(str)
    forbidden = {
        target, "name", "student_id", "studentid", "roll_no", "rollno",
        "email", "phone", "mobile", "address",
    }
    # Avoid common sensitive or protected attributes.
    forbidden.update({"gender", "religion", "caste", "ethnicity", "disability"})
    features = [c for c in data.columns if c.strip().lower() not in forbidden]
    X = data[features].select_dtypes(include=["number", "object", "category", "bool"])
    if X.empty:
        raise ValueError("No usable predictor columns remain after excluding identifiers and sensitive fields.")
    return X, y


def build_pipeline(X: pd.DataFrame, algorithm: str, seed: int):
    numeric = X.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical = [c for c in X.columns if c not in numeric]
    transformers = []
    if numeric:
        transformers.append(("num", Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]), numeric))
    if categorical:
        transformers.append(("cat", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]), categorical))
    prep = ColumnTransformer(transformers)
    models = {
        "Logistic Regression": LogisticRegression(max_iter=1500, class_weight="balanced"),
        "Random Forest": RandomForestClassifier(
            n_estimators=300, min_samples_leaf=2, class_weight="balanced",
            random_state=seed, n_jobs=-1,
        ),
        "Gradient Boosting": GradientBoostingClassifier(random_state=seed),
    }
    return Pipeline([("prep", prep), ("model", models[algorithm])])


def compare_models(df: pd.DataFrame, target: str, test_size: float, seed: int):
    X, y = make_features(df, target)
    if len(y) < 30:
        raise ValueError("Use at least 30 labelled rows for a meaningful initial comparison.")
    if y.nunique() < 2:
        raise ValueError("Target must contain at least two classes.")
    counts = y.value_counts()
    if counts.min() < 2:
        raise ValueError("Each target class needs at least two examples for a stratified split.")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )
    results, fitted = [], {}
    for name in ["Logistic Regression", "Random Forest", "Gradient Boosting"]:
        pipe = build_pipeline(X, name, seed)
        pipe.fit(X_train, y_train)
        pred = pipe.predict(X_test)
        scores = {
            "Model": name,
            "Accuracy": accuracy_score(y_test, pred),
            "Precision": precision_score(y_test, pred, average="weighted", zero_division=0),
            "Recall": recall_score(y_test, pred, average="weighted", zero_division=0),
            "F1": f1_score(y_test, pred, average="weighted", zero_division=0),
        }
        try:
            if y.nunique() == 2:
                scores["ROC AUC"] = roc_auc_score(y_test, pipe.predict_proba(X_test)[:, 1])
            else:
                scores["ROC AUC"] = np.nan
        except Exception:
            scores["ROC AUC"] = np.nan
        results.append(scores)
        fitted[name] = pipe
    table = pd.DataFrame(results).sort_values("F1", ascending=False)
    best_name = str(table.iloc[0]["Model"])
    best = fitted[best_name]
    cv_scores = None
    folds = min(5, int(counts.min()))
    if folds >= 2:
        try:
            cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
            cv_scores = cross_val_score(build_pipeline(X, best_name, seed), X, y,
                                        cv=cv, scoring="f1_weighted", n_jobs=1)
        except Exception:
            LOG.exception("Cross validation failed")
    pred = best.predict(X_test)
    labels = sorted(y.unique())
    cm = confusion_matrix(y_test, pred, labels=labels)
    try:
        importance = permutation_importance(
            best, X_test, y_test, n_repeats=8, random_state=seed,
            scoring="f1_weighted", n_jobs=1,
        )
        imp = pd.DataFrame({
            "Feature": X_test.columns,
            "Importance": importance.importances_mean,
            "Std": importance.importances_std,
        }).sort_values("Importance", ascending=False)
    except Exception:
        LOG.exception("Permutation importance failed")
        imp = pd.DataFrame(columns=["Feature", "Importance", "Std"])
    bundle = {
        "models": fitted, "best_name": best_name, "best": best,
        "features": list(X.columns), "target": target,
        "labels": labels, "confusion": cm,
        "report": classification_report(y_test, pred, zero_division=0),
        "X_test": X_test, "y_test": y_test, "importance": imp,
        "train_rows": len(X_train), "test_rows": len(X_test),
    }
    return table, bundle, cv_scores


def prediction_frame(df: pd.DataFrame, bundle: dict):
    target = bundle["target"]
    X = df.drop(columns=[target], errors="ignore").copy()
    forbidden = {"name", "student_id", "studentid", "roll_no", "rollno",
                 "email", "phone", "mobile", "address", "gender", "religion",
                 "caste", "ethnicity", "disability"}
    X = X.drop(columns=[c for c in X if c.strip().lower() in forbidden], errors="ignore")
    X = X.reindex(columns=bundle["features"])
    model = bundle["best"]
    pred = model.predict(X)
    prob = model.predict_proba(X) if hasattr(model, "predict_proba") else None
    return pred, prob


# ---------------------------------------------------------------------------
# Natural-language assistant and reports
# ---------------------------------------------------------------------------

def local_answer(question: str, df: pd.DataFrame) -> str:
    """Answer a safe subset of questions using calculations on the current dataset."""
    q = question.lower()
    if any(word in q for word in ["lowest attendance", "low attendance", "attendance below"]):
        if "Attendance" not in df:
            return "The uploaded dataset has no Attendance column."
        threshold = 75
        subset = df[pd.to_numeric(df["Attendance"], errors="coerce") < threshold]
        return f"{len(subset)} of {len(df)} records have attendance below {threshold}%. " \
               f"Average attendance in this filtered group: " \
               f"{pd.to_numeric(subset['Attendance'], errors='coerce').mean():.1f}%." if len(subset) else "No records are below 75% attendance."
    if any(word in q for word in ["average marks", "mean marks", "average score"]):
        if "Marks" not in df:
            return "The uploaded dataset has no Marks column."
        return f"Average marks: {pd.to_numeric(df['Marks'], errors='coerce').mean():.2f}%."
    if "department" in q and any(word in q for word in ["compare", "average", "performance", "lowest", "highest"]):
        if not {"Department", "Marks"}.issubset(df.columns):
            return "Department and Marks columns are required for this comparison."
        result = df.assign(Marks=pd.to_numeric(df["Marks"], errors="coerce")).groupby("Department")["Marks"].mean().sort_values()
        return "Department average marks (ascending):\n" + result.round(2).to_string()
    if "how many" in q or "number of students" in q or "student count" in q:
        return f"The current dataset contains {len(df)} records."
    if "pass rate" in q and "Marks" in df:
        marks = pd.to_numeric(df["Marks"], errors="coerce").dropna()
        return f"Pass rate using 40% as the reference threshold: {(marks.ge(40).mean()*100):.1f}%."
    if "missing" in q or "data quality" in q:
        missing = df.isna().sum().sort_values(ascending=False)
        return "Missing values by column:\n" + missing[missing.gt(0)].to_string() if missing.gt(0).any() else "No missing values were detected."
    return ("I can currently answer dataset questions about student count, average marks, "
            "pass rate (40% reference), attendance below 75%, department marks and missing values. "
            "For broader questions, connect an AI API key or ask a more specific question.")


def assistant_answer(question: str, df: pd.DataFrame) -> str:
    if not OPENAI_API_KEY:
        return local_answer(question, df)
    try:
        from openai import OpenAI
        # Send only aggregate dataset context, not identifiable student records.
        numeric = df.select_dtypes(include=np.number).describe().round(2).to_string()
        counts = {c: df[c].nunique() for c in df.select_dtypes(exclude=np.number).columns[:10]}
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.2,
            messages=[
                {"role": "system", "content":
                 "You are CampusPulse's campus analytics assistant. Use only supplied aggregate "
                 "statistics. Do not infer individual student facts, diagnose, or make high-stakes "
                 "decisions. State when data is insufficient. Recommend human review."},
                {"role": "user", "content":
                 f"Aggregate numeric summary:\n{numeric}\nCategorical distinct counts:\n{counts}\n"
                 f"Question: {question}"},
            ],
        )
        return response.choices[0].message.content or "No answer was returned."
    except Exception:
        LOG.exception("AI assistant request failed")
        return "The AI service could not be reached. Local dataset Q&A is still available:\n\n" + local_answer(question, df)


def report_summary(df: pd.DataFrame) -> str:
    lines = [
        f"CampusPulse AI report — {datetime.now().strftime('%d %b %Y %H:%M')}",
        f"Records analysed: {len(df)}",
        f"Columns: {len(df.columns)}",
    ]
    if "Marks" in df:
        marks = pd.to_numeric(df["Marks"], errors="coerce")
        lines += [f"Average marks: {marks.mean():.2f}%",
                  f"Pass rate (40% reference): {marks.ge(40).mean()*100:.1f}%"]
    if "Attendance" in df:
        att = pd.to_numeric(df["Attendance"], errors="coerce")
        lines += [f"Average attendance: {att.mean():.2f}%",
                  f"Below 75% attendance: {att.lt(75).sum()}"]
    if "Department" in df and "Marks" in df:
        lines.append("Department average marks:")
        lines.append(df.assign(_marks=pd.to_numeric(df["Marks"], errors="coerce"))
                     .groupby("Department")["_marks"].mean().round(2).to_string())
    lines.append("Interpretation: descriptive analytics only; validate findings with authorized staff.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Startup and account header
# ---------------------------------------------------------------------------

st.markdown("""
<div class="hero">
<h1>CampusPulse AI</h1>
<p>One intelligent workspace for academic insight, early support and campus decisions.</p>
</div>
""", unsafe_allow_html=True)
st.caption(f"Signed in as **{USERNAME}** · Role: **{ROLE.title()}** · Database: **{db_kind()}**")

with st.sidebar:
    st.markdown("### Workspace")
    st.write(f"**{USERNAME}**")
    st.caption(ROLE.title())
    if st.button("Sign out", width="stretch"):
        log_activity(USERNAME, "logout")
        st.session_state.account = None
        for key in ["ml_bundle", "ml_table", "ml_cv"]:
            st.session_state.pop(key, None)
        st.rerun()

# ---------------------------------------------------------------------------
# Dataset ingestion
# ---------------------------------------------------------------------------

with st.sidebar:
    st.divider()
    st.subheader("Data source")
    upload = st.file_uploader("Upload student CSV", type=["csv"])
    use_demo = st.checkbox("Use sample dataset", value=upload is None)

try:
    if upload is not None:
        if upload.size > MAX_UPLOAD_MB * 1024 * 1024:
            st.error(f"File exceeds the {MAX_UPLOAD_MB} MB upload limit.")
            st.stop()
        raw, notices = load_dataset(upload)
        source = upload.name
    elif use_demo:
        raw, notices = load_sample()
        source = "Sample dataset"
    else:
        st.info("Upload a CSV dataset to continue.")
        st.stop()
except DatasetError as exc:
    st.error(str(exc))
    st.stop()
except Exception as exc:
    LOG.exception("Dataset load error")
    st.error(f"Dataset could not be loaded: {exc}")
    st.stop()

if not isinstance(raw, pd.DataFrame) or raw.empty:
    st.error("The dataset is empty or invalid.")
    st.stop()
for note in notices:
    st.warning(str(note))

# Save metadata once per distinct session/source, not every rerun.
fingerprint = hashlib.sha256(
    (source + str(raw.shape) + "|".join(map(str, raw.columns))).encode()
).hexdigest()[:16]
if st.session_state.get("dataset_fingerprint") != fingerprint:
    db_execute(
        "INSERT INTO activity(username,event,details,created_at) VALUES(:u,:e,:d,:t)",
        {"u": USERNAME, "e": "dataset_loaded",
         "d": f"{source}; rows={len(raw)}; cols={len(raw.columns)}",
         "t": datetime.now(timezone.utc).isoformat()},
    )
    st.session_state.dataset_fingerprint = fingerprint

try:
    scored = cached_indicator(raw)
except Exception as exc:
    LOG.exception("Indicator calculation failed")
    st.error(f"Could not calculate Campus Indicator: {exc}")
    st.stop()

# ---------------------------------------------------------------------------
# Role-scoped views and filters
# ---------------------------------------------------------------------------

if ROLE == "student":
    key_col = next((c for c in ["Student_ID", "StudentID", "Roll_No", "Roll Number"] if c in scored.columns), None)
    if key_col is None or not USER.get("student_key"):
        st.error("Your account is not linked to a student record. Contact an administrator.")
        st.stop()
    student_rows = scored[key_col].astype(str).str.strip() == str(USER["student_key"]).strip()
    if not student_rows.any():
        st.error("No matching student record was found. Contact your administrator.")
        st.stop()
    scored = scored.loc[student_rows].copy()

with st.sidebar:
    st.divider()
    st.subheader("Filters")
    marks = pd.to_numeric(scored["Marks"], errors="coerce").dropna() if "Marks" in scored else pd.Series(dtype=float)
    if not marks.empty:
        lo, hi = float(marks.min()), float(marks.max())
        mark_filter = st.slider("Marks range", min_value=float(min(0, lo)),
                                max_value=float(max(100, hi)), value=(lo, hi))
    else:
        mark_filter = None
    bands = sorted(scored["Indicator_Band"].dropna().astype(str).unique()) if "Indicator_Band" in scored else []
    band_filter = st.multiselect("Indicator band", bands, default=bands)
    depts = sorted(scored["Department"].dropna().astype(str).unique()) if "Department" in scored else []
    dept_filter = st.multiselect("Department", depts, default=depts)

view = scored.copy()
if mark_filter and "Marks" in view:
    view = view[pd.to_numeric(view["Marks"], errors="coerce").between(*mark_filter)]
if band_filter and "Indicator_Band" in view:
    view = view[view["Indicator_Band"].astype(str).isin(band_filter)]
if dept_filter and "Department" in view:
    view = view[view["Department"].astype(str).isin(dept_filter)]
if view.empty:
    st.warning("No rows match the selected filters.")
    st.stop()

# ---------------------------------------------------------------------------
# Notifications and interventions
# ---------------------------------------------------------------------------

def user_notifications():
    return db_execute(
        """SELECT id,title,message,severity,is_read,created_at FROM notifications
           WHERE recipient IS NULL OR recipient=:u ORDER BY id DESC LIMIT 50""",
        {"u": USERNAME}, fetch=True,
    )


# Create non-duplicated in-app alerts for low attendance / marks.
if ROLE in {"admin", "faculty"}:
    alert_key = f"alerts_{fingerprint}"
    if st.session_state.get(alert_key) != True:
        for _, row in view.iterrows():
            flags = []
            m = pd.to_numeric(pd.Series([row.get("Marks")]), errors="coerce").iloc[0]
            a = pd.to_numeric(pd.Series([row.get("Attendance")]), errors="coerce").iloc[0]
            if pd.notna(m) and m < 40:
                flags.append("marks below 40%")
            if pd.notna(a) and a < 75:
                flags.append("attendance below 75%")
            if flags:
                label = str(row.get("Name", row.get("Student_ID", "Student record")))
                add_notification(None, "Student support review suggested",
                                 f"{label}: {', '.join(flags)}. Please verify and contact the student supportively.",
                                 "warning")
        st.session_state[alert_key] = True

notifications = user_notifications()

# ---------------------------------------------------------------------------
# Dashboard navigation
# ---------------------------------------------------------------------------

if ROLE == "student":
    tab_names = [
        "My Dashboard",
        "My Support Plan",
        "Ask CampusPulse",
        "My Reports",
        "Notifications"
    ]

elif ROLE == "faculty":
    tab_names = [
        "Faculty Overview",
        "Academics",
        "Attendance",
        "Insights",
        "Student Support",
        "Interventions",
        "AI & ML Lab",
        "Ask CampusPulse",
        "Reports",
        "Notifications"
    ]

else:  # Admin
    tab_names = [
        "Executive Overview",
        "Academics",
        "Attendance",
        "Insights",
        "Data Quality",
        "Student Support",
        "Student Profile",
        "AI & ML Lab",
        "Ask CampusPulse",
        "Interventions",
        "Reports",
        "Notifications",
        "User Management",
        "System Health"
    ]

tabs = st.tabs(tab_names)
tab = {name: tabs[i] for i, name in enumerate(tab_names)}

def metric_row(df: pd.DataFrame):
    c = st.columns(5)
    c[0].metric("Students", f"{len(df):,}")
    if "Marks" in df:
        m = pd.to_numeric(df["Marks"], errors="coerce")
        c[1].metric("Average marks", f"{m.mean():.1f}%")
        c[2].metric("Pass rate", f"{m.ge(40).mean()*100:.1f}%")
    if "Attendance" in df:
        a = pd.to_numeric(df["Attendance"], errors="coerce")
        c[3].metric("Average attendance", f"{a.mean():.1f}%")
    if "Campus_Indicator" in df:
        c[4].metric("Campus Indicator", f"{pd.to_numeric(df['Campus_Indicator'], errors='coerce').mean():.1f}/100")
# ---------------------------------------------------------------------------
# Overview / student dashboard
# ---------------------------------------------------------------------------

overview_name = (
    "My Dashboard" if ROLE == "student"
    else ("Faculty Overview" if ROLE == "faculty" else "Executive Overview")
)

with tab[overview_name]:
    st.subheader(
        "Your campus at a glance"
        if ROLE != "student"
        else "Your academic snapshot"
    )

    metric_row(view)

    left, right = st.columns(2)

    if "Marks" in view:
        left.plotly_chart(
            marks_histogram(view),
            width="stretch",
            key="overview_marks_histogram"
        )

    if "Indicator_Band" in view:
        right.plotly_chart(
            px.histogram(
                view,
                x="Indicator_Band",
                color="Indicator_Band",
                title="Campus Indicator bands"
            ),
            width="stretch",
            key="overview_indicator_bands"
        )

    if ROLE != "student" and "Department" in view:
        dept = department_summary(view)

        if isinstance(dept, pd.DataFrame) and not dept.empty:
            st.subheader("Department comparison")
            st.dataframe(
                dept,
                width="stretch",
                hide_index=True
            )

    st.info(
        "Campus Indicator is a descriptive weighted score, not an ML prediction."
    )


# ---------------------------------------------------------------------------
# Academics, Attendance and Insights
# ---------------------------------------------------------------------------

if ROLE != "student":

    with tab["Academics"]:
        st.subheader("Academic performance")

        if "Marks" in view:
            st.plotly_chart(
                marks_histogram(view),
                width="stretch",
                key="academics_marks_histogram"
            )

            st.dataframe(
                view[
                    [
                        c for c in [
                            "Name", "Department", "Year", "Marks",
                            "Campus_Indicator", "Indicator_Band"
                        ]
                        if c in view
                    ]
                ].sort_values("Marks", ascending=False),
                width="stretch",
                hide_index=True
            )
        else:
            st.info("Marks column is unavailable.")


    with tab["Attendance"]:
        st.subheader("Attendance monitoring")

        if "Attendance" in view and view["Attendance"].notna().any():

            st.plotly_chart(
                attendance_histogram(view),
                width="stretch",
                key="attendance_histogram"
            )

            low = view[
                pd.to_numeric(
                    view["Attendance"],
                    errors="coerce"
                ) < 75
            ]

            st.metric(
                "Records below 75% attendance",
                len(low)
            )

            st.dataframe(
                low[
                    [
                        c for c in [
                            "Name", "Student_ID", "Department",
                            "Attendance", "Marks"
                        ]
                        if c in low
                    ]
                ],
                width="stretch",
                hide_index=True
            )

        else:
            st.info("No usable Attendance column.")


    with tab["Insights"]:
        st.subheader("Advanced interactive analytics")

        numeric = view.select_dtypes(include=np.number)

        if numeric.shape[1] >= 2:
            corr = numeric.corr()

            st.plotly_chart(
                px.imshow(
                    corr,
                    text_auto=".2f",
                    zmin=-1,
                    zmax=1,
                    color_continuous_scale="RdBu_r",
                    title="Correlation explorer"
                ),
                width="stretch",
                key="insights_correlation_explorer"
            )

        if {"Department", "Marks"}.issubset(view.columns):
            st.plotly_chart(
                px.box(
                    view,
                    x="Department",
                    y="Marks",
                    color="Department",
                    points="outliers",
                    title="Marks distribution by department"
                ),
                width="stretch",
                key="insights_department_marks"
            )

        if {"Department", "Attendance", "Marks"}.issubset(view.columns):
            st.plotly_chart(
                px.scatter(
                    view,
                    x="Attendance",
                    y="Marks",
                    color="Department",
                    hover_name="Name" if "Name" in view else None,
                    title="Attendance versus marks"
                ),
                width="stretch",
                key="insights_attendance_vs_marks"
            )

        try:
            out = outlier_summary(view)

            st.subheader("Outlier summary")

            st.dataframe(
                out,
                width="stretch",
                hide_index=True
            )

        except Exception:
            st.info("Outlier summary is unavailable for this dataset.")


    # -----------------------------------------------------------------------
    # Admin Data Quality
    # -----------------------------------------------------------------------

    if ROLE == "admin":

        with tab["Data Quality"]:
            st.subheader("Data quality and validation")

            try:
                q = quality_report(raw)

                st.dataframe(
                    q,
                    width="stretch",
                    hide_index=True
                )

            except Exception as exc:
                st.warning(
                    f"Quality report unavailable: {exc}"
                )

            a, b, c = st.columns(3)

            a.metric("Rows", len(raw))
            b.metric("Columns", len(raw.columns))
            c.metric(
                "Duplicate rows",
                int(raw.duplicated().sum())
            )

            st.dataframe(
                raw.head(100),
                width="stretch",
                hide_index=True
            )


# ---------------------------------------------------------------------------
# Student Support
# ---------------------------------------------------------------------------

support_tab_name = (
    "My Support Plan"
    if ROLE == "student"
    else "Student Support"
)

with tab[support_tab_name]:
    st.subheader("Support and recommendations")

    support = build_support_plan(view)

    if ROLE == "student":

        for action in recommendations(view.iloc[0]):
            st.markdown(f"- {action}")

        st.caption(
            "These suggestions are supportive prompts, "
            "not a diagnosis or academic decision."
        )

    else:

        st.dataframe(
            support,
            width="stretch",
            hide_index=True
        )

        st.download_button(
            "Download support plan CSV",
            csv_bytes(support),
            "campuspulse_support_plan.csv",
            "text/csv"
        )


# ---------------------------------------------------------------------------
# Admin Student Profile
# ---------------------------------------------------------------------------

if ROLE == "admin":

    with tab["Student Profile"]:
        st.subheader("Student profile")

        if "Name" in view:

            choices = list(range(len(view)))
            frame = view.reset_index(drop=True)

            idx = st.selectbox(
                "Select student",
                choices,
                format_func=lambda i: str(frame.iloc[i]["Name"])
            )

            row = frame.iloc[idx]

            st.dataframe(
                row.astype(str).to_frame("Value"),
                width="stretch",
                hide_index=True
            )

            for action in recommendations(row):
                st.markdown(f"- {action}")

            st.download_button(
                "Download profile PDF",
                student_pdf_bytes(
                    frame.iloc[[idx]],
                    source
                ),
                "student_profile.pdf",
                "application/pdf"
            )

        else:
            st.info(
                "A Name column is needed for this profile selector."
            )


# ---------------------------------------------------------------------------
# Student-specific profile content
# ---------------------------------------------------------------------------

if ROLE == "student":

    with tab["My Support Plan"]:
        row = view.iloc[0]

        st.subheader("Personal support suggestions")

        for action in recommendations(row):
            st.markdown(f"- {action}")

        st.caption(
            "Please discuss these suggestions with your faculty mentor."
        )
# ---------------------------------------------------------------------------
# Model comparison and explainability
# ---------------------------------------------------------------------------

if ROLE in {"admin", "faculty"}:
    with tab["AI & ML Lab"]:
        st.subheader("Model comparison and explainable predictions")
        candidates = [c for c in raw.columns if c.strip().lower() in {
            "at_risk", "risk_status", "next_term_result", "outcome", "result_class"
        }]
        candidates += [c for c in raw.columns if c not in candidates and
                       c.strip().lower().endswith(("_label", "_outcome", "_target"))]
        if not candidates:
            st.warning("No recognized labelled outcome column found. Add a genuine historical outcome (e.g. At_Risk) to train models.")
        else:
            c1, c2, c3 = st.columns(3)
            target = c1.selectbox("Historical target", candidates)
            test_size = c2.slider("Test split", 0.15, 0.40, 0.25, 0.05)
            seed = c3.number_input("Random seed", 1, 99999, 42)
            st.caption("Identifiers and common sensitive attributes are excluded from model features. Check your institution's policy before training.")
            if st.button("Compare all models", type="primary"):
                try:
                    with st.spinner("Training and evaluating three classifiers..."):
                        table, bundle, cv = compare_models(raw, target, test_size, int(seed))
                    st.session_state.ml_table = table
                    st.session_state.ml_bundle = bundle
                    st.session_state.ml_cv = cv
                    st.success(f"Comparison complete. Best holdout F1: {bundle['best_name']}")
                except Exception as exc:
                    LOG.exception("Model comparison failed")
                    st.error(str(exc))
            if "ml_table" in st.session_state and st.session_state.get("ml_bundle", {}).get("target") == target:
                table = st.session_state.ml_table
                bundle = st.session_state.ml_bundle
                st.subheader("Model leaderboard")
                st.dataframe(table.style.format(precision=3), width="stretch", hide_index=True)
                st.plotly_chart(px.bar(table, x="Model", y="F1", color="Model",
                                       title="Weighted F1 comparison"), width="stretch")
                st.success(f"Best model: {bundle['best_name']}")
                m = table[table["Model"] == bundle["best_name"]].iloc[0]
                k = st.columns(4)
                for col, metric in zip(k, ["Accuracy","Precision","Recall","F1"]):
                    col.metric(metric, f"{m[metric]:.3f}")
                cv = st.session_state.get("ml_cv")
                if cv is not None:
                    st.metric("Best-model cross-validation F1", f"{cv.mean():.3f} ± {cv.std():.3f}")
                labels = bundle["labels"]
                cm = pd.DataFrame(bundle["confusion"], index=labels, columns=labels)
                st.subheader("Confusion matrix")
                st.plotly_chart(px.imshow(cm, text_auto=True,
                                          labels={"x":"Predicted","y":"Actual","color":"Count"}),
                                width="stretch")
                st.subheader("Classification report")
                st.code(bundle["report"])
                st.subheader("Explainability: permutation feature importance")
                imp = bundle["importance"]
                if not imp.empty:
                    st.plotly_chart(px.bar(imp.head(15).sort_values("Importance"),
                                           x="Importance", y="Feature", orientation="h",
                                           error_x="Std", title="Features that influence held-out F1"),
                                    width="stretch")
                    st.caption("Permutation importance measures how much test performance changes when a feature is shuffled. It is not causal evidence.")
                try:
                    pred, probs = prediction_frame(raw, bundle)
                    output = pd.DataFrame(index=raw.index)
                    if "Name" in raw:
                        output["Student"] = raw["Name"].astype(str)
                    output["Predicted class"] = pred
                    if probs is not None:
                        output["Maximum class probability"] = probs.max(axis=1)
                    st.subheader("Model-assisted review")
                    st.dataframe(output, width="stretch", hide_index=True)
                    st.download_button("Download predictions CSV", csv_bytes(output),
                                       "campuspulse_predictions.csv", "text/csv")
                except Exception as exc:
                    st.warning(f"Prediction for current rows was not available: {exc}")
                st.warning("A model score is not a student verdict. Validate on a future cohort, assess subgroup performance and require human review before any intervention.")

# ---------------------------------------------------------------------------
# Dataset-aware chatbot
# ---------------------------------------------------------------------------

assistant_tab = "Ask CampusPulse"
with tab[assistant_tab]:
    st.subheader("Ask CampusPulse")
    st.caption("Ask questions about aggregate dataset patterns. Identifiable student data is not sent to the optional AI provider.")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    for item in st.session_state.chat_history[-12:]:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
    question = st.chat_input("Ask about attendance, marks, departments, pass rate or data quality...")
    if question:
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("assistant"):
            answer = assistant_answer(question, view)
            st.markdown(answer)
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
    if not OPENAI_API_KEY:
        st.info("Local Q&A is active. To enable broader AI-generated answers, configure OPENAI_API_KEY and install the openai package.")

# ---------------------------------------------------------------------------
# Intervention tracker
# ---------------------------------------------------------------------------

if ROLE in {"admin", "faculty"}:
    with tab["Interventions"]:
        st.subheader("Faculty intervention tracker")
        with st.form("new_intervention"):
            student_id = st.text_input("Student ID / roll number")
            action = st.text_area("Agreed support action")
            follow = st.date_input("Follow-up date")
            save = st.form_submit_button("Save intervention")
        if save:
            if not student_id.strip() or not action.strip():
                st.error("Student ID and support action are required.")
            else:
                db_execute(
                    """INSERT INTO interventions(student_key,owner,action,status,follow_up,created_at)
                       VALUES(:k,:o,:a,'Open',:f,:t)""",
                    {"k": student_id.strip(), "o": USERNAME, "a": action.strip(),
                     "f": follow.isoformat(), "t": datetime.now(timezone.utc).isoformat()},
                )
                log_activity(USERNAME, "intervention_created", student_id)
                st.success("Intervention saved.")
        interventions = db_execute(
            "SELECT id,student_key,owner,action,status,follow_up,created_at FROM interventions ORDER BY id DESC LIMIT 200",
            fetch=True,
        )
        if interventions:
            idf = pd.DataFrame(interventions)
            st.dataframe(idf, width="stretch", hide_index=True)
            open_ids = idf[idf["status"] == "Open"]["id"].tolist()
            if open_ids:
                selected_id = st.selectbox("Mark intervention completed", open_ids)
                if st.button("Mark completed"):
                    db_execute("UPDATE interventions SET status='Completed' WHERE id=:i",
                               {"i": int(selected_id)})
                    st.rerun()

# ---------------------------------------------------------------------------
# Reports and generated summaries
# ---------------------------------------------------------------------------

report_tab = "My Reports" if ROLE == "student" else "Reports"
with tab[report_tab]:
    st.subheader("Reports and exports")
    summary = report_summary(view)
    st.text_area("Generated report summary", summary, height=220)
    col1, col2, col3 = st.columns(3)
    col1.download_button("Download filtered data CSV", csv_bytes(view),
                         "campuspulse_data.csv", "text/csv", width="stretch")
    col2.download_button("Download campus PDF", campus_pdf_bytes(view, source),
                         "campuspulse_report.pdf", "application/pdf", width="stretch")
    if ROLE == "admin" and "Name" in view:
        col3.download_button("Download quality CSV", csv_bytes(quality_report(raw)),
                             "campuspulse_quality.csv", "text/csv", width="stretch")
    if st.button("Create in-app report notification"):
        add_notification(USERNAME, "Report generated", "Your CampusPulse report is ready.", "success")
        st.success("Notification created.")

# ---------------------------------------------------------------------------
# Notification centre
# ---------------------------------------------------------------------------
print("DEBUG ROLE:", ROLE)
print("DEBUG TABS:", list(tab.keys()))
print("NOTIFICATIONS EXISTS:", "Notifications" in tab)
with tab["Notifications"]:
    st.subheader("Notification centre")
    if notifications:
        nf = pd.DataFrame(notifications)
        st.dataframe(nf[["title","message","severity","is_read","created_at"]],
                     width="stretch", hide_index=True)
        unread = nf[nf["is_read"] == 0]["id"].tolist()
        if unread and st.button("Mark my notifications as read"):
            for nid in unread:
                db_execute("UPDATE notifications SET is_read=1 WHERE id=:i", {"i": int(nid)})
            st.rerun()
    else:
        st.info("No notifications yet.")
    if ROLE in {"admin", "faculty"}:
        with st.form("manual_notification"):
            recipient = st.text_input("Recipient username (leave blank for all)")
            title = st.text_input("Notification title")
            message = st.text_area("Message")
            send = st.form_submit_button("Publish notification")
        if send:
            if title.strip() and message.strip():
                add_notification(recipient.strip() or None, title, message, "info")
                st.success("Notification published.")
            else:
                st.error("Title and message are required.")
        if SMTP_HOST:
            with st.form("email_notification"):
                to_email = st.text_input("Email recipient")
                email_subject = st.text_input("Email subject")
                email_body = st.text_area("Email message")
                email_send = st.form_submit_button("Send email")
            if email_send:
                ok, msg = send_email(to_email, email_subject, email_body)
                (st.success if ok else st.error)(msg)

# ---------------------------------------------------------------------------
# User administration and system health
# ---------------------------------------------------------------------------

if ROLE == "admin":
    with tab["User Management"]:
        st.subheader("Role-based account management")
        users = db_execute(
            "SELECT username,role,student_key,email,created_at FROM users ORDER BY created_at",
            fetch=True,
        )
        if users:
            st.dataframe(pd.DataFrame(users), width="stretch", hide_index=True)
        with st.form("admin_create_account"):
            new_u = st.text_input("Username")
            new_p = st.text_input("Temporary password (12+ characters)", type="password")
            new_role = st.selectbox("Role", ["faculty", "student", "admin"])
            new_key = st.text_input("Student ID (required for student role)")
            new_email = st.text_input("Email")
            create = st.form_submit_button("Create account")
        if create:
            if new_role == "student" and not new_key.strip():
                st.error("Student ID is required for student accounts.")
            else:
                ok, msg = create_account(new_u, new_p, new_role, new_key, new_email)
                (st.success if ok else st.error)(msg)
        st.warning("For production, add verified password reset, MFA, rate limiting, account lockout and audited admin recovery. Do not expose this app publicly without those controls.")

    with tab["System Health"]:
        st.subheader("Deployment and system health")
        st.write({
            "Database backend": db_kind(),
            "PostgreSQL configured": bool(DATABASE_URL),
            "OpenAI API configured": bool(OPENAI_API_KEY),
            "SMTP configured": bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD),
            "Python": sys.version.split()[0],
            "Pandas": pd.__version__,
            "Rows loaded": len(raw),
            "Columns loaded": len(raw.columns),
        })
        activity = db_execute(
            "SELECT username,event,details,created_at FROM activity ORDER BY id DESC LIMIT 100",
            fetch=True,
        )
        st.subheader("Recent audit activity")
        if activity:
            st.dataframe(pd.DataFrame(activity), width="stretch", hide_index=True)
        st.markdown("""
        **Production checklist**
        - Use PostgreSQL with TLS and restricted database credentials.
        - Configure secrets in Streamlit secrets / deployment environment.
        - Enable HTTPS at the hosting layer.
        - Back up the database and test restore procedures.
        - Add MFA, verified password reset, rate limiting and session expiry.
        - Run automated tests and review dependency vulnerabilities.
        - Validate model performance on a later cohort and audit subgroup errors.
        """)

# ---------------------------------------------------------------------------
# Footer and safeguards
# ---------------------------------------------------------------------------

st.divider()
st.caption(
    "CampusPulse AI is an educational decision-support prototype. "
    "Predictions and support flags must never be used as the sole basis for "
    "grading, discipline, admission, scholarships or other high-impact decisions. "
    "Use consented, minimized and appropriately anonymized data."
)

