import streamlit as st
import pandas as pd
from utils.data import load_kids, add_kid_record, save_kids

def run():
    st.title("Kids Management")

    if "user" not in st.session_state or not st.session_state.user:
        st.warning("Please log in first.")
        st.stop()

    user = st.session_state.user
    df = load_kids()

    # Leader sees only their programs' kids
    if user["role"].lower() == "leader":
        allowed = user.get("programs", [])
        if not allowed:
            st.info("No program assigned to you. Contact admin.")
            return
        df = df[df["program"].isin(allowed)]

    st.subheader("Existing kids")
    st.dataframe(df[["id","name","age","program"]])

    st.markdown("---")
    st.subheader("Add new kid")
    with st.form("add_kid_form"):
        name = st.text_input("Full name", key="add_name")
        age = st.number_input("Age", min_value=1, max_value=30, value=6, key="add_age")
        program = st.text_input("Program", value=(user.get("programs",[\"\"])[0] if user["role"].lower() == "leader" else ""), key="add_program")
        dob = st.text_input("DOB (YYYY-MM-DD)", key="add_dob")
        gender = st.selectbox("Gender", ("Male","Female","Other"), key="add_gender")
        school = st.text_input("School", key="add_school")
        location = st.text_input("Location", key="add_location")
        guardian = st.text_input("Guardian name", key="add_guardian")
        contact = st.text_input("Guardian contact", key="add_contact")
        relationship = st.text_input("Relationship", key="add_relation")
        submitted = st.form_submit_button("Add kid", key="submit_add_kid")
        if submitted:
            if not name.strip() or not program.strip():
                st.error("Name and program are required.")
            else:
                kid_id = add_kid_record(name.strip(), age, program.strip(), dob.strip(), gender, school.strip(), location.strip(), guardian.strip(), contact.strip(), relationship.strip(), "")
                st.success(f"Kid added with id {kid_id}")
                st.experimental_rerun()

if __name__ == "__main__":
    run()
