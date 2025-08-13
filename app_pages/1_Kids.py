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
    st.title("Kids Management")

    # Load existing kids
    kids_df = load_kids()

    user = st.session_state.user  # Current logged-in user
    role = user["role"].lower()
    username = user["username"]

    # Filter for leaders
    if role == "leader":
        kids_df = kids_df[kids_df["Leader"] == username]

    # Display kids list
    st.subheader("Current Kids")
    if kids_df.empty:
        st.info("No kids found.")
    else:
        st.dataframe(kids_df)

    # Add new kid form
    st.subheader("Add a New Kid")
    with st.form("add_kid_form"):
        name = st.text_input("Kid's Name")
        age = st.number_input("Age", min_value=1, max_value=18)
        program = st.selectbox("Program", ["Sunday School", "Teens", "Youth"])

        submitted = st.form_submit_button("Add Kid")
        if submitted:
            if name.strip() == "":
                st.error("Name cannot be empty.")
            else:
                new_kid = {"Name": name.strip(), "Age": age, "Program": program, "Leader": username}
                kids_df = kids_df.append(new_kid, ignore_index=True)
                save_kids(kids_df)
                st.success(f"Added {name} to {program}.")
                st.experimental_rerun()
