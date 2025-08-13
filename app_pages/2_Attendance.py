import streamlit as st
import pandas as pd
import os

KIDS_FILE = "kids.csv"
ATTENDANCE_FILE = "attendance.csv"  # separate file to store attendance records

# Load kids data
def load_kids():
    if os.path.exists(KIDS_FILE):
        return pd.read_csv(KIDS_FILE)
    return pd.DataFrame(columns=["Name", "Age", "Program", "Leader"])

# Load attendance data
def load_attendance():
    if os.path.exists(ATTENDANCE_FILE):
        return pd.read_csv(ATTENDANCE_FILE)
    return pd.DataFrame(columns=["Date", "Kid", "Present", "MarkedBy"])

# Save attendance data
def save_attendance(df):
    df.to_csv(ATTENDANCE_FILE, index=False)

def attendance_page():
    st.title("Mark Attendance")

    kids = load_kids()
    attendance = load_attendance()

    if kids.empty:
        st.info("No kids available. Please add kids first on the Kids page.")
        return

    # Get current user safely
    username = st.session_state.user.get("username", "unknown") if "user" in st.session_state else "unknown"
    role = st.session_state.user.get("role", "leader").lower() if "user" in st.session_state else "leader"

    # Leaders only see their own kids
    if role == "leader":
        kids = kids[kids["Leader"] == username]

    st.subheader("Kids List")
    st.dataframe(kids[["Name", "Program", "Age"]])

    st.subheader("Mark Attendance for Today")
    with st.form("attendance_form"):
        today = pd.Timestamp.now().strftime("%Y-%m-%d")
        # Multiple select for kids present today
        present_kids = st.multiselect("Select kids who are present", kids["Name"].tolist())
        submitted = st.form_submit_button("Submit Attendance")

        if submitted:
            if not present_kids:
                st.warning("No kids selected as present.")
            else:
                for kid in kids["Name"]:
                    record = {
                        "Date": today,
                        "Kid": kid,
                        "Present": kid in present_kids,
                        "MarkedBy": username
                    }
                    attendance = pd.concat([attendance, pd.DataFrame([record])], ignore_index=True)
                save_attendance(attendance)
                st.success("Attendance recorded successfully!")
                st.experimental_rerun()
