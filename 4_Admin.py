import streamlit as st
import pandas as pd
from utils.auth import load_users, save_users, change_password
from utils.data import load_kids, save_kids

def run():
    st.title("Admin Panel")
    if "user" not in st.session_state or not st.session_state.user:
        st.warning("Please log in first.")
        st.stop()
    user = st.session_state.user
    if user["role"].lower() != "admin":
        st.error("Access denied.")
        st.stop()

    st.subheader("Users")
    users = load_users()
    st.table(users)

    with st.form("add_user_form"):
        st.write("Add user")
        uname = st.text_input("Username", key="admin_add_uname")
        pwd = st.text_input("Password", key="admin_add_pwd")
        role = st.selectbox("Role", ("admin","leader"), key="admin_add_role")
        programs = st.text_input("Programs (comma separated)", key="admin_add_programs")
        full_name = st.text_input("Full name", key="admin_add_fullname")
        if st.form_submit_button("Create user", key="admin_create_btn"):
            if not uname or not pwd:
                st.error("Username and password required.")
            else:
                users.append({"username":uname,"password":pwd,"role":role,"program":programs,"full_name":full_name})
                save_users(users)
                st.success("User created.")

    st.markdown('---')
    st.subheader("Kids (raw)")
    kids = load_kids()
    st.dataframe(kids[["id","name","program","age"]])

if __name__ == "__main__":
    run()
