import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Import your modules
from jobsearch import scrape_jobs, pre_install_driver
from matcher import match_jobs
from emailer import send_email
from resume import extract_resume_text
from tracker import filter_new_jobs
from config import JOB_KEYWORDS, LOCATIONS, RESUME_PATH, MIN_SCORE
from skill_tracker import track_missing_skills

load_dotenv()

def search_and_match(keyword, location, resume_text):
    try:
        # Step 1 — Scrape
        jobs, logs = scrape_jobs(keyword, location)

        if not jobs:
            return keyword, location, [], "blocked", logs

        # Step 2 — Deduplicate
        new_jobs = filter_new_jobs(jobs)
        if not new_jobs:
            return keyword, location, [], "already_seen", logs

        # Step 3 — AI Matching
        matched = match_jobs(new_jobs, resume_text)
        if not matched:
            return keyword, location, [], "no_matches", logs

        return keyword, location, matched, "ok", logs
    except Exception as e:
        return keyword, location, [], "error", [f"❌ Error: {str(e)}"]

def run():
    print("🚀 Starting Job Alert Agent...")
    
    # CRITICAL: Pre-install driver to prevent Race Condition on GitHub
    pre_install_driver()
    
    resume_text = extract_resume_text(RESUME_PATH)
    all_jobs = []
    system_logs = []
    seen = set()

    tasks = [(kw, loc) for kw in JOB_KEYWORDS for loc in LOCATIONS]
    print(f"Running {len(tasks)} searches in parallel (3 workers)...\n")

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(search_and_match, kw, loc, resume_text): (kw, loc)
            for kw, loc in tasks
        }

        for future in as_completed(futures):
            keyword, location, new_jobs, status, logs = future.result()
            system_logs.extend(logs)

            if status == "blocked":
                print(f"  ⚠️  {keyword} — scraper blocked")
            elif status == "already_seen":
                print(f"  ⏭️  {keyword} — all jobs already seen")
            elif status == "error":
                print(f"  ❌  {keyword} — crashed (Check Logs)")
            else:
                print(f"  ✅ {keyword} — {len(new_jobs)} new matches")
                for job in new_jobs:
                    url = job.get('apply_url', '')
                    if url not in seen:
                        seen.add(url)
                        all_jobs.append(job)

    # Final Processing
    if all_jobs:
        all_jobs.sort(key=lambda x: x.get("score", 0), reverse=True)
        track_missing_skills(all_jobs)
        
        high_score_matches = [j for j in all_jobs if j.get("score", 0) >= MIN_SCORE]
        
        print(f"\nTotal matches: {len(all_jobs)} | High-quality: {len(high_score_matches)}")
        send_email(high_score_matches, system_logs)
    else:
        print("\nℹ️ No new jobs found in this run.")

if __name__ == "__main__":
    run()