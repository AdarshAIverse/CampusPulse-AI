REQUIRED_COLUMNS = ("Name", "Marks")
NUMERIC_RANGES = {
    "Marks": (0, 100),
    "Attendance": (0, 100),
    "Sleep_Hours": (0, 24),
    "Study_Hours": (0, 24),
    "Screen_Time": (0, 24),
}
DEFAULT_WEIGHTS = {
    "Marks": 0.40,
    "Attendance": 0.25,
    "Study_Hours": 0.15,
    "Sleep_Hours": 0.10,
    "Screen_Time": 0.10,
}
PASS_MARK = 40
ATTENDANCE_THRESHOLD = 75
MAX_UPLOAD_MB = 10
