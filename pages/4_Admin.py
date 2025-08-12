import streamlit as st
import pandas as pd
from utils.auth import load_users, save_users

def run():
    st.title("Admin Panel")

    st.subheader("Manage Users")
    users = load_users()
    st.dataframe(users)

    with st.form("add_user_form"):
        st.subheader("Add New User")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["Admin", "Leader"])

        if st.form_submit_button("Add User"):
            if username and password:
                new_user = pd.DataFrame([{"username": username, "password": password, "role": role}])
                users = pd.concat([users, new_user], ignore_index=True)
                save_users(users)
                st.success(f"User {username} added successfully.")
                st.rerun()
            else:
                st.error("All fields are required.")
