# app.py
import streamlit as st
import pandas as pd
import os
import hashlib
import uuid
from datetime import date, datetime
from pathlib import Path

# ---------------- Configuration ----------------
APP_TITLE = "Fafali Attendance Manager"
LOGO_FILE = "Fafali_icont.png"   # put this image in same folder as app.py
IMAGES_DIR = "images"

USERS_CSV = "users.csv"
PROGRAMS_CSV = "programs.csv"
KIDS_CSV = "kids.csv"
ATT_CSV = "attendance.csv"

# Colors pulled from your logo (approx)
PRIMARY_GREEN = "#0b7a3a"
ACCENT_YELLOW = "#ffd83a"
BG = "#070b0d"
CARD = "#0f1720"
MUTED = "#94a3b8"
TEXT = "#e6eef6"

# Ensure folders
os.makedirs(IMAGES_DIR, exist_ok=True)

# ---------------- Utility functions ----------------
def hash_pwd(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def ensure_csv(path, columns, create_admin=False):
    if not os.path.exists(path):
        pd.DataFrame(columns=columns).to_csv(path, index=False)
    if create_admin and path == USERS_CSV:
        users = pd.read_csv(USERS_CSV)
        if users.empty:
            admin = {"username": "admin", "password": hash_pwd("admin"), "role": "admin", "program": "", "full_name": "Administrator"}
            pd.DataFrame([admin]).to_csv(USERS_CSV, index=False)

# Initialize CSVs if missing
ensure_csv(USERS_CSV, ["username", "password", "role", "program", "full_name"], create_admin=True)
ensure_csv(PROGRAMS_CSV, ["program"])
ensure_csv(KIDS_CSV, ["id", "name", "age", "gender", "program", "image_path"])
ensure_csv(ATT_CSV, ["date", "kid_id", "present", "note", "program", "marked_by", "timestamp"])

# Load/save helpers
def load_users(): return pd.read_csv(USERS_CSV) if os.path.exists(USERS_CSV) else pd.DataFrame(columns=["username","password","role","program","full_name"])
def save_users(df): df.to_csv(USERS_CSV, index=False)

def load_programs(): return pd.read_csv(PROGRAMS_CSV) if os.path.exists(PROGRAMS_CSV) else pd.DataFrame(columns=["program"])
def save_programs(df): df.to_csv(PROGRAMS_CSV, index=False)

def load_kids(): return pd.read_csv(KIDS_CSV, dtype={"id": str}) if os.path.exists(KIDS_CSV) else pd.DataFrame(columns=["id","name","age","gender","program","image_path"])
def save_kids(df): df.to_csv(KIDS_CSV, index=False)

def load_att(): return pd.read_csv(ATT_CSV, dtype={"kid_id": str}) if os.path.exists(ATT_CSV) else pd.DataFrame(columns=["date","kid_id","present","note","program","marked_by","timestamp"])
def save_att(df): df.to_csv(ATT_CSV, index=False)

# Domain helpers
def add_user(username, password, role, program="", full_name=""):
    users = load_users()
    if username in users["username"].values:
        return False, "Username already exists."
    row = {"username": username, "password": hash_pwd(password), "role": role, "program": program, "full_name": full_name}
    users = pd.concat([users, pd.DataFrame([row])], ignore_index=True)
    save_users(users)
    return True, "User created."

def remove_user(username):
    users = load_users()
    users = users[users["username"] != username]
    save_users(users)

def add_program(name):
    progs = load_programs()
    if name in progs["program"].values:
        return False
    progs = pd.concat([progs, pd.DataFrame([{"program": name}])], ignore_index=True)
    save_programs(progs)
    return True

def save_kid_image(uploaded_file, kid_name, kid_id):
    ext = Path(uploaded_file.name).suffix
    safe = "".join([c for c in kid_name if c.isalnum() or c in (" ", "_")]).strip().replace(" ", "_")
    dest = os.path.join(IMAGES_DIR, f"{safe}_{kid_id}{ext}")
    with open(dest, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return dest

def add_kid(name, age, gender, program, image_file=None):
    kids = load_kids()
    kid_id = str(uuid.uuid4())[:8]
    image_path = ""
    if image_file is not None:
        image_path = save_kid_image(image_file, name, kid_id)
    row = {"id": kid_id, "name": name, "age": int(age), "gender": gender, "program": program, "image_path": image_path}
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

def kid_stats(kid_id):
    att = load_att()
    kids = load_kids()
    rec = att[att["kid_id"]==kid_id]
    present_days = rec[rec["present"]==1]["date"].nunique()
    prog_arr = kids[kids["id"]==kid_id]["program"].values
    if len(prog_arr)==0:
        total_days = att["date"].nunique()
    else:
        p = prog_arr[0]
        total_days = att[att["program"]==p]["date"].nunique()
    pct = (present_days/total_days*100) if total_days>0 else 0.0
    return present_days, round(pct,1), total_days

# ---------------- Styling ----------------
st.set_page_config(APP_TITLE, layout="wide", page_icon=LOGO_FILE if os.path.exists(LOGO_FILE) else None)
st.markdown(f"""
    <style>
    :root {{ --bg:{BG}; --card:{CARD}; --muted:{MUTED}; --accent:{PRIMARY_GREEN}; --highlight:{ACCENT_YELLOW}; --text:{TEXT}; }}
    html, body, [class*="css"] {{ background: var(--bg) !important; color: var(--text) !important; }}
    .block-container{{ padding-top:1rem; }}
    .card{{ background:var(--card); padding:14px; border-radius:10px; box-shadow: 0 6px 30px rgba(0,0,0,0.6); }}
    .muted{{ color:var(--muted); font-size:13px; }}
    .btn-primary > button {{ background: var(--accent); color: #fff; border-radius:8px; padding:8px 12px; }}
    .logo-row {{ display:flex; align-items:center; gap:14px; }}
    .small {{ font-size:13px; color:var(--muted); }}
    </style>
""", unsafe_allow_html=True)

# ---------------- Authentication UI ----------------
def login_sidebar():
    st.sidebar.image(LOGO_FILE, width=120) if os.path.exists(LOGO_FILE) else None
    st.sidebar.title("Sign in")
    role_choice = st.sidebar.radio("Login as", ("Admin", "User"))
    username = st.sidebar.text_input("Username", key="login_user")
    password = st.sidebar.text_input("Password", type="password", key="login_pw")
    if st.sidebar.button("Login"):
        users = load_users()
        row = users[users["username"]==username]
        if row.empty:
            st.sidebar.error("No such user.")
            return False
        stored = row.iloc[0]
        if hash_pwd(password) != stored["password"]:
            st.sidebar.error("Incorrect password.")
            return False
        # role enforcement: admin must select Admin, users must select User
        if role_choice.lower() == "admin" and stored["role"] != "admin":
            st.sidebar.error("You are not an admin. Select User or contact admin.")
            return False
        if role_choice.lower() == "user" and stored["role"] == "admin":
            st.sidebar.warning("Admin must select Admin role to login.")
            # allow admin to still login as admin if they change role_choice; but for now force them to pick Admin.
            return False
        # successful login
        st.session_state.logged_in = True
        st.session_state.username = stored["username"]
        st.session_state.role = stored["role"]
        st.session_state.program = stored.get("program", "")
        st.session_state.full_name = stored.get("full_name", stored["username"])
        st.sidebar.success(f"Signed in: {st.session_state.full_name} ({st.session_state.role})")
        return True
    return False

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# If not logged in -> show centered hero and stop (login lives in sidebar)
if not st.session_state.logged_in:
    cols = st.columns([1,2,1])
    with cols[1]:
        if os.path.exists(LOGO_FILE):
            st.image(LOGO_FILE, width=140)
        st.markdown(f"<h1 style='color:{TEXT}; margin:6px 0'>{APP_TITLE}</h1>", unsafe_allow_html=True)
        st.markdown("<p class='muted'>Role-select login (Admin or User). Default admin: <b>admin</b> / <b>admin</b></p>", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("<div class='card'><b>Instructions</b><p class='muted'>Admins create programs & users. Users see only assigned program kids and can mark attendance.</p></div>", unsafe_allow_html=True)
    login_sidebar()
    st.stop()

# After login
username = st.session_state.username
role = st.session_state.role
user_program = st.session_state.program
full_name = st.session_state.full_name

# Sidebar info & menu
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
    admin_tool = st.sidebar.selectbox("Admin tools", ("None", "Manage Programs", "Manage Users", "System Reset"))

menu = st.sidebar.radio("Main", ("Dashboard", "Kids", "Attendance", "Profiles", "Export"), index=0)

# ---------------- Dashboard ----------------
if menu == "Dashboard":
    st.markdown(f"<div style='display:flex; align-items:center; gap:12px;'>"
                f"{('<img src=\"'+LOGO_FILE+'\" width=\"48\" style=\"border-radius:8px;\">') if os.path.exists(LOGO_FILE) else ''}"
                f"<h2 style='margin:0; color:{TEXT}'>{APP_TITLE}</h2></div>", unsafe_allow_html=True)
    st.markdown("### Overview")
    kids = load_kids()
    att = load_att()
    progs = load_programs()
    c1, c2, c3 = st.columns(3)
    c1.metric("Programs", len(progs))
    c2.metric("Kids", kids.shape[0])
    c3.metric("Attendance records", att.shape[0])
    st.markdown("---")
    st.subheader("Recent attendance")
    if att.empty:
        st.write("No attendance yet.")
    else:
        recent = att.sort_values("timestamp", ascending=False).head(30)
        merged = recent.merge(kids[["id","name"]], left_on="kid_id", right_on="id", how="left")
        merged = merged.rename(columns={"date":"Date","name":"Kid","present":"Present","marked_by":"Marked by","note":"Note","timestamp":"When","program":"Program"})
        st.dataframe(merged[["When","Date","Kid","Program","Present","Marked by","Note"]])

# ---------------- Admin tools ----------------
if admin_tool == "Manage Programs":
    st.header("Manage Programs")
    progs = load_programs()
    st.subheader("Existing Programs")
    if progs.empty:
        st.write("— none —")
    else:
        st.write(list(progs["program"].values))
    with st.form("add_program"):
        p = st.text_input("Program name")
        if st.form_submit_button("Add program"):
            if p.strip():
                ok = add_program(p.strip())
                if ok:
                    st.success("Program added.")
                    st.experimental_rerun()
                else:
                    st.warning("Program already exists.")
    st.stop()

if admin_tool == "Manage Users":
    st.header("Manage Users")
    users = load_users()
    st.subheader("Existing users")
    if users.empty:
        st.write("No users")
    else:
        st.dataframe(users[["username","role","program","full_name"]].rename(columns={"username":"Username","role":"Role","program":"Program","full_name":"Full name"}))
    st.subheader("Create user (program leader)")
    with st.form("create_user"):
        uname = st.text_input("Username")
        fname = st.text_input("Full name")
        pwd = st.text_input("Password")
        role_choice = st.selectbox("Role", ("leader",))
        assign_prog = st.text_input("Assign program (exact name)")
        if st.form_submit_button("Create"):
            if not (uname and pwd and assign_prog):
                st.error("Fill username, password and program")
            else:
                ok, msg = add_user(uname, pwd, role_choice, program=assign_prog, full_name=fname)
                if ok:
                    st.success("User created.")
                    st.experimental_rerun()
                else:
                    st.error(msg)
    st.stop()

if admin_tool == "System Reset":
    st.header("System Reset")
    st.warning("Deletes programs, kids, attendance and users (except default admin).")
    if st.button("RESET SYSTEM"):
        for f in [PROGRAMS_CSV, KIDS_CSV, ATT_CSV, USERS_CSV]:
            if os.path.exists(f): os.remove(f)
        ensure_csv(USERS_CSV, ["username","password","role","program","full_name"], create_admin=True)
        ensure_csv(PROGRAMS_CSV, ["program"])
        ensure_csv(KIDS_CSV, ["id","name","age","gender","program","image_path"])
        ensure_csv(ATT_CSV, ["date","kid_id","present","note","program","marked_by","timestamp"])
        st.success("System reset.")
        st.experimental_rerun()

# ---------------- Kids Management ----------------
if menu == "Kids":
    st.header("Kids Management")
    kids = load_kids()
    programs_df = load_programs()
    programs = sorted(list(set(programs_df["program"].dropna().tolist() + kids["program"].dropna().unique().tolist())))
    st.subheader("Add kid")
    with st.form("add_kid"):
        name = st.text_input("Full name")
        age = st.number_input("Age", min_value=1, max_value=30, value=6)
        gender = st.selectbox("Gender", ("Male","Female","Other"))
        if role == "admin":
            program = st.selectbox("Program", ([""] + programs)) if programs else st.text_input("Program")
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
                kid_id = add_kid(name.strip(), age, gender, program, image)
                st.success("Kid added.")
                st.experimental_rerun()

    st.markdown("---")
    st.subheader("Kids list")
    kids = load_kids()
    if role == "admin":
        df_show = kids.copy()
        prog_filter = st.selectbox("Filter by program", (["-- All --"] + programs))
        if prog_filter and prog_filter != "-- All --":
            df_show = df_show[df_show["program"]==prog_filter]
    else:
        df_show = kids[kids["program"]==user_program]

    if df_show.empty:
        st.info("No kids in view.")
    else:
        for _, r in df_show.iterrows():
            cols = st.columns([1,3,4,2])
            with cols[0]:
                if r["image_path"] and os.path.exists(r["image_path"]):
                    st.image(r["image_path"], width=84)
                else:
                    st.write("🧒")
            with cols[1]:
                st.markdown(f"**{r['name']}**")
                st.write(f"Age: {r['age']} • {r['gender']}")
            with cols[2]:
                st.write(f"Program: **{r['program']}**")
                present, pct, total = kid_stats(r["id"])
                st.write(f"Present days: {present} — Attendance: {pct}% (program days: {total})")
            with cols[3]:
                if st.button(f"View|{r['id']}", key=f"view_{r['id']}"):
                    st.session_state.selected_kid = r['id']
                    st.experimental_rerun()
                if role in ("admin","leader"):
                    if st.button(f"Remove|{r['id']}", key=f"remove_{r['id']}"):
                        remove_kid(r["id"])
                        st.success("Kid removed")
                        st.experimental_rerun()

# ---------------- Attendance ----------------
if menu == "Attendance":
    st.header("Attendance")
    kids = load_kids()
    att = load_att()
    programs_df = load_programs()
    programs = sorted(list(set(programs_df["program"].dropna().tolist() + kids["program"].dropna().unique().tolist())))
    att_date = st.date_input("Attendance date", value=date.today())
    att_str = att_date.isoformat()

    if role == "admin":
        prog_choice = st.selectbox("Program to mark", (["-- All --"] + programs))
        if prog_choice and prog_choice != "-- All --":
            scope = kids[kids["program"]==prog_choice]
        else:
            scope = kids.copy()
    else:
        scope = kids[kids["program"]==user_program]

    if scope.empty:
        st.info("No kids to mark.")
    else:
        st.subheader(f"Mark attendance for {len(scope)} kids")
        existing = att[att["date"]==att_str]
        present_defaults = {row["kid_id"]: int(row["present"])==1 for _,row in existing.iterrows()}
        notes_defaults = {row["kid_id"]: row.get("note","") for _,row in existing.iterrows()}
        with st.form("mark_att"):
            checked = {}
            notes = {}
            for _, k in scope.iterrows():
                c1,c2,c3 = st.columns([1,4,3])
                with c1:
                    val = st.checkbox("", value=present_defaults.get(k["id"], False), key=f"chk_{k['id']}")
                with c2:
                    st.markdown(f"**{k['name']}**")
                    st.write(f"Program: {k['program']}")
                with c3:
                    note = st.text_input("Note", value=notes_defaults.get(k["id"], ""), key=f"note_{k['id']}")
                checked[k["id"]] = val
                notes[k["id"]] = note
            if st.form_submit_button("Save attendance"):
                new_att = att[att["date"]!=att_str]  # remove any existing for this date
                now = datetime.now().isoformat(timespec="seconds")
                for kid_id, is_present in checked.items():
                    kid_prog = kids[kids["id"]==kid_id]["program"].values[0] if not kids.empty else ""
                    row = {"date": att_str, "kid_id": kid_id, "present": 1 if is_present else 0, "note": notes.get(kid_id,""), "program": kid_prog, "marked_by": username, "timestamp": now}
                    new_att = pd.concat([new_att, pd.DataFrame([row])], ignore_index=True)
                save_att(new_att)
                st.success("Attendance saved.")
                st.experimental_rerun()

# ---------------- Profiles ----------------
if menu == "Profiles":
    st.header("Child Profile")
    selected = st.session_state.get("selected_kid", None)
    kids = load_kids()
    if selected is None:
        st.info("Select a kid from the 'Kids' list to view their profile.")
    else:
        if selected not in kids["id"].values:
            st.error("Kid not found.")
        else:
            kid = kids[kids["id"]==selected].iloc[0]
            if role == "leader" and kid["program"] != user_program:
                st.error("Access denied to this profile.")
            else:
                c1,c2,c3 = st.columns([1,2,4])
                with c1:
                    if kid["image_path"] and os.path.exists(kid["image_path"]):
                        st.image(kid["image_path"], width=180)
                    else:
                        st.write("No image")
                with c2:
                    st.subheader(kid["name"])
                    st.write(f"Age: {kid['age']}")
                    st.write(f"Gender: {kid['gender']}")
                    st.write(f"Program: {kid['program']}")
                    if role in ("admin","leader"):
                        if st.button("Edit kid"):
                            st.session_state.edit_kid = kid["id"]
                            st.experimental_rerun()
                with c3:
                    att = load_att()
                    kid_att = att[att["kid_id"]==kid["id"]].sort_values("date", ascending=False)
                    present_days = kid_att[kid_att["present"]==1].shape[0]
                    total_prog_days = kid_att["date"].nunique()
                    pct = (present_days/total_prog_days*100) if total_prog_days>0 else 0.0
                    st.markdown("**Attendance summary**")
                    st.write(f"Total records: {kid_att.shape[0]}")
                    st.write(f"Days present: {present_days}")
                    st.write(f"Attendance % (program days): {pct:.1f}%")
                    st.markdown("---")
                    st.subheader("Attendance history")
                    if kid_att.empty:
                        st.write("No records")
                    else:
                        display = kid_att.merge(kids[["id","name"]], left_on="kid_id", right_on="id", how="left")
                        display = display[["date","present","note","marked_by","timestamp"]].rename(columns={"date":"Date","present":"Present","note":"Note","marked_by":"Marked by","timestamp":"When"})
                        display["Present"] = display["Present"].apply(lambda x: "Yes" if int(x)==1 else "No")
                        st.dataframe(display)

# ---------------- Export ----------------
if menu == "Export":
    st.header("Export Data")
    st.write("Download CSV backups")
    for fn,label in [(USERS_CSV,"users.csv"), (PROGRAMS_CSV,"programs.csv"), (KIDS_CSV,"kids.csv"), (ATT_CSV,"attendance.csv")]:
        if os.path.exists(fn):
            with open(fn, "rb") as f:
                st.download_button(label, f, file_name=label)

# ---------------- Edit kid modal ----------------
if st.session_state.get("edit_kid", None):
    kid_id = st.session_state.get("edit_kid")
    kids = load_kids()
    if kid_id not in kids["id"].values:
        st.error("Kid not found.")
    else:
        kid = kids[kids["id"]==kid_id].iloc[0]
        st.markdown("---")
        st.header("Edit Kid")
        with st.form("edit_kid"):
            ename = st.text_input("Name", value=kid["name"])
            eage = st.number_input("Age", min_value=1, max_value=30, value=int(kid["age"]))
            egender = st.selectbox("Gender", ("Male","Female","Other"), index=["Male","Female","Other"].index(kid["gender"]) if kid["gender"] in ["Male","Female","Other"] else 2)
            programs_df = load_programs()
            programs = sorted(list(set(programs_df["program"].dropna().tolist() + kids["program"].dropna().unique().tolist())))
            if role == "admin":
                eprogram = st.selectbox("Program", ([""]+programs), index=(programs.index(kid["program"]) if kid["program"] in programs else 0))
            else:
                eprogram = kid["program"]
                st.write(f"Program: {eprogram}")
            eimage = st.file_uploader("Replace image (optional)", type=["png","jpg","jpeg"])
            if st.form_submit_button("Save changes"):
                image_path = kid["image_path"]
                if eimage is not None:
                    image_path = save_kid_image(eimage, ename, kid_id)
                kids.loc[kids["id"]==kid_id, ["name","age","gender","program","image_path"]] = [ename, int(eage), egender, eprogram, image_path]
                save_kids(kids)
                st.success("Kid updated.")
                del st.session_state["edit_kid"]
                st.experimental_rerun()
