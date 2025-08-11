# app.py
"""
Fafali Attendance Manager - single-file app (starter-ready)

Run: streamlit run app.py
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

STARTER_XLSX = Path("/mnt/data/KidsT.xlsx")  # if present, used for initial import (optional)
DEFAULT_IMAGE = ""  # if empty we show emoji as placeholder

# ---------------- Helpers ----------------
def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

@st.cache_data
def load_csv(path: Path) -> pd.DataFrame:
    if path.exists():
        try:
            return pd.read_csv(path, dtype=str).fillna("")
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

def atomic_save(path: Path, df: pd.DataFrame):
    tmp = path.with_suffix(".tmp")
    df.to_csv(tmp, index=False)
    shutil.move(str(tmp), str(path))
    # clear cached loaders so new reads reflect saved data
    try:
        st.cache_data.clear()
    except Exception:
        pass

def ensure_csv(path: Path, columns: list):
    if not path.exists():
        pd.DataFrame(columns=columns).to_csv(path, index=False)

def calc_age(dob_str):
    try:
        dob = pd.to_datetime(dob_str, errors="coerce")
        if pd.isna(dob):
            return ""
        today = pd.Timestamp(date.today())
        years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return int(years)
    except Exception:
        return ""

# ---------------- Init starter files ----------------
def init_files_with_starter():
    ensure_csv(USERS_CSV, ["username","password","role","programs","full_name"])
    ensure_csv(KIDS_CSV, ["id","name","age","program","dob","gender","school","location","guardian_name","guardian_contact","relationship","image"])
    ensure_csv(PROGRAMS_CSV, ["program"])
    ensure_csv(ATT_CSV, ["date","kid_id","present","note","program","marked_by","timestamp"])

    # create a default admin if no users exist
    users = load_csv(USERS_CSV)
    if users.empty:
        admin = {"username":"admin","password":_hash("admin"),"role":"admin","programs":"","full_name":"Administrator"}
        atomic_save(USERS_CSV, pd.DataFrame([admin]))

    # If kids empty and starter XLSX exists, try to import
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
                        # avoid collisions
                        sid = f"{sid}_{i}"
                    used_ids.add(sid)
                    name = f"{str(r.get('FirstName','')).strip()} {str(r.get('LastName','')).strip()}".strip()
                    dob_val = r.get("Date of Birth", "")
                    dob_str = ""
                    try:
                        if pd.notna(dob_val):
                            dob_str = pd.to_datetime(dob_val).date().isoformat()
                    except Exception:
                        dob_str = ""
                    prog = str(r.get("Project","")).strip()
                    row = {
                        "id": sid,
                        "name": name,
                        "age": calc_age(dob_str),
                        "program": prog,
                        "dob": dob_str,
                        "gender": str(r.get("Gender","")).strip(),
                        "school": str(r.get("Current School","")).strip(),
                        "location": str(r.get("Location","")).strip(),
                        "guardian_name": str(r.get("guardian_name","")).strip(),
                        "guardian_contact": str(r.get("guardian_contact","")).strip(),
                        "relationship": str(r.get("Relationship","")).strip(),
                        "image": DEFAULT_IMAGE
                    }
                    rows.append(row)
                if rows:
                    atomic_save(KIDS_CSV, pd.DataFrame(rows))
                    # add programs
                    progs = load_csv(PROGRAMS_CSV)
                    for p in {r["program"] for r in rows if r["program"]}:
                        if p not in progs.get("program", []).tolist():
                            progs = pd.concat([progs, pd.DataFrame([{"program":p}])], ignore_index=True)
                    if not progs.empty:
                        atomic_save(PROGRAMS_CSV, progs)
        except Exception:
            # ignore starter import errors silently
            pass

# ---------------- Domain actions ----------------
def add_user(username, password, role, programs="", full_name=""):
    users = load_csv(USERS_CSV)
    if username in users.get("username", []):
        return False, "Username exists"
    row = {"username": username, "password": _hash(password), "role": role, "programs": programs, "full_name": full_name}
    users = pd.concat([users, pd.DataFrame([row])], ignore_index=True)
    atomic_save(USERS_CSV, users)
    return True, "Created"

def add_program_if_missing(name: str):
    name = str(name).strip()
    if not name:
        return
    progs = load_csv(PROGRAMS_CSV)
    existing = [p.strip().lower() for p in progs.get("program",[])]
    if name.lower() not in existing:
        progs = pd.concat([progs, pd.DataFrame([{"program": name}])], ignore_index=True)
        atomic_save(PROGRAMS_CSV, progs)

# ---------------- Auth ----------------
def attempt_login(username: str, password: str, role_choice: str):
    users = load_csv(USERS_CSV)
    if users.empty:
        return None
    row = users[users["username"] == username]
    if row.empty:
        return None
    user = row.iloc[0]
    if user["role"] != role_choice:
        return None
    if not check_password(password, user["password"]):
        return None
    programs = [p.strip() for p in str(user.get("programs","") or "").split(",") if p.strip()]
    return {"username": user["username"], "role": user["role"], "programs": programs, "full_name": user.get("full_name", user["username"])}

# ---------------- UI Pages ----------------
def show_login():
    st.title(APP_TITLE)
    st.write("Sign in as admin or leader (user). Default admin: admin / admin")
    with st.form("login"):
        role_choice = st.selectbox("Sign in as", ("admin","leader"), index=0)
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
        if submitted:
            user = attempt_login(username.strip(), password, role_choice)
            if user:
                st.session_state.user = user
                st.success(f"Welcome {user['full_name']} ({user['role']})")
                st.rerun()
            else:
                st.error("Invalid credentials or role mismatch.")

def kids_page():
    st.header("Kids")
    kids = load_csv(KIDS_CSV)
    progs = sorted([p for p in load_csv(PROGRAMS_CSV).get("program",[]) if p.strip()])
    locations = sorted(list({str(x).strip() for x in kids.get("location",[]) if str(x).strip()}))

    # role-based program selection
    if st.session_state.user["role"] == "admin":
        prog_filter = st.selectbox("Filter by program", ["-- All --"] + progs)
        chosen_prog = None if prog_filter == "-- All --" else prog_filter
    else:
        leader_progs = st.session_state.user.get("programs", [])
        if not leader_progs:
            st.info("No programs assigned. Contact admin.")
            return
        chosen_prog = st.selectbox("Choose program (leaders)", ["-- All my programs --"] + leader_progs)
        if chosen_prog == "-- All my programs --":
            chosen_prog = None

    loc_choice = st.selectbox("Filter by location", ["-- All --"] + ([""] + locations))
    chosen_loc = None if loc_choice == "-- All --" or loc_choice == "" else loc_choice

    search = st.text_input("Search name")

    view = kids.copy()
    # restrict for leaders
    if st.session_state.user["role"] != "admin":
        allowed = st.session_state.user.get("programs", [])
        view = view[view["program"].isin(allowed)]
    if chosen_prog:
        view = view[view["program"] == chosen_prog]
    if chosen_loc:
        view = view[view["location"] == chosen_loc]
    if search:
        view = view[view["name"].str.contains(search, case=False, na=False)]

    st.subheader("Import from Excel (KidsT format)")
    uploaded = st.file_uploader("Upload .xlsx or .xls", type=["xlsx","xls"])
    if uploaded:
        try:
            df = pd.read_excel(uploaded)
        except Exception as e:
            st.error(f"Could not read file: {e}")
            df = None
        if df is not None:
            required = {"Student ID","FirstName","LastName","Date of Birth","Gender","Current School","Project","Location","guardian_name","guardian_contact","Relationship"}
            if not required.issubset(set(df.columns)):
                st.error("Excel must include columns: " + ", ".join(sorted(required)))
            else:
                mapped = pd.DataFrame()
                mapped["id"] = df["Student ID"].astype(str).fillna("").replace("nan","")
                # generate IDs for blanks
                existing_ids = set(load_csv(KIDS_CSV).get("id",[]))
                gen_counter = 1
                gen_ids = []
                for idx, val in mapped["id"].iteritems():
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
                mapped["age"] = mapped["dob"].apply(calc_age)
                mapped["gender"] = df["Gender"].astype(str)
                mapped["school"] = df["Current School"].astype(str)
                mapped["program"] = df["Project"].astype(str)
                mapped["location"] = df["Location"].astype(str)
                mapped["guardian_name"] = df["guardian_name"].astype(str)
                mapped["guardian_contact"] = df["guardian_contact"].astype(str)
                mapped["relationship"] = df["Relationship"].astype(str)
                mapped["image"] = DEFAULT_IMAGE

                existing = load_csv(KIDS_CSV)
                combined = pd.concat([existing, mapped], ignore_index=True)
                before = len(existing)
                # dedupe by id first then name+program
                combined = combined.drop_duplicates(subset=["id"], keep="first")
                combined = combined.drop_duplicates(subset=["name","program"], keep="first")
                after = len(combined)
                added = max(0, after - before)
                st.subheader("Preview (new rows shown)")
                new_rows = combined[~combined["id"].isin(existing.get("id",[]))]
                st.dataframe(new_rows)
                if st.button("Confirm import"):
                    atomic_save(KIDS_CSV, combined)
                    # add programs
                    for p in mapped["program"].unique():
                        if str(p).strip():
                            add_program_if_missing(p)
                    st.success(f"Import done. {added} new kids added.")
                    st.rerun()

    st.markdown("---")
    st.subheader(f"Kids ({len(view)})")
    if view.empty:
        st.info("No kids to show.")
    else:
        for _, r in view.sort_values("name").iterrows():
            with st.expander(r["name"]):
                c1, c2 = st.columns([1, 3])
                with c1:
                    if r.get("image"):
                        try:
                            st.image(r["image"], width=110)
                        except Exception:
                            st.write("🧒")
                    else:
                        st.write("🧒")
                with c2:
                    st.write(f"**ID:** {r.get('id','')}")
                    st.write(f"**Program:** {r.get('program','')}")
                    st.write(f"**Age:** {r.get('age','')}  **DOB:** {r.get('dob','')}")
                    st.write(f"**School:** {r.get('school','')}")
                    st.write(f"**Location:** {r.get('location','')}")
                    st.write(f"**Guardian:** {r.get('guardian_name','')} ({r.get('relationship','')}) — {r.get('guardian_contact','')}")
                    btns = st.columns([1,1,1])
                    if btns[0].button("View profile", key=f"view_{r['id']}"):
                        st.session_state.selected_kid = r["id"]
                        st.rerun()
                    # admin-only delete
                    if st.session_state.user["role"] == "admin":
                        if btns[1].button("Delete", key=f"del_{r['id']}"):
                            # simple confirmation radio
                            confirm = st.radio(f"Confirm delete {r['name']}?", ("No","Yes"), key=f"confirm_{r['id']}")
                            if confirm == "Yes":
                                df_k = load_csv(KIDS_CSV)
                                df_k = df_k[df_k["id"] != r["id"]]
                                atomic_save(KIDS_CSV, df_k)
                                st.success("Deleted.")
                                st.rerun()
                    if btns[2].button("Open profile", key=f"open_{r['id']}"):
                        st.session_state.selected_kid = r["id"]
                        st.rerun()

def attendance_page():
    st.header("Attendance")
    kids = load_csv(KIDS_CSV)
    if kids.empty:
        st.info("No kids in database.")
        return

    # scope selection
    if st.session_state.user["role"] == "admin":
        progs = sorted(list({str(x).strip() for x in kids.get("program",[]) if str(x).strip()}))
        prog_choice = st.selectbox("Program (admin)", ["-- All --"] + progs)
        program_scope = None if prog_choice == "-- All --" else prog_choice
    else:
        programs = st.session_state.user.get("programs", [])
        if not programs:
            st.info("No programs assigned.")
            return
        prog_choice = st.selectbox("Choose program", ["-- Select --"] + programs)
        program_scope = None if prog_choice == "-- Select --" else prog_choice

    if program_scope:
        scope = kids[kids["program"] == program_scope]
    else:
        if st.session_state.user["role"] == "admin":
            scope = kids.copy()
        else:
            scope = kids[kids["program"].isin(st.session_state.user.get("programs", []))]

    if scope.empty:
        st.info("No kids in scope.")
        return

    att = load_csv(ATT_CSV)
    att_date = st.date_input("Attendance date", value=date.today())
    att_str = att_date.isoformat()

    existing = att[att["date"] == att_str]
    present_defaults = {row["kid_id"]:(row["present"]=="1") for _, row in existing.iterrows()}
    notes_defaults = {row["kid_id"]: row.get("note","") for _, row in existing.iterrows()}

    col1, col2, _ = st.columns([1,1,6])
    if col1.button("All present"):
        for kid_id in scope["id"].tolist():
            present_defaults[kid_id] = True
    if col2.button("All absent"):
        for kid_id in scope["id"].tolist():
            present_defaults[kid_id] = False

    with st.form("attendance_form"):
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
            atomic_save(ATT_CSV, new_att)
            st.success("Attendance saved.")
            st.rerun()

def profiles_page():
    st.header("Child profile")
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
    att = load_csv(ATT_CSV)
    kid_att = att[att["kid_id"] == sel].sort_values("date", ascending=False)
    if kid_att.empty:
        st.write("No records.")
    else:
        disp = kid_att[["date","present","note","marked_by","timestamp"]].rename(columns={"present":"Present","note":"Note","marked_by":"Marked by","timestamp":"When"})
        disp["Present"] = disp["Present"].apply(lambda x: "Yes" if str(x) == "1" else "No")
        st.dataframe(disp)

def programs_page():
    st.header("Programs")
    progs = load_csv(PROGRAMS_CSV).get("program", []).tolist()
    if st.session_state.user["role"] == "admin":
        st.write(sorted(progs))
        newp = st.text_input("Add program")
        if st.button("Add"):
            if newp.strip():
                add_program_if_missing(newp.strip())
                st.success("Added")
                st.rerun()
            else:
                st.error("Enter name.")
    else:
        st.info("Leaders cannot manage programs.")

def export_page():
    st.header("Export CSVs")
    for p, label in [(USERS_CSV,"users.csv"), (KIDS_CSV,"kids.csv"), (PROGRAMS_CSV,"programs.csv"), (ATT_CSV,"attendance.csv")]:
        if p.exists():
            with open(p, "rb") as f:
                st.download_button(label, f, file_name=label)

def admin_tools():
    if st.session_state.user["role"] != "admin":
        st.error("Admin only.")
        return
    st.header("Admin Tools")
    users = load_csv(USERS_CSV)
    st.subheader("Users")
    if not users.empty:
        st.dataframe(users)
    st.subheader("Create user")
    with st.form("create_user"):
        uname = st.text_input("Username")
        fname = st.text_input("Full name")
        pwd = st.text_input("Password")
        role_choice = st.selectbox("Role", ("leader","admin"))
        prog_assign = st.text_input("Assign programs (comma separated)")
        submitted = st.form_submit_button("Create")
        if submitted:
            if not (uname and pwd):
                st.error("Provide username and password.")
            else:
                ok, msg = add_user(uname.strip(), pwd, role_choice, programs=prog_assign, full_name=fname)
                if ok:
                    # ensure programs present
                    for p in [x.strip() for x in prog_assign.split(",") if x.strip()]:
                        add_program_if_missing(p)
                    st.success("User created.")
                    st.rerun()
                else:
                    st.error(msg)
    st.markdown("---")
    st.subheader("Reset system (danger)")
    if st.button("RESET SYSTEM"):
        for f in [USERS_CSV, KIDS_CSV, PROGRAMS_CSV, ATT_CSV]:
            if f.exists():
                f.unlink()
        init_files_with_starter()
        st.success("Reset.")
        st.rerun()

# ---------------- Layout & Router ----------------
st.set_page_config(APP_TITLE, layout="wide")
init_files_with_starter()

if "user" not in st.session_state:
    st.session_state.user = None
if "selected_kid" not in st.session_state:
    st.session_state.selected_kid = None

if not st.session_state.user:
    show_login()
    st.stop()

# Sidebar and menu based on role
with st.sidebar:
    st.markdown(f"**Signed in:** {st.session_state.user['full_name']} ({st.session_state.user['role']})")
    st.markdown("---")
    if st.session_state.user["role"] == "admin":
        menu = st.radio("Menu", ["Dashboard","Kids","Attendance","Programs","Import","Profiles","Export","Admin Tools","Logout"])
    else:
        menu = st.radio("Menu", ["Kids","Attendance","Profiles","Logout"])
    st.markdown("---")
    if st.button("Log out") or menu == "Logout":
        st.session_state.user = None
        st.session_state.selected_kid = None
        st.rerun()

# Routes
if st.session_state.user["role"] == "admin":
    if menu == "Dashboard":
        st.header("Dashboard")
        k = load_csv(KIDS_CSV)
        a = load_csv(ATT_CSV)
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
        kids_page()  # import lives on kids page
    elif menu == "Profiles":
        profiles_page()
    elif menu == "Export":
        export_page()
    elif menu == "Admin Tools":
        admin_tools()
    elif menu == "Logout":
        st.session_state.user = None
        st.rerun()
else:
    # leader routes
    if menu == "Kids":
        kids_page()
    elif menu == "Attendance":
        attendance_page()
    elif menu == "Profiles":
        profiles_page()
    elif menu == "Logout":
        st.session_state.user = None
        st.rerun()
