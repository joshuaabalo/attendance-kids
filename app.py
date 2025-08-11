# app.py
"""
Fafali Attendance Manager - single-file app
Features:
- Role login (Admin or User/Leader)
- Admin has full rights; Leaders see only Kids & Attendance but can view full kid profiles
- Leaders can have multiple comma-separated programs
- Program & Location filters; leaders limited to their programs
- Excel import (mapped to KidsT.xlsx columns)
- On first run, imports /mnt/data/KidsT.xlsx if present (starter data)
- Atomic CSV writes + caching
"""
import streamlit as st
import pandas as pd
import os
import shutil
from pathlib import Path
from datetime import date, datetime
import hashlib

# ---------------------------
# CONFIG
# ---------------------------
APP_TITLE = "Fafali Attendance Manager"
DATA_DIR = Path("data")
IMAGES_DIR = Path("images")
DATA_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

USERS_CSV = DATA_DIR / "users.csv"
KIDS_CSV = DATA_DIR / "kids.csv"
PROGRAMS_CSV = DATA_DIR / "programs.csv"
ATTENDANCE_CSV = DATA_DIR / "attendance.csv"

UPLOADED_STARTER_XLSX = Path("/mnt/data/KidsT.xlsx")  # optionally available in this environment

DEFAULT_IMG = ""  # empty -> show emoji; you can set a local placeholder path here

# ---------------------------
# UTILITIES
# ---------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def check_password(password: str, hashed: str) -> bool:
    return hash_password(password) == str(hashed)

@st.cache_data
def load_csv(path: Path) -> pd.DataFrame:
    if path.exists():
        try:
            df = pd.read_csv(path, dtype=str).fillna("")
            return df
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

def atomic_save_csv(path: Path, df: pd.DataFrame):
    tmp = path.with_suffix(".tmp")
    df.to_csv(tmp, index=False)
    shutil.move(str(tmp), str(path))
    # clear cached loader so subsequent loads see the new version
    try:
        st.cache_data.clear()
    except Exception:
        pass

def ensure_csv(path: Path, columns: list):
    if not path.exists():
        pd.DataFrame(columns=columns).to_csv(path, index=False)

def calc_age_from_dob(dob_str):
    try:
        dob = pd.to_datetime(dob_str, errors="coerce")
        if pd.isna(dob):
            return ""
        today = pd.Timestamp(date.today())
        years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return int(years)
    except Exception:
        return ""

