import pandas as pd
import os
import uuid

KIDS_CSV = os.path.join("data","kids.csv")
ATT_CSV = os.path.join("data","attendance.csv")

def ensure_csv(path, headers):
    if not os.path.exists(path) or os.stat(path).st_size == 0:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        pd.DataFrame(columns=headers).to_csv(path, index=False)

def load_kids():
    ensure_csv(KIDS_CSV, ["id","name","age","program","dob","gender","school","location","guardian_name","guardian_contact","relationship","image"])
    df = pd.read_csv(KIDS_CSV, dtype=str).fillna("")
    return df

def save_kids(df):
    os.makedirs(os.path.dirname(KIDS_CSV), exist_ok=True)
    df.to_csv(KIDS_CSV, index=False)

def add_kid_record(name, age, program, dob="", gender="", school="", location="", guardian_name="", guardian_contact="", relationship="", image=""):
    df = load_kids()
    kid_id = str(uuid.uuid4())[:8]
    row = {"id": kid_id, "name": name, "age": str(age), "program": program, "dob": dob, "gender": gender, "school": school, "location": location, "guardian_name": guardian_name, "guardian_contact": guardian_contact, "relationship": relationship, "image": image}
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save_kids(df)
    return kid_id

def load_attendance():
    ensure_csv(ATT_CSV, ["date","kid_id","present","note","program","marked_by","timestamp"])
    df = pd.read_csv(ATT_CSV, dtype=str).fillna("")
    return df

def save_attendance(df):
    os.makedirs(os.path.dirname(ATT_CSV), exist_ok=True)
    df.to_csv(ATT_CSV, index=False)
