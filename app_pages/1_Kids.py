import streamlit as st
import pandas as pd
from utils.data import load_kids, save_kids

def run():
    st.header("Kids Management")

    user = st.session_state.user
    kids = load_kids()

    # Add New Kid Form
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
            new_kid_df = pd.DataFrame([new_kid])
            kids_df = pd.concat([kids_df, new_kid_df], ignore_index=True)
            save_kids(kids_df)
            st.success(f"Added {name} to {program}.")
            st.experimental_rerun()

    # Show Kids List
    st.subheader("Kids List")
    if user["role"].lower() == "leader":
        kids = kids[kids["program"] == user["program"]]

    st.dataframe(kids)
