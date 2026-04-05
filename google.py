import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time

def test_google_stealth():
    options = uc.ChromeOptions()
    # options.add_argument("--headless") 
    
    try:
        driver = uc.Chrome(options=options, version_main=146) 
        # Using your exact URL format
        url = "https://www.google.com/search?q=Cloud+Engineer+jobs+in+United+States&udm=8"
        driver.get(url)
        
        print("⏳ Waiting for Google Jobs Grid...")
        time.sleep(12) 
        
        # Look for all elements that contain "ago"
        time_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'ago')]")
        
        print(f"📊 Found {len(time_elements)} timestamps. Extracting parent data...\n")
        
        for time_el in time_elements[:8]:
            try:
                # We climb up 4 levels to find the "Big Box" containing everything
                # Google's job cards are usually deep, so we go high to grab the Title
                card = time_el.find_element(By.XPATH, "./../../../../..") 
                
                card_text = card.text
                lines = [line.strip() for line in card_text.split('\n') if line.strip()]
                
                # In this view (udm=8):
                # Usually: Title is the first line, Company is the second
                if len(lines) >= 2:
                    job_title = lines[0]
                    company = lines[1]
                    # Check if the first line is actually a title (not a date)
                    if "ago" in job_title.lower() and len(lines) > 2:
                        job_title = lines[1]
                        company = lines[2]

                    print(f"✅ Job: {job_title}")
                    print(f"🏢 Co:  {company}")
                    print(f"🕒 Time: {time_el.text}")
                    print("-" * 30)
            except:
                continue

        driver.quit()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_google_stealth()