# ---------------------------
# INITIALIZATION (files & starter data)
# ---------------------------
def init_files_and_starter_data():
    ensure_csv(USERS_CSV, ["username", "password", "role", "programs", "full_name"])
    ensure_csv(KIDS_CSV, ["id","name","age","program","dob","gender","school","location","guardian_name","guardian_contact","relationship","image"])
    ensure_csv(PROGRAMS_CSV, ["program"])
    ensure_csv(ATTENDANCE_CSV, ["date","kid_id","present","note","program","marked_by","timestamp"])
    # create default admin if users empty
    users = load_csv(USERS_CSV)
    if users.empty:
        admin = {"username":"admin","password":hash_password("admin"),"role":"admin","programs":"","full_name":"Administrator"}
        atomic_save_csv(USERS_CSV, pd.DataFrame([admin]))
    # if kids CSV is empty and starter xlsx exists, import it automatically
    kids = load_csv(KIDS_CSV)
    if kids.empty and UPLOADED_STARTER_XLSX.exists():
        try:
            df = pd.read_excel(UPLOADED_STARTER_XLSX)
            # expected columns from your file
            expected = {"Student ID","FirstName","LastName","Date of Birth","Gender","Current School","Project","Location","guardian_name","guardian_contact","Relationship"}
            if expected.issubset(set(df.columns)):
                mapped = []
                existing_ids = set()
                for _, r in df.iterrows():
                    sid = str(r.get("Student ID","")).strip()
                    if sid == "" or sid.lower() == "nan":
                        # generate Kxxxx id
                        sid = f"K{str(len(mapped)+1).zfill(4)}"
                    # build name
                    name = f"{str(r.get('FirstName','')).strip()} {str(r.get('LastName','')).strip()}".strip()
                    dob = r.get("Date of Birth", "")
                    dob_s = ""
                    try:
                        if pd.notna(dob):
                            dob_s = pd.to_datetime(dob).date().isoformat()
                    except Exception:
                        dob_s = ""
                    age = calc_age_from_dob(dob_s)
                    program = str(r.get("Project","")).strip()
                    row = {
                        "id": sid,
                        "name": name,
                        "age": age,
                        "program": program,
                        "dob": dob_s,
                        "gender": str(r.get("Gender","")).strip(),
                        "school": str(r.get("Current School","")).strip(),
                        "location": str(r.get("Location","")).strip(),
                        "guardian_name": str(r.get("guardian_name","")).strip(),
                        "guardian_contact": str(r.get("guardian_contact","")).strip(),
                        "relationship": str(r.get("Relationship","")).strip(),
                        "image": DEFAULT_IMG
                    }
                    # avoid duplicate IDs
                    if row["id"] in existing_ids:
                        # append numeric suffix if collision
                        counter = 1
                        newid = f"{row['id']}_{counter}"
                        while newid in existing_ids:
                            counter += 1
                            newid = f"{row['id']}_{counter}"
                        row["id"] = newid
                    existing_ids.add(row["id"])
                    mapped.append(row)
                if mapped:
                    atomic_save_csv(KIDS_CSV, pd.DataFrame(mapped))
                    # also add programs to programs.csv
                    progs = set([r["program"] for r in mapped if r["program"]])
                    if progs:
                        existing_progs = load_csv(PROGRAMS_CSV)
                        existing_list = [p.strip().lower() for p in existing_progs.get("program",[])]
                        for p in progs:
                            if p.strip().lower() not in existing_list:
                                existing_progs = pd.concat([existing_progs, pd.DataFrame([{"program":p}])], ignore_index=True)
                        atomic_save_csv(PROGRAMS_CSV, existing_progs)
        except Exception:
            # ignore starter import failures, user can import manually
            pass

# ---------------------------
# DOMAIN FUNCTIONS
# ---------------------------
def add_program_if_missing(name: str):
    name = str(name).strip()
    if name == "":
        return
    progs = load_csv(PROGRAMS_CSV)
    existing = [p.strip().lower() for p in progs.get("program",[])]
    if name.lower() not in existing:
        progs = pd.concat([progs, pd.DataFrame([{"program":name}])], ignore_index=True)
        atomic_save_csv(PROGRAMS_CSV, progs)

def save_kids_df(df: pd.DataFrame):
    atomic_save_csv(KIDS_CSV, df)

def save_users_df(df: pd.DataFrame):
    atomic_save_csv(USERS_CSV, df)

def save_att_df(df: pd.DataFrame):
    atomic_save_csv(ATTENDANCE_CSV, df)

def add_user(username, password, role, programs="", full_name=""):
    users = load_csv(USERS_CSV)
    if username in users.get("username",[]):
        return False, "Username exists"
    row = {"username":username,"password":hash_password(password),"role":role,"programs":programs,"full_name":full_name}
    users = pd.concat([users, pd.DataFrame([row])], ignore_index=True)
    save_users_df(users)
    return True, "Created"

# ---------------------------
# AUTH (login)
# ---------------------------
def attempt_login(username: str, password: str, chosen_role: str):
    users = load_csv(USERS_CSV)
    if users.empty:
        return None
    row = users[users["username"] == username]
    if row.empty:
        return None
    user = row.iloc[0]
    if user["role"] != chosen_role.lower():
        # role mismatch
        return None
    if not check_password(password, user["password"]):
        return None
    # parse programs into list (comma-separated)
    progs_raw = str(user.get("programs","") or "")
    programs = [p.strip() for p in progs_raw.split(",") if p.strip()]
    return {"username": user["username"], "role": user["role"], "programs": programs, "full_name": user.get("full_name", user["username"])}

