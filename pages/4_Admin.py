import streamlit as st
import pandas as pd
import os

KIDS_CSV = "data/kids.csv"
USERS_CSV = "data/users.csv"

def load_csv(path, columns):
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame(columns=columns)

def save_csv(path, df):
    df.to_csv(path, index=False)

def run():
    st.title("⚙️ Admin Panel")

    if "user" not in st.session_state:
        st.warning("Please log in first.")
        st.stop()

    user = st.session_state.user
    if user["role"] != "admin":
        st.error("You do not have permission to access this page.")
        st.stop()

    tab1, tab2 = st.tabs(["Manage Kids", "Manage Users"])

    # --- MANAGE KIDS ---
    with tab1:
        st.subheader("Kids Records")
        kids_df = load_csv(KIDS_CSV, ["Name", "Program", "Age"])

        st.dataframe(kids_df)

        # Add new kid
        with st.expander("➕ Add New Kid"):
            kid_name = st.text_input("Name")
            kid_program = st.text_input("Program")
            kid_age = st.number_input("Age", min_value=0, step=1)

            if st.button("Add Kid"):
                if kid_name and kid_program:
                    kids_df = pd.concat(
                        [kids_df, pd.DataFrame([{
                            "Name": kid_name,
                            "Program": kid_program,
                            "Age": kid_age
                        }])],
                        ignore_index=True
                    )
                    save_csv(KIDS_CSV, kids_df)
                    st.success(f"Added kid: {kid_name}")
                    st.experimental_rerun()
                else:
                    st.error("Please fill in all fields.")

        # Import kids from Excel
        with st.expander("📥 Import Kids from Excel"):
            uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])
            if uploaded_file:
                try:
                    imported_df = pd.read_excel(uploaded_file)
                    required_cols = {"Name", "Program", "Age"}
                    if required_cols.issubset(imported_df.columns):
                        kids_df = pd.concat([kids_df, imported_df], ignore_index=True)
                        save_csv(KIDS_CSV, kids_df)
                        st.success("Kids imported successfully.")
                        st.experimental_rerun()
                    else:
                        st.error(f"Excel must contain columns: {required_cols}")
                except Exception as e:
                    st.error(f"Error reading Excel: {e}")

    # --- MANAGE USERS ---
    with tab2:
        st.subheader("User Accounts")
        users_df = load_csv(USERS_CSV, ["username", "password", "role", "program"])

        st.dataframe(users_df)

        # Add new user
        with st.expander("➕ Add New User"):
            username = st.text_input("Username")
            password = st.text_input("Password")
            role = st.selectbox("Role", ["admin", "leader"])
            program = st.text_input("Program (if leader)", disabled=(role == "admin"))

            if st.button("Add User"):
                if username and password and role:
                    if role == "leader" and not program:
                        st.error("Leaders must have a program assigned.")
                    else:
                        users_df = pd.concat(
                            [users_df, pd.DataFrame([{
                                "username": username,
                                "password": password,
                                "role": role,
                                "program": program if role == "leader" else ""
                            }])],
                            ignore_index=True
                        )
                        save_csv(USERS_CSV, users_df)
                        st.success(f"User {username} added.")
                        st.experimental_rerun()
                else:
                    st.error("Please fill all required fields.")

if __name__ == "__main__":
    run()

