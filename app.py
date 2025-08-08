
import streamlit as st
import pandas as pd
import os
from datetime import date, datetime

# ---------- Config ----------
KIDS_CSV = "kids.csv"
ATT_CSV = "attendance.csv"

ADMIN_USER = "admin"
ADMIN_PASS = "admin"

# ---------- Utilities ----------
def ensure_csvs_exist():
    if not os.path.exists(KIDS_CSV):
        df = pd.DataFrame(columns=["id","name","age","gender","program"])
        df.to_csv(KIDS_CSV, index=False)
    if not os.path.exists(ATT_CSV):
        df = pd.DataFrame(columns=["date","kid_id","present","note","timestamp"])
        df.to_csv(ATT_CSV, index=False)

def load_kids():
    ensure_csvs_exist()
    return pd.read_csv(KIDS_CSV, dtype={"id": str})

def save_kids(df):
    df.to_csv(KIDS_CSV, index=False)

def load_attendance():
    ensure_csvs_exist()
    return pd.read_csv(ATT_CSV, dtype={"kid_id": str})

def save_attendance(df):
    df.to_csv(ATT_CSV, index=False)

def next_kid_id(kids_df):
    if kids_df.empty:
        return "1"
    try:
        max_id = max(int(x) for x in kids_df["id"].tolist())
        return str(max_id + 1)
    except:
        return str(len(kids_df) + 1)

def attendance_percentage_for(kid_id, attendance_df):
    if attendance_df.empty:
        return None
    total_days = attendance_df["date"].nunique()
    if total_days == 0:
        return None
    present_count = attendance_df[(attendance_df["kid_id"]==kid_id) & (attendance_df["present"]==1)]["date"].nunique()
    return round((present_count / total_days) * 100, 1)

def total_attendance_days_for(kid_id, attendance_df):
    if attendance_df.empty:
        return 0
    return attendance_df[(attendance_df["kid_id"]==kid_id) & (attendance_df["present"]==1)]["date"].nunique()

# ---------- Auth ----------
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if st.session_state.logged_in:
        return True
    with st.sidebar.form("login_form"):
        st.write("### Login")
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")
        if submitted:
            if user == ADMIN_USER and pwd == ADMIN_PASS:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid credentials")
    return False

# ---------- Main ----------
def main():
    st.set_page_config(page_title="Kids Attendance App", layout="wide")
    st.title("Kids Attendance / Management App")

    if not check_login():
        st.info("Use username `admin` and password `admin` to log in.")
        return

    ensure_csvs_exist()
    kids_df = load_kids()
    att_df = load_attendance()

    menu = st.sidebar.radio("Menu", ["Dashboard", "Kids Management", "Attendance", "Child Profiles", "Export / CSV"])

    # -------- Dashboard --------
    if menu == "Dashboard":
        st.header("Dashboard")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total kids", len(kids_df))
        col2.metric("Attendance days", att_df["date"].nunique() if not att_df.empty else 0)
        col3.metric("Records", len(att_df))

        st.subheader("Recent Attendance")
        if att_df.empty:
            st.write("No attendance recorded yet.")
        else:
            recent = att_df.sort_values("timestamp", ascending=False).head(15)
            merged = recent.merge(kids_df, left_on="kid_id", right_on="id", how="left")
            merged["present"] = merged["present"].apply(lambda x: "Present" if int(x)==1 else "Absent")
            st.dataframe(merged[["timestamp","date","name","present","note"]])

    # -------- Kids Management --------
    elif menu == "Kids Management":
        st.header("Add new kid")
        with st.form("add_kid"):
            name = st.text_input("Full name")
            age = st.number_input("Age", min_value=0, max_value=30, value=6)
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
            program = st.text_input("Program / Project")
            if st.form_submit_button("Add"):
                if name.strip():
                    new_id = next_kid_id(kids_df)
                    new_row = {"id": new_id, "name": name.strip(), "age": int(age), "gender": gender, "program": program.strip()}
                    kids_df = pd.concat([kids_df, pd.DataFrame([new_row])], ignore_index=True)
                    save_kids(kids_df)
                    st.success(f"Added {name}")
                    st.rerun()
                else:
                    st.error("Enter a name.")

        st.subheader("Kids List")
        st.dataframe(kids_df)

    # -------- Attendance --------
    elif menu == "Attendance":
        st.header("Mark Attendance")
        att_date = st.date_input("Date", value=date.today())
        att_date_str = att_date.isoformat()
        present_ids = att_df[att_df["date"]==att_date_str]["kid_id"].tolist()

        if kids_df.empty:
            st.info("No kids yet.")
        else:
            with st.form("mark_attendance"):
                new_records = []
                for _, row in kids_df.iterrows():
                    present = st.checkbox(row["name"], value=row["id"] in present_ids)
                    new_records.append({"kid_id": row["id"], "present": 1 if present else 0, "note": ""})
                if st.form_submit_button("Save"):
                    att_df = att_df[att_df["date"]!=att_date_str]
                    ts = datetime.now().isoformat(timespec="seconds")
                    for rec in new_records:
                        att_df = pd.concat([att_df, pd.DataFrame([{"date":att_date_str, **rec, "timestamp": ts}])], ignore_index=True)
                    save_attendance(att_df)
                    st.success("Saved!")
                    st.rerun()

    # -------- Child Profiles --------
    elif menu == "Child Profiles":
        if kids_df.empty:
            st.info("No kids yet.")
        else:
            kid_id = st.selectbox("Select kid", kids_df["id"])
            kid = kids_df[kids_df["id"]==kid_id].iloc[0]
            st.subheader(kid["name"])
            st.write(f"Age: {kid['age']}, Gender: {kid['gender']}, Program: {kid['program']}")
            st.write(f"Total days present: {total_attendance_days_for(kid_id, att_df)}")
            pct = attendance_percentage_for(kid_id, att_df)
            st.write(f"Attendance %: {pct if pct is not None else 'N/A'}")

    # -------- Export --------
    elif menu == "Export / CSV":
        st.header("Download CSVs")
        if os.path.exists(KIDS_CSV):
            with open(KIDS_CSV, "rb") as f:
                st.download_button("Download kids.csv", f, file_name=KIDS_CSV)
        if os.path.exists(ATT_CSV):
            with open(ATT_CSV, "rb") as f:
                st.download_button("Download attendance.csv", f, file_name=ATT_CSV)

    # Logout
    if st.sidebar.button("Log out"):
        st.session_state.logged_in = False
        st.rerun()

if __name__ == "__main__":
    main()
