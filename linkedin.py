import asyncio
from linkedin_mcp_server.core import LinkedInScraper

async def _search(keyword, location):
    async with LinkedInScraper() as scraper:
        results = await scraper.search_jobs(
            keywords=keyword,
            location=location,
            date_posted="past_week",
            work_type="remote,hybrid",
            experience_level="entry,associate",
            max_pages=1
        )
        return str(results)

def search_linkedin_jobs(keyword, location):
    try:
        return asyncio.run(_search(keyword, location))
    except Exception as e:
        print(f"LinkedIn error: {e}")
        return None