# ---------------------------
# UI PAGES
# ---------------------------
def page_login():
    st.markdown(f"## {APP_TITLE}")
    st.write("Sign in as Admin or User (Leader). If first time, default admin/admin exists.")
    with st.form("login_form"):
        role_choice = st.selectbox("Sign in as", ("admin","leader"))
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
        if submitted:
            user = attempt_login(username.strip(), password, "admin" if role_choice=="admin" else "leader")
            if user:
                st.session_state.user = user
                st.success(f"Signed in as {user['full_name']} ({user['role']})")
                st.experimental_rerun()  # safe here after user action
            else:
                st.error("Invalid credentials or role mismatch.")

def kids_page():
    st.header("Kids")
    kids = load_csv(KIDS_CSV)
    progs = load_csv(PROGRAMS_CSV).get("program", []).tolist()
    locations = sorted(list({str(x).strip() for x in kids.get("location",[]) if str(x).strip()}))

    # role-based program options
    if st.session_state.user["role"] == "admin":
        prog_filter = st.selectbox("Filter by program", ["-- All --"] + sorted(progs))
        chosen_program = None if prog_filter == "-- All --" else prog_filter
    else:
        # leader: dropdown of their programs (plus option to view all their programs)
        leader_programs = st.session_state.user.get("programs", [])
        if not leader_programs:
            st.info("You have no programs assigned. Contact admin.")
            return
        prog_choice = st.selectbox("Choose program to view", ["-- All My Programs --"] + leader_programs)
        chosen_program = None if prog_choice == "-- All My Programs --" else prog_choice

    loc_choice = st.selectbox("Filter by location", ["-- All --"] + [""] + locations)
    chosen_location = None if loc_choice == "-- All --" or loc_choice == "" else loc_choice

    search = st.text_input("Search by name")

    # apply filters
    view = kids.copy()
    if st.session_state.user["role"] != "admin":
        # leader: limit to their programs
        allowed = st.session_state.user.get("programs", [])
        view = view[view["program"].isin(allowed)]
    if chosen_program:
        view = view[view["program"] == chosen_program]
    if chosen_location:
        view = view[view["location"] == chosen_location]
    if search:
        view = view[view["name"].str.contains(search, case=False, na=False)]

    st.subheader("Import Excel (KidsT format)")
    excel = st.file_uploader("Upload .xlsx/.xls", type=["xlsx","xls"])
    if excel:
        try:
            df = pd.read_excel(excel)
        except Exception as e:
            st.error(f"Unable to read file: {e}")
            df = None
        if df is not None:
            required = {"Student ID","FirstName","LastName","Date of Birth","Gender","Current School","Project","Location","guardian_name","guardian_contact","Relationship"}
            if not required.issubset(set(df.columns)):
                st.error(f"Excel must include columns: {', '.join(sorted(required))}")
            else:
                # map and preview
                mapped = pd.DataFrame()
                mapped["id"] = df["Student ID"].astype(str).fillna("").replace("nan","")
                # generate ids for empty
                missing_mask = mapped["id"].str.strip() == ""
                if missing_mask.any():
                    base = 1
                    existing_ids = [x for x in load_csv(KIDS_CSV).get("id",[])]
                    # create generated IDs that don't collide
                    for i in range(missing_mask.sum()):
                        gen = f"K{str(base).zfill(4)}"
                        while gen in existing_ids:
                            base += 1
                            gen = f"K{str(base).zfill(4)}"
                        mapped.loc[missing_mask.where(missing_mask).notnull(), "id"] = gen
                        base += 1
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
                # dedupe against existing by id first, then name+program
                existing = load_csv(KIDS_CSV)
                combined = pd.concat([existing, mapped], ignore_index=True)
                before = len(existing)
                combined = combined.drop_duplicates(subset=["id"], keep="first")
                combined = combined.drop_duplicates(subset=["name","program"], keep="first")
                after = len(combined)
                added = max(0, after - before)
                st.subheader("Preview new records")
                new_preview = combined[~combined["id"].isin(existing.get("id",[]))]
                st.dataframe(new_preview)
                if st.button("Confirm import"):
                    save_kids_df(combined)
                    # add programs found
                    for p in mapped["program"].unique():
                        if str(p).strip():
                            add_program_if_missing(p)
                    st.success(f"Imported. {added} new kids added.")
                    st.rerun()

    st.markdown("---")
    st.subheader(f"Kids ({len(view)})")
    if view.empty:
        st.info("No kids match the filters.")
    else:
        # show list with expanders; clicking View opens Profiles page
        for _, r in view.sort_values("name").iterrows():
            with st.expander(r["name"]):
                cols = st.columns([1,3])
                with cols[0]:
                    if r.get("image"):
                        try:
                            st.image(r["image"], width=120)
                        except Exception:
                            st.write("🧒")
                    else:
                        st.write("🧒")
                with cols[1]:
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
                    # Admin-only delete
                    if st.session_state.user["role"] == "admin":
                        if btns[1].button("Delete", key=f"del_{r['id']}"):
                            # confirmation simple flow
                            confirm = st.confirm(f"Delete {r['name']} (ID {r['id']})? This cannot be undone.")
                            if confirm:
                                df_k = load_csv(KIDS_CSV)
                                df_k = df_k[df_k["id"] != r["id"]]
                                save_kids_df(df_k)
                                st.success("Deleted.")
                                st.rerun()
                    # placeholder for edit that opens Profiles
                    if btns[2].button("Open profile (edit)", key=f"open_{r['id']}"):
                        st.session_state.selected_kid = r["id"]
                        st.rerun()

