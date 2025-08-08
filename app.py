import streamlit as st
import sqlite3
from datetime import datetime

# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect("kids_app.db")
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS kids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        age INTEGER,
        program TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kid_id INTEGER,
        date TEXT,
        status TEXT,
        FOREIGN KEY (kid_id) REFERENCES kids(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kid_id INTEGER,
        date TEXT,
        feedback TEXT,
        FOREIGN KEY (kid_id) REFERENCES kids(id)
    )""")

    # Create default admin if not exists
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ('admin', 'admin', 'admin'))

    conn.commit()
    conn.close()

init_db()

# ---------- HELPER FUNCTIONS ----------
def add_user(username, password, role):
    conn = sqlite3.connect("kids_app.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  (username, password, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_users():
    conn = sqlite3.connect("kids_app.db")
    c = conn.cursor()
    c.execute("SELECT id, username, role FROM users")
    data = c.fetchall()
    conn.close()
    return data

def remove_user(user_id):
    conn = sqlite3.connect("kids_app.db")
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

def add_kid(name, age, program):
    conn = sqlite3.connect("kids_app.db")
    c = conn.cursor()
    c.execute("INSERT INTO kids (name, age, program) VALUES (?, ?, ?)",
              (name, age, program))
    conn.commit()
    conn.close()

def get_kids():
    conn = sqlite3.connect("kids_app.db")
    c = conn.cursor()
    c.execute("SELECT id, name, age, program FROM kids")
    data = c.fetchall()
    conn.close()
    return data

def remove_kid(kid_id):
    conn = sqlite3.connect("kids_app.db")
    c = conn.cursor()
    c.execute("DELETE FROM kids WHERE id=?", (kid_id,))
    conn.commit()
    conn.close()

def mark_attendance(kid_id, status):
    conn = sqlite3.connect("kids_app.db")
    c = conn.cursor()
    c.execute("INSERT INTO attendance (kid_id, date, status) VALUES (?, ?, ?)",
              (kid_id, datetime.now().strftime("%Y-%m-%d"), status))
    conn.commit()
    conn.close()

def give_feedback(kid_id, feedback):
    conn = sqlite3.connect("kids_app.db")
    c = conn.cursor()
    c.execute("INSERT INTO feedback (kid_id, date, feedback) VALUES (?, ?, ?)",
              (kid_id, datetime.now().strftime("%Y-%m-%d"), feedback))
    conn.commit()
    conn.close()

def get_kid_profile(kid_id):
    conn = sqlite3.connect("kids_app.db")
    c = conn.cursor()
    c.execute("SELECT name, age, program FROM kids WHERE id=?", (kid_id,))
    kid_info = c.fetchone()

    c.execute("SELECT date, status FROM attendance WHERE kid_id=?", (kid_id,))
    attendance_data = c.fetchall()

    c.execute("SELECT date, feedback FROM feedback WHERE kid_id=?", (kid_id,))
    feedback_data = c.fetchall()

    conn.close()
    return kid_info, attendance_data, feedback_data

def check_login(username, password, role):
    conn = sqlite3.connect("kids_app.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=? AND role=?",
              (username, password, role))
    data = c.fetchone()
    conn.close()
    return data

# ---------- APP UI ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None

if not st.session_state.logged_in:
    st.title("Login Page")
    role_choice = st.selectbox("Login as", ["admin", "user"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if check_login(username, password, role_choice):
            st.session_state.logged_in = True
            st.session_state.role = role_choice
            st.success(f"Logged in as {role_choice}")
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")

else:
    st.sidebar.title("Navigation")
    choice = st.sidebar.radio("Go to", ["Dashboard", "Child Profile", "Logout"])

    if choice == "Dashboard":
        st.header("Dashboard")

        if st.session_state.role == "admin":
            st.subheader("Manage Users")
            with st.form("add_user_form"):
                new_user = st.text_input("New Username")
                new_pass = st.text_input("Password", type="password")
                new_role = st.selectbox("Role", ["user", "admin"])
                if st.form_submit_button("Add User"):
                    if add_user(new_user, new_pass, new_role):
                        st.success("User added successfully")
                    else:
                        st.error("Username already exists")

            users = get_users()
            st.write("All Users")
            for uid, uname, urole in users:
                st.write(f"{uname} ({urole})")
                if st.button(f"Remove User {uname}"):
                    remove_user(uid)
                    st.success("User removed")
                    st.experimental_rerun()

            st.subheader("Manage Kids")
            with st.form("add_kid_form"):
                kid_name = st.text_input("Kid Name")
                kid_age = st.number_input("Age", min_value=1, max_value=18)
                kid_program = st.text_input("Program/Project")
                if st.form_submit_button("Add Kid"):
                    add_kid(kid_name, kid_age, kid_program)
                    st.success("Kid added successfully")

            kids = get_kids()
            st.write("All Kids")
            for kid_id, name, age, program in kids:
                st.write(f"{name} - {program}")
                if st.button(f"Remove Kid {name}"):
                    remove_kid(kid_id)
                    st.success("Kid removed")
                    st.experimental_rerun()

        elif st.session_state.role == "user":
            st.subheader("Kids Management")
            kids = get_kids()
            kid_names = {name: kid_id for kid_id, name, _, _ in kids}

            st.write("Mark Attendance")
            selected_kid = st.selectbox("Select Kid", list(kid_names.keys()))
            status = st.selectbox("Status", ["Present", "Absent"])
            if st.button("Submit Attendance"):
                mark_attendance(kid_names[selected_kid], status)
                st.success("Attendance recorded")

            st.write("Give Feedback")
            selected_kid_fb = st.selectbox("Select Kid for Feedback", list(kid_names.keys()))
            feedback_text = st.text_area("Feedback")
            if st.button("Submit Feedback"):
                give_feedback(kid_names[selected_kid_fb], feedback_text)
                st.success("Feedback recorded")

    elif choice == "Child Profile":
        kids = get_kids()
        if kids:
            kid_dict = {name: kid_id for kid_id, name, _, _ in kids}
            selected = st.selectbox("Select a Child", list(kid_dict.keys()))
            kid_info, attendance_data, feedback_data = get_kid_profile(kid_dict[selected])

            st.subheader("Child Info")
            st.write(f"Name: {kid_info[0]}")
            st.write(f"Age: {kid_info[1]}")
            st.write(f"Program: {kid_info[2]}")

            st.subheader("Attendance History")
            for date, status in attendance_data:
                st.write(f"{date} - {status}")

            st.subheader("Feedback History")
            for date, fb in feedback_data:
                st.write(f"{date} - {fb}")
        else:
            st.warning("No kids in database.")

    elif choice == "Logout":
        st.session_state.logged_in = False
        st.session_state.role = None
        st.experimental_rerun()
