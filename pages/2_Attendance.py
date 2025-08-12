import streamlit as st
import pandas as pd
from datetime import date
from utils.data import load_kids_from_csv, load_attendance_csv, save_attendance_csv

def run():
    st.title("Daily Attendance")

    kids = load_kids_from_csv()

    # Filter for leader
    if st.session_state.role == "Leader":
        kids = kids[kids["program"] == st.session_state.username]

    attendance = load_attendance_csv()

    today = date.today().strftime("%Y-%m-%d")
    st.subheader(f"Mark Attendance - {today}")

    attendance_today = {}
    for _, row in kids.iterrows():
        present = st.checkbox(f"{row['name']} (Program: {row['program']})", key=f"att_{row['name']}")
        attendance_today[row['name']] = "Present" if present else "Absent"

    if st.button("Save Attendance"):
        for kid_name, status in attendance_today.items():
            attendance = pd.concat([
                attendance,
                pd.DataFrame([{"date": today, "name": kid_name, "status": status}])
            ], ignore_index=True)
        save_attendance_csv(attendance)
        st.success("Attendance saved successfully.")
