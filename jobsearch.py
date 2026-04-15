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
            jobs = []
            if self.driver is None:
                self.setup_driver()
    
            try:
                print(f"🔍 Fetching: {self.config['job_url']}")
                self.driver.get(self.config['job_url'])
                time.sleep(4)
    
                # --- POP-UP DISMISSAL ---
                try:
                    # Try to find the 'X' on a login modal if it exists
                    close_button = self.driver.find_element(By.XPATH, "//button[@aria-label='Dismiss']")
                    close_button.click()
                    print("🛡️ Dismissed LinkedIn login modal.")
                except:
                    pass
    
                # Scroll to load initial cards
                self.driver.execute_script("window.scrollTo(0, 500);")
                time.sleep(2)
    
                # Get initial count
                job_cards = self.driver.find_elements(By.CLASS_NAME, 'base-card')
                print(f"📊 Cards detected: {len(job_cards)}")
    
                for i in range(len(job_cards)):
                    try:
                        # RE-FETCH to avoid StaleElementReferenceException
                        current_cards = self.driver.find_elements(By.CLASS_NAME, 'base-card')
                        if i >= len(current_cards): break
                        card = current_cards[i]
    
                        # Scroll card into view
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
                        time.sleep(0.5)
    
                        # CLICK the card
                        try:
                            card.click()
                        except:
                            # Backup: JS Click if something is overlapping
                            self.driver.execute_script("arguments[0].click();", card)
    
                        # WAIT for the description to load
                        wait = WebDriverWait(self.driver, 5)
                        try:
                            # Targeted class for the description area
                            desc_selector = "show-more-less-html__markup"
                            wait.until(EC.presence_of_element_located((By.CLASS_NAME, desc_selector)))
                            description_element = self.driver.find_element(By.CLASS_NAME, desc_selector)
                            description_text = description_element.text.strip()
                        except TimeoutException:
                            print(f"⚠️ Skip {i}: Description didn't load in time.")
                            continue
    
                        # Metadata Extraction
                        soup_html = card.get_attribute('outerHTML')
                        # (Your existing parsing logic for title/company/url goes here)
                        # For speed, let's grab title and URL directly via Selenium:
                        title = card.find_element(By.CLASS_NAME, 'base-search-card__title').text.strip()
                        url = card.find_element(By.TAG_NAME, 'a').get_attribute('href').split('?')[0]
                        company = card.find_element(By.CLASS_NAME, 'base-search-card__subtitle').text.strip()
    
                        if description_text and url:
                            jobs.append({
                                'title': title,
                                'company': company,
                                'url': url,
                                'description': description_text,
                                'scraped_date': time.strftime("%Y-%m-%d %H:%M")
                            })
                            print(f"✅ Scraped: {title}")
    
                    except StaleElementReferenceException:
                        print(f"🔄 Stale element at card {i}, retrying...")
                        continue
                    except Exception as e:
                        print(f"❌ Card {i} error: {str(e)[:50]}")
                        continue
    
            except Exception as e:
                print(f"🚨 Critical Scraper Error: {e}")
            
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
