import streamlit as st
import pandas as pd
import os

KIDS_CSV = "data/kids.csv"

def load_kids():
    if not os.path.exists(KIDS_CSV) or os.stat(KIDS_CSV).st_size == 0:
        df = pd.DataFrame(columns=["name", "age", "program"])
        df.to_csv(KIDS_CSV, index=False)
        return df
    return pd.read_csv(KIDS_CSV)

def save_kids(df):
    df.to_csv(KIDS_CSV, index=False)

st.title("Kids Management")

# Load kids data
kids_df = load_kids()

# Add kid form
with st.form("add_kid_form"):
    name = st.text_input("Child's Name")
    age = st.number_input("Age", min_value=1, max_value=18)
    program = st.text_input("Program")
    submitted = st.form_submit_button("Add Kid")
    
    if submitted:
        if name.strip() and program.strip():
            new_row = pd.DataFrame([[name.strip(), age, program.strip()]],
                                   columns=["name", "age", "program"])
            kids_df = pd.concat([kids_df, new_row], ignore_index=True)
            save_kids(kids_df)
            st.success(f"{name} added successfully!")
            st.experimental_rerun()
        else:
            st.error("Please fill in all fields.")

# Show kids list
st.subheader("All Kids")
st.dataframe(kids_df)
