import streamlit as st
import pandas as pd
import os

ATTENDANCE_FILE = "attendance.csv"

def load_attendance():
    if os.path.exists(ATTENDANCE_FILE):
        return pd.read_csv(ATTENDANCE_FILE)
    return pd.DataFrame(columns=["Date", "Kid", "Present", "MarkedBy"])

def run():
    st.title("Attendance Reports")

    attendance = load_attendance()

    if attendance.empty:
        st.info("No attendance records found.")
    else:
        st.dataframe(attendance)
