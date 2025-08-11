# app.py
"""
Fafali Attendance Manager - single-file refactor

Key upgrades:
- Dedicated login page before the main UI
- Centralized CSV helpers with caching and safe atomic writes
- Search for kids, confirm-before-delete, bulk attendance controls
- Cleaner session-state handling
- Export CSVs or download a ZIP backup
- Keeps your original features and structure, just tidier
"""
import streamlit as st
import pandas as pd
import os
import shutil
import hashlib
import uuid
from datetime import date, datetime
from pathlib import Path
import zipfile
import io

# ---------------- Configuration ----------------
APP_TITLE = "Fafali Attendance Manager"
LOGO_FILE = "Fafali_icont.png"   # optional
IMAGES_DIR = "images"
DATA_DIR = "data"

USERS_CSV = os.path.join(DATA_DIR, "users.csv")
PROGRAMS_CSV = os.path.join(DATA_DIR, "programs.csv")
KIDS_CSV = os.path.join(DATA_DIR, "kids.csv")
ATT_CSV = os.path.join(DATA_DIR, "attendance.csv")

# Colors (kept similar to your original)
PRIMARY_GREEN = "#0b7a3a"
ACCENT_YELLOW = "#ffd83a"
BG = "#070b0d"
CARD = "#0f1720"
MUTED = "#94a3b8"
TEXT = "#e6eef6"

# ---------------- Ensure folders ----------------
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------- Utility helpers ----------------
def hash_pwd(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def atomic_save_csv(path: str, df: pd.DataFrame):
    """Save CSV to a tmp file then move it into place. Clear cache after."""
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False)
    shutil.move(tmp, path)
    # clear cached loaders
    try:
        load_csv.clear()
    except Exception:
        # if caching not present or different streamlit version, ignore
        pass
    st.experimental_rerun_allowed = False  # no-op but clear intent

@st.cache_data
def load_csv(path: str) -> pd.DataFrame:
    """Cached CSV loader. Returns empty DF with no rows if file missing."""
    if os.path.exists(path):
        try:
            return pd.read_csv(path, dtype=str).fillna("")
        except Exception:
            # if file corrupted, return empty frame with no rows
            return pd.DataFrame()
    return pd.DataFrame()

def ensure_csv(path: str, columns: list, create_admin=False):
    if not os.path.exists(path):
        pd.DataFrame(columns=columns).to_csv(path, index=False)
    # create default admin user at users csv initial creation
    if create_admin and path == USERS_CSV:
        df = load_csv(USERS_CSV)
        if df.empty:
            admin = {"username":"admin", "password": hash_pwd("admin"), "role":"admin", "program":"", "full_name":"Administrator"}
            atomic_save_csv(USERS_CSV, pd.DataFrame([admin]))

# initialize files with columns
ensure_csv(USERS_CSV, ["username","password","role","program","full_name"], create_admin=True)
ensure_csv(PROGRAMS_CSV, ["program"])
ensure_csv(KIDS_CSV, ["id","name","age","gender","program","image_path"])
ensure_csv(ATT_CSV, ["date","kid_id","present","note","program","marked_by","timestamp"])

# Domain helpers
def get_users(): return load_csv(USERS_CSV)
def save_users(df): atomic_save_csv(USERS_CSV, df)

def get_programs(): return load_csv(PROGRAMS_CSV)
def save_programs(df): atomic_save_csv(PROGRAMS_CSV, df)

def get_kids(): return load_csv(KIDS_CSV)
def save_kids(df): atomic_save_csv(KIDS_CSV, df)

def get_att(): return load_csv(ATT_CSV)
def save_att(df): atomic_save_csv(ATT_CSV, df)

def add_user(username, password, role, program="", full_name=""):
    users = get_users()
    if username in users.get("username", []).tolist():
        return False, "Username already exists."
    row = {"username":username, "password": hash_pwd(password), "role": role, "program": program, "full_name": full_name}
    users = pd.concat([users, pd.DataFrame([row])], ignore_index=True)
    save_users(users)
    return True, "User created."

def remove_user(username):
    users = get_users()
    users = users[users["username"] != username]
    save_users(users)

