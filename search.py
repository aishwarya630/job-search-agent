import subprocess
import json
from config import JOB_KEYWORDS, LOCATIONS

def search_jobs():
    all_jobs = []
    seen_ids = set()

    for keyword in JOB_KEYWORDS:
        for location in LOCATIONS:
            print(f"Searching: {keyword} in {location}")
            # We'll call LinkedIn MCP via the Claude API in matcher.py
            # For now store the search params
            all_jobs.append({
                "keyword": keyword,
                "location": location
            })

    return all_jobs

if __name__ == "__main__":
    jobs = search_jobs()
    print(json.dumps(jobs, indent=2))