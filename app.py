import streamlit as st
import pandas as pd
import os
import hashlib
import uuid
from datetime import date, datetime
from pathlib import Path

# ---------------- Config ----------------
APP_TITLE = "Fafali Attendance Manager"
LOGO_FILE = "Fafali_icont.png"
IMAGES_DIR = "images"

USERS_FILE = "users.csv"
PROGRAMS_FILE = "programs.csv"
KIDS_FILE = "kids.csv"
ATT_FILE = "attendance.csv"

# Colors
PRIMARY_GREEN = "#0b7a3a"
ACCENT_YELLOW = "#ffd83a"
BG = "#0b0f14"
CARD = "#0f1720"
MUTED = "#94a3b8"
TEXT = "#e6eef6"

# Ensure directories & files exist
os.makedirs(IMAGES_DIR, exist_ok=True)
def ensure_csv(path, columns, create_sample=False):
    if not os.path.exists(path):
        df = pd.DataFrame(columns=columns)
        df.to_csv(path, index=False)
        if create_sample and path == USERS_FILE:
            admin_hash = hashlib.sha256("admin".encode()).hexdigest()
            df = pd.DataFrame([{
                "username": "admin",
                "password": admin_hash,
                "role": "admin",
                "program": "",
                "full_name": "Administrator"
            }])
            df.to_csv(USERS_FILE, index=False)

ensure_csv(USERS_FILE, ["username", "password", "role", "program", "full_name"], create_sample=True)
ensure_csv(PROGRAMS_FILE, ["program"])
ensure_csv(KIDS_FILE, ["id", "name", "age", "gender", "program", "image_path"])
ensure_csv(ATT_FILE, ["date", "kid_id", "present", "note", "program", "marked_by", "timestamp"])

