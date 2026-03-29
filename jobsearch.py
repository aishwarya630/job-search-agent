import httpx
import re
import json
import time
import random
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

def parse_posted_time(time_str):
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
    Scrape Google Jobs for job listings.
    Returns list of job dicts — no AI involved.
    Google Jobs aggregates LinkedIn, Indeed, Glassdoor + company sites.
    """
    try:
        # Google Jobs search query
        query = f"{keyword} jobs in {location}"
        encoded_query = quote(query)

        url = f"https://www.google.com/search?q={encoded_query}&ibp=htl;jobs&htivrt=jobs&htidocid=&htiloc=&num=20"

        headers = random.choice(HEADERS_LIST)
        time.sleep(random.uniform(2, 4))

        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get(url, headers=headers)

        if response.status_code != 200:
            print(f"  HTTP {response.status_code} for {keyword}")
            return []

        html = response.text

        # Extract job data from Google's embedded JSON
        json_matches = re.findall(r'AF_initDataCallback\(({.*?})\)', html, re.DOTALL)

        jobs = []
        cutoff_time = datetime.now() - timedelta(hours=24)

        # Try to parse Google's job data
        for json_str in json_matches:
            try:
                # Find job posting arrays in the JSON
                titles = re.findall(r'"([^"]{5,80})"(?:,|\s*:\s*)"(?:Engineer|Developer|Analyst|Scientist|Manager|Architect)"', html)
                break
            except:
                continue

        # Fallback — extract from structured data on the page
        title_pattern = re.findall(r'class="BjJfJf[^"]*"[^>]*>([^<]+)<', html)
        company_pattern = re.findall(r'class="vNEEBe[^"]*"[^>]*>([^<]+)<', html)
        location_pattern = re.findall(r'class="Qk80Jf[^"]*"[^>]*>([^<]+)<', html)
        time_pattern = re.findall(r'class="LL4CDc[^"]*"[^>]*>([^<]+)<', html)

        if title_pattern:
            print(f"  Found {len(title_pattern)} jobs for '{keyword}' via Google Jobs")
            for i, title in enumerate(title_pattern[:10]):
                company = company_pattern[i].strip() if i < len(company_pattern) else "Unknown"
                location_str = location_pattern[i].strip() if i < len(location_pattern) else location
                time_str = time_pattern[i].strip() if i < len(time_pattern) else ""

                posted_time = parse_posted_time(time_str)
                if posted_time and posted_time < cutoff_time:
                    continue

                jobs.append({
                    "title": title.strip(),
                    "company": company,
                    "location": location_str,
                    "apply_url": f"https://www.google.com/search?q={quote(title+' '+company)}+jobs",
                    "description": "",
                    "posted": time_str,
                    "keyword": keyword
                })

        if not jobs:
            print(f"  No jobs found for '{keyword}' via Google Jobs — trying LinkedIn fallback")
            return _linkedin_fallback(keyword, location)

        print(f"  {len(jobs)} jobs for '{keyword}'")
        return jobs

    except Exception as e:
        print(f"  Search error: {e}")
        return _linkedin_fallback(keyword, location)

def _linkedin_fallback(keyword, location):
    """LinkedIn public job search as fallback"""
    try:
        from urllib.parse import quote
        keyword_encoded = quote(keyword)
        location_encoded = quote(location)

        url = (
            f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            f"?keywords={keyword_encoded}"
            f"&location={location_encoded}"
            f"&f_TPR=r86400"
            f"&sortBy=DD"
            f"&start=0"
        )

        headers = random.choice(HEADERS_LIST)
        time.sleep(random.uniform(2, 4))

        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get(url, headers=headers)

        if response.status_code != 200:
            return []

        html = response.text
        job_ids = re.findall(r'data-entity-urn="urn:li:jobPosting:(\d+)"', html)
        titles = re.findall(r'class="base-search-card__title"[^>]*>\s*([^<]+?)\s*</h3>', html)
        companies = re.findall(r'class="base-search-card__subtitle"[^>]*>.*?<a[^>]*>\s*([^<]+?)\s*</a>', html, re.DOTALL)
        locations = re.findall(r'class="job-search-card__location"[^>]*>\s*([^<]+?)\s*</span>', html)

        if not job_ids:
            return []

        jobs = []
        for i, job_id in enumerate(job_ids[:10]):
            title = titles[i].strip() if i < len(titles) else None
            company = companies[i].strip() if i < len(companies) else None
            location_str = locations[i].strip() if i < len(locations) else location

            if not title or not company:
                continue

            job_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
            jobs.append({
                "title": title,
                "company": company,
                "location": location_str,
                "apply_url": job_url,
                "description": "",
                "posted": "",
                "keyword": keyword
            })

        print(f"  LinkedIn fallback: {len(jobs)} jobs for '{keyword}'")
        return jobs

    except Exception as e:
        print(f"  LinkedIn fallback error: {e}")
        return []
