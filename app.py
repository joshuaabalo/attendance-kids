# app.py
"""
Fafali Attendance Manager - single-file app
- Top tabs navigation
- Admin & Leader roles (default admin/123, leader1/123)
- Excel import (KidsT.xlsx format)
- Kid profiles, attendance, create/delete kids
- Password change
- Unique widget keys to avoid duplicate-element errors
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import tempfile, shutil, os
from datetime import date, datetime
import uuid
import importlib

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

# Optional starter Excel in this environment (won't break if absent)
STARTER_XLSX = Path("/mnt/data/KidsT.xlsx")
DEFAULT_IMAGE = ""  # leave blank to show emoji in UI

# ---------------- Utilities ----------------
def atomic_save_csv(path: Path, df: pd.DataFrame):
    """Atomically write CSV to avoid partial writes."""
    tmp = None
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".tmp", dir=str(path.parent))
        tmp.close()
        df.to_csv(tmp.name, index=False)
        shutil.move(tmp.name, str(path))
    finally:
        if tmp is not None and os.path.exists(tmp.name):
            try:
                os.remove(tmp.name)
            except Exception:
                pass
    # Clear streamlit cache so subsequent reads are fresh
    try:
        st.cache_data.clear()
    except Exception:
        pass

@st.cache_data
def load_csv(path: Path) -> pd.DataFrame:
    """Load CSV as strings with no NaNs. Return empty DataFrame if read fails."""
    if path.exists():
        try:
            return pd.read_csv(path, dtype=str).fillna("")
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

def ensure_csv(path: Path, cols: list):
    if not path.exists():
        pd.DataFrame(columns=cols).to_csv(path, index=False)

def calc_age(dob_str):
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

# ---------------- Init files and defaults ----------------
def init_files_and_starter():
    ensure_csv(USERS_CSV, ["username","password","role","programs","full_name"])
    ensure_csv(KIDS_CSV, ["id","name","age","program","dob","gender","school","location","guardian_name","guardian_contact","relationship","image"])
    ensure_csv(PROGRAMS_CSV, ["program"])
    ensure_csv(ATT_CSV, ["date","kid_id","present","note","program","marked_by","timestamp"])

    users = load_csv(USERS_CSV)
    if users.empty:
        # default simple passwords as requested; encourage changing later
        df = pd.DataFrame([
            {"username":"admin","password":"123","role":"admin","programs":"","full_name":"Administrator"},
            {"username":"leader1","password":"123","role":"leader","programs":"Football Boys","full_name":"Leader One"},
        ])
        atomic_save_csv(USERS_CSV, df)

    # optional starter Excel import (non-critical)
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
                    rows.append({
                        "id": sid,
                        "name": name,
                        "age": calc_age(dob_s),
                        "program": prog,
                        "dob": dob_s,
                        "gender": str(r.get("Gender","")).strip(),
                        "school": str(r.get("Current School","")).strip(),
                        "location": str(r.get("Location","")).strip(),
                        "guardian_name": str(r.get("guardian_name","")).strip(),
                        "guardian_contact": str(r.get("guardian_contact","")).strip(),
                        "relationship": str(r.get("Relationship","")).strip(),
                        "image": DEFAULT_IMAGE
                    })
                if rows:
                    atomic_save_csv(KIDS_CSV, pd.DataFrame(rows))
                    # add programs
                    progs = load_csv(PROGRAMS_CSV)
                    existing = [p.strip().lower() for p in progs.get("program",[])]
                    for p in {r["program"] for r in rows if r["program"]}:
                        if p.strip().lower() not in existing:
                            progs = pd.concat([progs, pd.DataFrame([{"program":p}])], ignore_index=True)
                    if not progs.empty:
                        atomic_save_csv(PROGRAMS_CSV, progs)
        except Exception:
            pass

# ---------------- Domain helpers ----------------
def save_users_df(df: pd.DataFrame):
    atomic_save_csv(USERS_CSV, df)

def save_kids_df(df: pd.DataFrame):
    atomic_save_csv(KIDS_CSV, df)

def save_programs_df(df: pd.DataFrame):
    atomic_save_csv(PROGRAMS_CSV, df)

def save_att_df(df: pd.DataFrame):
    atomic_save_csv(ATT_CSV, df)

def create_user(username, password, role, programs="", full_name=""):
    users = load_csv(USERS_CSV)
    if username in users.get("username", []):
        return False, "Username exists"
    row = {"username":username,"password":password,"role":role,"programs":programs,"full_name":full_name}
    users = pd.concat([users, pd.DataFrame([row])], ignore_index=True)
    save_users_df(users)
    return True, "User created"

def add_program_if_missing(name: str):
    name = str(name).strip()
    if not name: return
    progs = load_csv(PROGRAMS_CSV)
    existing = [p.strip().lower() for p in progs.get("program",[])]
    if name.lower() not in existing:
        progs = pd.concat([progs, pd.DataFrame([{"program":name}])], ignore_index=True)
        save_programs_df(progs)

def save_kid_image(uploaded_file, kid_name, kid_id):
    ext = Path(uploaded_file.name).suffix
    safe = "".join([c for c in kid_name if c.isalnum() or c in (" ", "_")]).strip().replace(" ", "_")
    dest = IMAGES_DIR / f"{safe}_{kid_id}{ext}"
    with open(dest, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return str(dest)

def add_kid(name, age, gender, program, dob="", school="", location="", guardian_name="", guardian_contact="", relationship="", image_file=None):
    kids = load_csv(KIDS_CSV)
    kid_id = str(uuid.uuid4())[:8]
    image_path = ""
    if image_file is not None:
        image_path = save_kid_image(image_file, name, kid_id)
    row = {"id": kid_id, "name": name, "age": int(age) if str(age).isdigit() else age, "program": program, "dob": dob, "gender": gender, "school": school, "location": location, "guardian_name": guardian_name, "guardian_contact": guardian_contact, "relationship": relationship, "image": image_path}
    kids = pd.concat([kids, pd.DataFrame([row])], ignore_index=True)
    save_kids_df(kids)
    return kid_id

def remove_kid(kid_id):
    kids = load_csv(KIDS_CSV)
    kids = kids[kids["id"] != kid_id]
    save_kids_df(kids)
    att = load_csv(ATT_CSV)
    att = att[att["kid_id"] != kid_id]
    save_att_df(att)

def kid_stats(kid_id):
    att = load_csv(ATT_CSV)
    kids = load_csv(KIDS_CSV)
    rec = att[att["kid_id"]==kid_id]
    present_days = rec[rec["present"]=="1"]["date"].nunique()
    prog_arr = kids[kids["id"]==kid_id]["program"].values
    if len(prog_arr)==0:
        total_days = att["date"].nunique()
    else:
        p = prog_arr[0]
        total_days = att[att["program"]==p]["date"].nunique()
    pct = (present_days/total_days*100) if total_days>0 else 0.0
    return present_days, round(pct,1), total_days

# ---------------- Auth ----------------
def check_password(entered: str, stored: str) -> bool:
    return str(entered) == str(stored)

def attempt_login(username: str, password: str, role_choice: str):
    users = load_csv(USERS_CSV)
    if users.empty: return None
    row = users[users["username"] == username]
    if row.empty: return None
    user = row.iloc[0]
    if str(user["role"]).lower() != role_choice.lower():
        return None
    if not check_password(password, user["password"]):
        return None
    progs_raw = str(user.get("programs","") or "")
    programs = [p.strip() for p in progs_raw.split(",") if p.strip()]
    return {"username": user["username"], "role": user["role"], "programs": programs, "full_name": user.get("full_name", user["username"])}

# ---------------- Styling helper ----------------
def inject_css():
    st.markdown("""
    <style>
    .header-title {font-size:22px; font-weight:600; margin-bottom:6px;}
    .muted {color:#94a3b8}
    .card {padding:12px; border-radius:10px; background:#0f1720; color:#e6eef6}
    </style>
    """, unsafe_allow_html=True)

# ---------------- Pages ----------------
def page_login():
    inject_css()
    st.markdown(f"<div class='header-title'>{APP_TITLE}</div>", unsafe_allow_html=True)
    st.write("Sign in as Admin or Leader. Default accounts: `admin/123`, `leader1/123`")
    with st.form("login_form_main", clear_on_submit=False):
        role_choice = st.selectbox("Sign in as", ("admin","leader"), key="login_role_main")
        username = st.text_input("Username", key="login_username_main")
        password = st.text_input("Password", type="password", key="login_pw_main")
        submitted = st.form_submit_button("Sign in", key="login_submit_main")
        if submitted:
            user = attempt_login(username.strip(), password, role_choice)
            if user:
                st.session_state.user = user
                st.success(f"Signed in: {user['full_name']} ({user['role']})")
                st.experimental_rerun()
            else:
                st.error("Invalid credentials or role mismatch.")

def page_dashboard():
    st.header("Dashboard")
    kids = load_csv(KIDS_CSV)
    att = load_csv(ATT_CSV)
    progs = load_csv(PROGRAMS_CSV)
    c1,c2,c3 = st.columns(3)
    c1.metric("Programs", len(progs))
    c2.metric("Kids", len(kids))
    c3.metric("Attendance records", len(att))
    st.markdown("---")
    st.subheader("Recent attendance")
    if att.empty:
        st.info("No attendance yet.")
    else:
        merged = att.merge(kids[["id","name"]], left_on="kid_id", right_on="id", how="left")
        merged = merged.sort_values("timestamp", ascending=False).head(30)
        show = merged.rename(columns={"timestamp":"When","date":"Date","name":"Kid","present":"Present","marked_by":"By","note":"Note"})
        st.dataframe(show[["When","Date","Kid","program","Present","By","Note"]])

def page_kids():
    st.header("Kids")
    kids = load_csv(KIDS_CSV)
    programs_df = load_csv(PROGRAMS_CSV)
    all_programs = sorted([p for p in programs_df.get("program",[]) if p.strip()]) if not programs_df.empty else []
    locations = sorted(list({str(x).strip() for x in kids.get("location",[]) if str(x).strip()}))

    # program scope selection
    if st.session_state.user["role"].lower() == "admin":
        prog_filter = st.selectbox("Filter by program", ["-- All --"] + all_programs, key="kids_prog_filter_main")
        chosen_prog = None if prog_filter == "-- All --" else prog_filter
    else:
        leader_progs = st.session_state.user.get("programs", [])
        if not leader_progs:
            st.info("No programs assigned. Contact admin.")
            return
        prog_choice = st.selectbox("Your program", ["-- All my programs --"] + leader_progs, key="kids_leader_prog_main")
        chosen_prog = None if prog_choice == "-- All my programs --" else prog_choice

    loc_choice = st.selectbox("Filter by location", ["-- All --"] + ([""] + locations), key="kids_loc_filter_main")
    chosen_loc = None if loc_choice == "-- All --" or loc_choice == "" else loc_choice

    search = st.text_input("Search by name", key="kids_search_main")

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

    st.markdown("---")
    st.subheader(f"Kids ({len(view)})")
    if view.empty:
        st.info("No kids match filters.")
        return

    # Add kid form (admin or leader)
    with st.expander("Add new kid", expanded=False):
        with st.form("add_kid_form_main"):
            k_name = st.text_input("Full name", key="add_kid_name")
            k_dob = st.text_input("DOB (YYYY-MM-DD) optional", key="add_kid_dob")
            k_age = st.number_input("Age (optional)", min_value=1, max_value=99, value=6, key="add_kid_age")
            k_gender = st.selectbox("Gender", ("Male","Female","Other"), key="add_kid_gender")
            if st.session_state.user["role"].lower() == "admin":
                k_program = st.selectbox("Program", ([""] + all_programs), key="add_kid_program_admin")
            else:
                k_program = st.session_state.user.get("programs", [])[0]
                st.write(f"Program: **{k_program}**")
            k_school = st.text_input("School", key="add_kid_school")
            k_location = st.text_input("Location", key="add_kid_location")
            k_guardian = st.text_input("Guardian name", key="add_kid_guardian")
            k_contact = st.text_input("Guardian contact", key="add_kid_contact")
            k_relationship = st.text_input("Relationship", key="add_kid_relationship")
            k_image = st.file_uploader("Profile picture (optional)", type=["png","jpg","jpeg"], key="add_kid_image")
            if st.form_submit_button("Add kid", key="add_kid_submit"):
                if not k_name.strip():
                    st.error("Name required.")
                else:
                    if k_program and k_program not in all_programs:
                        add_program_if_missing(k_program)
                    add_kid(k_name.strip(), k_age, k_gender, k_program, dob=k_dob.strip(), school=k_school.strip(), location=k_location.strip(), guardian_name=k_guardian.strip(), guardian_contact=k_contact.strip(), relationship=k_relationship.strip(), image_file=k_image)
                    st.success("Kid added.")
                    st.experimental_rerun()

    # Display list
    for _, r in view.sort_values("name").iterrows():
        with st.expander(r["name"], expanded=False):
            cols = st.columns([1,3,2])
            with cols[0]:
                if r.get("image"):
                    try:
                        st.image(r["image"], width=84)
                    except Exception:
                        st.write("🧒")
                else:
                    st.write("🧒")
            with cols[1]:
                st.markdown(f"**{r['name']}**")
                st.write(f"Age: {r.get('age','')} • {r.get('gender','')}")
                st.write(f"Program: **{r.get('program','')}**")
                st.write(f"School: {r.get('school','')} • Location: {r.get('location','')}")
            with cols[2]:
                if st.button("View profile", key=f"kids_view_{r['id']}"):
                    st.session_state.selected_kid = r["id"]
                    st.experimental_rerun()
                if st.session_state.user["role"].lower() in ("admin","leader"):
                    if st.button("Open | Edit", key=f"kids_open_{r['id']}"):
                        # reuse selected_kid for opening edit UI in Profiles tab
                        st.session_state.selected_kid = r["id"]
                        st.experimental_rerun()
                if st.session_state.user["role"].lower() == "admin":
                    if st.button("Remove", key=f"kids_remove_{r['id']}"):
                        st.session_state.pending_delete = {"type":"kid","id":r["id"], "name": r["name"]}
                        st.experimental_rerun()

    # pending delete
    if st.session_state.get("pending_delete"):
        pdv = st.session_state["pending_delete"]
        if pdv.get("type") == "kid":
            st.warning(f"Confirm delete: {pdv.get('name')} (ID: {pdv.get('id')})")
            c_yes, c_no = st.columns(2)
            if c_yes.button("Yes, delete", key="kids_confirm_del_yes"):
                remove_kid(pdv["id"])
                st.success("Kid removed.")
                st.session_state.pending_delete = None
                st.experimental_rerun()
            if c_no.button("Cancel", key="kids_confirm_del_no"):
                st.session_state.pending_delete = None
                st.experimental_rerun()

def page_import():
    st.header("Import Kids (Excel - KidsT format)")
    st.write("Required columns: Student ID, FirstName, LastName, Date of Birth, Gender, Current School, Project, Location, guardian_name, guardian_contact, Relationship")
    uploaded = st.file_uploader("Upload .xlsx/.xls", type=["xlsx","xls"], key="import_file_main")
    if uploaded is None:
        return

    # check openpyxl availability
    try:
        importlib.import_module("openpyxl")
    except Exception:
        st.error("Reading .xlsx requires the 'openpyxl' package. Install it with: pip install openpyxl")
        return

    try:
        df = pd.read_excel(uploaded)
    except Exception as e:
        st.error(f"Could not read Excel: {e}")
        return

    required = {"Student ID","FirstName","LastName","Date of Birth","Gender","Current School","Project","Location","guardian_name","guardian_contact","Relationship"}
    if not required.issubset(set(df.columns)):
        st.error("Excel is missing required columns: " + ", ".join(sorted(required)))
        return

    mapped = pd.DataFrame()
    mapped["id"] = df["Student ID"].astype(str).fillna("").replace("nan","")
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
    combined = combined.drop_duplicates(subset=["id"], keep="first")
    combined = combined.drop_duplicates(subset=["name","program"], keep="first")
    after = len(combined)
    added = max(0, after - before)

    st.subheader("Preview (new rows)")
    new_preview = combined[~combined["id"].isin(existing.get("id", []))]
    st.dataframe(new_preview)

    if st.button("Confirm import", key="import_confirm_btn"):
        save_kids_df(combined)
        for p in mapped["program"].unique():
            if str(p).strip():
                add_program_if_missing(p)
        st.success(f"Imported. {added} new kids added (duplicates skipped).")
        st.experimental_rerun()

def page_attendance():
    st.header("Attendance")
    kids = load_csv(KIDS_CSV)
    if kids.empty:
        st.info("No kids available.")
        return

    # program scope
    if st.session_state.user["role"].lower() == "admin":
        progs = sorted(list({str(x).strip() for x in kids.get("program",[]) if str(x).strip()}))
        prog_choice = st.selectbox("Program (admin)", ["-- All --"] + progs, key="att_prog_admin_main")
        prog_scope = None if prog_choice == "-- All --" else prog_choice
    else:
        programs = st.session_state.user.get("programs", [])
        if not programs:
            st.info("No programs assigned.")
            return
        prog_choice = st.selectbox("Choose program", ["-- Select --"] + programs, key="att_prog_leader_main")
        prog_scope = None if prog_choice == "-- Select --" else prog_choice

    if prog_scope:
        scope = kids[kids["program"] == prog_scope]
    else:
        if st.session_state.user["role"].lower() == "admin":
            scope = kids.copy()
        else:
            scope = kids[kids["program"].isin(st.session_state.user.get("programs", []))]

    if scope.empty:
        st.info("No kids in the selected scope.")
        return

    att = load_csv(ATT_CSV)
    att_date = st.date_input("Attendance date", value=date.today(), key="att_date_main")
    att_str = att_date.isoformat()

    # defaults from existing records
    existing = att[att["date"] == att_str]
    present_defaults = {row["kid_id"]:(row["present"]=="1") for _,row in existing.iterrows()}
    notes_defaults = {row["kid_id"]: row.get("note","") for _,row in existing.iterrows()}

    c1, c2, _ = st.columns([1,1,6])
    if c1.button