def add_program(name):
    progs = get_programs()
    # case-insensitive dup check
    if name.strip().lower() in [p.strip().lower() for p in progs.get("program", []).tolist()]:
        return False
    progs = pd.concat([progs, pd.DataFrame([{"program": name.strip()}])], ignore_index=True)
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
    kids = get_kids()
    kid_id = str(uuid.uuid4())[:8]
    image_path = ""
    if image_file is not None:
        image_path = save_kid_image(image_file, name, kid_id)
    row = {"id": kid_id, "name": name, "age": str(int(age)), "gender": gender, "program": program, "image_path": image_path}
    kids = pd.concat([kids, pd.DataFrame([row])], ignore_index=True)
    save_kids(kids)
    return kid_id

def remove_kid(kid_id):
    kids = get_kids()
    kids = kids[kids["id"] != kid_id]
    save_kids(kids)
    att = get_att()
    att = att[att["kid_id"] != kid_id]
    save_att(att)

def kid_stats(kid_id):
    att = get_att()
    kids = get_kids()
    rec = att[att["kid_id"]==kid_id]
    present_days = rec[rec["present"]=="1"]["date"].nunique()
    prog_arr = kids[kids["id"]==kid_id]["program"].values
    if len(prog_arr)==0:
        total_days = att["date"].nunique()
    else:
        p = prog_arr[0]
        total_days = att[att["program"]==p]["date"].nunique()
    pct = (int(present_days)/int(total_days)*100) if int(total_days)>0 else 0.0
    return int(present_days), round(float(pct),1), int(total_days)

# ---------------- Styling ----------------
st.set_page_config(APP_TITLE, layout="wide", page_icon=LOGO_FILE if os.path.exists(LOGO_FILE) else None)
st.markdown(f"""
    <style>
    :root {{ --bg:{BG}; --card:{CARD}; --muted:{MUTED}; --accent:{PRIMARY_GREEN}; --highlight:{ACCENT_YELLOW}; --text:{TEXT}; }}
    html, body, [class*="css"] {{ background: var(--bg) !important; color: var(--text) !important; }}
    .block-container{{ padding-top:1rem; }}
    .card{{ background:var(--card); padding:14px; border-radius:10px; box-shadow: 0 6px 30px rgba(0,0,0,0.6); }}
    .muted{{ color:var(--muted); font-size:13px; }}
    .btn-primary > button {{ background: var(--accent); color: #000; border-radius:8px; padding:8px 12px; }}
    .logo-row {{ display:flex; align-items:center; gap:14px; }}
    .small {{ font-size:13px; color:var(--muted); }}
    </style>
""", unsafe_allow_html=True)

# ---------------- Session defaults ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "program" not in st.session_state:
    st.session_state.program = ""
if "full_name" not in st.session_state:
    st.session_state.full_name = ""
if "selected_kid" not in st.session_state:
    st.session_state.selected_kid = None
if "pending_delete" not in st.session_state:
    st.session_state.pending_delete = None

# ---------------- Authentication UI (dedicated page) ----------------
def login_page():
    st.markdown("<div style='display:flex; align-items:center; gap:12px;'>"
                f"{('<img src=\"'+LOGO_FILE+'\" width=\"64\" style=\"border-radius:8px;\">') if os.path.exists(LOGO_FILE) else ''}"
                f"<h1 style='margin:0; color:{TEXT}'>{APP_TITLE}</h1></div>", unsafe_allow_html=True)
    st.write("")
    st.markdown("<div class='card'><p class='muted'>Sign in with your username and password. Default admin: <b>admin</b>/<b>admin</b></p></div>", unsafe_allow_html=True)
    st.write("")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        role_choice = st.selectbox("Login as", ("Admin", "User"))
        submitted = st.form_submit_button("Login")
        if submitted:
            users = get_users()
            row = users[users["username"]==username]
            if row.empty:
                st.error("No such user.")
                return False
            stored = row.iloc[0]
            if hash_pwd(password) != stored["password"]:
                st.error("Incorrect password.")
                return False
            # role enforcement
            if role_choice.lower() == "admin" and stored["role"] != "admin":
                st.error("You are not an admin. Select User or contact admin.")
                return False
            if role_choice.lower() == "user" and stored["role"] == "admin":
                st.warning("Admin must select Admin role to login.")
                return False
            # success
            st.session_state.logged_in = True
            st.session_state.username = stored["username"]
            st.session_state.role = stored["role"]
            st.session_state.program = stored.get("program","")
            st.session_state.full_name = stored.get("full_name", stored["username"])
            st.success(f"Signed in as {st.session_state.full_name}")
            return True
    return False

