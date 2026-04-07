import os
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

from jobsearch import scrape_jobs, pre_install_driver
from matcher import match_jobs
from emailer import send_email
from resume import extract_resume_text
from tracker import filter_new_jobs
from config import JOB_KEYWORDS, LOCATIONS, RESUME_PATH, MIN_SCORE
from skill_tracker import track_missing_skills

load_dotenv()

def update_dashboard(new_matches):
    """Saves high-quality matches to a persistent JSON file for the Streamlit dashboard."""
    file_path = "dashboard_data.json"
    dashboard_data = []
    
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                dashboard_data = json.load(f)
            except:
                dashboard_data = []

    existing_urls = {job.get("apply_url") for job in dashboard_data}
    
    for job in new_matches:
        if job.get("apply_url") not in existing_urls:
            job["saved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            dashboard_data.append(job)

    with open(file_path, "w") as f:
        json.dump(dashboard_data, f, indent=4)

def search_and_match(keyword, location, resume_text):
    try:
        jobs, logs = scrape_jobs(keyword, location)
        if not jobs: return keyword, location, [], "blocked", logs

        new_jobs = filter_new_jobs(jobs)
        if not new_jobs: return keyword, location, [], "already_seen", logs

        matched = match_jobs(new_jobs, resume_text)
        return keyword, location, matched, "ok", logs
    except Exception as e:
        return keyword, location, [], "error", [f"❌ Error: {str(e)}"]

def run():
    print("🚀 Starting Job Alert Agent...")
    pre_install_driver()
    resume_text = extract_resume_text(RESUME_PATH)
    
    all_jobs = []
    system_logs = []
    seen = set()

    tasks = [(kw, loc) for kw in JOB_KEYWORDS for loc in LOCATIONS]
    # Use 1 worker for absolute stability with AI API Rate Limits
    # Find this section in your main.py and replace it:
    with ThreadPoolExecutor(max_workers=1) as executor:
        futures = {}
        for kw, loc in tasks:
            # We explicitly pass the variables to the submit function
            job_task = executor.submit(search_and_match, kw, loc, resume_text)
            futures[job_task] = (kw, loc)

        for future in as_completed(futures):
            kw, loc = futures[future]  # Get the keywords back from the map
            try:
                keyword, location, new_jobs, status, logs = future.result()
                system_logs.extend(logs)
                
                if status == "ok":
                    for job in new_jobs:
                        if job.get('apply_url') not in seen:
                            seen.add(job.get('apply_url'))
                            all_jobs.append(job)
            except Exception as e:
                print(f"❌ Critical error in thread for {kw}: {e}")

    if all_jobs:
        # 1. Sort by score
        all_jobs.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # 2. Strict Blacklist (Manual Filter)
        blacklist = ["lead", "staff", "principal", "manager", "director"]
        filtered = [j for j in all_jobs if not any(b in j.get("title", "").lower() for b in blacklist)]
        
        # 3. Final thresholds
        high_score_matches = [j for j in filtered if j.get("score", 0) >= MIN_SCORE]

        if high_score_matches:
            update_dashboard(high_score_matches)
            track_missing_skills(high_score_matches)
            send_email(high_score_matches, system_logs)
            print(f"✅ Run Complete: {len(high_score_matches)} jobs sent.")
    else:
        print("ℹ️ No new matches found.")

if __name__ == "__main__":
    run()