import json
import os
from datetime import datetime, timedelta

SEEN_FILE = "seen_jobs.json"


def is_real_job_url(url):
    """Only track real job URLs, not hallucinated ones"""
    if not url or "123456" in url:
        return False
    if not url.startswith("https://"):
        return False
    return True


def load_seen_jobs():
    """Load previously seen jobs from file"""
    if not os.path.exists(SEEN_FILE):
        return {}
    try:
        with open(SEEN_FILE, "r") as f:
            return json.load(f)
    except Exception:
        # Corrupted file? Start fresh
        return {}


def save_seen_jobs(seen):
    """Save seen jobs to file"""
    try:
        with open(SEEN_FILE, "w") as f:
            json.dump(seen, f, indent=2)
    except Exception as e:
        print(f"Error saving seen jobs: {e}")


def cleanup_old_jobs(seen, days=7):
    """Remove jobs older than X days"""
    cutoff = datetime.now() - timedelta(days=days)
    cleaned = {}

    for key, timestamp in seen.items():
        try:
            job_time = datetime.fromisoformat(timestamp)
            if job_time > cutoff:
                cleaned[key] = timestamp
        except Exception:
            # Skip bad timestamps
            continue

    return cleaned


def filter_new_jobs(jobs):
    if not jobs:
        return []

    jobs = [j for j in jobs if isinstance(j, dict)]
    if not jobs:
        return []

    seen = load_seen_jobs()
    seen = cleanup_old_jobs(seen)

    new_jobs = []
    now = datetime.now().isoformat()

    for job in jobs:
        key = job.get("apply_url") or f"{job.get('title')}-{job.get('company')}"

        if not is_real_job_url(key):
            print(f"  Skipping suspected hallucinated URL: {str(key)[:60]}")
            continue

        if key not in seen:
            new_jobs.append(job)
            seen[key] = now

    save_seen_jobs(seen)
    return new_jobs
