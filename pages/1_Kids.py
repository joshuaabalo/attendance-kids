import streamlit as st
import pandas as pd
import os
from utils.data import load_kids, save_kids

KIDS_FILE = "data/kids.csv"

def run():
    st.title("Kids Management")

    user = st.session_state.user

    # Load kids data
    kids = load_kids()

    # Leader should only see kids under their program
    if user["role"].lower() == "leader":
        kids = kids[kids["program"] == user["program"]]

    st.subheader("Add a New Kid")
    with st.form("add_kid_form"):
        name = st.text_input("Full Name")
        age = st.number_input("Age", min_value=1, max_value=18, step=1)
        program = st.selectbox("Program", ["Sunday School", "Teens", "Youth"])
        submit = st.form_submit_button("Add Kid")

        if submit:
            if name.strip() == "":
                st.error("Name cannot be empty.")
            else:
                new_row = {
                    "name": name.strip(),
                    "age": int(age),
                    "program": program
                }
                kids = pd.concat([kids, pd.DataFrame([new_row])], ignore_index=True)
                save_kids(kids)
                st.success(f"Kid '{name}' added successfully!")

    st.subheader("Kids List")
    if kids.empty:
        st.info("No kids found.")
    else:
        st.dataframe(kids)
