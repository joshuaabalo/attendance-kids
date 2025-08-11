# app.py
"""
Fafali Attendance Manager - Single-file complete app
Features:
- Admin & Leader role login (role picker on login)
- Admin: full access (programs, users, kids, attendance, import, export, admin tools)
- Leader: limited access (Kids, Attendance, Profiles) but can view full kid profiles for their program(s)
- Excel import (mapped to KidsT.xlsx columns)
- Atomic CSV saves and caching
- Starter import from /mnt/data/KidsT.xlsx if present
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import shutil
import hashlib
from datetime import date, datetime

# ---------------- Config ----------------
APP_TITLE = "Fafali Attendance Manager"
DATA_DIR = Path("data")
IMAGES_DIR = Path("images")
DATA_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

USERS_CSV = DATA_DIR / "users.csv"
KIDS_CSV = DATA_DIR / "kids.csv"
PROGRAMS_CSV = DATA_DIR / "programs.csv"
ATT_CSV = DATA_DIR / "attendance.csv"

STARTER_XLSX = Path("/mnt/data/KidsT.xlsx")  # optional starter file in this environment
DEFAULT_IMG = ""  # leave empty to show emoji placeholder

# ---------------- Utilities ----------------
def check_password(entered_password: str, stored_password: str) -> bool:
    """Plain-text password check (Option 1)."""
    return str(entered_password) == str(stored_password)

@st.cache_data
def load_csv(path: Path) -> pd.DataFrame:
    if path.exists():
        try:
            return pd.read_csv(path, dtype=str).fillna("")
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

def atomic_save_csv(path: Path, df: pd.DataFrame):
    tmp = path.with_suffix(".tmp")
    df.to_csv(tmp, index=False)
    shutil.move(str(tmp), str(path))
    # clear cache so next load sees changes
    try:
        st.cache_data.clear()
    except Exception:
        pass

def ensure_csv(path: Path, columns: list):
    if not path.exists():
        pd.DataFrame(columns=columns).to_csv(path, index=False)

def calc_age_from_dob(dob_str):
    try:
        if not dob_str or pd.isna(dob_str):
            return ""
        dob = pd.to_datetime(dob_str, errors="coerce")
        if pd.isna(dob):
            return ""
        today = pd.Timestamp(date.today())
        years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return int(years)
    except Exception:
        return ""

# ---------------- Init files and optional starter import ----------------
def init_files_and_starter():
    ensure_csv(USERS_CSV, ["username","password","role","programs","full_name"])
    ensure_csv(KIDS_CSV, ["id","name","age","program","dob","gender","school","location","guardian_name","guardian_contact","relationship","image"])
    ensure_csv(PROGRAMS_CSV, ["program"])
    ensure_csv(ATT_CSV, ["date","kid_id","present","note","program","marked_by","timestamp"])

    users = load_csv(USERS_CSV)
    if users.empty:
        # default admin: admin / admin
        admin_row = {"username":"admin","password":"admin","role":"admin","programs":"","full_name":"Administrator"}
        atomic_save_csv(USERS_CSV, pd.DataFrame([admin_row]))

    # starter import: if kids empty and STARTER_XLSX exists, import it
    kids = load_csv(KIDS_CSV)
    if kids.empty and STARTER_XLSX.exists():
        try:
            df = pd.read_excel(STARTER_XLSX)
            expected = {"Student ID","FirstName","LastName","Date of Birth","Gender","Current School","Project","Location","guardian_name","guardian_contact","Relationship"}
            if expected.issubset(set(df.columns)):
                rows = []
                used_ids = set()
                for i, r in df.iterrows():
                    sid = str(r.get("Student ID","")).strip()
                    if sid == "" or sid.lower() == "nan":
                        sid = f"K{str(i+1).zfill(4)}"
                    if sid in used_ids:
                        sid = f"{sid}_{i}"
                    used_ids.add(sid)
                    name = f"{str(r.get('FirstName','')).strip()} {str(r.get('LastName','')).strip()}".strip()
                    dob_val = r.get("Date of Birth", "")
                    dob_s = ""
                    try:
                        if pd.notna(dob_val):
                            dob_s = pd.to_datetime(dob_val).date().isoformat()
                    except Exception:
                        dob_s = ""
                    prog = str(r.get("Project","")).strip()
                    row = {
                        "id": sid,
                        "name": name,
                        "age": calc_age_from_dob(dob_s),
                        "program": prog,
                        "dob": dob_s,
                        "gender": str(r.get("Gender","")).strip(),
                        "school": str(r.get("Current School","")).strip(),
                        "location": str(r.get("Location","")).strip(),
                        "guardian_name": str(r.get("guardian_name","")).strip(),
                        "guardian_contact": str(r.get("guardian_contact","")).strip(),
                        "relationship": str(r.get("Relationship","")).strip(),
                        "image": DEFAULT_IMG
                    }
                    rows.append(row)
                if rows:
                    atomic_save_csv(KIDS_CSV, pd.DataFrame(rows))
                    # add programs found
                    progs = load_csv(PROGRAMS_CSV)
                    exist = [p.strip().lower() for p in progs.get("program",[])]
                    for p in {r["program"] for r in rows if r["program"]}:
                        if p.strip().lower() not in exist:
                            progs = pd.concat([progs, pd.DataFrame([{"program":p}])], ignore_index=True)
                    if not progs.empty:
                        atomic_save_csv(PROGRAMS_CSV, progs)
        except Exception:
            # ignore errors importing starter file
            pass

# ---------------- Domain helpers ----------------
def add_program_if_missing(name: str):
    name = str(name).strip()
    if not name:
        return
    progs = load_csv(PROGRAMS_CSV)
    existing = [p.strip().lower() for p in progs.get("program",[])]
    if name.lower() not in existing:
        progs = pd.concat([progs, pd.DataFrame([{"program":name}])], ignore_index=True)
        atomic_save_csv(PROGRAMS_CSV, progs)

def save_kids(df: pd.DataFrame):
    atomic_save_csv(KIDS_CSV, df)

def save_users(df: pd.DataFrame):
    atomic_save_csv(USERS_CSV, df)

def save_att(df: pd.DataFrame):
    atomic_save_csv(ATT_CSV, df)

def add_user(username, password, role, programs="", full_name=""):
    users = load_csv(USERS_CSV)
    if username in users.get("username", []):
        return False, "Username exists."
    row = {"username":username,"password":password,"role":role,"programs":programs,"full_name":full_name}
    users = pd.concat([users, pd.DataFrame([row])], ignore_index=True)
    save_users(users)
    return True, "User created."

# ---------------- Auth ----------------
def attempt_login(username: str, password: str, chosen_role: str):
    users = load_csv(USERS_CSV)
    if users.empty:
        return None
    row = users[users["username"] == username]
    if row.empty:
        return None
    user = row.iloc[0]
    # role stored as 'admin' or 'leader' (or whatever)
    if str(user["role"]).lower() != chosen_role.lower():
        return None
    if not check_password(password, user["password"]):
        return None
    progs_raw = str(user.get("programs","") or "")
    programs = [p.strip() for p in progs_raw.split(",") if p.strip()]
    return {"username": user["username"], "role": user["role"], "programs": programs, "full_name": user.get("full_name", user["username"])}

# ---------------- UI pages ----------------
def page_login():
    st.markdown(f"## {APP_TITLE}")
    st.write("Choose role, enter credentials. Default admin: `admin` / `admin`")
    with st.form("login_form"):
        role_choice = st.selectbox("Sign in as", ("admin","leader"))
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
        if submitted:
            user = attempt_login(username.strip(), password, role_choice)
            if user:
                st.session_state.user = user
                st.success(f"Signed in: {user['full_name']} ({user['role']})")
                st.rerun()
            else:
                st.error("Invalid credentials or role mismatch.")

def kids_page():
    st.header("Kids Management")
    kids = load_csv(KIDS_CSV)
    progs = sorted([p for p in load_csv(PROGRAMS_CSV).get("program", []) if p.strip()])
    locations = sorted(list({str(x).strip() for x in kids.get("location",[]) if str(x).strip()}))

    # role-based program selection / filter
    if st.session_state.user["role"].lower() == "admin":
        prog_filter = st.selectbox("Filter by program", ["-- All --"] + progs)
        chosen_prog = None if prog_filter == "-- All --" else prog_filter
    else:
        leader_progs = st.session_state.user.get("programs", [])
        if not leader_progs:
            st.info("No programs assigned. Contact admin.")
            return
        # allow leader to pick one of their programs or view all
        prog_choice = st.selectbox("Choose program (leaders)", ["-- All my programs --"] + leader_progs)
        chosen_prog = None if prog_choice == "-- All my programs --" else prog_choice

    loc_choice = st.selectbox("Filter by location", ["-- All --"] + ([""] + locations))
    chosen_loc = None if loc_choice == "-- All --" or loc_choice == "" else loc_choice

    search = st.text_input("Search by name")

    view = kids.copy()
    if st.session_state.user["role"].lower() != "admin":
        allowed = st.session_state.user.get("programs", [])
        view = view[view["program"].isin(allowed)]
    if chosen_prog:
        view = view[view["program"] == chosen_prog]
    if chosen_loc:
        view = view[view["location"] == chosen_loc]
    if search:
        view = view[view["name"].str.contains(search, case=False, na=False)]

    # Import area
    st.subheader("Import from Excel (KidsT format)")
    uploaded = st.file_uploader("Upload .xlsx/.xls (KidsT format)", type=["xlsx","xls"])
    if uploaded:
        try:
            df = pd.read_excel(uploaded)
        except Exception as e:
            st.error(f"Could not read Excel: {e}")
            df = None
        if df is not None:
            req = {"Student ID","FirstName","LastName","Date of Birth","Gender","Current School","Project","Location","guardian_name","guardian_contact","Relationship"}
            if not req.issubset(set(df.columns)):
                st.error("Excel must include columns: " + ", ".join(sorted(req)))
            else:
                # mapping
                mapped = pd.DataFrame()
                mapped["id"] = df["Student ID"].astype(str).fillna("").replace("nan","")
                # generate ids for blanks without colliding with existing
                existing_ids = set(load_csv(KIDS_CSV).get("id", []))
                gen_counter = 1
                gen_ids = []
                for val in mapped["id"].tolist():
                    if str(val).strip() == "":
                        gen = f"K{str(gen_counter).zfill(4)}"
                        while gen in existing_ids:
                            gen_counter += 1
                            gen = f"K{str(gen_counter).zfill(4)}"
                        gen_ids.append(gen)
                        existing_ids.add(gen)
                        gen_counter += 1
                    else:
                        gen_ids.append(val)
                mapped["id"] = gen_ids
                mapped["name"] = df["FirstName"].astype(str).str.strip() + " " + df["LastName"].astype(str).str.strip()
                mapped["dob"] = pd.to_datetime(df["Date of Birth"], errors="coerce").dt.date.astype(str)
                mapped["age"] = mapped["dob"].apply(calc_age_from_dob)
                mapped["gender"] = df["Gender"].astype(str)
                mapped["school"] = df["Current School"].astype(str)
                mapped["program"] = df["Project"].astype(str)
                mapped["location"] = df["Location"].astype(str)
                mapped["guardian_name"] = df["guardian_name"].astype(str)
                mapped["guardian_contact"] = df["guardian_contact"].astype(str)
                mapped["relationship"] = df["Relationship"].astype(str)
                mapped["image"] = DEFAULT_IMG

                existing = load_csv(KIDS_CSV)
                combined = pd.concat([existing, mapped], ignore_index=True)
                before = len(existing)
                # dedupe by id then name+program
                combined = combined.drop_duplicates(subset=["id"], keep="first")
                combined = combined.drop_duplicates(subset=["name","program"], keep="first")
                after = len(combined)
                added = max(0, after - before)
                st.subheader("Preview new rows (will be added)")
                new_preview = combined[~combined["id"].isin(existing.get("id", []))]
                st.dataframe(new_preview)
                if st.button("Confirm import"):
                    atomic_save_csv(KIDS_CSV, combined)
                    # add programs found to programs.csv
                    for p in mapped["program"].unique():
                        if str(p).strip():
                            add_program_if_missing(p)
                    st.success(f"Imported. {added} new kids added (duplicates skipped).")
                    st.rerun()

    st.markdown("---")
    st.subheader(f"Kids ({len(view)})")
    if view.empty:
        st.info("No kids match the filters.")
    else:
        for _, r in view.sort_values("name").iterrows():
            with st.expander(r["name"]):
                left, right = st.columns([1,3])
                with left:
                    if r.get("image"):
                        try:
                            st.image(r["image"], width=120)
                        except Exception:
                            st.write("🧒")
                    else:
                        st.write("🧒")
                with right:
                    st.markdown(f"**ID:** {r.get('id','')}")
                    st.markdown(f"**Program:** {r.get('program','')}")
                    st.markdown(f"**Age:** {r.get('age','')}  **DOB:** {r.get('dob','')}")
                    st.markdown(f"**School:** {r.get('school','')}")
                    st.markdown(f"**Location:** {r.get('location','')}")
                    st.markdown(f"**Guardian:** {r.get('guardian_name','')} ({r.get('relationship','')}) — {r.get('guardian_contact','')}")
                    btns = st.columns([1,1,1])
                    if btns[0].button("View profile", key=f"view_{r['id']}"):
                        st.session_state.selected_kid = r["id"]
                        st.rerun()
                    if st.session_state.user["role"].lower() == "admin":
                        if btns[1].button("Delete", key=f"del_{r['id']}"):
                            # confirmation flow via session_state
                            st.session_state.pending_delete = {"type":"kid","id":r["id"],"name":r["name"]}
                            st.rerun()
                    if btns[2].button("Open profile (edit)", key=f"open_{r['id']}"):
                        st.session_state.selected_kid = r["id"]
                        st.rerun()

    # handle pending delete confirmation
    if st.session_state.get("pending_delete"):
        pdv = st.session_state["pending_delete"]
        if pdv.get("type") == "kid":
            st.warning(f"Confirm delete kid: {pdv.get('name')} (ID: {pdv.get('id')})")
            c1, c2 = st.columns(2)
            if c1.button("Yes, delete kid"):
                dfk = load_csv(KIDS_CSV)
                dfk = dfk[dfk["id"] != pdv.get("id")]
                atomic_save_csv(KIDS_CSV, dfk)
                # remove attendance records for this kid
                att = load_csv(ATT_CSV)
                att = att[att["kid_id"] != pdv.get("id")]
                atomic_save_csv(ATT_CSV, att)
                st.success("Kid deleted.")
                st.session_state.pending_delete = None
                st.rerun()
            if c2.button("Cancel"):
                st.session_state.pending_delete = None
                st.rerun()

def attendance_page():
    st.header("Attendance")
    kids = load_csv(KIDS_CSV)
    if kids.empty:
        st.info("No kids available.")
        return

    # program scope selection
    if st.session_state.user["role"].lower() == "admin":
        progs = sorted(list({str(x).strip() for x in kids.get("program",[]) if str(x).strip()}))
        prog_choice = st.selectbox("Program (admin)", ["-- All --"] + progs)
        program_scope = None if prog_choice == "-- All --" else prog_choice
    else:
        programs = st.session_state.user.get("programs", [])
        if not programs:
            st.info("No assigned programs.")
            return
        prog_choice = st.selectbox("Choose your program", ["-- Select --"] + programs)
        program_scope = None if prog_choice == "-- Select --" else prog_choice

    # build scope
    if program_scope:
        scope = kids[kids["program"] == program_scope]
    else:
        if st.session_state.user["role"].lower() == "admin":
            scope = kids.copy()
        else:
            scope = kids[kids["program"].isin(st.session_state.user.get("programs", []))]

    if scope.empty:
        st.info("No kids in the selected scope.")
        return

    att = load_csv(ATT_CSV)
    att_date = st.date_input("Attendance date", value=date.today())
    att_str = att_date.isoformat()

    existing = att[att["date"] == att_str]
    present_defaults = {row["kid_id"]:(row["present"]=="1") for _,row in existing.iterrows()}
    notes_defaults = {row["kid_id"]: row.get("note","") for _,row in existing.iterrows()}

    c1,c2,_ = st.columns([1,1,6])
    if c1.button("All present"):
        for kid_id in scope["id"].tolist():
            present_defaults[kid_id] = True
    if c2.button("All absent"):
        for kid_id in scope["id"].tolist():
            present_defaults[kid_id] = False

    with st.form("mark_att"):
        checked = {}
        notes = {}
        for _, k in scope.sort_values("name").iterrows():
            a,b,c = st.columns([1,4,3])
            with a:
                val = st.checkbox("", value=present_defaults.get(k["id"], False), key=f"chk_{k['id']}")
            with b:
                st.markdown(f"**{k['name']}**")
                st.write(f"Program: {k['program']}")
            with c:
                note = st.text_input("Note", value=notes_defaults.get(k["id"], ""), key=f"note_{k['id']}")
            checked[k["id"]] = val
            notes[k["id"]] = note
        if st.form_submit_button("Save attendance"):
            new_att = att[att["date"] != att_str]
            now = datetime.now().isoformat(timespec="seconds")
            for kid_id, is_present in checked.items():
                kid_prog = kids[kids["id"] == kid_id]["program"].values[0] if not kids.empty else ""
                row = {"date":att_str,"kid_id":kid_id,"present":"1" if is_present else "0","note":notes.get(kid_id,""),"program":kid_prog,"marked_by":st.session_state.user["username"],"timestamp":now}
                new_att = pd.concat([new_att, pd.DataFrame([row])], ignore_index=True)
            atomic_save_csv(ATT_CSV, new_att)
            st.success("Attendance saved.")
            st.rerun()

def profiles_page():
    st.header("Child Profile")
    sel = st.session_state.get("selected_kid", None)
    if not sel:
        st.info("Open a kid from the Kids page to view profile.")
        return
    kids = load_csv(KIDS_CSV)
    if sel not in kids.get("id", []):
        st.error("Kid not found.")
        return
    kid = kids[kids["id"] == sel].iloc[0]
    # leader access check
    if st.session_state.user["role"].lower() != "admin":
        if kid["program"] not in st.session_state.user.get("programs", []):
            st.error("Access denied.")
            return

    left, right = st.columns([1,2])
    with left:
        if kid.get("image"):
            try:
                st.image(kid["image"], width=200)
            except Exception:
                st.write("🧒")
        else:
            st.write("🧒")
    with right:
        st.subheader(kid.get("name",""))
        st.write(f"Student ID: {kid.get('id','')}")
        st.write(f"Program: {kid.get('program','')}")
        st.write(f"Age: {kid.get('age','')}  DOB: {kid.get('dob','')}")
        st.write(f"Gender: {kid.get('gender','')}")
        st.write(f"School: {kid.get('school','')}")
        st.write(f"Location: {kid.get('location','')}")
        st.write(f"Guardian: {kid.get('guardian_name','')} ({kid.get('relationship','')}) — {kid.get('guardian_contact','')}")

    st.markdown("---")
    st.subheader("Attendance history")
    att = load_csv(ATT_CSV)
    kid_att = att[att["kid_id"] == sel].sort_values("date", ascending=False)
    if kid_att.empty:
        st.write("No attendance records.")
    else:
        disp = kid_att[["date","present","note","marked_by","timestamp"]].rename(columns={"present":"Present","note":"Note","marked_by":"Marked by","timestamp":"When"})
        disp["Present"] = disp["Present"].apply(lambda x: "Yes" if str(x) == "1" else "No")
        st.dataframe(disp)

def programs_page():
    st.header("Programs")
    progs = load_csv(PROGRAMS_CSV).get("program", []).tolist()
    if st.session_state.user["role"].lower() == "admin":
        st.subheader("Existing programs")
        st.write(sorted(progs))
        new = st.text_input("New program")
        if st.button("Add program"):
            if new.strip():
                add_program_if_missing(new.strip())
                st.success("Program added.")
                st.rerun()
            else:
                st.error("Enter program name.")
    else:
        st.info("Leaders cannot manage programs.")

def export_page():
    st.header("Export Data")
    for p,label in [(USERS_CSV,"users.csv"), (PROGRAMS_CSV,"programs.csv"), (KIDS_CSV,"kids.csv"), (ATT_CSV,"attendance.csv")]:
        if p.exists():
            with open(p,"rb") as f:
                st.download_button(label, f, file_name=label)

def admin_tools_page():
    if st.session_state.user["role"].lower() != "admin":
        st.error("Admin only.")
        return
    st.header("Admin Tools")
    users = load_csv(USERS_CSV)
    if not users.empty:
        st.dataframe(users)
    st.subheader("Create user")
    with st.form("create_user"):
        uname = st.text_input("Username")
        fname = st.text_input("Full name")
        pwd = st.text_input("Password")
        role_choice = st.selectbox("Role", ("leader","admin"))
        prog_assign = st.text_input("Assign programs (comma separated) - leaders only")
        submitted = st.form_submit_button("Create")
        if submitted:
            if not (uname and pwd):
                st.error("Username and password required.")
            else:
                ok,msg = add_user(uname.strip(), pwd, role_choice, programs=prog_assign, full_name=fname)
                if ok:
                    # ensure programs exist
                    for p in [x.strip() for x in prog_assign.split(",") if x.strip()]:
                        add_program_if_missing(p)
                    st.success("User created.")
                    st.rerun()
                else:
                    st.error(msg)
    st.markdown("---")
    st.subheader("System Reset")
    st.warning("Deletes programs, kids, attendance and users (except default admin).")
    if st.button("RESET SYSTEM"):
        for f in [USERS_CSV, KIDS_CSV, PROGRAMS_CSV, ATT_CSV]:
            if f.exists():
                f.unlink()
        init_files_and_starter()
        st.success("System reset.")
        st.rerun()

# ---------------- Layout / Router ----------------
st.set_page_config(APP_TITLE, layout="wide")
init_files_and_starter()

if "user" not in st.session_state:
    st.session_state.user = None
if "selected_kid" not in st.session_state:
    st.session_state.selected_kid = None
if "pending_delete" not in st.session_state:
    st.session_state.pending_delete = None

if not st.session_state.user:
    page_login()
    st.stop()

# Sidebar
with st.sidebar:
    st.markdown(f"**Signed in:** {st.session_state.user['full_name']} ({st.session_state.user['role']})")
    st.markdown("---")
    if st.session_state.user["role"].lower() == "admin":
        menu = st.radio("Menu", ["Dashboard","Kids","Attendance","Programs","Profiles","Export","Admin Tools","Logout"])
    else:
        menu = st.radio("Menu", ["Kids","Attendance","Profiles","Logout"])
    st.markdown("---")
    if st.button("Log out") or menu == "Logout":
        st.session_state.user = None
        st.session_state.selected_kid = None
        st.rerun()

# Router
role = st.session_state.user["role"].lower()
if role == "admin":
    if menu == "Dashboard":
        st.header("Dashboard")
        ks = load_csv(KIDS_CSV)
        at = load_csv(ATT_CSV)
        pr = load_csv(PROGRAMS_CSV)
        c1,c2,c3 = st.columns(3)
        c1.metric("Programs", len(pr))
        c2.metric("Kids", len(ks))
        c3.metric("Attendance records", len(at))
    elif menu == "Kids":
        kids_page()
    elif menu == "Attendance":
        attendance_page()
    elif menu == "Programs":
        programs_page()
    elif menu == "Profiles":
        profiles_page()
    elif menu == "Export":
        export_page()
    elif menu == "Admin Tools":
        admin_tools_page()
    elif menu == "Logout":
        st.session_state.user = None
        st.rerun()
else:
    # leader
    if menu == "Kids":
        kids_page()
    elif menu == "Attendance":
        attendance_page()
    elif menu == "Profiles":
        profiles_page()
    elif menu == "Logout":
        st.session_state.user = None
        st.rerun()
