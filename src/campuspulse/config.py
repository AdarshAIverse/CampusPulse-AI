REQUIRED_COLUMNS = ("Name", "Marks")
NUMERIC_RANGES = {"Marks": (0, 100), "Attendance": (0, 100), "Sleep_Hours": (0, 24), "Study_Hours": (0, 24), "Screen_Time": (0, 24)}
DEFAULT_WEIGHTS = {"Marks": .40, "Attendance": .25, "Study_Hours": .15, "Sleep_Hours": .10, "Screen_Time": .10}
PASS_MARK = 40
ATTENDANCE_THRESHOLD = 75
