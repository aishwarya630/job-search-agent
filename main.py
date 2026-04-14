import os
import json
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Local Imports 
from jobsearch import LinkedInJobCrawler  # Your buttery smooth class
from matcher import match_jobs
from emailer import send_email
from resume import extract_resume_text
from tracker import filter_new_jobs
from config import JOB_KEYWORDS, LOCATIONS, RESUME_PATH, MIN_SCORE

load_dotenv()

def update_sheets(new_matches):
    """Pushes high-quality matches to Google Sheets with AI analysis."""
    if not new_matches:
        return

    try:
        creds_raw = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
        if not creds_raw:
            print("❌ ERROR: GCP_SERVICE_ACCOUNT_JSON not found.")
            return

        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_json = json.loads(creds_raw)
        creds = Credentials.from_service_account_info(creds_json, scopes=scope)
        client = gspread.authorize(creds)
        
        sheet_url = os.getenv("GSHEET_URL")
        sheet = client.open_by_url(sheet_url).sheet1
        
        new_rows = []
        for job in new_matches:
            new_rows.append([
                job.get("title", "N/A"),
                job.get("company", "N/A"),
                job.get("location", "N/A"),
                job.get("url", ""), # Changed from apply_url to match crawler
                job.get("score", 0),
                job.get("what_fits", ""),
                job.get("whats_missing", ""),
                job.get("why_apply", ""),
                job.get("visa_note", ""),
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Not Applied", 
                "",            
                ""             
            ])
        
        if new_rows:
            sheet.append_rows(new_rows)
            print(f"✅ Google Sheets updated with {len(new_rows)} jobs.")
            
    except Exception as e:
        print(f"❌ Sheet Update Error: {e}")

def search_and_match(keyword, location, resume_text):
    """Uses the custom Selenium Crawler instead of Apify."""
    print(f"🔍 Starting search: [{keyword}] in [{location}]...") 
    
    # Initialize crawler for this specific run
    crawler = LinkedInJobCrawler()
    logs = []
    
    try:
        # Override the crawler's default URL with our current keyword/location
        # Note: LinkedIn uses %20 for spaces
        kw_encoded = keyword.replace(" ", "%20")
        loc_encoded = location.replace(" ", "%20")
        crawler.config['job_url'] = f"https://www.linkedin.com/jobs/search/?f_TPR=r3600&keywords={kw_encoded}&location={loc_encoded}"
        
        # 1. Scrape
        raw_jobs = crawler.scrape_linkedin_jobs()
        logs.append(f"ℹ️ Found {len(raw_jobs)} listings for {keyword}")

        if not raw_jobs:
            return keyword, location, [], "no_results", logs

        # 2. Filter against Google Sheets (tracker.py)
        # Note: Ensure tracker.py uses 'url' key to match your new crawler
        new_jobs = filter_new_jobs(raw_jobs)
        
        if not new_jobs:
            return keyword, location, [], "already_seen", logs

        # 3. AI Match
        print(f"✨ Analyzing {len(new_jobs)} NEW jobs for {keyword}...")
        matched = match_jobs(new_jobs, resume_text)
        
        return keyword, location, matched, "ok", logs
        
    except Exception as e:
        return keyword, location, [], "error", [f"❌ Error: {str(e)}"]
    finally:
        crawler.cleanup()

def run():
    print("🚀 Starting Job Alert Agent (Selenium Version)...")
    
    resume_text = extract_resume_text(RESUME_PATH)
    all_jobs = []
    system_logs = []
    seen_urls = set()

    tasks = [(kw, loc) for kw in JOB_KEYWORDS for loc in LOCATIONS]
    
    # We use max_workers=1 because Selenium is resource heavy and multiple 
    # browsers from one IP can trigger LinkedIn's security.
    with ThreadPoolExecutor(max_workers=1) as executor:
        futures = {executor.submit(search_and_match, kw, loc, resume_text): (kw, loc) for kw, loc in tasks}

        for future in as_completed(futures):
            kw, loc = futures[future]
            try:
                keyword, location, matched_batch, status, logs = future.result()
                system_logs.extend(logs)
                
                if status == "ok":
                    for job in matched_batch:
                        url = job.get('url')
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_jobs.append(job)
                
                print(f"✅ Finished {kw} | Matches: {len(matched_batch)}")
            except Exception as e:
                print(f"❌ Thread Error for {kw}: {e}")

    # Final Export
    if all_jobs:
        all_jobs.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        blacklist = ["senior", "lead", "staff", "principal", "manager", "director"]
        filtered = [j for j in all_jobs if not any(b in j.get("title", "").lower() for b in blacklist)]
        print(f"DEBUG: {len(all_jobs)} found, {len(filtered)} survived title blacklist.")
        high_score = [j for j in filtered if j.get("score", 0) >= MIN_SCORE]

        if high_score:
            update_sheets(high_score) 
            send_email(high_score, system_logs)
            print(f"🎉 Run Complete: {len(high_score)} jobs sent.")
    else:
        print("ℹ️ No new matches found.")

if __name__ == "__main__":
    run()