# If not logged in, show the login page and stop
if not st.session_state.logged_in:
    cols = st.columns([1,2,1])
    with cols[1]:
        login_page()
    st.stop()

# ---------------- After login: Sidebar and navigation ----------------
username = st.session_state.username
role = st.session_state.role
user_program = st.session_state.program
full_name = st.session_state.full_name

with st.sidebar:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=120)
    st.markdown(f"**{full_name}**")
    st.markdown(f"Role: `{role}`")
    if role != "admin":
        st.markdown(f"Program: `{user_program}`")
    st.markdown("---")
    menu = st.radio("Menu", ("Dashboard","Kids","Attendance","Programs","Profiles","Export","Admin Tools"))
    st.markdown("---")
    if st.button("Log out"):
        # clear session state & refresh
        for k in ["logged_in","username","role","program","full_name","selected_kid","pending_delete","edit_kid"]:
            if k in st.session_state:
                del st.session_state[k]
        st.experimental_rerun()

# ---------------- Dashboard ----------------
def page_dashboard():
    st.markdown(f"<div style='display:flex; align-items:center; gap:12px;'>"
                f"<h2 style='margin:0; color:{TEXT}'>{APP_TITLE} — Dashboard</h2></div>", unsafe_allow_html=True)
    st.markdown("### Overview")
    kids = get_kids()
    att = get_att()
    progs = get_programs()
    c1,c2,c3 = st.columns(3)
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
        st.dataframe(merged[["When","Date","Kid","Program","Present","Marked by","Note"]], use_container_width=True)

# ---------------- Kids Page ----------------
def page_kids():
    st.header("Kids Management")
    kids = get_kids()
    programs_df = get_programs()
    programs = sorted(list(set(programs_df["program"].dropna().tolist() + kids["program"].dropna().unique().tolist())))
    # Add kid form
    with st.expander("Add kid"):
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
            submitted = st.form_submit_button("Add kid")
            if submitted:
                if not name.strip():
                    st.error("Enter a name")
                else:
                    if program and program not in programs:
                        add_program(program)
                    add_kid(name.strip(), age, gender, program, image)
                    st.success("Kid added.")
                    st.experimental_rerun()

    st.markdown("---")
    st.subheader("Kids list")
    search = st.text_input("Search by name")
    if role == "admin":
        prog_filter = st.selectbox("Filter by program", (["-- All --"] + programs))
        df_show = kids.copy()
        if prog_filter and prog_filter != "-- All --":
            df_show = df_show[df_show["program"]==prog_filter]
    else:
        df_show = kids[kids["program"]==user_program]
    if search:
        df_show = df_show[df_show["name"].str.contains(search, case=False, na=False)]
    if df_show.empty:
        st.info("No kids in view.")
    else:
        # sort by name
        df_show = df_show.sort_values("name")
        for _, r in df_show.iterrows():
            cols = st.columns([1,3,4,2])
            with cols[0]:
                if r.get("image_path") and os.path.exists(r["image_path"]):
                    st.image(r["image_path"], width=84)
                else:
                    st.markdown("🧒")
            with cols[1]:
                st.markdown(f"**{r['name']}**")
                st.write(f"Age: {r['age']} • {r['gender']}")
            with cols[2]:
                st.write(f"Program: **{r['program']}**")
                present, pct, total = kid_stats(r["id"])
                st.write(f"Present days: {present} — Attendance: {pct}% (program days: {total})")
            with cols[3]:
                if st.button("View", key=f"view_{r['id']}"):
                    st.session_state.selected_kid = r['id']
                    st.experimental_rerun()
                if role in ("admin","leader"):
                    # delete with confirmation flow
                    if st.button("Remove", key=f"remove_{r['id']}"):
                        st.session_state.pending_delete = {"type":"kid", "id": r["id"], "name": r["name"]}
                        st.experimental_rerun()

    # Pending delete confirmation
    if st.session_state.pending_delete and st.session_state.pending_delete.get("type")=="kid":
        pdv = st.session_state.pending_delete
        st.warning(f"Confirm delete kid: {pdv['name']} (id: {pdv['id']})")
        col1,col2 = st.columns(2)
        if col1.button("Yes, delete"):
            remove_kid(pdv["id"])
            st.success("Kid removed.")
            st.session_state.pending_delete = None
            st.experimental_rerun()
        if col2.button("Cancel"):
            st.session_state.pending_delete = None
            st.experimental_rerun()

