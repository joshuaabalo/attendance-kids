import pandas as pd
import os

USERS_CSV = "data/users.csv"

def load_users():
    """Load users from CSV into a list of dicts."""
    if not os.path.exists(USERS_CSV):
        # Create a default file if it doesn't exist
        df = pd.DataFrame([
            {"username": "admin", "password": "123", "role": "admin", "program": ""},
            {"username": "leader1", "password": "123", "role": "leader", "program": "Sunday School"},
            {"username": "leader2", "password": "123", "role": "leader", "program": "Youth"}
        ])
        os.makedirs(os.path.dirname(USERS_CSV), exist_ok=True)
        df.to_csv(USERS_CSV, index=False)
    return pd.read_csv(USERS_CSV).to_dict(orient="records")


def save_users(users):
    """Save updated users list back to CSV."""
    pd.DataFrame(users).to_csv(USERS_CSV, index=False)


def login_user(username, password, role):
    """Check credentials and return user dict if valid."""
    users = load_users()
    for user in users:
        if (user["username"] == username 
            and str(user["password"]) == str(password) 
            and user["role"].lower() == role.lower()):
            return user
    return None


def change_password(username, new_password):
    """Update password for given username."""
    users = load_users()
    for user in users:
        if user["username"] == username:
            user["password"] = new_password
            break
    save_users(users)
    return True