def attendance_page():
    st.header("Attendance")
    kids = load_csv(KIDS_CSV)
    if kids.empty:
        st.info("No kids in database.")
        return
    # choose program scope
    if st.session_state.user["role"] == "admin":
        progs = sorted(list(set(kids.get("program",[]))))
        prog_choice = st.selectbox("Program (admin)", ["-- All --"] + progs)
        program_scope = None if prog_choice == "-- All --" else prog_choice
    else:
        # leader: dropdown of their programs
        programs = st.session_state.user.get("programs", [])
        if not programs:
            st.info("No programs assigned.")
            return
        prog_choice = st.selectbox("Choose your program", ["-- Select --"] + programs)
        program_scope = None if prog_choice == "-- Select --" else prog_choice

    # determine scope
    if program_scope:
        scope = kids[kids["program"] == program_scope]
    else:
        if st.session_state.user["role"] == "admin":
            scope = kids.copy()
        else:
            scope = kids[kids["program"].isin(st.session_state.user.get("programs", []))]

    if scope.empty:
        st.info("No kids in the chosen scope.")
        return

    att = load_csv(ATTENDANCE_CSV)
    att_date = st.date_input("Attendance date", value=date.today())
    att_str = att_date.isoformat()

    # existing entries for this date
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
                kid_prog = kids[kids["id"]==kid_id]["program"].values[0] if not kids.empty else ""
                row = {"date":att_str,"kid_id":kid_id,"present":"1" if is_present else "0","note":notes.get(kid_id,""),"program":kid_prog,"marked_by":st.session_state.user["username"],"timestamp":now}
                new_att = pd.concat([new_att, pd.DataFrame([row])], ignore_index=True)
            save_att_df(new_att)
            st.success("Saved.")
            st.rerun()

def profiles_page():
    st.header("Child Profile")
    sel = st.session_state.get("selected_kid", None)
    if not sel:
        st.info("Open a kid from the Kids page to view profile.")
        return
    kids = load_csv(KIDS_CSV)
    if sel not in kids.get("id",[]):
        st.error("Kid not found.")
        return
    kid = kids[kids["id"] == sel].iloc[0]
    # access check for leaders
    if st.session_state.user["role"] != "admin":
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
    att = load_csv(ATTENDANCE_CSV)
    kid_att = att[att["kid_id"]==sel].sort_values("date", ascending=False)
    if kid_att.empty:
        st.write("No attendance records.")
    else:
        disp = kid_att[["date","present","note","marked_by","timestamp"]].rename(columns={"present":"Present","note":"Note","marked_by":"Marked by","timestamp":"When"})
        disp["Present"] = disp["Present"].apply(lambda x: "Yes" if str(x)=="1" else "No")
        st.dataframe(disp)

