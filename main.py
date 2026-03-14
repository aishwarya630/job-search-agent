from dotenv import load_dotenv
load_dotenv()

from jobsearch import search_jobs
from matcher import match_jobs
from emailer import send_email
from resume import extract_resume_text
from tracker import filter_new_jobs
from config import JOB_KEYWORDS, LOCATIONS, RESUME_PATH, MIN_SCORE
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from skill_tracker import track_missing_skills, get_skill_recommendations

def search_and_match(keyword, location, resume_text):
    """Single unit of work — search + match for one keyword/location pair"""
    print(f"  Starting: {keyword} in {location}...")
    jobs_text = search_jobs(keyword, location)

    if not jobs_text:
        return keyword, location, [], "blocked"

    matched = match_jobs(jobs_text, resume_text)

    if not matched:
        return keyword, location, [], "no_matches"

    new_only = filter_new_jobs(matched)
    return keyword, location, new_only, "ok"

def run():
    resume_text = extract_resume_text(RESUME_PATH)
    all_jobs = []
    seen = set()

    # Build all search tasks
    tasks = [(kw, loc) for kw in JOB_KEYWORDS for loc in LOCATIONS]
    print(f"Running {len(tasks)} searches in parallel...\n")

    # Run in parallel — 3 at a time to avoid rate limiting
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(search_and_match, kw, loc, resume_text): (kw, loc)
            for kw, loc in tasks
        }

        for future in as_completed(futures):
            keyword, location, new_jobs, status = future.result()

            if status == "blocked":
                print(f"  ⚠️  {keyword} in {location} — scraper blocked")
            elif status == "no_matches":
                print(f"  ℹ️  {keyword} in {location} — no matches above {MIN_SCORE}/10")
            else:
                print(f"  ✅ {keyword} in {location} — {len(new_jobs)} new matches")
                for job in new_jobs:
                    key = job.get('apply_url', f"{job['title']}-{job['company']}")
                    if key not in seen:
                        seen.add(key)
                        all_jobs.append(job)

    all_jobs.sort(key=lambda x: x["score"], reverse=True)
    print(f"\nTotal new matches: {len(all_jobs)}")

    # Track missing skills
    track_missing_skills(all_jobs)
    
    # Check for skill recommendations
    recommendations = get_skill_recommendations(threshold=5)
    if recommendations:
        print("\n📚 Skills appearing frequently in jobs you're missing:")
        for skill, count in recommendations[:10]:
            print(f"   {skill}: seen in {count} jobs")

    send_email(all_jobs)

if __name__ == "__main__":
    run()