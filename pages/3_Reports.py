import streamlit as st
import pandas as pd
import os
from datetime import date

ATTENDANCE_CSV = "data/attendance.csv"

def load_attendance():
    if os.path.exists(ATTENDANCE_CSV):
        return pd.read_csv(ATTENDANCE_CSV)
    return pd.DataFrame(columns=["Date", "Kid", "Program", "Present"])

def run():
    st.title("📊 Attendance Reports")

    if "user" not in st.session_state:
        st.warning("Please log in first.")
        st.stop()

    user = st.session_state.user
    att_df = load_attendance()

    if att_df.empty:
        st.info("No attendance records found.")
        st.stop()

    # Restrict to leader's program
    if user["role"] == "leader":
        att_df = att_df[att_df["Program"] == user["program"]]

    # Filter by date
    dates = sorted(att_df["Date"].unique(), reverse=True)
    selected_date = st.selectbox("Select date", dates, index=0)

    daily_df = att_df[att_df["Date"] == selected_date]

    # Summary
    present_count = daily_df[daily_df["Present"] == True].shape[0]
    total_count = daily_df.shape[0]
    st.subheader(f"Summary for {selected_date}")
    st.write(f"**Present:** {present_count} / {total_count}")

    # Detailed table
    st.dataframe(daily_df)

    # Download CSV
    csv_data = daily_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download CSV",
        data=csv_data,
        file_name=f"attendance_{selected_date}.csv",
        mime="text/csv"
    )

if __name__ == "__main__":
    run()

