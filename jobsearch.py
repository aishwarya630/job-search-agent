import httpx
import re
import time
import random
import json
from datetime import datetime, timedelta
from urllib.parse import quote

HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.google.com/",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Accept-Language": "en-US,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.7",
        "Referer": "https://www.google.com/",
    }
]

def get_job_description(job_id):
    """Fetch full job description from LinkedIn job page"""
    try:
        url = f"https://www.linkedin.com/jobs/view/{job_id}/"
        headers = random.choice(HEADERS_LIST)
        time.sleep(random.uniform(1.5, 3.0))

        with httpx.Client(timeout=20, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            if response.status_code != 200:
                return ""
            html = response.text

            # Try JSON-LD first
            ld_match = re.search(
                r'<script type="application/ld\+json">(.*?)</script>',
                html, re.DOTALL
            )
            if ld_match:
                data = json.loads(ld_match.group(1))
                desc = data.get("description", "")
                desc = re.sub(r'<[^>]+>', ' ', desc)
                return desc[:2000].strip()

    except Exception as e:
        print(f"  Description error for {job_id}: {e}")
    return ""

def parse_posted_time(time_str):
    """Parse LinkedIn relative time string to datetime"""
    if not time_str:
        return None
    match = re.search(r'(\d+)\s*(minute|hour|day|week|month)', time_str, re.IGNORECASE)
    if match:
        value = int(match.group(1))
        unit = match.group(2).lower()
        if unit == "minute":
            return datetime.now() - timedelta(minutes=value)
        elif unit == "hour":
            return datetime.now() - timedelta(hours=value)
        elif unit == "day":
            return datetime.now() - timedelta(days=value)
        elif unit == "week":
            return datetime.now() - timedelta(weeks=value)
        elif unit == "month":
            return datetime.now() - timedelta(days=value * 30)
    return None

def search_jobs(keyword, location="United States"):
    """
    Scrape LinkedIn public job search.
    Returns a list of job dicts — no AI involved.
    """
    try:
        keyword_encoded = quote(keyword)
        location_encoded = quote(location)

        url = (
            f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            f"?keywords={keyword_encoded}"
            f"&location={location_encoded}"
            f"&f_TPR=r1800"
            f"&f_E=2%2C3"
            f"&sortBy=DD"
            f"&start=0"
        )

        headers = random.choice(HEADERS_LIST)
        time.sleep(random.uniform(2, 4))

        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get(url, headers=headers)

        if response.status_code != 200:
            print(f"  HTTP {response.status_code} for {keyword}")
            return []

        html = response.text

        # Extract job IDs
        job_ids = re.findall(r'data-entity-urn="urn:li:jobPosting:(\d+)"', html)

        # Extract titles
        titles = re.findall(
            r'class="base-search-card__title"[^>]*>\s*([^<]+?)\s*</h3>', html
        )

        # Extract companies
        companies = re.findall(
            r'class="base-search-card__subtitle"[^>]*>.*?<a[^>]*>\s*([^<]+?)\s*</a>',
            html, re.DOTALL
        )

        # Extract locations
        locations = re.findall(
            r'class="job-search-card__location"[^>]*>\s*([^<]+?)\s*</span>', html
        )

        # Extract posted times
        times = re.findall(
            r'class="job-search-card__listdate[^"]*"[^>]*>\s*([^<]+?)\s*</time>', html
        )

        if not job_ids:
            print(f"  No jobs found for '{keyword}'")
            return []

        print(f"  Found {len(job_ids)} jobs for '{keyword}'")

        jobs = []
        cutoff_time = datetime.now() - timedelta(minutes=30)

        for i, job_id in enumerate(job_ids[:10]):
            title = titles[i].strip() if i < len(titles) else None
            company = companies[i].strip() if i < len(companies) else None
            location_str = locations[i].strip() if i < len(locations) else location
            time_str = times[i].strip() if i < len(times) else ""

            if not title or not company:
                continue

            # Filter by posting time
            posted_time = parse_posted_time(time_str)
            if posted_time and posted_time < cutoff_time:
                print(f"  Skipping old job: {title} ({time_str})")
                continue

            job_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
            description = get_job_description(job_id)

            jobs.append({
                "job_id": job_id,
                "title": title,
                "company": company,
                "location": location_str,
                "apply_url": job_url,
                "description": description,
                "posted": time_str,
                "keyword": keyword
            })

        print(f"  {len(jobs)} jobs after time filter for '{keyword}'")
        return jobs

    except Exception as e:
        print(f"  Search error: {e}")
        return []