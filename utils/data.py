import pandas as pd
import os

KIDS_CSV = "data/kids.csv"

def load_kids_from_csv():
    if os.path.exists(KIDS_CSV):
        return pd.read_csv(KIDS_CSV)
    else:
        return pd.DataFrame(columns=["Name", "Age", "Program"])

def save_kids_to_csv(df):
    df.to_csv(KIDS_CSV, index=False)

def import_kids_from_excel(excel_file):
    df = pd.read_excel(excel_file)
    save_kids_to_csv(df)
    return df

