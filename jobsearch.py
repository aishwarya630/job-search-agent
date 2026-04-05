import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

def get_driver():
    options = Options()
    # options.add_argument("--headless") # Uncomment for GitHub Actions
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def scrape_jobs(keyword, location):
    driver = get_driver()
    all_found = []
    logs = []
    
    try:
        # --- 1. LINKEDIN ---
        print(f"🕵️ Searching LinkedIn: {keyword}")
        ln_url = f"https://www.linkedin.com/jobs/search/?keywords={keyword.replace(' ', '%20')}&location={location.replace(' ', '%20')}&f_TPR=r86400"
        driver.get(ln_url)
        time.sleep(5)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        ln_cards = soup.find_all('div', class_='base-card')
        for card in ln_cards[:10]:
            try:
                title = card.find('h3', class_='base-search-card__title').text.strip()
                company = card.find('h4', class_='base-search-card__subtitle').text.strip()
                link = card.find('a', class_='base-card__full-link')['href']
                all_found.append({
                    "title": title, "company": company, "apply_url": link,
                    "source": "LinkedIn", "location": location, "description": "LinkedIn Fresh"
                })
            except: continue
        logs.append(f"✅ LinkedIn: Found {len(all_found)} jobs")

        # --- 2. INDEED ---
        print(f"🕵️ Searching Indeed: {keyword}")
        ind_url = f"https://www.indeed.com/jobs?q={keyword.replace(' ', '+')}&l={location.replace(' ', '+')}&fromage=1"
        driver.get(ind_url)
        time.sleep(5)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        ind_cards = soup.find_all('div', class_='job_seen_beacon')
        ind_count = 0
        for card in ind_cards[:10]:
            try:
                title = card.find('h2', class_='jobTitle').text.strip()
                company = card.find('span', attrs={'data-testid': 'company-name'}).text.strip()
                all_found.append({
                    "title": title, "company": company, "apply_url": ind_url,
                    "source": "Indeed", "location": location, "description": "Indeed Fresh"
                })
                ind_count += 1
            except: continue
        logs.append(f"✅ Indeed: Found {ind_count} jobs")

    finally:
        driver.quit()
    
    return all_found, logs