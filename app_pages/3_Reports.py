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

# Load attendance and normalize column names
def load_attendance():
    if os.path.exists(ATTENDANCE_FILE):
        df = pd.read_csv(ATTENDANCE_FILE)
        df.columns = [c.strip().capitalize() for c in df.columns]  # Normalize headers
        return df
    return pd.DataFrame(columns=["Date", "Name", "Program", "Status"])


def run():
    st.title("Reports")

    # Check user session
    if "user" not in st.session_state:
        st.error("Please log in to access reports.")
        return

    user = st.session_state.user
    role = user.get("role", "").lower()
    program = user.get("program", None)

    # Load data
    kids_df = load_kids()
    attendance_df = load_attendance()

    # Filter kids based on role
    if role == "leader" and program:
        kids_df = kids_df[kids_df["Program"] == program]

    if kids_df.empty:
        st.info("No kids found for your program.")
        return

    st.subheader("Kids List")
    selected_kid = st.selectbox("Select a kid to view their report:", kids_df["Name"].tolist())

    if selected_kid:
        st.write(f"### Attendance Report for {selected_kid}")

        # Filter attendance for the selected kid
        kid_attendance = attendance_df[attendance_df["Name"] == selected_kid]

        if kid_attendance.empty:
            st.warning("No attendance records found for this kid.")
            return

        # Calculate attendance percentage
        total_classes = len(kid_attendance)
        present_count = len(kid_attendance[kid_attendance["Status"].str.lower() == "present"])
        attendance_percentage = (present_count / total_classes) * 100

        # Show summary
        st.write(f"**Total Sessions:** {total_classes}")
        st.write(f"**Present:** {present_count}")
        st.write(f"**Attendance Percentage:** {attendance_percentage:.2f}%")

        # Progress bar
        st.progress(int(attendance_percentage))

        # Show attendance history
        st.subheader("Attendance History")
        st.dataframe(kid_attendance.sort_values(by="Date", ascending=False))
