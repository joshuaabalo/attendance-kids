import streamlit as st
import pandas as pd
import os

KIDS_FILE = "kids.csv"
ATTENDANCE_FILE = "attendance.csv"

# Load kids
def load_kids():
    if os.path.exists(KIDS_FILE):
        return pd.read_csv(KIDS_FILE)
    return pd.DataFrame(columns=["Name", "Age", "Program", "Leader"])

# Load attendance
def load_attendance():
    if os.path.exists(ATTENDANCE_FILE):
        return pd.read_csv(ATTENDANCE_FILE)
    return pd.DataFrame(columns=["Date", "Name", "Program", "Status"])

def run():
    st.title("Reports")

    # Ensure user is logged in
    if "user" not in st.session_state:
        st.error("Please log in to access reports.")
        return

    user = st.session_state.user
    role = user["Role"].lower()
    program = user.get("Program", None)

    # Load data
    kids_df = load_kids()
    attendance_df = load_attendance()

    # Filter kids for leaders
    if role == "leader" and program:
        kids_df = kids_df[kids_df["Program"] == program]

    if kids_df.empty:
        st.info("No kids found for your program.")
        return

    # Show list of kids
    st.subheader("Kids List")
    selected_kid = st.selectbox("Select a kid to view report:", kids_df["Name"].tolist())

    if selected_kid:
        st.write(f"### Report for {selected_kid}")

        # Get attendance for the selected kid
        kid_attendance = attendance_df[attendance_df["Name"] == selected_kid]

        if kid_attendance.empty:
            st.warning("No attendance records found for this kid.")
            return

        # Calculate attendance percentage
        total_classes = len(kid_attendance)
        present_count = len(kid_attendance[kid_attendance["Status"] == "Present"])
        attendance_percentage = (present_count / total_classes) * 100

        st.write(f"**Total Classes:** {total_classes}")
        st.write(f"**Present:** {present_count}")
        st.write(f"**Attendance Percentage:** {attendance_percentage:.2f}%")

        # Show progress bar
        st.progress(int(attendance_percentage))

        # Show detailed history
        st.subheader("Attendance History")
        st.dataframe(kid_attendance.sort_values(by="Date", ascending=False))
