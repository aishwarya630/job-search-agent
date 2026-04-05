from dotenv import load_dotenv
load_dotenv()

from jobsearch import scrape_jobs
from matcher import match_jobs
from emailer import send_email
from resume import extract_resume_text
from tracker import filter_new_jobs
from config import JOB_KEYWORDS, LOCATIONS, RESUME_PATH, MIN_SCORE
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from skill_tracker import track_missing_skills, get_skill_recommendations

def search_and_match(keyword, location, resume_text):
    # Step 1 — scrape (Updated to receive logs)
    jobs, logs =  scrape_jobs(keyword, location)

    if not jobs:
        return keyword, location, [], "blocked", logs

    # Step 2 — deduplicate
    new_jobs = filter_new_jobs(jobs)
    if not new_jobs:
        return keyword, location, [], "already_seen", logs

    # Step 3 — AI matching
    matched = match_jobs(new_jobs, resume_text)
    if not matched:
        return keyword, location, [], "no_matches", logs

    return keyword, location, matched, "ok", logs

def run():
        resume_text = extract_resume_text(RESUME_PATH)
        all_jobs = []
        system_logs = []  # <--- Initialize logs here
        seen = set()

        tasks = [(kw, loc) for kw in JOB_KEYWORDS for loc in LOCATIONS]
        print(f"Running {len(tasks)} searches in parallel...\n")

        # Use 3 workers to stay under the radar
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(search_and_match, kw, loc, resume_text): (kw, loc)
                for kw, loc in tasks
            }

            for future in as_completed(futures):
                # 1. Update search_and_match to return logs (see below)
                keyword, location, new_jobs, status, logs = future.result()
                system_logs.extend(logs) # Collect logs from every thread

                if status == "blocked":
                    print(f"  ⚠️  {keyword} — scraper blocked")
                elif status == "already_seen":
                    print(f"  ⏭️  {keyword} — all jobs already seen")
                else:
                    print(f"  ✅ {keyword} — {len(new_jobs)} new matches")
                    for job in new_jobs:
                        # Deduplicate within this single run
                        url = job.get('apply_url', '')
                        if url not in seen:
                            seen.add(url)
                            all_jobs.append(job)

        all_jobs.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # Track skills before filtering by score
        track_missing_skills(all_jobs)
        
        # Filter for the email report
        high_score_matches = [j for j in all_jobs if j.get("score", 0) >= MIN_SCORE]
        
        print(f"\nTotal matches found: {len(all_jobs)}")
        print(f"High-quality matches (>{MIN_SCORE}): {len(high_score_matches)}")

        # Final step: Send the single unified email
        send_email(high_score_matches, system_logs)

if __name__ == "__main__":
    run()