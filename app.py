import streamlit as st
from utils.auth import login_user, load_users
from utils.data import load_kids_from_csv, save_kids_to_csv

st.set_page_config(page_title="Attendance Kids", layout="wide")

# Load users (admin & leaders)
users = load_users()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None

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

else:
    st.sidebar.write(f"Logged in as: {st.session_state.username} ({st.session_state.role})")
    st.sidebar.page_link("pages/1_Kids.py", label="Kids Management")
    st.sidebar.page_link("pages/2_Attendance.py", label="Attendance")
    st.sidebar.page_link("pages/3_Reports.py", label="Reports")
    if st.session_state.role == "Admin":
        st.sidebar.page_link("pages/4_Admin.py", label="Admin Panel")

    if st.sidebar.button("Logout", key="logout_btn"):
        st.session_state.clear()
        st.rerun()



# ---------- simple file-based navigation (replace page_link usage) ----------
import importlib
from pathlib import Path

def discover_pages(folder="pages"):
    pages = {}
    p = Path(folder)
    if not p.exists():
        return pages
    for f in sorted(p.glob("*.py")):
        key = f.stem  # e.g. "1_Kids" or "2_Attendance"
        # turn filename into a friendly label
        label = key.split("_", 1)[-1].replace("_", " ").strip().title()
        pages[label] = f"pages.{key}"
    return pages

pages_map = discover_pages("pages")
choice = st.sidebar.radio("Navigate", list(pages_map.keys()), key="nav_choice")

# load and run the chosen page module (expects each page to expose run())
module_name = pages_map.get(choice)
try:
    mod = importlib.import_module(module_name)
    importlib.reload(mod)
    if hasattr(mod, "run"):
        mod.run()          # page modules should use st.session_state for user
    else:
        st.error(f"Page {module_name} has no run() function.")
except Exception as e:
    st.error(f"Error loading page {module_name}: {e}")


