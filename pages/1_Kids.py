import streamlit as st
import pandas as pd
from utils.data import load_kids_from_csv, save_kids_to_csv

def run():
    st.title("Kids Management")

    kids = load_kids_from_csv()

    # If Leader, filter kids to only those in their program
    if st.session_state.role == "Leader":
        kids = kids[kids["program"] == st.session_state.username]

    st.dataframe(kids)

    with st.form("add_kid_form"):
        st.subheader("Add New Kid")
        name = st.text_input("Name")
        age = st.number_input("Age", min_value=0, max_value=18)
        program = st.text_input("Program")

        if st.form_submit_button("Add Kid"):
            if name and program:
                new_row = {"name": name, "age": age, "program": program}
                kids = pd.concat([kids, pd.DataFrame([new_row])], ignore_index=True)
                save_kids_to_csv(kids)
                st.success(f"Kid {name} added successfully.")
                st.rerun()
            else:
                st.error("Please fill all required fields.")
