import pandas as pd
import os

KIDS_CSV = "data/kids.csv"
ATTENDANCE_CSV = "data/attendance.csv"

def load_kids_from_csv():
    if not os.path.exists(KIDS_CSV) or os.stat(KIDS_CSV).st_size == 0:
        # Create file with correct headers if missing/empty
        df = pd.DataFrame(columns=["name", "age", "program"])
        df.to_csv(KIDS_CSV, index=False)
        return df
    return pd.read_csv(KIDS_CSV)

def save_kids_to_csv(df):
    df.to_csv(KIDS_CSV, index=False)

def load_attendance_csv():
    if not os.path.exists(ATTENDANCE_CSV) or os.stat(ATTENDANCE_CSV).st_size == 0:
        df = pd.DataFrame(columns=["date", "name", "program", "status"])
        df.to_csv(ATTENDANCE_CSV, index=False)
        return df
    return pd.read_csv(ATTENDANCE_CSV)

def save_attendance_csv(df):
    df.to_csv(ATTENDANCE_CSV, index=False)
