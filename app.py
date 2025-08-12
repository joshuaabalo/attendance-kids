import streamlit as st
import importlib
from utils.auth import login_user, load_users

st.set_page_config(page_title="Attendance Kids", layout="wide")

# Load users (admin & leaders)
users = load_users()

# Session state setup
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None

# Login page
if not st.session_state.logged_in:
    st.title("Login")
    role_choice = st.selectbox("Login as", ["Admin", "Leader"], key="role_select")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login", key="login_btn"):
        if login_user(username, password, role_choice):
            st.session_state.logged_in = True
            st.session_state.role = role_choice
            st.session_state.username = username
            st.success(f"Welcome {username} ({role_choice})")
            st.rerun()
        else:
            st.error("Invalid credentials or role mismatch.")

# Main app (after login)
else:
    st.sidebar.write(f"Logged in as: {st.session_state.username} ({st.session_state.role})")

    # Sidebar navigation
    menu = ["Kids Management", "Attendance", "Reports"]
    if st.session_state.role == "Admin":
        menu.append("Admin Panel")
    menu.append("Logout")

    choice = st.sidebar.radio("Navigation", menu, key="main_nav")

    if choice == "Logout":
        st.session_state.clear()
        st.rerun()

    else:
        # Map menu labels to module names in `pages/`
        page_map = {
            "Kids Management": "pages.1_Kids",
            "Attendance": "pages.2_Attendance",
            "Reports": "pages.3_Reports",
            "Admin Panel": "pages.4_Admin"
        }

        if choice in page_map:
            try:
                page_module = importlib.import_module(page_map[choice])
                importlib.reload(page_module)
                if hasattr(page_module, "run"):
                    page_module.run()
                else:
                    st.error(f"The page `{choice}` has no `run()` function.")
            except Exception as e:
                st.error(f"Error loading `{choice}`: {e}")
