import json
import os
from datetime import datetime, timedelta
from collections import Counter

SKILL_TRACKER_FILE = "skill_gaps.json"

def load_skill_gaps():
    if not os.path.exists(SKILL_TRACKER_FILE):
        return {}
    with open(SKILL_TRACKER_FILE, "r") as f:
        return json.load(f)

def save_skill_gaps(data):
    with open(SKILL_TRACKER_FILE, "w") as f:
        json.dump(data, f, indent=2)

def track_missing_skills(jobs):
    """Extract and count missing skills from matched jobs"""
    data = load_skill_gaps()
    today = datetime.now().strftime("%Y-%m-%d")

    for job in jobs:
        missing = job.get("whats_missing", "")
        if not missing or missing.lower() in ["none", "nothing", "n/a", "not mentioned"]:
            continue

        # Split by comma, semicolon or "and"
        skills = [s.strip() for s in missing.replace(";", ",").replace(" and ", ",").split(",")]
        
        for skill in skills:
            skill = skill.strip().lower()
            if len(skill) < 3:
                continue
            if skill not in data:
                data[skill] = {"count": 0, "first_seen": today, "last_seen": today}
            data[skill]["count"] += 1
            data[skill]["last_seen"] = today

    save_skill_gaps(data)

def get_skill_recommendations(threshold=5):
    """Return skills that appear in more than threshold jobs"""
    data = load_skill_gaps()
    
    # Only look at last 30 days
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    recent = {k: v for k, v in data.items() if v["last_seen"] >= cutoff}
    
    # Sort by count
    sorted_skills = sorted(recent.items(), key=lambda x: x[1]["count"], reverse=True)
    recommendations = [(skill, info["count"]) for skill, info in sorted_skills if info["count"] >= threshold]
    
    return recommendations