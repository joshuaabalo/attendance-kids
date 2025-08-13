import streamlit as st
import pandas as pd
import os

USERS_FILE = "users.csv"

# Load users
def load_users():
    if os.path.exists(USERS_FILE):
        return pd.read_csv(USERS_FILE)
    return pd.DataFrame(columns=["Username", "Role", "FullName"])

# Save users
def save_users(df):
    df.to_csv(USERS_FILE, index=False)

def run():
    st.title("Admin Page - User Management")

    users = load_users()

    st.subheader("Current Users")
    if users.empty:
        st.info("No users found.")
    else:
        st.dataframe(users)

    st.subheader("Add a New User")
    with st.form("add_user_form"):
        username = st.text_input("Username")
        full_name = st.text_input("Full Name")
        role = st.selectbox("Role", ["Leader", "Admin"])
        submitted = st.form_submit_button("Add User")

        if submitted:
            if username.strip() == "" or full_name.strip() == "":
                st.error("Please provide both username and full name.")
            elif username in users["Username"].values:
                st.error("Username already exists.")
            else:
                new_user = {"Username": username.strip(), "FullName": full_name.strip(), "Role": role}
                new_user_df = pd.DataFrame([new_user])
                users = pd.concat([users, new_user_df], ignore_index=True)
                save_users(users)
                st.success(f"User '{username}' added successfully!")
                st.experimental_rerun()
