import os
import json
import gspread # NEW: Add to requirements.txt
from datetime import datetime
from google.oauth2.service_account import Credentials # NEW
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# ... (Keep your other imports) ...

def update_sheets(new_matches):
    """Pushes high-quality matches directly to Google Sheets."""
    # 1. Setup Authentication from GitHub Secrets
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # Load JSON from environment variable (GitHub Secrets)
    creds_json = json.loads(os.getenv("GCP_SERVICE_ACCOUNT_JSON"))
    creds = Credentials.from_service_account_info(creds_json, scopes=scope)
    client = gspread.authorize(creds)
    
    # 2. Open the Sheet (Use your Sheet ID from the URL)
    sheet_url = os.getenv("GSHEET_URL") 
    sheet = client.open_by_url(sheet_url).sheet1 # Targets the first tab
    
    # 3. Get existing URLs to avoid duplicates
    existing_urls = sheet.col_values(4) # Column D is apply_url
    
    new_rows = []
    for job in new_matches:
        url = job.get("apply_url")
        if url not in existing_urls:
            # Match the column order: Title, Company, Location, URL, Status, Date, Score, Notes
            new_rows.append([
                job.get("title"),
                job.get("company"),
                job.get("location"),
                url,
                "Not Applied", # Default Status
                "",            # Date Applied (Empty)
                job.get("score"),
                ""             # Notes (Empty)
            ])
    
    # 4. Batch Append
    if new_rows:
        sheet.append_rows(new_rows)
        print(f"✅ Google Sheets updated with {len(new_rows)} new jobs.")
    else:
        print("ℹ️ No unique jobs to add to Sheets.")

# --- Update your run() function to call update_sheets instead of update_dashboard ---
def run():
    # ... (Keep your scraping logic) ...
    if high_score_matches:
        update_sheets(high_score_matches) # <--- Changed this
        track_missing_skills(high_score_matches)
        send_email(high_score_matches, system_logs)
    # ...
