import os
import json
import gspread
import streamlit as st  # <--- STREAMLIT IMPORT
from datetime import datetime
from google.oauth2.service_account import Credentials
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Local Imports 
from jobsearch import LinkedInJobCrawler 
from matcher import match_jobs
from emailer import send_email  # <--- EMAILER IMPORT
from tracker import filter_new_jobs
from config import JOB_KEYWORDS, LOCATIONS, MIN_SCORE
from profile import MY_PROFILE 

load_dotenv()

def update_sheets(new_matches):
    """Pushes high-quality matches to Google Sheets."""
    if not new_matches:
        return
    try:
        # STREAMLIT USAGE: Accessing secrets if you are deploying to Streamlit Cloud
        creds_raw = st.secrets.get("GCP_SERVICE_ACCOUNT_JSON") or os.getenv("GCP_SERVICE_ACCOUNT_JSON")
        
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_json = json.loads(creds_raw)
        creds = Credentials.from_service_account_info(creds_json, scopes=scope)
        client = gspread.authorize(creds)
        
        sheet_url = st.secrets.get("GSHEET_URL") or os.getenv("GSHEET_URL")
        sheet = client.open_by_url(sheet_url).sheet1
        
        new_rows = []
        for job in new_matches:
            new_rows.append([
                job.get("title", "N/A"),
                job.get("company", "N/A"),
                job.get("location", "N/A"),
                job.get("apply_url", ""), 
                job.get("score", 0),
                job.get("what_fits", ""),
                job.get("whats_missing", ""),
                job.get("why_apply", ""),
                job.get("visa_note", ""),
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Not Applied"
            ])
        
        if new_rows:
            sheet.append_rows(new_rows)
            print(f"✅ Google Sheets updated.")
    except Exception as e:
        print(f"❌ Sheet Update Error: {e}")

def search_and_match(keyword, location, profile_data):
    """The core logic for searching and matching."""
    crawler = LinkedInJobCrawler()
    try:
        kw_encoded = keyword.replace(" ", "%20")
        loc_encoded = location.replace(" ", "%20")
        crawler.config['job_url'] = f"https://www.linkedin.com/jobs/search/?f_TPR=r3600&keywords={kw_encoded}&location={loc_encoded}"
        
        raw_jobs = crawler.scrape_linkedin_jobs()
        new_jobs = filter_new_jobs(raw_jobs)
        
        if not new_jobs:
            return [], []

        matched = match_jobs(new_jobs, profile_data)
        return matched, [f"Found {len(matched)} for {keyword}"]
    finally:
        crawler.cleanup()

def run():
    # STREAMLIT USAGE: Creating a simple title if running as an app
    st.title("🚀 Job Alert Agent")
    st.write("Starting Deterministic Pipeline...")
    
    all_jobs = []
    system_logs = []

    tasks = [(kw, loc) for kw in JOB_KEYWORDS for loc in LOCATIONS]
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        futures = {executor.submit(search_and_match, kw, loc, MY_PROFILE): kw for kw, loc in tasks}

        for future in as_completed(futures):
            matched_batch, logs = future.result()
            all_jobs.extend(matched_batch)
            system_logs.extend(logs)

    if all_jobs:
        high_score = [j for j in all_jobs if j.get("score", 0) >= MIN_SCORE]

        if high_score:
            update_sheets(high_score) 
            
            # --- EMAILER USAGE ---
            # This sends the high-score matches to your inbox
            send_email(high_score, system_logs) 
            
            st.success(f"🎉 Run Complete: {len(high_score)} jobs sent.")
        else:
            st.info("ℹ️ No jobs met the MIN_SCORE threshold.")
    else:
        st.warning("ℹ️ No new jobs found.")

if __name__ == "__main__":
    run()