# ---------------- Attendance Page ----------------
def page_attendance():
    st.header("Attendance")
    kids = get_kids()
    att = get_att()
    programs_df = get_programs()
    programs = sorted(list(set(programs_df["program"].dropna().tolist() + kids["program"].dropna().unique().tolist())))
    att_date = st.date_input("Attendance date", value=date.today())
    att_str = att_date.isoformat()

    # scope selection
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
        return

    st.subheader(f"Mark attendance for {len(scope)} kids")
    existing = att[att["date"]==att_str]
    present_defaults = {row["kid_id"]: (row["present"]=="1") for _,row in existing.iterrows()}
    notes_defaults = {row["kid_id"]: row.get("note","") for _,row in existing.iterrows()}

    # Bulk buttons
    col1,col2,col3 = st.columns([1,1,6])
    if col1.button("All present"):
        for k in scope["id"].tolist():
            present_defaults[k] = True
    if col2.button("All absent"):
        for k in scope["id"].tolist():
            present_defaults[k] = False

    with st.form("mark_att"):
        checked = {}
        notes = {}
        for _, k in scope.sort_values("name").iterrows():
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
            new_att = att[att["date"]!=att_str]  # remove any existing entries for this date
            now = datetime.now().isoformat(timespec="seconds")
            for kid_id, is_present in checked.items():
                kid_prog = kids[kids["id"]==kid_id]["program"].values[0] if not kids.empty else ""
                row = {"date": att_str, "kid_id": kid_id, "present": "1" if is_present else "0", "note": notes.get(kid_id,""), "program": kid_prog, "marked_by": username, "timestamp": now}
                new_att = pd.concat([new_att, pd.DataFrame([row])], ignore_index=True)
            save_att(new_att)
            st.success("Attendance saved.")
            st.experimental_rerun()

# ---------------- Programs Page ----------------
def page_programs():
    st.header("Programs")
    progs = get_programs()
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
            else:
                st.error("Enter program name.")