# ---------------- Helpers ----------------
def hash_pwd(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def load_users():
    return pd.read_csv(USERS_FILE) if os.path.exists(USERS_FILE) else pd.DataFrame(columns=["username","password","role","program","full_name"])

def save_users(df):
    df.to_csv(USERS_FILE, index=False)

def load_programs():
    return pd.read_csv(PROGRAMS_FILE) if os.path.exists(PROGRAMS_FILE) else pd.DataFrame(columns=["program"])

def save_programs(df):
    df.to_csv(PROGRAMS_FILE, index=False)

def load_kids():
    return pd.read_csv(KIDS_FILE, dtype={"id": str}) if os.path.exists(KIDS_FILE) else pd.DataFrame(columns=["id","name","age","gender","program","image_path"])

def save_kids(df):
    df.to_csv(KIDS_FILE, index=False)

def load_att():
    return pd.read_csv(ATT_FILE, dtype={"kid_id": str}) if os.path.exists(ATT_FILE) else pd.DataFrame(columns=["date","kid_id","present","note","program","marked_by","timestamp"])

def save_att(df):
    df.to_csv(ATT_FILE, index=False)

def add_user(username, password, role, program="", full_name=""):
    users = load_users()
    if username in users["username"].values:
        return False, "Username exists"
    row = {
        "username": username,
        "password": hash_pwd(password),
        "role": role,
        "program": program,
        "full_name": full_name
    }
    users = pd.concat([users, pd.DataFrame([row])], ignore_index=True)
    save_users(users)
    return True, "User created"

def add_program(prog):
    progs = load_programs()
    if prog in progs["program"].values:
        return False
    progs = pd.concat([progs, pd.DataFrame([{"program": prog}])], ignore_index=True)
    save_programs(progs)
    return True

def save_kid_image(uploaded_file, kid_name, kid_id):
    ext = Path(uploaded_file.name).suffix
    safe = "".join([c for c in kid_name if c.isalnum() or c in (" ", "_")]).strip().replace(" ", "_")
    dest = os.path.join(IMAGES_DIR, f"{safe}_{kid_id}{ext}")
    with open(dest, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return dest

def add_kid(name, age, gender, program, image_file):
    kids = load_kids()
    kid_id = str(uuid.uuid4())[:8]
    image_path = ""
    if image_file is not None:
        image_path = save_kid_image(image_file, name, kid_id)
    row = {
        "id": kid_id,
        "name": name,
        "age": int(age),
        "gender": gender,
        "program": program,
        "image_path": image_path
    }
    kids = pd.concat([kids, pd.DataFrame([row])], ignore_index=True)
    save_kids(kids)
    return kid_id

def remove_kid(kid_id):
    kids = load_kids()
    kids = kids[kids["id"] != kid_id]
    save_kids(kids)
    att = load_att()
    att = att[att["kid_id"] != kid_id]
    save_att(att)

def stats_for_kid(kid_id):
    att = load_att()
    kids = load_kids()
    rec = att[att["kid_id"]==kid_id]
    present = rec[rec["present"]==1]["date"].nunique()
    prog = kids[kids["id"]==kid_id]["program"].values
    if len(prog)==0:
        total = att["date"].nunique()
    else:
        p = prog[0]
        total = att[att["program"]==p]["date"].nunique()
    pct = (present/total*100) if total>0 else 0.0
    return present, round(pct,1), total

# ---------------- UI Styling ----------------
st.set_page_config(APP_TITLE, layout="wide", page_icon=LOGO_FILE if os.path.exists(LOGO_FILE) else None)
st.markdown(f"""
<style>
:root{{--bg:{BG}; --card:{CARD}; --muted:{MUTED}; --accent:{PRIMARY_GREEN}; --highlight:{ACCENT_YELLOW}; --text:{TEXT};}}
body {{ background: var(--bg); color: var(--text); }}
.stButton>button {{ background-color: var(--accent); color: #fff; border: none; padding: 8px 12px; border-radius: 8px; }}
.stButton>button:hover {{ filter: brightness(1.05); }}
.card {{ background: var(--card); padding: 16px; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.6); }}
.small-muted {{ color: var(--muted); font-size: 13px; }}
</style>
""", unsafe_allow_html=True)

# ---------------- Login ----------------
def login_panel():
    st.sidebar.markdown("---")
    if os.path.exists(LOGO_FILE):
        st.sidebar.image(LOGO_FILE, width=140)
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        users = load_users()
        user_row = users[users["username"]==username]
        if user_row.empty:
            st.sidebar.error("No such user.")
            return False
        stored = user_row.iloc[0]
        if hash_pwd(password) == stored["password"]:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = stored["role"]
            st.session_state.program = stored.get("program", "")
            st.session_state.full_name = stored.get("full_name", username)
            st.sidebar.success(f"Signed in as {st.session_state.full_name} ({st.session_state.role})")
            return True
        else:
            st.sidebar.error("Incorrect password")
            return False
    return False

# Session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.info("Please log in from the sidebar. Default admin: **admin / admin**")
    login_panel()
    st.stop()

username = st.session_state.username
role = st.session_state.role
user_program = st.session_state.program
full_name = st.session_state.full_name

# Sidebar
st.sidebar.markdown("---")
st.sidebar.write(f"**{full_name}**")
st.sidebar.write(f"Role: `{role}`")
if role != "admin":
    st.sidebar.write(f"Program: `{user_program}`")
st.sidebar.markdown("---")
if st.sidebar.button("Log out"):
    for k in ["logged_in","username","role","program","full_name"]:
        if k in st.session_state: del st.session_state[k]
    st.experimental_rerun()

admin_tool = None
if role == "admin":
    admin_tool = st.sidebar.selectbox("Admin Tools", ["None","Manage Programs","Manage Users","System Reset"])
menu = st.sidebar.radio("Main", ["Dashboard","Kids","Attendance","Profiles","Export"])

# ---------------- Dashboard ----------------
if menu == "Dashboard":
    st.header(APP_TITLE)
    kids = load_kids()
    att = load_att()
    progs = load_programs()
    if role != "admin":
        kids = kids[kids["program"]==user_program]
        att = att[att["program"]==user_program]
    c1,c2,c3 = st.columns(3)
    c1.metric("Total programs", len(progs) if role=="admin" else 1)
    c2.metric("Total kids", kids.shape[0])
    c3.metric("Attendance records", att.shape[0])
    st.markdown("---")
    st.subheader("Recent attendance")
    if att.empty:
        st.write("No attendance yet.")
    else:
        show = att.sort_values("timestamp", ascending=False).head(30)
        merged = show.merge(kids[["id","name"]], left_on="kid_id", right_on="id", how="left")
        merged = merged.rename(columns={"date":"Date","name":"Kid","present":"Present","marked_by":"Marked by","note":"Note","timestamp":"When","program":"Program"})
        st.dataframe(merged[["When","Date","Kid","Program","Present","Marked by","Note"]])

# ---------------- Manage Programs ----------------
if admin_tool == "Manage Programs":
    st.header("Manage Programs")
    progs = load_programs()
    st.subheader("Existing Programs")
    st.write(list(progs["program"].values) if not progs.empty else "— none —")
    with st.form("add_program"):
        newp = st.text_input("Add program name")
        if st.form_submit_button("Add program"):
            if newp.strip():
                ok = add_program(newp.strip())
                if ok:
                    st.success("Program added.")
                    st.experimental_rerun()
                else:
                    st.warning("Program already exists.")
    st.stop()

# ---------------- Manage Users ----------------
if admin_tool == "Manage Users":
    st.header("Manage Users")
    users = load_users()
    st.subheader("Existing users")
    st.dataframe(users[["username","role","program","full_name"]])
    progs = load_programs()
    prog_list = sorted(progs["program"].dropna().tolist())
    st.subheader("Create User")
    with st.form("create_user"):
        un = st.text_input("Username")
        fn = st.text_input("Full name")
        pw = st.text_input("Password")
        role_choice = st.selectbox("Role", ["admin", "user"], index=1)
        assign_prog = ""
        if role_choice != "admin":
            assign_prog = st.selectbox("Assign to program", prog_list)
        if st.form_submit_button("Create user"):
            if not un or not pw or (role_choice != "admin" and not assign_prog):
                st.error("Fill all required fields.")
            else:
                ok, msg = add_user(un.strip(), pw.strip(), role_choice, program=assign_prog, full_name=fn.strip())
                if ok:
                    st.success("User created")
                    st.experimental_rerun()
                else:
                    st.error(msg)
    st.stop()

# ---------------- Reset ----------------
if admin_tool == "System Reset":
    st.warning("This will delete all data and recreate default admin.")
    if st.button("Reset system"):
        for f in [KIDS_FILE, ATT_FILE, PROGRAMS_FILE, USERS_FILE]:
            if os.path.exists(f): os.remove(f)
        ensure_csv(USERS_FILE, ["username","password","role","program","full_name"], create_sample=True)
        ensure_csv(PROGRAMS_FILE, ["program"])
        ensure_csv(KIDS_FILE, ["id","name","age","gender","program","image_path"])
        ensure_csv(ATT_FILE, ["date","kid_id","present","note","program","marked_by","timestamp"])
        st.success("System reset.")
        st.experimental_rerun()

# ---------------- Kids ----------------
if menu == "Kids":
    st.header("Kids Management")
    kids = load_kids()
    programs_df = load_programs()
    programs = sorted(list(set(programs_df["program"].dropna().tolist())))
    st.subheader("Add a kid")
    with st.form("add_kid"):
        name = st.text_input("Full name")
        age = st.number_input("Age", min_value=1, max_value=30, value=6)
        gender = st.selectbox("Gender", ["Male","Female","Other"])
        if role == "admin":
            program = st.selectbox("Program", programs) if programs else st.text_input("Program")
        else:
            st.write(f"You are leader for: **{user_program}**")
            program = user_program
        image = st.file_uploader("Profile picture (optional)", type=["png","jpg","jpeg"])
        if st.form_submit_button("Add kid"):
            if not name.strip():
                st.error("Enter a name")
            else:
                if program and program not in programs:
                    add_program(program)
                add_kid(name.strip(), age, gender, program, image)
                st.success("Kid added")
                st.experimental_rerun()

    st.markdown("---")
    st.subheader("List of kids")
    if role != "admin":
        kids = kids[kids["program"]==user_program]
    if kids.empty:
        st.info("No kids to show.")
    else:
        st.dataframe(kids)

# ---------------- Attendance ----------------
if menu == "Attendance":
    st.header("Attendance")
    kids = load_kids()
    att = load_att()
    programs_df = load_programs()
    programs = sorted(list(set(programs_df["program"].dropna().tolist())))
    att_date = st.date_input("Attendance date", value=date.today())
    att_str = att_date.isoformat()
    if role == "admin":
        prog_choice = st.selectbox("Select program", programs)
        scope = kids[kids["program"]==prog_choice] if prog_choice else kids.copy()
    else:
        scope = kids[kids["program"]==user_program]
    if scope.empty:
        st.info("No kids to mark attendance for.")
    else:
        existing = att[att["date"]==att_str]
        present_defaults = {r["kid_id"]: int(r["present"])==1 for _,r in existing.iterrows()}
        notes_defaults = {r["kid_id"]: r.get("note","") for _,r in existing.iterrows()}
        with st.form("mark_att"):
            checked_map = {}
            notes_map = {}
            for _, k in scope.iterrows():
                cols = st.columns([1,4,3])
                with cols[0]:
                    checked = st.checkbox("", value=present_defaults.get(k["id"], False))
                with cols[1]:
                    st.markdown(f"**{k['name']}**")
                    st.write(f"Program: {k['program']}")
                with cols[2]:
                    note = st.text_input("Note", value=notes_defaults.get(k["id"], ""))
                checked_map[k["id"]] = checked
                notes_map[k["id"]] = note
            if st.form_submit_button("Save attendance"):
                new_att = att[att["date"]!=att_str]
                now = datetime.now().isoformat(timespec="seconds")
                for kid_id, is_present in checked_map.items():
                    kid_prog = kids[kids["id"]==kid_id]["program"].values[0]
                    row = {
                        "date": att_str,
                        "kid_id": kid_id,
                        "present": 1 if is_present else 0,
                        "note": notes_map.get(kid_id,""),
                        "program": kid_prog,
                        "marked_by": username,
                        "timestamp": now
                    }
                    new_att = pd.concat([new_att, pd.DataFrame([row])], ignore_index=True)
                save_att(new_att)
                st.success("Attendance saved.")
                st.experimental_rerun()

# ---------------- Profiles ----------------
if menu == "Profiles":
    st.header("Child Profile")
    kids = load_kids()
    if role != "admin":
        kids = kids[kids["program"]==user_program]
    st.dataframe(kids)

# ---------------- Export ----------------
if menu == "Export":
    st.header("Export Data")
    for fn, label in [(USERS_FILE,"users.csv"), (PROGRAMS_FILE,"programs.csv"), (KIDS_FILE,"kids.csv"), (ATT_FILE,"attendance.csv")]:
        if os.path.exists(fn):
            with open(fn,"rb") as f:
                st.download_button(label, f, file_name=label)
