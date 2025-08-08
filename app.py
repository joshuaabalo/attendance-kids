
import streamlit as st
import pandas as pd
import os
from datetime import date, datetime
import hashlib
import uuid

# ---------- Files & folders ----------
USERS_CSV = "users.csv"
KIDS_CSV = "kids.csv"
ATT_CSV = "attendance.csv"
IMAGES_DIR = "images"

os.makedirs(IMAGES_DIR, exist_ok=True)

# ---------- Helpers ----------
def hash_pwd(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def ensure_files():
    if not os.path.exists(USERS_CSV):
        # create admin user: username=admin, password=admin
        admin = pd.DataFrame([{"username":"admin","password":hash_pwd("admin"),"role":"admin","program":"" ,"name":"Administrator"}])
        admin.to_csv(USERS_CSV, index=False)
    if not os.path.exists(KIDS_CSV):
        pd.DataFrame(columns=["id","name","age","gender","program","image_path"]).to_csv(KIDS_CSV, index=False)
    if not os.path.exists(ATT_CSV):
        pd.DataFrame(columns=["date","kid_id","present","note","program","marked_by","timestamp"]).to_csv(ATT_CSV, index=False)

def load_users(): return pd.read_csv(USERS_CSV)
def save_users(df): df.to_csv(USERS_CSV, index=False)

def load_kids(): return pd.read_csv(KIDS_CSV, dtype={"id": str})
def save_kids(df): df.to_csv(KIDS_CSV, index=False)

def load_att(): return pd.read_csv(ATT_CSV, dtype={"kid_id": str})
def save_att(df): df.to_csv(ATT_CSV, index=False)

def add_user(username, password, role, program="", name=""):
    users = load_users()
    if username in users["username"].values:
        st.error("Username already exists.")
        return False
    row = {"username": username, "password": hash_pwd(password), "role": role, "program": program, "name": name}
    users = pd.concat([users, pd.DataFrame([row])], ignore_index=True)
    save_users(users)
    return True

def add_kid(name, age, gender, program, image_file):
    kids = load_kids()
    kid_id = str(uuid.uuid4())[:8]
    image_path = ""
    if image_file is not None:
        ext = os.path.splitext(image_file.name)[1]
        safe_name = "".join([c for c in name if c.isalnum() or c in (" ", "_")]).strip().replace(" ","_")
        image_path = os.path.join(IMAGES_DIR, f"{safe_name}_{kid_id}{ext}")
        with open(image_path, "wb") as f:
            f.write(image_file.getbuffer())
    row = {"id": kid_id, "name": name, "age": int(age), "gender": gender, "program": program, "image_path": image_path}
    kids = pd.concat([kids, pd.DataFrame([row])], ignore_index=True)
    save_kids(kids)
    return True

def attendance_stats_for(kid_id, att_df):
    if att_df.empty: return (0, 0.0)
    kid_rec = att_df[att_df["kid_id"]==kid_id]
    present_days = kid_rec[kid_rec["present"]==1]["date"].nunique()
    kids = load_kids()
    prog = kids[kids["id"]==kid_id]["program"].values
    if len(prog)==0:
        total_days = att_df["date"].nunique()
    else:
        prog = prog[0]
        total_days = att_df[att_df["program"]==prog]["date"].nunique()
    pct = (present_days/total_days*100) if total_days>0 else 0.0
    return (present_days, round(pct,1))

# ---------- UI styles (dark) ----------
st.set_page_config(page_title="Attendance Manager", layout="wide")
st.markdown(
    """
    <style>
    :root { --bg:#0b0f14; --card:#0f1720; --muted:#94a3b8; --accent:#6ee7b7; --danger:#ff6b6b; }
    .reportview-container {background: var(--bg); color: #e6eef6;}
    .stSidebar { background-color: #07101a; }
    .card { background: var(--card); padding:16px; border-radius:12px; box-shadow: 0 4px 18px rgba(0,0,0,0.4); }
    .small-muted { color: var(--muted); font-size: 13px; }
    .kpi { font-size:22px; font-weight:700; }
    img.profile { border-radius:10px; border: 2px solid rgba(255,255,255,0.04); }
    </style>
    """, unsafe_allow_html=True
)

# ---------- App logic ----------
ensure_files()
users_df = load_users()
kids_df = load_kids()
att_df = load_att()

def login_ui():
    st.sidebar.title("🔐 Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Log in"):
        user = users_df[users_df["username"]==username]
        if user.empty:
            st.sidebar.error("No such user.")
            return None
        if hash_pwd(password) == user.iloc[0]["password"]:
            st.session_state.user = username
            st.session_state.role = user.iloc[0]["role"]
            st.session_state.program = user.iloc[0]["program"] if "program" in user.columns else ""
            st.session_state.display_name = user.iloc[0].get("name", username)
            st.sidebar.success(f"Logged in as {st.session_state.display_name} ({st.session_state.role})")
            return True
        else:
            st.sidebar.error("Wrong password.")
            return None

def logout():
    if "user" in st.session_state:
        del st.session_state.user
    if "role" in st.session_state:
        del st.session_state.role
    if "program" in st.session_state:
        del st.session_state.program
    if "display_name" in st.session_state:
        del st.session_state.display_name
    st.rerun()

# If not logged in show login
if "user" not in st.session_state:
    login_ui()
    st.title("Attendance Manager")
    st.markdown("Please log in from the sidebar. Default admin: **admin / admin**")
    st.caption("Admins can manage programs, users, kids, and view all attendance. Program leaders can only manage their program.")
    st.stop()

# Main app (user is logged in)
username = st.session_state.user
role = st.session_state.role
user_program = st.session_state.program

st.sidebar.markdown("---")
if st.sidebar.button("Log out"):
    logout()

st.title("📋 Attendance Manager")
st.write(f"Signed in as **{st.session_state.display_name}** — role: **{role}**")

# Admin-only: Programs and Users management
if role == "admin":
    admin_menu = st.sidebar.selectbox("Admin tools", ["None","Manage Programs","Manage Users"])
else:
    admin_menu = "None"

menu = st.sidebar.radio("Main", ["Dashboard","Kids","Attendance","Child Profile","Export"])

# --- Manage Programs (simple: programs derived from kids' program plus ability to add new program via a CSV-less list) ---
if admin_menu == "Manage Programs":
    st.header("Manage Programs")
    programs = sorted(kids_df["program"].dropna().unique().tolist())
    st.write("Existing programs:", programs if programs else "— none —")
    with st.form("add_program"):
        new_prog = st.text_input("Add new program name")
        addp = st.form_submit_button("Add program")
        if addp and new_prog.strip():
            st.success(f"Program '{new_prog.strip()}' added — you can now assign it to kids or leaders.")
            progs_file = "programs.csv"
            if not os.path.exists(progs_file):
                pd.DataFrame(columns=["program"]).to_csv(progs_file, index=False)
            progs = pd.read_csv(progs_file)
            if new_prog.strip() not in progs["program"].values:
                progs = pd.concat([progs, pd.DataFrame([{"program":new_prog.strip()}])], ignore_index=True)
                progs.to_csv(progs_file, index=False)
    st.stop()

# --- Manage Users (Admin) ---
if admin_menu == "Manage Users":
    st.header("Manage Users (Admin)")
    st.subheader("Existing users")
    st.dataframe(users_df[["username","role","program","name"]].rename(columns={"username":"Username","role":"Role","program":"Program","name":"Full name"}))
    st.subheader("Create a program leader")
    with st.form("create_leader"):
        uname = st.text_input("Username")
        fullname = st.text_input("Full name")
        pwd = st.text_input("Password")
        assign_prog = st.text_input("Assign program (exact name)")
        submitted = st.form_submit_button("Create leader")
        if submitted:
            if not (uname and pwd and assign_prog):
                st.error("Fill username, password and program")
            else:
                ok = add_user(uname, pwd, "leader", program=assign_prog, name=fullname)
                if ok:
                    st.success(f"Leader '{uname}' created for program '{assign_prog}'")
    st.stop()

# --- Programs list (from programs.csv or kids) ---
progs_file = "programs.csv"
programs = []
if os.path.exists(progs_file):
    try:
        programs = pd.read_csv(progs_file)["program"].dropna().unique().tolist()
    except:
        programs = []
programs = sorted(list(set(programs + kids_df["program"].dropna().unique().tolist())))

# --- Dashboard ---
if menu == "Dashboard":
    st.header("Dashboard")
    st.write("Quick overview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total kids", kids_df.shape[0])
    c2.metric("Attendance records", att_df.shape[0])
    c3.metric("Programs", len(programs))
    st.markdown("---")
    st.subheader("Recent attendance")
    if att_df.empty:
        st.write("No attendance yet.")
    else:
        show = att_df.sort_values("timestamp", ascending=False).head(20)
        merged = show.merge(kids_df, left_on="kid_id", right_on="id", how="left")
        st.dataframe(merged[["timestamp","date","name","program","marked_by","present","note"]].rename(columns={ "timestamp":"When","date":"Date","name":"Kid","program":"Program","marked_by":"Marked by","present":"Present","note":"Note"}))

# --- Kids management ---
elif menu == "Kids":
    st.header("Kids Management")
    st.subheader("Add a kid")
    with st.form("add_kid_form"):
        kname = st.text_input("Full name")
        kage = st.number_input("Age", min_value=1, max_value=30, value=6)
        kgender = st.selectbox("Gender", ["Male","Female","Other"])
        if role == "admin":
            kprogram = st.selectbox("Program", [""] + programs) if programs else st.text_input("Program")
        else:
            st.write(f"You are leader for program: **{user_program}**")
            kprogram = user_program
        kimage = st.file_uploader("Profile picture (optional)", type=["png","jpg","jpeg"], key="img_uploader")
        submitted = st.form_submit_button("Add kid")
        if submitted:
            if not kname.strip():
                st.error("Enter a name")
            else:
                add_kid(kname.strip(), kage, kgender, kprogram, kimage)
                st.success("Kid added")
                st.rerun()

    st.markdown("---")
    st.subheader("All kids")
    if role == "admin":
        df_show = kids_df.copy()
    else:
        df_show = kids_df[kids_df["program"]==user_program]
    if df_show.empty:
        st.info("No kids in this view.")
    else:
        for _, r in df_show.iterrows():
            cols = st.columns([1,3,6,2])
            with cols[0]:
                if r["image_path"] and os.path.exists(r["image_path"]):
                    st.image(r["image_path"], width=80)
                else:
                    st.write("🧒")
            with cols[1]:
                st.markdown(f"**{r['name']}**")
            with cols[1]:
                st.write(f"Age: {r['age']} • {r['gender']}")
            with cols[2]:
                st.write(f"Program: **{r['program']}**")
                present, pct = attendance_stats_for(r["id"], att_df)
                st.write(f"Present days: {present} — Attendance: {pct}%")
            with cols[3]:
                if st.button(f"View|{r['id']}", key=f"view_{r['id']}"):
                    st.session_state.selected_kid = r['id']
                    st.rerun()
        st.markdown("---")
        st.write("You can manage kids by selecting their profile from the list above. To remove or edit, open their profile.")

# --- Attendance ---
elif menu == "Attendance":
    st.header("Mark Attendance")
    att_date = st.date_input("Date", value=date.today())
    att_str = att_date.isoformat()
    if role == "admin":
        scope_df = kids_df.copy()
        prog_filter = st.selectbox("Filter by program", ["-- All --"] + programs)
        if prog_filter != "-- All --":
            scope_df = scope_df[scope_df["program"]==prog_filter]
    else:
        scope_df = kids_df[kids_df["program"]==user_program]

    if scope_df.empty:
        st.info("No kids to mark for your selection.")
    else:
        st.subheader(f"Mark attendance for {len(scope_df)} kids ({'All programs' if role=='admin' else user_program})")
        existing = att_df[att_df["date"]==att_str]
        present_defaults = {row["kid_id"]: int(row["present"])==1 for _,row in existing.iterrows()}
        notes_defaults = {row["kid_id"]: row.get("note","") for _,row in existing.iterrows()}

        with st.form("mark_form"):
            checkboxes = {}
            notes = {}
            for _, kid in scope_df.iterrows():
                cols = st.columns([1,4,3])
                with cols[0]:
                    checked = st.checkbox("", value=present_defaults.get(kid["id"], False), key=f"chk_{kid['id']}")
                with cols[1]:
                    st.markdown(f"**{kid['name']}**")
                    st.write(f"Program: {kid['program']}")
                with cols[2]:
                    n = st.text_input("Note", value=notes_defaults.get(kid["id"], ""), key=f"note_{kid['id']}")
                    notes[kid["id"]] = n
                checkboxes[kid["id"]] = checked
            if st.form_submit_button("Save attendance"):
                new_att = att_df[att_df["date"]!=att_str]
                now = datetime.now().isoformat(timespec="seconds")
                for kid_id, checked in checkboxes.items():
                    kid_prog = kids_df[kids_df["id"]==kid_id]["program"].values[0] if not kids_df.empty else ""
                    row = {"date":att_str, "kid_id":kid_id, "present":1 if checked else 0, "note": notes.get(kid_id,""), "program": kid_prog, "marked_by": username, "timestamp": now}
                    new_att = pd.concat([new_att, pd.DataFrame([row])], ignore_index=True)
                save_att(new_att)
                st.success("Attendance saved.")
                st.rerun()

# --- Child Profile view ---
elif menu == "Child Profile":
    st.header("Child Profile")
    selected = st.session_state.get("selected_kid", None)
    if selected is None:
        st.info("Select a kid from the 'Kids' list to view their profile.")
    else:
        kid = kids_df[kids_df["id"]==selected].iloc[0]
        # access check: leader cannot view kids outside their program
        if role=="leader" and kid["program"]!=user_program:
            st.error("You don't have access to this child's profile.")
        else:
            cols = st.columns([1,2,4])
            with cols[0]:
                if kid["image_path"] and os.path.exists(kid["image_path"]):
                    st.image(kid["image_path"], width=160)
                else:
                    st.write("No image")
            with cols[1]:
                st.subheader(kid["name"])
                st.write(f"Age: {kid['age']}")
                st.write(f"Gender: {kid['gender']}")
                st.write(f"Program: {kid['program']}")
                if role in ("admin","leader"):
                    if st.button("Edit kid"):
                        st.session_state.edit_kid = kid["id"]
                        st.rerun()
            with cols[2]:
                kid_att = att_df[att_df["kid_id"]==kid["id"]].sort_values("date", ascending=False)
                present_days = kid_att[kid_att["present"]==1].shape[0]
                total_days = kid_att["date"].nunique()
                pct = (present_days/total_days*100) if total_days>0 else 0.0
                st.markdown("**Attendance summary**")
                st.write(f"Total records: {kid_att.shape[0]}")
                st.write(f"Days present: {present_days}")
                st.write(f"Attendance % (program days): {pct:.1f}%")
                st.markdown("---")
                st.subheader("Attendance history")
                if kid_att.empty:
                    st.write("No attendance records yet.")
                else:
                    display = kid_att.merge(kids_df[["id","name"]], left_on="kid_id", right_on="id", how="left")
                    display = display[["date","present","note","marked_by","timestamp"]].rename(columns={"date":"Date","present":"Present","note":"Note","marked_by":"Marked by","timestamp":"When"})
                    display["Present"] = display["Present"].apply(lambda x: "Yes" if int(x)==1 else "No")
                    st.dataframe(display)

# --- Export ---
elif menu == "Export":
    st.header("Export CSVs")
    st.write("Download the app CSVs for backup or inspection.")
    for fn, label in [(USERS_CSV,"users.csv"), (KIDS_CSV,"kids.csv"), (ATT_CSV,"attendance.csv"), ("programs.csv","programs.csv")]:
        if os.path.exists(fn):
            with open(fn, "rb") as f:
                st.download_button(label, f, file_name=label)

# --- Edit kid modal simple ---
if st.session_state.get("edit_kid", None):
    kid_id = st.session_state.get("edit_kid")
    kids = load_kids()
    if kid_id in kids["id"].values:
        kid = kids[kids["id"]==kid_id].iloc[0]
        st.markdown("---")
        st.header("Edit kid")
        with st.form("edit_kid_form"):
            ename = st.text_input("Name", value=kid["name"])
            eage = st.number_input("Age", min_value=1, max_value=30, value=int(kid["age"]))
            egender = st.selectbox("Gender", ["Male","Female","Other"], index=["Male","Female","Other"].index(kid["gender"]) if kid["gender"] in ["Male","Female","Other"] else 2)
            if role == "admin":
                eprogram = st.selectbox("Program", [""]+programs, index=(0 if kid["program"]=="" else (programs.index(kid["program"]) if kid["program"] in programs else 0)))
            else:
                eprogram = kid["program"]
                st.write(f"Program: {eprogram}")
            eimage = st.file_uploader("Replace profile image (optional)", type=["png","jpg","jpeg"], key="edit_img")
            if st.form_submit_button("Save changes"):
                # save image if any
                image_path = kid["image_path"]
                if eimage is not None:
                    ext = os.path.splitext(eimage.name)[1]
                    safe_name = "".join([c for c in ename if c.isalnum() or c in (" ", "_")]).strip().replace(" ","_")
                    image_path = os.path.join(IMAGES_DIR, f"{safe_name}_{kid_id}{ext}")
                    with open(image_path, "wb") as f:
                        f.write(eimage.getbuffer())
                kids.loc[kids["id"]==kid_id, ["name","age","gender","program","image_path"]] = [ename, int(eage), egender, eprogram, image_path]
                save_kids(kids)
                st.success("Kid updated.")
                del st.session_state["edit_kid"]
                st.rerun()
    else:
        st.error("Kid not found.")
