import requests
from bs4 import BeautifulSoup
import json
import os
import time
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pathlib import Path

class LinkedInJobCrawler:
    def __init__(self, config_file=None):
        """Initialize the LinkedIn job crawler with configuration."""
        base_dir = Path.cwd() / "data"
        os.makedirs(base_dir, exist_ok=True)
        
        # Default configuration
        self.config = {
            'job_url': 'https://www.linkedin.com/jobs/search/?f_TPR=r3600&f_E=2%2C3&keywords=data%20engineer',
            'excluded_keywords': ['5+ years', '4+ years', 'manager', 'director', 'senior', 'lead', 'principal'],
            'user_agents': [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
            ]
        }
        
        self.driver = None

    def setup_driver(self):
        """Set up Selenium WebDriver for JavaScript rendering."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Change to False if you need to debug visually
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        user_agent = random.choice(self.config['user_agents'])
        chrome_options.add_argument(f"--user-agent={user_agent}")
        
        try:
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        except Exception as e:
            print(f"Error setting up Chrome driver: {e}")
            self.driver = webdriver.Chrome(options=chrome_options)

    def is_job_relevant(self, job_title):
        """Check if job title contains excluded keywords."""
        title_lower = job_title.lower()
        return not any(keyword.lower() in title_lower for keyword in self.config['excluded_keywords'])

    def scrape_linkedin_jobs(self):
        """Scrape job data from LinkedIn including full descriptions."""
        jobs = []
        try:
            if self.driver is None:
                self.setup_driver()
                
            print(f"🔍 Fetching LinkedIn jobs from: {self.config['job_url']}")
            self.driver.get(self.config['job_url'])
            
            # Initial wait for page load
            time.sleep(5)
            
            # Scroll to load more cards
            print("📜 Scrolling to load more listings...")
            for _ in range(2):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            # Find job cards using Selenium to enable interaction
            job_cards = self.driver.find_elements(By.CLASS_NAME, 'base-card')
            print(f"📊 Found {len(job_cards)} potential job cards.")
            
            for i in range(len(job_cards)):
                try:
                    # Re-find elements to avoid StaleElementReferenceException
                    current_cards = self.driver.find_elements(By.CLASS_NAME, 'base-card')
                    if i >= len(current_cards): break
                    card = current_cards[i]
                    
                    # 1. CLICK the card to reveal description in the right pane
                    self.driver.execute_script("arguments[0].click();", card)
                    time.sleep(random.uniform(2.0, 3.5)) # Give it time to load details

                    # 2. Extract Title and metadata from card
                    soup_card = BeautifulSoup(card.get_attribute('outerHTML'), 'html.parser')
                    title_element = soup_card.find('h3', class_='base-search-card__title')
                    
                    if not title_element: continue
                    title = title_element.text.strip()
                    
                    if not self.is_job_relevant(title):
                        continue

                    # 3. SCRAPE THE DESCRIPTION (Now loaded in the detail pane)
                    try:
                        # LinkedIn uses this class for the job details section
                        desc_box = self.driver.find_element(By.CLASS_NAME, "show-more-less-html__markup")
                        description_text = desc_box.text.strip()
                    except:
                        description_text = ""

                    company_element = soup_card.find('h4', class_='base-search-card__subtitle')
                    company = company_element.text.strip() if company_element else "Unknown"
                    
                    location_element = soup_card.find('span', class_='job-search-card__location')
                    location = location_element.text.strip() if location_element else "Unknown"
                    
                    link_element = soup_card.find('a', class_='base-card__full-link', href=True)
                    job_url = link_element['href'].split('?')[0] if link_element else ""
                    
                    if job_url and description_text:
                        jobs.append({
                            'title': title,
                            'company': company,
                            'location': location,
                            'url': job_url,
                            'description': description_text, # AI matching is now possible
                            'source': 'LinkedIn',
                            'scraped_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        print(f"✅ Scraped: {title} at {company}")
                    else:
                        print(f"⚠️ Skipped {title}: Missing URL or Description.")

                except Exception as e:
                    print(f"❌ Error extracting card {i}: {e}")
            
        except Exception as e:
            print(f"🚨 Scraper Error: {e}")
        
        return jobs

    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
                print("🔒 Browser closed.")
            except:
                pass
            self.driver = None

if __name__ == "__main__":
    crawler = LinkedInJobCrawler()
    try:
        results = crawler.scrape_linkedin_jobs()
        print(f"\n✨ Successfully scraped {len(results)} jobs with descriptions.")
    finally:
        crawler.cleanup()
