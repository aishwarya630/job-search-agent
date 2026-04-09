import os
import json
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Local Imports
from jobsearch import scrape_jobs, pre_install_driver
from matcher import match_jobs
from emailer import send_email
from resume import extract_resume_text
from tracker import filter_new_jobs  # This now checks Google Sheets
from config import JOB_KEYWORDS, LOCATIONS, RESUME_PATH, MIN_SCORE
from skill_tracker import track_missing_skills

load_dotenv()

def update_sheets(new_matches):
    """Pushes high-quality matches directly to Google Sheets."""
    if not new_matches:
        return

    try:
        # 1. Setup Authentication from GitHub Secrets
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # Ensure your Secret Name in GitHub matches this env variable
        creds_json = json.loads(os.getenv("GCP_SERVICE_ACCOUNT_JSON"))
        creds = Credentials.from_service_account_info(creds_json, scopes=scope)
        client = gspread.authorize(creds)
        
        # 2. Open the Sheet using the URL in your Secrets
        sheet_url = os.getenv("GSHEET_URL") 
        sheet = client.open_by_url(sheet_url).sheet1
        
        new_rows = []
        for job in new_matches:
            # Match the Google Sheet column order: 
            # A: title, B: company, C: location, D: apply_url, E: status, F: applied_date, G: score, H: notes
            new_rows.append([
                job.get("title"),
                job.get("company"),
                job.get("location"),
                job.get("apply_url"),
                "Not Applied",  # Default status for new jobs
                "",             # applied_date starts empty
                job.get("score"),
                ""              # notes starts empty
            ])
        
        # 3. Batch Append to minimize API calls
        if new_rows:
            sheet.append_rows(new_rows)
            print(f"✅ Google Sheets updated with {len(new_rows)} new jobs.")
            
    except Exception as e:
        print(f"❌ Failed to update Google Sheets: {e}")

def search_and_match(keyword, location, resume_text):
    """Scrapes and matches jobs for a specific keyword/location pair."""
    # ADDED: Clear start log
    print(f"🔍 Starting search: [{keyword}] in [{location}]...") 
    
    try:
        jobs, logs = scrape_jobs(keyword, location)
        
        if not jobs: 
            print(f"⚠️  No raw jobs found for {keyword}")
            return keyword, location, [], "no_results", logs

        print(f"Found {len(jobs)} raw results for {keyword}. Checking for duplicates...")

        # This checks the Google Sheet
        new_jobs = filter_new_jobs(jobs)
        
        if not new_jobs: 
            print(f"⏭️  All {len(jobs)} jobs for {keyword} were already in your Google Sheet.")
            return keyword, location, [], "already_seen", logs

        print(f"✨ {len(new_jobs)} NEW jobs to analyze for {keyword}...")
        
        matched = match_jobs(new_jobs, resume_text)
        return keyword, location, matched, "ok", logs
        
    except Exception as e:
        print(f"❌ Error in search_and_match for {keyword}: {e}")
        return keyword, location, [], "error", [f"❌ Error: {str(e)}"]

def run():
    print("🚀 Starting Job Alert Agent...")
    pre_install_driver()
    resume_text = extract_resume_text(RESUME_PATH)
    
    all_jobs = []
    system_logs = []
    seen_urls = set()

    tasks = [(kw, loc) for kw in JOB_KEYWORDS for loc in LOCATIONS]
    print(f"📋 Total Keyword/Location combinations to check: {len(tasks)}")
    
    # We use a loop or ThreadPool. If workers=1, it's basically a sequential loop.
    with ThreadPoolExecutor(max_workers=1) as executor:
        futures = {executor.submit(search_and_match, kw, loc, resume_text): (kw, loc) for kw, loc in tasks}

        for future in as_completed(futures):
            kw, loc = futures[future]
            try:
                # This line waits for the individual search to finish
                keyword, location, new_jobs, status, logs = future.result()
                system_logs.extend(logs)
                
                if status == "ok":
                    for job in new_jobs:
                        url = job.get('apply_url')
                        # Internal de-duplication (in case different keywords find the same job)
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_jobs.append(job)
                
                print(f"✅ Finished {kw} | Total new jobs found so far: {len(all_jobs)}")

            except Exception as e:
                print(f"❌ Critical error in thread for {kw}: {e}")

    # --- AFTER THE LOOP ---
    if all_jobs:
        print(f"📊 Final processing for {len(all_jobs)} jobs...")
        
        # 1. Basic Cleaning & Sorting
        all_jobs.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # 2. Filtering Senior Roles (Double check this isn't too strict!)
        blacklist = ["senior", "lead", "staff", "principal", "manager", "director"]
        filtered = [j for j in all_jobs if not any(b in j.get("title", "").lower() for b in blacklist)]
        
        print(f"Filtered out {len(all_jobs) - len(filtered)} senior roles.")

        # 3. Apply Minimum Score Threshold
        high_score_matches = [j for j in filtered if j.get("score", 0) >= MIN_SCORE]

        if high_score_matches:
            update_sheets(high_score_matches) 
            track_missing_skills(high_score_matches)
            send_email(high_score_matches, system_logs)
            print(f"🎉 Run Complete: {len(high_score_matches)} high-quality matches saved!")
        else:
            print(f"📉 Found {len(filtered)} jobs, but none met the score threshold of {MIN_SCORE}.")
    else:
        print("ℹ️ No new matches found during this run. (Either nothing new on LinkedIn or all are duplicates).")
if __name__ == "__main__":
    run()
