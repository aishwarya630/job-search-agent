import os
import json
import gspread
import re
from datetime import datetime
from google.oauth2.service_account import Credentials
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Local Imports
from jobsearch import scrape_jobs, pre_install_driver
from matcher import match_jobs
from emailer import send_email
from resume import extract_resume_text
from tracker import filter_new_jobs
from config import JOB_KEYWORDS, LOCATIONS, RESUME_PATH, MIN_SCORE
from skill_tracker import track_missing_skills

load_dotenv()

def update_sheets(new_matches):
    """Pushes high-quality matches to Google Sheets with full AI analysis."""
    if not new_matches:
        return

    try:
        # 1. Setup Authentication
        creds_raw = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
        if not creds_raw:
            print("❌ ERROR: GCP_SERVICE_ACCOUNT_JSON not found in environment.")
            return

        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_json = json.loads(creds_raw)
        creds = Credentials.from_service_account_info(creds_json, scopes=scope)
        client = gspread.authorize(creds)
        
        # 2. Open the Sheet
        sheet_url = os.getenv("GSHEET_URL")
        if not sheet_url:
            print("❌ ERROR: GSHEET_URL not found.")
            return
        sheet = client.open_by_url(sheet_url).sheet1
        
        new_rows = []
        for job in new_matches:
            # A: title, B: company, C: location, D: apply_url, E: score, 
            # F: what_fits, G: whats_missing, H: why_apply, I: visa_note, 
            # J: saved_at, K: status, L: applied_date, M: notes
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
                "Not Applied", # Status
                "",            # Applied Date
                ""             # Notes
            ])
        
        # 3. Batch Append
        if new_rows:
            sheet.append_rows(new_rows)
            print(f"✅ Google Sheets updated with {len(new_rows)} analyzed jobs.")
            
    except Exception as e:
        print(f"❌ Failed to update Google Sheets: {e}")

def search_and_match(keyword, location, resume_text):
    """Scrapes and matches jobs for a specific keyword/location pair."""
    print(f"🔍 Starting search: [{keyword}] in [{location}]...") 
    
    try:
        jobs, logs = scrape_jobs(keyword, location)
        
        if not jobs: 
            print(f"⚠️  No raw jobs found for {keyword}")
            return keyword, location, [], "no_results", logs

        # This now checks Google Sheets via tracker.py
        new_jobs = filter_new_jobs(jobs)
        
        if not new_jobs: 
            print(f"⏭️  All {len(jobs)} jobs for {keyword} were already in your Google Sheet.")
            return keyword, location, [], "already_seen", logs

        print(f"✨ Analyzing {len(new_jobs)} NEW jobs for {keyword}...")
        
        # AI Logic inside matcher.py
        matched = match_jobs(new_jobs, resume_text)
        return keyword, location, matched, "ok", logs
        
    except Exception as e:
        print(f"❌ Error in search_and_match for {keyword}: {e}")
        return keyword, location, [], "error", [f"❌ Error: {str(e)}"]

def run():
    print("🚀 Starting Job Alert Agent...")
    
    # 1. Initialization
    pre_install_driver()
    resume_text = extract_resume_text(RESUME_PATH)
    
    all_jobs = []
    system_logs = []
    seen_urls = set()

    # 2. Multi-threaded Search
    tasks = [(kw, loc) for kw in JOB_KEYWORDS for loc in LOCATIONS]
    print(f"📋 Total Keyword/Location combinations to check: {len(tasks)}")
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        futures = {executor.submit(search_and_match, kw, loc, resume_text): (kw, loc) for kw, loc in tasks}

        for future in as_completed(futures):
            kw, loc = futures[future]
            try:
                keyword, location, new_jobs, status, logs = future.result()
                system_logs.extend(logs)
                
                if status == "ok":
                    for job in new_jobs:
                        url = job.get('apply_url')
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_jobs.append(job)
                
                print(f"✅ Finished {kw} | New matches found in this thread: {len(new_jobs)}")

            except Exception as e:
                print(f"❌ Critical error in thread for {kw}: {e}")

    # 3. Final Filtering and Export
    if all_jobs:
        # Sort by match quality
        all_jobs.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # Filter Senior Roles (Prevent spamming senior roles to a junior/mid dev)
        blacklist = ["senior", "lead", "staff", "principal", "manager", "director"]
        filtered = [j for j in all_jobs if not any(b in j.get("title", "").lower() for b in blacklist)]
        
        # Final Score Threshold
        high_score_matches = [j for j in filtered if j.get("score", 0) >= MIN_SCORE]

        if high_score_matches:
            update_sheets(high_score_matches) 
            track_missing_skills(high_score_matches)
            send_email(high_score_matches, system_logs)
            print(f"🎉 Run Complete: {len(high_score_matches)} high-quality matches saved to CRM.")
        else:
            print(f"📉 Found {len(filtered)} jobs, but none met your MIN_SCORE of {MIN_SCORE}.")
    else:
        print("ℹ️ No new matches found during this run.")

if __name__ == "__main__":
    run()
