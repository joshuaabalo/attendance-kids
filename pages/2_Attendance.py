import streamlit as st
import pandas as pd
from datetime import date
import os

KIDS_CSV = "data/kids.csv"
ATTENDANCE_CSV = "data/attendance.csv"

# Load kids data
def load_kids():
    if os.path.exists(KIDS_CSV):
        return pd.read_csv(KIDS_CSV)
    return pd.DataFrame(columns=["Name", "Program", "Age", "Gender"])

# Save attendance
def save_attendance(att_df):
    if os.path.exists(ATTENDANCE_CSV):
        existing = pd.read_csv(ATTENDANCE_CSV)
        combined = pd.concat([existing, att_df], ignore_index=True)
    else:
        combined = att_df
    combined.to_csv(ATTENDANCE_CSV, index=False)

# Page for daily attendance
def run():
    st.title("📋 Daily Attendance")

    if "user" not in st.session_state:
        st.warning("Please log in first.")
        st.stop()

    user = st.session_state.user
    kids_df = load_kids()

    # Filter kids if leader
    if user["role"] == "leader":
        kids_df = kids_df[kids_df["Program"] == user["program"]]

    if kids_df.empty:
        st.info("No kids found for your program.")
        st.stop()

    today = date.today().strftime("%Y-%m-%d")
    st.subheader(f"Mark Attendance for {today}")

    attendance_data = []
    for _, row in kids_df.iterrows():
        present = st.checkbox(f"{row['Name']} ({row['Program']})", value=True)
        attendance_data.append({
            "Date": today,
            "Kid": row["Name"],
            "Program": row["Program"],
            "Present": present
        })

    if st.button("Save Attendance"):
        att_df = pd.DataFrame(attendance_data)
        save_attendance(att_df)
        st.success("Attendance saved successfully!")

if __name__ == "__main__":
    run()

