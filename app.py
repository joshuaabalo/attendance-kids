import streamlit as st
import sqlite3
from datetime import datetime

# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect('kids.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password TEXT,
                  role TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS kids
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  program TEXT,
                  age INTEGER,
                  gender TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS attendance
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  kid_id INTEGER,
                  date TEXT,
                  status TEXT,
                  FOREIGN KEY (kid_id) REFERENCES kids (id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS feedback
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  kid_id INTEGER,
                  date TEXT,
                  comments TEXT,
                  FOREIGN KEY (kid_id) REFERENCES kids (id))''')

    # Create default admin account
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ('admin', 'admin', 'admin'))

    conn.commit()
    conn.close()

# ---------- USER FUNCTIONS ----------
def add_user(username, password, role):
    conn = sqlite3.connect('kids.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  (username, password, role))
        conn.commit()
    except sqlite3.IntegrityError:
        st.error("Username already exists.")
    conn.close()

def get_user(username, password):
    conn = sqlite3.connect('kids.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = c.fetchone()
    conn.close()
    return user

def get_all_users():
    conn = sqlite3.connect('kids.db')
    c = conn.cursor()
    c.execute("SELECT id, username, role FROM users")
    users = c.fetchall()
    conn.close()
    return users

def delete_user(user_id):
    conn = sqlite3.connect('kids.db')
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

# ---------- KIDS FUNCTIONS ----------
def add_kid(name, program, age, gender):
    conn = sqlite3.connect('kids.db')
    c = conn.cursor()
    c.execute("INSERT INTO kids (name, program, age, gender) VALUES (?, ?, ?, ?)",
              (name, program, age, gender))
    conn.commit()
    conn.close()

def get_all_kids():
    conn = sqlite3.connect('kids.db')
    c = conn.cursor()
    c.execute("SELECT * FROM kids")
    kids = c.fetchall()
    conn.close()
    return kids

def delete_kid(kid_id):
    conn = sqlite3.connect('kids.db')
    c = conn.cursor()
    c.execute("DELETE FROM kids WHERE id = ?", (kid_id,))
    c.execute("DELETE FROM attendance WHERE kid_id = ?", (kid_id,))
    c.execute("DELETE FROM feedback WHERE kid_id = ?", (kid_id,))
    conn.commit()
    conn.close()

# ---------- ATTENDANCE FUNCTIONS ----------
def mark_attendance(kid_id, status):
    conn = sqlite3.connect('kids.db')
    c = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d")
    c.execute("INSERT INTO attendance (kid_id, date, status) VALUES (?, ?, ?)",
              (kid_id, date, status))
    conn.commit()
    conn.close()

def get_attendance(kid_id):
    conn = sqlite3.connect('kids.db')
    c = conn.cursor()
    c.execute("SELECT date, status FROM attendance WHERE kid_id = ?", (kid_id,))
    attendance = c.fetchall()
    conn.close()
    return attendance

# ---------- FEEDBACK FUNCTIONS ----------
def add_feedback(kid_id, comments):
    conn = sqlite3.connect('kids.db')
    c = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d")
    c.execute("INSERT INTO feedback (kid_id, date, comments) VALUES (?, ?, ?)",
              (kid_id, date, comments))
    conn.commit()
    conn.close()

def get_feedback(kid_id):
    conn = sqlite3.connect('kids.db')
    c = conn.cursor()
    c.execute("SELECT date, comments FROM feedback WHERE kid_id = ?", (kid_id,))
    feedback = c.fetchall()
    conn.close()
    return feedback

# ---------- MAIN APP ----------
def main():
    st.title("Kids Attendance & Feedback System")

    # Session state for login
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.role = None

    if not st.session_state.logged_in:
        role_choice = st.selectbox("Login as", ["Admin", "User"])
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            user = get_user(username, password)
            if user and ((role_choice.lower() == "admin" and user[3] == "admin") or
                         (role_choice.lower() == "user" and user[3] == "user")):
                st.session_state.logged_in = True
                st.session_state.role = user[3]
                st.experimental_rerun()
            else:
                st.error("Invalid credentials or role.")
    else:
        st.sidebar.write(f"Logged in as: **{st.session_state.role}**")
        menu = []

        # Admin can see all
        if st.session_state.role == "admin":
            menu = ["Manage Users", "Add Kid", "Remove Kid", "Attendance", "Child Profiles"]
        elif st.session_state.role == "user":
            menu = ["Add Kid", "Attendance", "Child Profiles"]

        choice = st.sidebar.selectbox("Menu", menu)

        # Manage Users (Admin only)
        if choice == "Manage Users" and st.session_state.role == "admin":
            st.subheader("Manage Users")
            with st.form("add_user_form"):
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
                role = st.selectbox("Role", ["user", "admin"])
                submitted = st.form_submit_button("Add User")
                if submitted:
                    add_user(new_username, new_password, role)
                    st.success("User added successfully.")

            users = get_all_users()
            st.write("Existing Users")
            for u in users:
                st.write(f"ID: {u[0]}, Username: {u[1]}, Role: {u[2]}")
                if st.button(f"Delete {u[1]}", key=f"deluser{u[0]}"):
                    delete_user(u[0])
                    st.experimental_rerun()

        # Add Kid
        elif choice == "Add Kid":
            with st.form("add_kid_form"):
                name = st.text_input("Name")
                program = st.text_input("Program")
                age = st.number_input("Age", min_value=1, max_value=18)
                gender = st.selectbox("Gender", ["Male", "Female"])
                submitted = st.form_submit_button("Add Kid")
                if submitted:
                    add_kid(name, program, age, gender)
                    st.success("Kid added successfully.")

        # Remove Kid (Admin only)
        elif choice == "Remove Kid" and st.session_state.role == "admin":
            kids = get_all_kids()
            kid_dict = {f"{k[1]} ({k[2]})": k[0] for k in kids}
            selected_kid = st.selectbox("Select Kid to Remove", list(kid_dict.keys()))
            if st.button("Remove Kid"):
                delete_kid(kid_dict[selected_kid])
                st.success("Kid removed successfully.")
                st.experimental_rerun()

        # Attendance
        elif choice == "Attendance":
            kids = get_all_kids()
            for kid in kids:
                st.write(f"{kid[1]} ({kid[2]})")
                col1, col2 = st.columns(2)
                if col1.button(f"Present - {kid[0]}", key=f"present{kid[0]}"):
                    mark_attendance(kid[0], "Present")
                if col2.button(f"Absent - {kid[0]}", key=f"absent{kid[0]}"):
                    mark_attendance(kid[0], "Absent")

        # Child Profiles
        elif choice == "Child Profiles":
            kids = get_all_kids()
            kid_dict = {f"{k[1]} ({k[2]})": k[0] for k in kids}
            selected_kid = st.selectbox("Select Kid", list(kid_dict.keys()))
            kid_id = kid_dict[selected_kid]
            st.subheader(f"Profile: {selected_kid}")

            st.write("**Attendance Records**")
            for a in get_attendance(kid_id):
                st.write(f"{a[0]} - {a[1]}")

            st.write("**Feedback**")
            for f in get_feedback(kid_id):
                st.write(f"{f[0]} - {f[1]}")

            feedback_text = st.text_area("Add Feedback")
            if st.button("Submit Feedback"):
                add_feedback(kid_id, feedback_text)
                st.success("Feedback added successfully.")

if __name__ == "__main__":
    init_db()
    main()
