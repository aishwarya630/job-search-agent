from jobspy import scrape_jobs

def search_jobs(keyword, location="United States"):
    logs = []
    formatted_jobs = []
    try:
        jobs = scrape_jobs(
            site_name=["google", "indeed", "linkedin"], # Explicitly list all three
            search_term=keyword,
            location=location,
            results_wanted=15,
            hours_old=1,              # Your 15-minute window logic
            sorting="posted_at",      # Ensures we get the freshest ones
            country_around_canada=False,
            enforce_alignment=True    # Helps with Google Jobs precision
)
        
        if jobs.empty:
            logs.append(f"⚠️ No new jobs found for '{keyword}' in the last 15 mins.")
            return [], logs
            
        # ... (your existing formatting logic)
        logs.append(f"✅ Found {len(formatted_jobs)} jobs for '{keyword}'")
        return formatted_jobs, logs

    except Exception as e:
        error_msg = f"❌ Scraper Error for '{keyword}': {str(e)}"
        print(error_msg)
        return [], [error_msg]  