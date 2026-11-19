from pathlib import Path
from campuspulse.data import load_dataset
from campuspulse.analytics import academic_summary, attendance_summary
from campuspulse.scoring import calculate_indicator

def main():
    df, notes = load_dataset(Path(__file__).parent/"data"/"sample_students.csv")
    result = calculate_indicator(df)
    print("CAMPUSPULSE — SMART CAMPUS INTELLIGENCE")
    print("Rows:", len(result))
    print("Academic:", academic_summary(result))
    print("Attendance:", attendance_summary(result))
    print(result.nlargest(5,"Campus_Indicator")[["Name","Campus_Indicator","Indicator_Coverage","Indicator_Band"]].to_string(index=False))
    for note in notes: print("NOTICE:",note)
if __name__ == "__main__": main()
