import streamlit as st
import pandas as pd
import os

KIDS_CSV = "data/kids.csv"
KIDS_XLSX = "data/KidsT.xlsx"

def load_kids():
    """Load kids from CSV, or from Excel if CSV doesn't exist yet."""
    if os.path.exists(KIDS_CSV):
        return pd.read_csv(KIDS_CSV)
    elif os.path.exists(KIDS_XLSX):
        df = pd.read_excel(KIDS_XLSX, engine="openpyxl")
        df.to_csv(KIDS_CSV, index=False)
        return df
    else:
        return pd.DataFrame(columns=["Name", "Age", "Program", "Gender"])

def save_kids(df):
    df.to_csv(KIDS_CSV, index=False)

def page_kids(user):
    st.header("Kids Management")

    # Load data
    kids_df = load_kids()

    # Filter for leader role
    if user["role"] == "leader":
        kids_df = kids_df[kids_df["Program"] == user.get("program", "")]

    # Program filter
    programs = ["-- All --"] + sorted(kids_df["Program"].dropna().unique().tolist())
    prog_filter = st.selectbox("Filter by Program", programs)

    if prog_filter != "-- All --":
        kids_df = kids_df[kids_df["Program"] == prog_filter]

    # Display kids
    st.subheader("Kids List")
    st.dataframe(kids_df)

    # View kid profile
    if not kids_df.empty:
        selected_kid = st.selectbox("Select a kid to view profile", kids_df["Name"].tolist())
        kid_data = kids_df[kids_df["Name"] == selected_kid].iloc[0]
        st.write(f"**Name:** {kid_data['Name']}")
        st.write(f"**Age:** {kid_data['Age']}")
        st.write(f"**Gender:** {kid_data['Gender']}")
        st.write(f"**Program:** {kid_data['Program']}")

    # Admin: Add new kid
    if user["role"] == "admin":
        st.subheader("Add New Kid")
        with st.form("add_kid_form"):
            name = st.text_input("Name")
            age = st.number_input("Age", min_value=0, max_value=30)
            gender = st.selectbox("Gender", ["Male", "Female"])
            program = st.text_input("Program")
            submitted = st.form_submit_button("Add Kid")
            if submitted:
                new_row = {"Name": name, "Age": age, "Gender": gender, "Program": program}
                kids_df = kids_df.append(new_row, ignore_index=True)
                save_kids(kids_df)
                st.success("Kid added successfully!")
                st.rerun()

