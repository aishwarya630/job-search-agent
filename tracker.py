def is_real_job_url(url):
    """Only track real job URLs, not hallucinated ones"""
    if not url or "123456" in url:
        return False
    if not url.startswith("https://"):
        return False
    return True

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
        key = job.get('apply_url', f"{job['title']}-{job['company']}")
        if not is_real_job_url(key):
            print(f"  Skipping suspected hallucinated URL: {key[:60]}")
            continue
        if key not in seen:
            new_jobs.append(job)
            seen[key] = now

    save_seen_jobs(seen)
    return new_jobs