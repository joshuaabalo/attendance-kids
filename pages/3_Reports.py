import streamlit as st
import pandas as pd
from utils.data import load_attendance, load_kids
from datetime import date

def run():
    st.title("Attendance Reports")

    if "user" not in st.session_state or not st.session_state.user:
        st.warning("Please log in first.")
        st.stop()

    user = st.session_state.user
    att = load_attendance()
    kids = load_kids()

    if att.empty:
        st.info("No attendance records yet.")
        return

    # Leader scope
    if user["role"].lower() == "leader":
        allowed = user.get("programs", [])
        att = att[att["program"].isin(allowed)]

    dates = sorted(att["date"].unique(), reverse=True)
    selected = st.selectbox("Select date", dates, key="reports_date_select")
    daily = att[att["date"] == selected].merge(kids[["id","name"]], left_on="kid_id", right_on="id", how="left")
    daily["Present"] = daily["present"].apply(lambda x: "Yes" if str(x)=="1" else "No")
    st.subheader(f"Summary for {selected}")
    st.write(f"Records: {daily.shape[0]}")
    st.dataframe(daily[["name","program","Present","note","marked_by","timestamp"]].rename(columns={"name":"Kid"}))
    csv = daily.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, file_name=f"attendance_{selected}.csv", key="download_reports_btn")

if __name__ == "__main__":
    run()

