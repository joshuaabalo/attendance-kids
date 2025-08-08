
import streamlit as st
import pandas as pd
import os
from datetime import datetime

# File paths
KIDS_FILE = "kids.csv"
ATTENDANCE_FILE = "attendance.csv"
IMAGES_DIR = "images"

# Create directories if missing
os.makedirs(IMAGES_DIR, exist_ok=True)

# Initialize CSV files if they don't exist
if not os.path.exists(KIDS_FILE):
    pd.DataFrame(columns=["Name", "Age", "Gender", "Program", "Image"]).to_csv(KIDS_FILE, index=False)
if not os.path.exists(ATTENDANCE_FILE):
    pd.DataFrame(columns=["Date", "Name", "Present"]).to_csv(ATTENDANCE_FILE, index=False)

# Load data
kids_df = pd.read_csv(KIDS_FILE)
attendance_df = pd.read_csv(ATTENDANCE_FILE)

# Custom dark theme CSS
st.markdown("""
    <style>
    body {
        background-color: #0e1117;
        color: #fafafa;
    }
    .stButton>button {
        background-color: #262730;
        color: white;
        border-radius: 8px;
        padding: 0.5em 1em;
    }
    .stButton>button:hover {
        background-color: #FF4B4B;
        color: white;
    }
    .card {
        background-color: #1e1e1e;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 15px;
    }
    img {
        border-radius: 50%;
        object-fit: cover;
    }
    </style>
""", unsafe_allow_html=True)

# Login system
def login():
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == "admin" and password == "admin":
            st.session_state.logged_in = True
        else:
            st.error("Invalid username or password")

# Add new kid
def add_kid():
    st.title("➕ Add New Kid")
    name = st.text_input("Name")
    age = st.number_input("Age", min_value=1, max_value=18, step=1)
    gender = st.selectbox("Gender", ["Male", "Female"])
    program = st.text_input("Program/Project")
    image_file = st.file_uploader("Upload Profile Picture", type=["jpg", "jpeg", "png"])

    if st.button("Save Kid"):
        if name and program:
            img_path = ""
            if image_file is not None:
                img_path = os.path.join(IMAGES_DIR, f"{name}_{image_file.name}")
                with open(img_path, "wb") as f:
                    f.write(image_file.getbuffer())
            new_kid = pd.DataFrame([[name, age, gender, program, img_path]], columns=["Name", "Age", "Gender", "Program", "Image"])
            updated_df = pd.concat([kids_df, new_kid], ignore_index=True)
            updated_df.to_csv(KIDS_FILE, index=False)
            st.success(f"{name} added successfully!")
        else:
            st.error("Please fill all required fields.")

# View kids list
def view_kids():
    st.title("👦 Kids List")
    for _, row in kids_df.iterrows():
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            if pd.notna(row["Image"]) and row["Image"] != "" and os.path.exists(row["Image"]):
                st.image(row["Image"], width=100)
            st.subheader(row["Name"])
            st.write(f"**Age:** {row['Age']}")
            st.write(f"**Gender:** {row['Gender']}")
            st.write(f"**Program:** {row['Program']}")
            if st.button(f"View Profile - {row['Name']}"):
                profile(row["Name"])
            st.markdown('</div>', unsafe_allow_html=True)

# Attendance
def attendance():
    st.title("📅 Mark Attendance")
    today = datetime.today().strftime("%Y-%m-%d")
    present_names = st.multiselect("Select kids present today", kids_df["Name"].tolist())

    if st.button("Save Attendance"):
        new_records = []
        for name in kids_df["Name"]:
            new_records.append([today, name, name in present_names])
        new_df = pd.DataFrame(new_records, columns=["Date", "Name", "Present"])
        updated_attendance = pd.concat([attendance_df, new_df], ignore_index=True)
        updated_attendance.to_csv(ATTENDANCE_FILE, index=False)
        st.success("Attendance saved!")

# Profile view
def profile(name):
    st.title(f"📌 Profile - {name}")
    kid = kids_df[kids_df["Name"] == name].iloc[0]
    if pd.notna(kid["Image"]) and kid["Image"] != "" and os.path.exists(kid["Image"]):
        st.image(kid["Image"], width=150)
    st.write(f"**Age:** {kid['Age']}")
    st.write(f"**Gender:** {kid['Gender']}")
    st.write(f"**Program:** {kid['Program']}")

    total_days = attendance_df[attendance_df["Name"] == name].shape[0]
    present_days = attendance_df[(attendance_df["Name"] == name) & (attendance_df["Present"] == True)].shape[0]
    attendance_percent = (present_days / total_days * 100) if total_days > 0 else 0
    st.write(f"**Total Attendance Days:** {present_days}")
    st.write(f"**Attendance Percentage:** {attendance_percent:.2f}%")

    notes = st.text_area("Notes/Remarks")
    if st.button("Save Notes"):
        st.success("Notes saved! (Not persistent in this version)")

# Navigation
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
else:
    menu = st.sidebar.radio("Navigation", ["Add Kid", "View Kids", "Attendance"])
    if menu == "Add Kid":
        add_kid()
    elif menu == "View Kids":
        view_kids()
    elif menu == "Attendance":
        attendance()
