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



    # Show Kids List
    st.subheader("Kids List")
    if user["role"].lower() == "leader":
        kids = kids[kids["program"] == user["program"]]

    st.dataframe(kids)
