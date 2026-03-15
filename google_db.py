import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

import streamlit as st
import os

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

def get_credentials():
    # Try reading from Streamlit Secrets (for Streamlit Cloud deployment)
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except Exception:
        pass
    
    # Fallback to local file
    if os.path.exists("service_account.json"):
        return ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    else:
        raise Exception("Google Credentials not found. Please provide 'service_account.json' locally or configure Streamlit Secrets 'gcp_service_account'.")

creds = get_credentials()

client = gspread.authorize(creds)

_sheet = None

def get_sheet():
    global _sheet
    if _sheet is None:
        try:
            _sheet = client.open("CUET_RESULTS").sheet1
        except gspread.exceptions.SpreadsheetNotFound:
            raise Exception("Spreadsheet 'CUET_RESULTS' not found. Make sure you shared it as 'Editor' with: cuet-db@rugged-practice-463007-n4.iam.gserviceaccount.com")
    return _sheet


def save_result(app_no, roll_no, name, marks):
    sheet = get_sheet()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sheet.append_row([
        app_no,
        roll_no,
        name,
        marks,
        timestamp
    ])