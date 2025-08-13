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
        program = st.text_input("Program Name")
        submitted = st.form_submit_button("Add Kid")

    if submitted:
        if kid_name and program:
            new_kid = {"name": kid_name, "age": age, "program": program}
            kids = pd.DataFrame(new_kid, ignore_index=True)
            save_kids(kids)
            st.success(f"{kid_name} added successfully!")
        else:
            st.error("Please provide both name and program.")

    # Show Kids List
    st.subheader("Kids List")
    if user["role"].lower() == "leader":
        kids = kids[kids["program"] == user["program"]]

    st.dataframe(kids)
