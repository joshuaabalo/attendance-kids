import streamlit as st
import pandas as pd
from utils.data import load_attendance_csv

def run():
    st.title("Attendance Reports")

    attendance = load_attendance_csv()

    # Filter for leader
    if st.session_state.role == "Leader":
        attendance = attendance[attendance["program"] == st.session_state.username]

    if attendance.empty:
        st.info("No attendance records found.")
        return

    report_type = st.selectbox("Report Type", ["Daily Summary", "Full History"])

    if report_type == "Daily Summary":
        summary = attendance.groupby(["date", "status"]).size().unstack(fill_value=0)
        st.dataframe(summary)
    else:
        st.dataframe(attendance)
