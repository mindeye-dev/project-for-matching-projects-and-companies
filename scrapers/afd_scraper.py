import os
import time
import requests
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
import undetected_chromedriver as uc
from datetime import datetime

# --- Config ---
BACKEND_API = os.environ.get('BACKEND_API', 'http://localhost:5000/api/opportunity')
AFD_URL = 'https://www.afd.fr/en/projects/list'
PROXY_API_KEY = os.environ.get('PROXY_API_KEY', '')
SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK', '')
HEADLESS = os.environ.get('HEADLESS', '1') == '1'

# --- Logging ---
logging.basicConfig(
    filename='AFD_scraper.log', 
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s'
)

def get_cloud_proxy():
    if not PROXY_API_KEY:
        return None
    return f'{PROXY_API_KEY}@proxy-server.scraperapi.com:8001'

def notify_error(message):
    if SLACK_WEBHOOK:
        try:
            requests.post(SLACK_WEBHOOK, json={'text': message})
        except Exception as e:
            logging.error(f"Failed to send Slack notification: {e}")

def setup_driver(proxy=None):
    options = uc.ChromeOptions()
    if HEADLESS:
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--disable-blink-features=AutomationControlled")
    if proxy:
        options.add_argument(f'--proxy-server=http://{proxy}')
    driver = uc.Chrome(options=options)
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
    )
    return driver

def scrape_afd():
    """Main scraping function for Agence Française de Développement"""
    start_time = datetime.now()
    logging.info(f"Starting AFD scrape at {start_time}")
    
    page_num = 1
    total_opportunities = 0
    
    while True:
        proxy = get_cloud_proxy()
        driver = setup_driver(proxy)
        url = AFD_URL + f'?page={page_num}' if page_num > 1 else AFD_URL
        logging.info(f"Scraping AFD page {page_num} with proxy {proxy or 'none'}")
        
        try:
            driver.get(url)
            time.sleep(5)
            
            # Try different table selectors for AFD
            table = None
            try:
                table = driver.find_element(By.TAG_NAME, 'table')
            except Exception:
                try:
                    table = driver.find_element(By.CSS_SELECTOR, '.procurement-table, .opportunities-table')
                except Exception:
                    logging.info('No table found, ending pagination.')
                    break
            
            rows = table.find_elements(By.TAG_NAME, 'tr')[1:]
            if not rows:
                logging.info('No more rows found, ending pagination.')
                break
            
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, 'td')
                if len(cols) < 3:
                    continue
                
                opp = {
                    'project_name': cols[0].text.strip(),
                    'client': 'African Development Bank',
                    'country': cols[1].text.strip() if len(cols) > 1 else '',
                    'sector': cols[2].text.strip() if len(cols) > 2 else '',
                    'summary': '',
                    'deadline': cols[3].text.strip() if len(cols) > 3 else '',
                    'program': '',
                    'budget': '',
                    'url': AFD_URL
                }
                
                if not opp['project_name']:
                    continue
                
                logging.info(f"Submitting AFD: {opp['project_name']} ({opp['country']})")
                try:
                    r = requests.post(BACKEND_API, json=opp)
                    if r.status_code == 200:
                        total_opportunities += 1
                        logging.info(f'Submitted AFD: {r.status_code}')
                except Exception as e:
                    logging.error(f'Error submitting AFD: {e}')
                    notify_error(f'Error submitting AFD opportunity: {e}')
                time.sleep(1)
            
            next_btns = driver.find_elements(By.LINK_TEXT, 'Next')
            if next_btns and next_btns[0].is_enabled():
                page_num += 1
                driver.quit()
                continue
            else:
                logging.info('No next page button found, ending.')
                break
                
        except Exception as e:
            logging.error(f'Error scraping AFD table: {e}')
            notify_error(f'AFD scraper error: {e}')
            break
        driver.quit()
    
    end_time = datetime.now()
    duration = end_time - start_time
    logging.info(f"AFD scrape completed. Total opportunities: {total_opportunities}. Duration: {duration}")
    
    if total_opportunities > 0:
        notify_error(f"✅ AFD scrape completed successfully!\n"
                   f"📊 Opportunities found: {total_opportunities}\n"
                   f"⏱️ Duration: {duration}")

if __name__ == '__main__':
    scrape_afd() 