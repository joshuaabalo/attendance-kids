import streamlit as st
import importlib
from utils.auth import login_user, load_users

st.set_page_config(page_title="Attendance Kids", layout="wide")

# Initialize session state
if "user" not in st.session_state:
    st.session_state.user = None

# Login Page
if not st.session_state.user:
    st.title("Login")
    role_choice = st.selectbox("Login as", ["admin", "leader"], key="login_role_main")
    username = st.text_input("Username", key="login_user_main")
    password = st.text_input("Password", type="password", key="login_pw_main")

    if st.button("Sign in", key="login_btn_main"):
        user = login_user(username.strip(), password, role_choice)
        if user:
            st.session_state.user = user
            st.success(f"Signed in: {user['full_name']} ({user['role']})")
            st.experimental_rerun()
        else:
            st.error("Invalid credentials or role mismatch.")

else:
    user = st.session_state.user
    st.sidebar.markdown(f"**Signed in:** {user['full_name']} ({user['role']})")

    # Role-based menu
    menu = ["Kids", "Attendance", "Reports", "Logout"]
    if user["role"].lower() == "admin":
        menu.insert(-1, "Admin")

    choice = st.sidebar.radio("Navigation", menu, key="main_nav")

    pages = {
        "Kids": "app_pages.1_Kids",
        "Attendance": "app_pages.2_Attendance",
        "Reports": "app_pages.3_Reports",
        "Admin": "app_pages.4_Admin"
    }

    if choice == "Logout":
        if st.sidebar.button("Log out", key="logout_main"):
            st.session_state.user = None
            st.experimental_rerun()
    else:
        module = pages.get(choice)
        try:
            mod = importlib.import_module(module)
            importlib.reload(mod)
            if hasattr(mod, "run"):
                mod.run()
            else:
                st.error("Page has no run() function.")
        except Exception as e:
            st.error(f"Error loading page: {e}")
