import pandas as pd

USERS_CSV = "data/users.csv"

def load_users():
    try:
        return pd.read_csv(USERS_CSV).to_dict(orient="records")
    except FileNotFoundError:
        # Default users (password = 123)
        default_users = [
            {"username": "admin", "password": "123", "role": "Admin"},
            {"username": "leader1", "password": "123", "role": "Leader"}
        ]
        pd.DataFrame(default_users).to_csv(USERS_CSV, index=False)
        return default_users

def login_user(username, password, role):
    users = load_users()
    for user in users:
        if user["username"] == username and user["password"] == password and user["role"] == role:
            return True
    return False

