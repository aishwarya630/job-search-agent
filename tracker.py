import gspread
import os
import json
from google.oauth2.service_account import Credentials

def filter_new_jobs(jobs):
    """Checks Google Sheets directly to see if jobs are duplicates."""
    if not jobs:
        return []

    # 1. Connect to Google Sheets
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_json = json.loads(os.getenv("GCP_SERVICE_ACCOUNT_JSON"))
    creds = Credentials.from_service_account_info(creds_json, scopes=scope)
    client = gspread.authorize(creds)
    
    sheet_url = os.getenv("GSHEET_URL")
    sheet = client.open_by_url(sheet_url).sheet1
    
    # 2. Get every URL currently in Column D (adjust if your URL is in a different column)
    # col_values(4) is Column D
    existing_urls = set(sheet.col_values(4)) 

    new_jobs = []
    for job in jobs:
        url = job.get("apply_url")
        
        # Validation
        if not url or "123456" in url or not url.startswith("https://"):
            continue
            
        # Check against Google Sheet data
        if url not in existing_urls:
            new_jobs.append(job)
            # Add to set immediately so duplicates within the SAME run are caught
            existing_urls.add(url) 

    return new_jobs
