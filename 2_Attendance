import streamlit as st
import pandas as pd
from datetime import date, datetime
from utils.data import load_kids, load_attendance, save_attendance

def run():
    st.title("Daily Attendance")

    if "user" not in st.session_state or not st.session_state.user:
        st.warning("Please log in first.")
        st.stop()

    user = st.session_state.user
    kids = load_kids()

    # Scope for leader
    if user["role"].lower() == "leader":
        allowed = user.get("programs", [])
        kids = kids[kids["program"].isin(allowed)]

    if kids.empty:
        st.info("No kids in scope.")
        st.stop()

    today = date.today().isoformat()
    st.subheader(f"Mark attendance for {today}")

    att = load_attendance()
    existing = att[att["date"] == today]
    present_defaults = {row["kid_id"]:(row["present"]=="1") for _,row in existing.iterrows()}
    notes_defaults = {row["kid_id"]: row.get("note","") for _,row in existing.iterrows()}

    checked = {}
    notes = {}
    for _, k in kids.sort_values("name").iterrows():
        cols = st.columns([1,4,3])
        with cols[0]:
            val = st.checkbox("", value=present_defaults.get(k["id"], False), key=f"chk_{k['id']}")
        with cols[1]:
            st.markdown(f"**{k['name']}**")
            st.write(f"Program: {k['program']}")
        with cols[2]:
            note = st.text_input("Note", value=notes_defaults.get(k["id"], ""), key=f"note_{k['id']}")
        checked[k["id"]] = val
        notes[k["id"]] = note

    if st.button("Save attendance", key="save_attendance_btn"):
        new_att = att[att["date"] != today]
        now = datetime.now().isoformat(timespec="seconds")
        for kid_id, is_present in checked.items():
            kid_prog = kids[kids["id"] == kid_id]["program"].values[0] if not kids.empty else ""
            row = {"date": today, "kid_id": kid_id, "present": "1" if is_present else "0", "note": notes.get(kid_id,""), "program": kid_prog, "marked_by": user["username"], "timestamp": now}
            new_att = pd.concat([new_att, pd.DataFrame([row])], ignore_index=True)
        save_attendance(new_att)
        st.success("Attendance saved.")
        st.experimental_rerun()

if __name__ == "__main__":
    run()