def programs_page():
    st.header("Programs")
    progs = load_csv(PROGRAMS_CSV).get("program",[]).tolist()
    if st.session_state.user["role"] == "admin":
        st.subheader("Existing programs")
        st.write(sorted(progs))
        new = st.text_input("Add new program")
        if st.button("Add program"):
            if new.strip():
                add_program_if_missing(new.strip())
                st.success("Added.")
                st.rerun()
            else:
                st.error("Enter a program name.")
    else:
        st.info("Leaders cannot manage programs. Contact admin.")

def export_page():
    st.header("Export CSVs")
    for p,label in [(USERS_CSV,"users.csv"),(KIDS_CSV,"kids.csv"),(PROGRAMS_CSV,"programs.csv"),(ATTENDANCE_CSV,"attendance.csv")]:
        if p.exists():
            with open(p,"rb") as f:
                st.download_button(label, f, file_name=label)

def admin_tools_page():
    if st.session_state.user["role"] != "admin":
        st.error("Admin only.")
        return
    st.header("Admin Tools")
    st.subheader("Users")
    users = load_csv(USERS_CSV)
    if not users.empty:
        st.dataframe(users)
    st.subheader("Create user")
    with st.form("create_user"):
        uname = st.text_input("Username")
        fname = st.text_input("Full name")
        pwd = st.text_input("Password")
        role_choice = st.selectbox("Role", ("leader","admin"))
        prog_assign = st.text_input("Assign programs (comma separated) - for leaders")
        submitted = st.form_submit_button("Create")
        if submitted:
            if not (uname and pwd):
                st.error("Username and password required.")
            else:
                ok,msg = add_user(uname.strip(), pwd, role_choice, programs=prog_assign, full_name=fname)
                if ok:
                    # ensure assigned programs exist
                    for p in [x.strip() for x in prog_assign.split(",") if x.strip()]:
                        add_program_if_missing(p)
                    st.success("User created.")
                    st.rerun()
                else:
                    st.error(msg)
    st.markdown("---")
    st.subheader("System Reset (danger)")
    if st.button("RESET SYSTEM"):
        # remove CSVs
        for f in [USERS_CSV, KIDS_CSV, PROGRAMS_CSV, ATTENDANCE_CSV]:
            if f.exists(): f.unlink()
        init_files_and_starter_data()
        st.success("System reset.")
        st.rerun()

# ---------------------------
# APP LAYOUT / ROUTER
# ---------------------------
st.set_page_config(APP_TITLE, layout="wide")
init_files_and_starter_data()

if "user" not in st.session_state:
    st.session_state.user = None
if "selected_kid" not in st.session_state:
    st.session_state.selected_kid = None

if not st.session_state.user:
    page_login()
    st.stop()

# Sidebar and menu depending on role
with st.sidebar:
    st.markdown(f"**Signed in:** {st.session_state.user['full_name']} ({st.session_state.user['role']})")
    st.markdown("---")
    if st.session_state.user["role"] == "admin":
        menu = st.radio("Menu", ["Dashboard","Kids","Attendance","Programs","Import","Profiles","Export","Admin Tools","Logout"])
    else:
        menu = st.radio("Menu", ["Kids","Attendance","Profiles","Logout"])
    st.markdown("---")
    if menu == "Logout" or st.button("Log out"):
        st.session_state.user = None
        st.session_state.selected_kid = None
        st.rerun()

# route to pages
if st.session_state.user["role"] == "admin":
    if menu == "Dashboard":
        st.header("Dashboard")
        k = load_csv(KIDS_CSV)
        a = load_csv(ATTENDANCE_CSV)
        p = load_csv(PROGRAMS_CSV)
        c1,c2,c3 = st.columns(3)
        c1.metric("Programs", len(p))
        c2.metric("Kids", len(k))
        c3.metric("Attendance records", len(a))
    elif menu == "Kids":
        kids_page()
    elif menu == "Attendance":
        attendance_page()
    elif menu == "Programs":
        programs_page()
    elif menu == "Import":
        # shortcut to the import area on kids page
        kids_page()
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
    # leader views
    if menu == "Kids":
        kids_page()
    elif menu == "Attendance":
        attendance_page()
    elif menu == "Profiles":
        profiles_page()
    elif menu == "Logout":
        st.session_state.user = None
        st.rerun()

# end of app.py
