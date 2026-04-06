import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Global variable to store the driver path once installed
_driver_path = None

def pre_install_driver():
    """Download and install the driver once to prevent race conditions."""
    global _driver_path
    print("Downloaded/Updating Chrome Driver...")
    _driver_path = ChromeDriverManager().install()
    return _driver_path

def get_driver():
    global _driver_path
    options = Options()
    
    # GitHub Actions MUST be headless
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # If the path isn't set yet (local run), install it
    if not _driver_path:
        pre_install_driver()
        
    service = Service(_driver_path)
    return webdriver.Chrome(service=service, options=options)

def scrape_jobs(keyword, location):
    driver = get_driver()
    all_found = []
    logs = [f"Started search for {keyword} in {location}"]
    
    try:
        # --- LINKEDIN ---
        ln_url = f"https://www.linkedin.com/jobs/search/?keywords={keyword.replace(' ', '%20')}&location={location.replace(' ', '%20')}&f_TPR=r86400"
        driver.get(ln_url)
        time.sleep(5)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        ln_cards = soup.find_all('div', class_='base-card')
        for card in ln_cards[:8]:
            try:
                title = card.find('h3', class_='base-search-card__title').text.strip()
                company = card.find('h4', class_='base-search-card__subtitle').text.strip()
                link = card.find('a', class_='base-card__full-link')['href']
                all_found.append({
                    "title": title, "company": company, "apply_url": link,
                    "source": "LinkedIn", "location": location, "description": "Fresh LinkedIn Post"
                })
            except: continue

        # --- INDEED ---
        ind_url = f"https://www.indeed.com/jobs?q={keyword.replace(' ', '+')}&l={location.replace(' ', '+')}&fromage=1"
        driver.get(ind_url)
        time.sleep(5)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        ind_cards = soup.find_all('div', class_='job_seen_beacon')
        for card in ind_cards[:8]:
            try:
                title = card.find('h2', class_='jobTitle').text.strip()
                company = card.find('span', attrs={'data-testid': 'company-name'}).text.strip()
                all_found.append({
                    "title": title, "company": company, "apply_url": ind_url,
                    "source": "Indeed", "location": location, "description": "Fresh Indeed Post"
                })
            except: continue

    finally:
        driver.quit()
    
    logs.append(f"✅ Found {len(all_found)} raw jobs for {keyword}")
    return all_found, logs