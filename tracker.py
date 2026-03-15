import json
import os
from datetime import datetime, timedelta

TRACKER_FILE = "seen_jobs.json"

def load_seen_jobs():
    if not os.path.exists(TRACKER_FILE):
        return {}
    with open(TRACKER_FILE, "r") as f:
        return json.load(f)

def save_seen_jobs(seen):
    with open(TRACKER_FILE, "w") as f:
        json.dump(seen, f, indent=2)

def cleanup_old_jobs(seen):
    """Remove jobs older than 7 days to keep file small"""
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    return {k: v for k, v in seen.items() if v >= cutoff}

def filter_new_jobs(jobs):
    # Guard against wrong input type
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
        key = job.get('apply_url', f"{job['title']}-{job['company']}")
        if key not in seen:
            new_jobs.append(job)
            seen[key] = now
    
    save_seen_jobs(seen)
    return new_jobs