# ---------------- Profiles Page ----------------
def page_profiles():
    st.header("Child Profile")
    selected = st.session_state.get("selected_kid", None)
    kids = get_kids()
    if selected is None:
        st.info("Select a kid from the 'Kids' list to view their profile.")
        return
    if selected not in kids["id"].values:
        st.error("Kid not found.")
        return
    kid = kids[kids["id"]==selected].iloc[0]
    if role == "leader" and kid["program"] != user_program:
        st.error("Access denied to this profile.")
        return

    tabs = st.tabs(["Info","Attendance History","Edit"])
    with tabs[0]:
        c1,c2 = st.columns([1,2])
        with c1:
            if kid["image_path"] and os.path.exists(kid["image_path"]):
                st.image(kid["image_path"], width=200)
            else:
                st.markdown("🧒")
        with c2:
            st.subheader(kid["name"])
            st.write(f"Age: {kid['age']}")
            st.write(f"Gender: {kid['gender']}")
            st.write(f"Program: {kid['program']}")
            present, pct, total = kid_stats(kid["id"])
            st.markdown("---")
            st.write(f"Days present: {present}")
            st.write(f"Attendance % (program days): {pct}%")

    with tabs[1]:
        att = get_att()
        kid_att = att[att["kid_id"]==kid["id"]].sort_values("date", ascending=False)
        if kid_att.empty:
            st.write("No records")
        else:
            display = kid_att.merge(kids[["id","name"]], left_on="kid_id", right_on="id", how="left")
            display = display[["date","present","note","marked_by","timestamp"]].rename(columns={"date":"Date","present":"Present","note":"Note","marked_by":"Marked by","timestamp":"When"})
            display["Present"] = display["Present"].apply(lambda x: "Yes" if str(x)=="1" else "No")
            st.dataframe(display)

    with tabs[2]:
        if role not in ("admin","leader"):
            st.info("Only admins or leaders for the kid's program can edit.")
        else:
            with st.form("edit_kid"):
                ename = st.text_input("Name", value=kid["name"])
                eage = st.number_input("Age", min_value=1, max_value=30, value=int(kid["age"]))
                egender = st.selectbox("Gender", ("Male","Female","Other"), index=["Male","Female","Other"].index(kid["gender"]) if kid["gender"] in ["Male","Female","Other"] else 2)
                programs_df = get_programs()
                programs = sorted(list(set(programs_df["program"].dropna().tolist() + get_kids()["program"].dropna().unique().tolist())))
                if role == "admin":
                    eprogram = st.selectbox("Program", ([""]+programs), index=(programs.index(kid["program"]) if kid["program"] in programs else 0))
                else:
                    eprogram = kid["program"]
                    st.write(f"Program: {eprogram}")
                eimage = st.file_uploader("Replace image (optional)", type=["png","jpg","jpeg"])
                if st.form_submit_button("Save changes"):
                    image_path = kid["image_path"]
                    if eimage is not None:
                        image_path = save_kid_image(eimage, ename, kid["id"])
                    kids_df = get_kids()
                    kids_df.loc[kids_df["id"]==kid["id"], ["name","age","gender","program","image_path"]] = [ename, str(int(eage)), egender, eprogram, image_path]
                    save_kids(kids_df)
                    st.success("Kid updated.")
                    st.session_state.selected_kid = kid["id"]
                    st.experimental_rerun()

# ---------------- Export Page ----------------
def page_export():
    st.header("Export Data")
    st.write("Download CSV backups or a single ZIP of everything.")
    files = [(USERS_CSV,"users.csv"), (PROGRAMS_CSV,"programs.csv"), (KIDS_CSV,"kids.csv"), (ATT_CSV,"attendance.csv")]
    for path,label in files:
        if os.path.exists(path):
            with open(path, "rb") as f:
                st.download_button(label, f, file_name=label)
    if st.button("Download all as ZIP"):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            for path,label in files:
                if os.path.exists(path):
                    z.write(path, arcname=label)
        buffer.seek(0)
        st.download_button("Download ZIP", buffer, file_name="fafali_backup.zip")

# ---------------- Admin Tools ----------------
def page_admin_tools():
    if role != "admin":
        st.error("Admin only.")
        return
    st.header("Admin Tools")
    st.subheader("Users")
    users = get_users()
    if users.empty:
        st.write("No users")
    else:
        st.dataframe(users[["username","role","program","full_name"]].rename(columns={"username":"Username","role":"Role","program":"Program","full_name":"Full name"}))
    st.subheader("Create user (program leader)")
    with st.form("create_user"):
        uname = st.text_input("Username")
        fname = st.text_input("Full name")
        pwd = st.text_input("Password")
        role_choice = st.selectbox("Role", ("leader","admin"))
        assign_prog = st.text_input("Assign program (exact name, optional)")
        if st.form_submit_button("Create"):
            if not (uname and pwd):
                st.error("Fill username and password")
            else:
                ok, msg = add_user(uname, pwd, role_choice, program=assign_prog, full_name=fname)
                if ok:
                    st.success("User created.")
                    st.experimental_rerun()
                else:
                    st.error(msg)

    st.markdown("---")
    st.subheader("System Reset")
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

# ---------------- Router ----------------
page_map = {
    "Dashboard": page_dashboard,
    "Kids": page_kids,
    "Attendance": page_attendance,
    "Programs": page_programs,
    "Profiles": page_profiles,
    "Export": page_export,
    "Admin Tools": page_admin_tools
}

handler = page_map.get(menu)
if handler:
    handler()
else:
    st.write("Select a page from the sidebar.")

