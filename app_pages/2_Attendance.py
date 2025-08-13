import streamlit as st
import pandas as pd
import os

KIDS_FILE = "kids.csv"

# Load kids data
def load_kids():
    if os.path.exists(KIDS_FILE):
        return pd.read_csv(KIDS_FILE)
    return pd.DataFrame(columns=["Name", "Age", "Program", "Leader"])

# Save kids data
def save_kids(df):
    df.to_csv(KIDS_FILE, index=False)

def run():
    st.title("Kids Attendance / Management")

    # Load existing kids
    kids = load_kids()

    # Get current user safely
    if "user" in st.session_state:
        user = st.session_state.user
        username = user.get("username", "unknown")
        role = user.get("role", "leader").lower()
    else:
        username = "unknown"
        role = "leader"

    # Filter for leaders
    if role == "leader":
        kids = kids[kids["Leader"] == username]

    # Display kids list
    st.subheader("Current Kids")
    if kids.empty:
        st.info("No kids found.")
    else:
        st.dataframe(kids)

    # Add new kid form
    st.subheader("Add a New Kid")
    with st.form("add_kid_form"):
        kid_name = st.text_input("Kid's Name")
        age = st.number_input("Age", min_value=1, max_value=18)
        program = st.selectbox("Program", ["Sunday School", "Teens", "Youth"])

        submitted = st.form_submit_button("Add Kid")
        if submitted:
            if kid_name.strip() != "" and program:
                new_kid = {"Name": kid_name.strip(), "Age": age, "Program": program, "Leader": username}
                new_kid_df = pd.DataFrame([new_kid])
                kids = pd.concat([kids, new_kid_df], ignore_index=True)
                save_kids(kids)
                st.success(f"{kid_name} added successfully!")
                st.experimental_rerun()
            else:
                st.error("Please provide both name and program.")
