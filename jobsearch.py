import httpx
import json
import time
import random
import re
from urllib.parse import quote

HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.google.com/",
        "DNT": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Accept-Language": "en-US,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.7",
        "Referer": "https://www.google.com/",
    }
]

def extract_jobs_from_json(html):
    """Extract job data from LinkedIn's embedded JSON"""
    jobs = []
    try:
        # LinkedIn embeds job data as JSON in the page
        pattern = r'"jobPostingId":"(\d+)".*?"title":"([^"]+)".*?"companyName":"([^"]+)".*?"formattedLocation":"([^"]+)"'
        matches = re.findall(pattern, html, re.DOTALL)
        for match in matches[:15]:
            job_id, title, company, location = match
            jobs.append({
                "job_id": job_id,
                "title": title,
                "company": company,
                "location": location,
                "url": f"https://www.linkedin.com/jobs/view/{job_id}/"
            })
    except Exception as e:
        print(f"  JSON extract error: {e}")
    return jobs

def get_job_description(job_id):
    """Fetch job description from LinkedIn public job page"""
    try:
        url = f"https://www.linkedin.com/jobs/view/{job_id}/"
        headers = random.choice(HEADERS_LIST)
        time.sleep(random.uniform(1.5, 3.0))
        
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            if response.status_code != 200:
                return ""
            
            html = response.text
            
            # Extract description from JSON-LD
            ld_match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
            if ld_match:
                data = json.loads(ld_match.group(1))
                desc = data.get("description", "")
                # Strip HTML tags
                desc = re.sub(r'<[^>]+>', ' ', desc)
                return desc[:1500].strip()
            
            # Fallback — look for description div
            desc_match = re.search(r'class="description__text[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
            if desc_match:
                text = re.sub(r'<[^>]+>', ' ', desc_match.group(1))
                return text[:1500].strip()
                
    except Exception as e:
        print(f"  Description fetch error for {job_id}: {e}")
    return ""

def search_jobs(keyword, location="United States"):
    """Search LinkedIn public job listings using direct HTTP requests"""
    try:
        keyword_encoded = quote(keyword)
        location_encoded = quote(location)
        
        # LinkedIn public jobs search — no login needed
        url = (
            f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            f"?keywords={keyword_encoded}"
            f"&location={location_encoded}"
            f"&f_TPR=900"  # past hour
            f"&f_E=2%2C3"    # entry + associate level
            f"&sortBy=DD"    # newest first
            f"&start=0"
        )
        
        headers = random.choice(HEADERS_LIST)
        time.sleep(random.uniform(2, 4))
        
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"  HTTP {response.status_code} for {keyword}")
            return None
        
        html = response.text
        
        # Parse job cards from LinkedIn's guest API response
        job_ids = re.findall(r'data-entity-urn="urn:li:jobPosting:(\d+)"', html)
        titles = re.findall(r'class="base-search-card__title"[^>]*>\s*([^<]+?)\s*</h3>', html)
        companies = re.findall(r'class="base-search-card__subtitle"[^>]*>.*?<a[^>]*>\s*([^<]+?)\s*</a>', html, re.DOTALL)
        locations = re.findall(r'class="job-search-card__location"[^>]*>\s*([^<]+?)\s*</span>', html)

        if not job_ids:
            print(f"  No jobs found for {keyword}")
            return None

        print(f"  Found {len(job_ids)} jobs for {keyword}")
        
        # Build jobs text with descriptions
        text = f"Job listings for '{keyword}' in '{location}':\n\n"
        
        for i, job_id in enumerate(job_ids[:10]):
            title = titles[i] if i < len(titles) else "Unknown Title"
            company = companies[i] if i < len(companies) else "Unknown Company"
            location_str = locations[i] if i < len(locations) else location
            job_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
            
            # Fetch full description
            description = get_job_description(job_id)
            
            text += f"Title: {title}\n"
            text += f"Company: {company}\n"
            text += f"Location: {location_str}\n"
            text += f"URL: {job_url}\n"
            text += f"Description: {description}\n\n"
            
        return text

    except Exception as e:
        print(f"  Search error: {e}")
        return None