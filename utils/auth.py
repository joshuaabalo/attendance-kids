import pandas as pd
import os

USERS_CSV = os.path.join("data","users.csv")

def load_users():
    if not os.path.exists(USERS_CSV) or os.stat(USERS_CSV).st_size == 0:
        # create default users if missing
        os.makedirs(os.path.dirname(USERS_CSV), exist_ok=True)
        df = pd.DataFrame([
            {"username":"admin","password":"123","role":"admin","program":"","full_name":"Administrator"},
            {"username":"leader1","password":"123","role":"leader","program":"Football Boys","full_name":"Leader One"}
        ])
        df.to_csv(USERS_CSV, index=False)
    try:
        return pd.read_csv(USERS_CSV, dtype=str).fillna("").to_dict(orient="records")
    except Exception:
        return []

def save_users(users):
    df = pd.DataFrame(users)
    os.makedirs(os.path.dirname(USERS_CSV), exist_ok=True)
    df.to_csv(USERS_CSV, index=False)

def login_user(username, password, role):
    users = load_users()
    for u in users:
        if str(u.get("username")) == str(username) and str(u.get("password")) == str(password) and str(u.get("role")).lower() == str(role).lower():
            # return user dict with programs list split by comma if present
            progs = str(u.get("program","") or "")
            programs = [p.strip() for p in progs.split(",") if p.strip()]
            return {"username":u.get("username"), "role":u.get("role"), "programs":programs, "full_name": u.get("full_name", u.get("username"))}
    return None

def change_password(username, new_password):
    users = load_users()
    changed = False
    for u in users:
        if u.get("username") == username:
            u["password"] = new_password
            changed = True
            break
    if changed:
        save_users(users)
    return changed
