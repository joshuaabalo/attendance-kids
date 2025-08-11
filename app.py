# app.py
"""
Fafali Attendance Manager - single-file app with:
- Excel import (KidsT format)
- Leaders with multiple programs (comma-separated)
- Program & Location filters + leader dropdown to pick program
- Leader-restricted views across Kids & Attendance
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
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

USERS_CSV = DATA_DIR / "users.csv"
KIDS_CSV = DATA_DIR / "kids.csv"
PROGRAMS_CSV = DATA_DIR / "programs.csv"
ATTENDANCE_CSV = DATA_DIR / "attendance.csv"

DEFAULT_IMG = "https://via.placeholder.com/150"

# ---------------------------
# HELPERS
# ---------------------------
def ensure_csv(path, columns, create_admin=False):
    if not path.exists():
        pd.DataFrame(columns=columns).to_csv(path, index=False)
    if create_admin and path == USERS_CSV:
        # create default admin row if empty
        df = load_csv(USERS_CSV)
        if df.empty:
            admin = {"username": "admin", "password": hash_password("admin"), "role": "admin", "programs": "", "full_name": "Administrator"}
            atomic_save_csv(USERS_CSV, pd.DataFrame([admin]))

def init_files():
    ensure_csv(USERS_CSV, ["username", "password", "role", "programs", "full_name"], create_admin=True)
    ensure_csv(KIDS_CSV, ["id", "name", "age", "program", "dob", "gender",
                          "school", "location", "guardian_name", "guardian_contact",
                          "relationship", "image"])
    ensure_csv(PROGRAMS_CSV, ["program"])
    ensure_csv(ATTENDANCE_CSV, ["date", "kid_id", "present", "note", "program", "marked_by", "timestamp"])

@st.cache_data
def load_csv(path: Path) -> pd.DataFrame:
    if path.exists():
        try:
            df = pd.read_csv(path, dtype=str)
            return df.fillna("")
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

def atomic_save_csv(path: Path, df: pd.DataFrame):
    tmp = path.with_suffix(".tmp")
    df.to_csv(tmp, index=False)
    shutil.move(str(tmp), str(path))
    # attempt to clear cache - try several common options
    try:
        load_csv.clear()
    except Exception:
        try:
            st.cache_data.clear()
        except Exception:
            pass

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def check_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def calc_age(dob):
    try:
        birth_date = pd.to_datetime(dob).date()
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    except Exception:
        return ""

# ---------------------------
# Domain helpers
# ---------------------------
def get_users(): return load_csv(USERS_CSV)
def save_users(df): atomic_save_csv(USERS_CSV, df)

def get_programs(): return load_csv(PROGRAMS_CSV)
def save_programs(df): atomic_save_csv(PROGRAMS_CSV, df)

def get_kids(): return load_csv(KIDS_CSV)
def save_kids(df): atomic_save_csv(KIDS_CSV, df)

def get_att(): return load_csv(ATTENDANCE_CSV)
def save_att(df): atomic_save_csv(ATTENDANCE_CSV, df)

def add_program_if_missing(name):
    progs = get_programs()
    if name.strip() == "":
        return
    existing = [p.strip().lower() for p in progs.get("program", []).tolist()]
    if name.strip().lower() not in existing:
        progs = pd.concat([progs, pd.DataFrame([{"program": name.strip()}])], ignore_index=True)
        save_programs(progs)

def add_user(username, password, role, programs="", full_name=""):
    users = get_users()
    if username in users.get("username", []).tolist():
        return False, "Username already exists."
    row = {"username": username, "password": hash_password(password), "role": role, "programs": programs, "full_name": full_name}
    users = pd.concat([users, pd.DataFrame([row])], ignore_index=True)
    save_users(users)
    return True, "User created."

def add_kid_row(row):
    """row is dict matching kids CSV columns; appends and saves"""
    kids = get_kids()
    kids = pd.concat([kids, pd.DataFrame([row])], ignore_index=True)
    save_kids(kids)

def build_name(first, last):
    return f"{str(first).strip()} {str(last).strip()}".strip()

# ---------------------------
# App UI / Auth
# ---------------------------
st.set_page_config("Fafali Attendance Manager", layout="wide")

# initialize data files
init_files()

if "user" not in st.session_state:
    st.session_state.user = None  # will store dict: {"username","role","programs":list,"full_name"}

def login_user(username: str, password: str):
    users = get_users()
    if users.empty:
        return None
    row = users[users["username"] == username]
    if row.empty:
        return None
    user = row.iloc[0]
    if not check_password(password, user["password"]):
        return None
    # parse programs (comma-separated) into list
    programs = [p.strip() for p in str(user.get("programs", "")).split(",") if p.strip()]
    return {"username": user["username"], "role": user["role"], "programs": programs, "full_name": user.get("full_name", user["username"])}

# ---------------------------
# Pages
# ---------------------------
def kids_page():
    st.header("Kids Management")

    kids_df = get_kids()
    progs_df = get_programs()
    all_programs = sorted([p for p in progs_df.get("program", []).tolist() if p.strip()])

    # role-based scope: build allowed_programs
    if st.session_state.user["role"] == "admin":
        allowed_programs = all_programs
    else:
        # leader: from session user programs
        allowed_programs = st.session_state.user.get("programs", [])
        # ensure they exist in programs list (if not, still allow)
        for p in allowed_programs:
            if p not in all_programs:
                all_programs.append(p)

    # top filters
    cols = st.columns(3)
    with cols[0]:
        # For leaders: let them pick which of their programs to view (dropdown)
        if st.session_state.user["role"] != "admin":
            chosen_prog = st.selectbox("Select program (leaders)", ["-- Select --"] + st.session_state.user.get("programs", []))
            if chosen_prog == "-- Select --":
                chosen_prog = None
        else:
            # Admin can filter by program
            chosen_prog = st.selectbox("Filter by program (admin)", ["-- All --"] + all_programs)
            if chosen_prog == "-- All --":
                chosen_prog = None
    with cols[1]:
        chosen_loc = st.selectbox("Filter by location", ["-- All --"] + sorted(list({str(v).strip() for v in kids_df.get("location", []) if str(v).strip()})))
        if chosen_loc == "-- All --":
            chosen_loc = None
    with cols[2]:
        search = st.text_input("Search name")

    # apply filters
    view_df = kids_df.copy()
    if st.session_state.user["role"] != "admin":
        # leader: restrict to allowed_programs
        if chosen_prog:
            view_df = view_df[view_df["program"] == chosen_prog]
        else:
            # if leader didn't pick a program, show all their programs
            view_df = view_df[view_df["program"].isin(allowed_programs)]
    else:
        if chosen_prog:
            view_df = view_df[view_df["program"] == chosen_prog]

    if chosen_loc:
        view_df = view_df[view_df["location"] == chosen_loc]
    if search:
        view_df = view_df[view_df["name"].str.contains(search, case=False, na=False)]

    st.subheader("Import from Excel (KidsT format)")
    excel_file = st.file_uploader("Upload Excel file (.xlsx/.xls)", type=["xlsx", "xls"])
    if excel_file:
        try:
            new_kids = pd.read_excel(excel_file)
        except Exception as e:
            st.error(f"Could not read Excel: {e}")
            new_kids = None

        if new_kids is not None:
            required_cols = {"Student ID", "FirstName", "LastName", "Date of Birth", "Gender",
                             "Current School", "Project", "Location", "guardian_name", "guardian_contact", "Relationship"}
            if not required_cols.issubset(set(new_kids.columns)):
                st.error(f"Excel must have columns: {', '.join(sorted(required_cols))}")
            else:
                # map columns
                new_kids_m = pd.DataFrame()
                new_kids_m["id"] = new_kids["Student ID"].astype(str).fillna("").replace("nan", "")
                # generate ids for empty ids
                missing_id_mask = new_kids_m["id"].astype(str).str.strip() == ""
                next_idx = 1
                if not get_kids().empty:
                    # try to avoid ID collisions by using a numeric new prefix
                    try:
                        existing_ids = [int(str(x).replace("K","")) for x in get_kids()["id"] if str(x).startswith("K") and str(x).replace("K","").isdigit()]
                        if existing_ids:
                            next_idx = max(existing_ids) + 1
                    except Exception:
                        next_idx = 1
                gen_ids = []
                for i in range(missing_id_mask.sum()):
                    gen_ids.append(f"K{str(next_idx).zfill(4)}")
                    next_idx += 1
                new_kids_m.loc[missing_id_mask, "id"] = gen_ids
                new_kids_m["name"] = new_kids["FirstName"].astype(str).str.strip() + " " + new_kids["LastName"].astype(str).str.strip()
                new_kids_m["dob"] = pd.to_datetime(new_kids["Date of Birth"], errors="coerce").dt.date.astype(str)
                new_kids_m["age"] = new_kids_m["dob"].apply(calc_age)
                new_kids_m["gender"] = new_kids["Gender"].astype(str)
                new_kids_m["school"] = new_kids["Current School"].astype(str)
                new_kids_m["program"] = new_kids["Project"].astype(str)
                new_kids_m["location"] = new_kids["Location"].astype(str)
                new_kids_m["guardian_name"] = new_kids["guardian_name"].astype(str)
                new_kids_m["guardian_contact"] = new_kids["guardian_contact"].astype(str)
                new_kids_m["relationship"] = new_kids["Relationship"].astype(str)
                new_kids_m["image"] = DEFAULT_IMG

                # preview candidates to add (compare by id primarily; fallback to name+program)
                existing = get_kids()
                if existing.empty:
                    existing = pd.DataFrame(columns=new_kids_m.columns)
                # merge candidates
                candidate = pd.concat([existing, new_kids_m], ignore_index=True)
                before = len(existing)
                # drop duplicates: keep existing first (keep='first') based on id
                candidate.drop_duplicates(subset=["id"], keep="first", inplace=True)
                after_id_dedup = len(candidate)
                # Additionally, drop duplicates by name+program to avoid duplicates when IDs differ/missing
                candidate = candidate.drop_duplicates(subset=["name", "program"], keep="first")
                after_nameprog_dedup = len(candidate)
                added_count = after_nameprog_dedup - before if after_nameprog_dedup > before else 0

                st.subheader("Preview (new rows to be added shown below)")
                # rows considered new are those in candidate that aren't in existing (by id)
                existing_ids = set(existing["id"].astype(str).tolist())
                new_rows = candidate[~candidate["id"].astype(str).isin(existing_ids)]
                st.dataframe(new_rows)

                if st.button("Confirm Import"):
                    # save candidate as new kids sheet
                    save_kids(candidate)
                    # ensure programs found in import are recorded in programs CSV
                    for prog in new_kids_m["program"].unique():
                        if str(prog).strip():
                            add_program_if_missing(str(prog).strip())
                    st.success(f"Import complete. {added_count} new kids added (skipped duplicates).")
                    st.experimental_rerun()

    st.markdown("---")
    st.subheader(f"Kids ({len(view_df)})")
    if view_df.empty:
        st.info("No kids match these filters.")
    else:
        # show table summary with clickable expanders
        # display columns that are useful in summary
        for _, r in view_df.sort_values("name").iterrows():
            with st.expander(r["name"]):
                left, right = st.columns([1, 3])
                with left:
                    st.image(r.get("image", DEFAULT_IMG), width=140)
                with right:
                    st.markdown(f"**Student ID:** {r.get('id','')}")
                    st.markdown(f"**Age:** {r.get('age','')}  **DOB:** {r.get('dob','')}")
                    st.markdown(f"**Gender:** {r.get('gender','')}")
                    st.markdown(f"**Program:** {r.get('program','')}")
                    st.markdown(f"**School:** {r.get('school','')}")
                    st.markdown(f"**Location:** {r.get('location','')}")
                    st.markdown(f"**Guardian:** {r.get('guardian_name','')} ({r.get('relationship','')}) — {r.get('guardian_contact','')}")
                    cols = st.columns(3)
                    if cols[0].button("View Profile", key=f"view_{r['id']}"):
                        st.session_state.selected_kid = r["id"]
                        st.experimental_rerun()
                    if st.session_state.user["role"] in ("admin",):
                        if cols[1].button("Delete", key=f"del_{r['id']}"):
                            # delete with confirmation
                            if st.confirm(f"Delete {r['name']} (ID: {r['id']})?"):
                                df = get_kids()
                                df = df[df["id"] != r["id"]]
                                save_kids(df)
                                st.success("Deleted.")
                                st.experimental_rerun()
                    if cols[2].button("Edit (Profile) - opens Profiles page", key=f"edit_{r['id']}"):
                        st.session_state.selected_kid = r["id"]
                        st.experimental_rerun()

def attendance_page():
    st.header("Attendance")
    kids_df = get_kids()
    if kids_df.empty:
        st.info("No kids available.")
        return
    # role-based program scope
    progs_df = get_programs()
    all_programs = sorted([p for p in progs_df.get("program", []).tolist() if p.strip()])
    if st.session_state.user["role"] == "admin":
        program_choice = st.selectbox("Program (admin) or -- All --", ["-- All --"] + all_programs)
        if program_choice == "-- All --":
            program_choice = None
    else:
        # leader: dropdown of their programs to pick which program to mark
        programs = st.session_state.user.get("programs", [])
        program_choice = st.selectbox("Choose your program", ["-- Select --"] + programs)
        if program_choice == "-- Select --":
            program_choice = None

    # filter kids to scope
    if program_choice:
        scope = kids_df[kids_df["program"] == program_choice]
    else:
        if st.session_state.user["role"] == "admin":
            scope = kids_df.copy()
        else:
            # leader: if no selection, show all kids across their programs
            scope = kids_df[kids_df["program"].isin(st.session_state.user.get("programs", []))]

    if scope.empty:
        st.info("No kids match the selected program.")
        return

    att_df = get_att()
    att_date = st.date_input("Attendance date", value=date.today())
    att_str = att_date.isoformat()

    # load existing attendance for that date into a dict
    existing = att_df[att_df["date"] == att_str]
    present_defaults = {row["kid_id"]: (row["present"] == "1") for _, row in existing.iterrows()}
    notes_defaults = {row["kid_id"]: row.get("note", "") for _, row in existing.iterrows()}

    col_all_1, col_all_2, _ = st.columns([1,1,6])
    if col_all_1.button("All Present"):
        for kid_id in scope["id"].tolist():
            present_defaults[kid_id] = True
    if col_all_2.button("All Absent"):
        for kid_id in scope["id"].tolist():
            present_defaults[kid_id] = False

    with st.form("mark_att"):
        checked = {}
        notes = {}
        for _, k in scope.sort_values("name").iterrows():
            c1, c2, c3 = st.columns([1, 4, 3])
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
            new_att = att_df[att_df["date"] != att_str]  # drop existing for the date
            now = datetime.now().isoformat(timespec="seconds")
            for kid_id, is_present in checked.items():
                kid_prog = kids_df[kids_df["id"] == kid_id]["program"].values[0] if not kids_df.empty else ""
                row = {"date": att_str, "kid_id": kid_id, "present": "1" if is_present else "0", "note": notes.get(kid_id, ""), "program": kid_prog, "marked_by": st.session_state.user["username"], "timestamp": now}
                new_att = pd.concat([new_att, pd.DataFrame([row])], ignore_index=True)
            save_att(new_att)
            st.success("Attendance saved.")
            st.experimental_rerun()

def programs_page():
    st.header("Programs")
    progs_df = get_programs()
    st.subheader("Existing programs")
    if progs_df.empty:
        st.write("— none —")
    else:
        st.dataframe(progs_df)

    if st.session_state.user["role"] == "admin":
        new_prog = st.text_input("New program name")
        if st.button("Add program"):
            if new_prog.strip():
                add_program_if_missing(new_prog.strip())
                st.success("Program added.")
                st.experimental_rerun()
            else:
                st.error("Enter a program name.")
    else:
        st.info("Leaders cannot create programs. Contact admin.")

def profiles_page():
    st.header("Profiles")
    selected = st.session_state.get("selected_kid", None)
    kids_df = get_kids()
    if not selected:
        st.info("Open a kid from the Kids page to view profile.")
        return
    if selected not in kids_df["id"].values:
        st.error("Kid not found.")
        return
    kid = kids_df[kids_df["id"] == selected].iloc[0]
    # leader access check
    if st.session_state.user["role"] != "admin" and kid["program"] not in st.session_state.user.get("programs", []):
        st.error("Access denied.")
        return

    left, right = st.columns([1, 2])
    with left:
        st.image(kid.get("image", DEFAULT_IMG), width=200)
    with right:
        st.subheader(kid.get("name", ""))
        st.write(f"Student ID: {kid.get('id','')}")
        st.write(f"Program: {kid.get('program','')}")
        st.write(f"Age: {kid.get('age','')}  DOB: {kid.get('dob','')}")
        st.write(f"Gender: {kid.get('gender','')}")
        st.write(f"School: {kid.get('school','')}")
        st.write(f"Location: {kid.get('location','')}")
        st.write(f"Guardian: {kid.get('guardian_name','')} ({kid.get('relationship','')}) — {kid.get('guardian_contact','')}")

    st.markdown("---")
    st.subheader("Attendance history")
    att = get_att()
    kid_att = att[att["kid_id"] == selected].sort_values("date", ascending=False)
    if kid_att.empty:
        st.write("No records.")
    else:
        disp = kid_att[["date", "present", "note", "marked_by", "timestamp"]].rename(columns={"present":"Present","note":"Note","marked_by":"Marked by","timestamp":"When"})
        disp["Present"] = disp["Present"].apply(lambda x: "Yes" if str(x) == "1" else "No")
        st.dataframe(disp)

# ---------------------------
# Layout / Router
# ---------------------------
# Sidebar login block (if not logged in, show classic login page)
if not st.session_state.user:
    st.title("Fafali Attendance Manager — Login")
    uname = st.text_input("Username")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        user = login_user(uname, pwd)
        if user:
            st.session_state.user = user
            st.success(f"Welcome {user['full_name']}")
            st.experimental_rerun()
        else:
            st.error("Invalid login.")
    st.stop()

# If logged in, show sidebar with navigation and logout
with st.sidebar:
    st.markdown(f"**Signed in:** {st.session_state.user['full_name']} ({st.session_state.user['role']})")
    st.markdown("---")
    pages = ["Kids", "Attendance", "Programs", "Profiles", "Export", "Admin Tools"]
    page = st.radio("Menu", pages)
    st.markdown("---")
    if st.button("Log out"):
        st.session_state.user = None
        # clear selection
        for k in ["selected_kid"]:
            if k in st.session_state: del st.session_state[k]
        st.experimental_rerun()

# Router
if page == "Kids":
    kids_page()
elif page == "Attendance":
    attendance_page()
elif page == "Programs":
    programs_page()
elif page == "Profiles":
    profiles_page()
elif page == "Export":
    st.header("Export")
    files = [(USERS_CSV, "users.csv"), (PROGRAMS_CSV, "programs.csv"), (KIDS_CSV, "kids.csv"), (ATTENDANCE_CSV, "attendance.csv")]
    for p, label in files:
        if p.exists():
            with open(p, "rb") as f:
                st.download_button(label, f, file_name=label)
elif page == "Admin Tools":
    if st.session_state.user["role"] != "admin":
        st.error("Admin only.")
    else:
        st.header("Admin Tools")
        st.subheader("Users")
        users = get_users()
        if not users.empty:
            st.dataframe(users)
        st.subheader("Create user")
        with st.form("create_user"):
            uname = st.text_input("Username")
            fname = st.text_input("Full name")
            pwd = st.text_input("Password")
            role_choice = st.selectbox("Role", ("leader", "admin"))
            prog_assign = st.text_input("Assign programs (comma separated) - leaders only")
            if st.form_submit_button("Create"):
                if not (uname and pwd):
                    st.error("Username and password required.")
                else:
                    ok, msg = add_user(uname, pwd, role_choice, programs=prog_assign, full_name=fname)
                    if ok:
                        st.success("User created.")
                        # ensure programs exist in program list
                        for p in [x.strip() for x in prog_assign.split(",") if x.strip()]:
                            add_program_if_missing(p)
                        st.experimental_rerun()
                    else:
                        st.error(msg)

        st.markdown("---")
        st.subheader("System Reset")
        st.warning("Deletes programs, kids, attendance and users (except default admin).")
        if st.button("RESET SYSTEM"):
            for f in [PROGRAMS_CSV, KIDS_CSV, ATTENDANCE_CSV, USERS_CSV]:
                if f.exists():
                    f.unlink()
            init_files()
            st.success("System reset.")
            st.experimental_rerun()

# End of file
