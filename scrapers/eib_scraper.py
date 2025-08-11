import os
import time
import requests
import logging
from openai import OpenAI
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
)


# --- Config ---
BACKEND_API = os.environ.get("BACKEND_API", "http://localhost:5000/api/opportunity")
EIB_URL = "https://www.eib.org/en/projects/pipelines/index.htm"
HEADLESS = os.environ.get("HEADLESS", "0") == "1"
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK", "")

# --- Logging ---
logging.basicConfig(
    filename="scraper.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(message)s",
)


def notify_error(message):
    if SLACK_WEBHOOK:
        try:
            requests.post(SLACK_WEBHOOK, json={"text": message})
        except Exception as e:
            logging.error(f"Failed to send Slack notification: {e}")



def setup_driver(proxy=None):
    options = FirefoxOptions()
    print("--setting up driver--1")
    if HEADLESS:
        options.add_argument("--headless")

    # Enhanced stealth settings
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)
    options.set_preference(
        "general.useragent.override",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )

    # Additional stealth preferences
    options.set_preference("dom.webnotifications.enabled", False)
    options.set_preference("media.volume_scale", "0.0")
    options.set_preference("network.proxy.type", 0)
    options.set_preference("privacy.resistFingerprinting", False)
    options.set_preference("browser.cache.disk.enable", False)
    options.set_preference("browser.cache.memory.enable", False)

    print("--setting up driver--2")

    # Create the Firefox driver
    driver = webdriver.Firefox(options=options)

    # Enhanced stealth: remove webdriver properties
    print("--setting up driver--3")
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: ()=> undefined})"
    )
    driver.execute_script(
        "Object.defineProperty(navigator, 'plugins', {get: ()=> [1, 2, 3, 4, 5]})"
    )
    driver.execute_script(
        "Object.defineProperty(navigator, 'languages', {get: ()=> ['en-US', 'en']})"
    )

    print("--setting up driver--4")
    return driver

def getOpenAIResponse(prompt, query):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Send a chat completion request
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # You can use "gpt-4o", "gpt-3.5-turbo", etc.
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": query}
        ],
        temperature=0.7,  # Controls creativity; 0.0 = strict, 1.0 = more creative
    )

    # Print the result
    return (response.choices[0].message.content)


def scrape_detail_page(driver, url):
    driver.execute_script("window.open('');")
    driver.switch_to.window(driver.window_handles[-1])
    driver.get(url)
    fields = {}

    try:
        # Wait for page to load completely
        WebDriverWait(driver, 50).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        # Wait until iframe with class "pdf" is present
        iframe = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.pdf"))
        )

        # Switch into iframe
        driver.switch_to.frame(iframe)

        # Wait for the PDF viewer to be present
        viewer_elem = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "viewer"))
        )
        # CRITICAL: Wait for PDF content to fully load and render
        # PDF viewers typically need time to convert PDF to HTML
        print("Waiting for PDF content to fully render...")
        # print(viewer_elem.text.strip())
        
        # Wait for PDF rendering to complete - look for actual content
        WebDriverWait(driver, 60).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "*")) > 10  # Wait for multiple elements to appear
        )
        
        # Additional wait for PDF-specific content to appear
        try:
            # Wait for text content to be available (PDF converted to HTML)
            WebDriverWait(driver, 30).until(
                lambda d: len(d.find_element(By.ID, "viewer").text.strip()) > 50
            )
            print("PDF content has rendered with sufficient text")
        except Exception as e:
            print(f"Warning: PDF text content may not be fully loaded: {e}")
        
        # Now extract the rendered HTML content
        viewer_elem = driver.find_element(By.ID, "viewer")
        print("Element with id 'viewer':")
        # print(viewer_elem.text)
        
        pdf_text=viewer_elem.text
        
        prompt="I will upload contract content. Plz analyze it and then give me project title only. Output must be only project title without any comment and prefix such as `project title:`"
        fields['title']=getOpenAIResponse(prompt, pdf_text)
        
        prompt="I will upload contract content. Plz analyze it and then give me applied country only. Output must be only country name without any comment and prefix such as `country:`"
        fields['country']=getOpenAIResponse(prompt, pdf_text)
        
        prompt="I will upload contract content. Plz analyze it and then give me budget only. Output must be only budget without any comment and prefix such as `budget:`. If budget is not specified, plz return `Not defined`"
        fields['budget']=getOpenAIResponse(prompt, pdf_text)
        
        prompt="I will upload contract content. Plz analyze it and then give me applied sector only. Output must be only applied sector without any comment and prefix such as `sector:`"
        fields['sector']=getOpenAIResponse(prompt, pdf_text)
        
        prompt="I will upload contract content. Plz analyze it and then give me summary only. Output must be only summary without any comment and prefix such as `summary:`"
        fields['summary']=getOpenAIResponse(prompt, pdf_text)
        
        prompt="I will upload contract content. Plz analyze it and then give me last updated date only. Output must be only last updated date without any comment and prefix such as `updated date:`"
        fields['updated']=getOpenAIResponse(prompt, pdf_text)
        
        prompt="I will upload contract content. Plz analyze it and then give me related program and project only. Output must be only related program and project without any comment and prefix such as `related program/project:`"
        fields['program']=getOpenAIResponse(prompt, pdf_text)
        
        print(fields['client'])
        print(fields['title'])
        print(fields['country'])
        print(fields['budget'])
        print(fields['sector'])
        print(fields['summary'])
        print(fields['updated'])
        print(fields['program'])
        
    except Exception as e:
        print(f"Failed to scrape pdf content")

    # Always switch back to top-level document
    driver.switch_to.default_content()
    
    driver.close()
    driver.switch_to.window(driver.window_handles[0])
    return fields


def parse_opportunity_row(row):
    try:
        # Initialize opportunity data
        opp = {
            "title": "",
            "client": "European Investment Bank",
            "country": "",
            "budget": "",
            "sector": "",
            "summary": "",
            "updated": "",
            "program": "",
            "url": "",
        }

        # Try to get URL from the row
        try:
            if row.tag_name == "a":
                row_url = row.get_attribute("href")
                opp["url"] = row_url or EIB_URL
            else:
                # Look for links within the row
                link = row.find_element(By.TAG_NAME, "a")
                if link:
                    opp["url"] = link.get_attribute("href") or EIB_URL
                else:
                    opp["url"] = EIB_URL
        except Exception:
            opp["url"] = EIB_URL

        return opp

    except Exception as e:
        logging.warning(f"Error parsing row: {e}")
        return None


def scrape_eib():
    """Main function to scrape European Investment Bank projects with proper pagination"""
    page_num = 1
    driver = None
    total_projects = 0

    # .view-content, col-xs-12 col-sm-12 col-md-4 col-lg-4, .field-content, a
    try:
        while True:
            print(f"Setting up driver for page {page_num}")
            driver = setup_driver()
            url = EIB_URL
            print(f"Preparing to scrape EIB page {page_num}")

            try:
                driver.get(url)
                
                # Wait until readyState == 'complete' (DOM + resources loaded)
                WebDriverWait(driver, 60).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                # Wait until at least one link appears inside .view-content .field-content
                # Wait until at least one link appears inside .search-filter__results
                rows = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".search-filter__results a"))
                )
                print(f"Found {len(rows)} rows:")
                print(f"Processing {len(rows)} project rows on page {page_num}")

                # Process each row
                page_projects = 0
                for i, row in enumerate(rows):
                    try:
                        print(row)
                        # Extract project information
                        opp = parse_opportunity_row(row)
                        print("parsed opportunity for ", opp["url"])
                        if not opp:
                            print(f"Could not parse row {i+1}")
                            continue

                        print(f"Processing project {i+1}: {opp['title']}")

                        # Scrape detail page for more info if a detail link exists
                        if opp["url"] and opp["url"] != EIB_URL:
                            try:
                                detail_fields = scrape_detail_page(driver, opp["url"])
                                opp.update(detail_fields)
                                print(
                                    f"Added detail fields: {list(detail_fields.keys())}"
                                )
                                print(opp)
                            except Exception as e:
                                logging.warning(f"Failed to scrape detail page: {e}")
                    except Exception as e:
                        print(f"Error processing row {i+1}: {e}")
                        continue
            except Exception as e:
                logging.error(f"Error scraping page {page_num}: {e}")
                print(f"Error on page {page_num}: {e}")

                # Print additional debugging info
                if driver:
                    try:
                        print(f"Current page title: {driver.title}")
                        print(f"Current URL: {driver.current_url}")
                        print(f"Page source length: {len(driver.page_source)}")
                    except Exception:
                        pass
                break

    except Exception as e:
        logging.error(f"Fatal error in scrape_eib: {e}")
        print(f"Fatal error: {e}")
    finally:
        if driver:
            driver.quit()
            print("Driver closed")

        print(f"\n{'='*50}")
        print(f"SCRAPING COMPLETED")


if __name__ == "__main__":
    try:
        print("I am scraping European Investment Bank now.")
        scrape_eib()
    except Exception as e:
        logging.critical(f"Fatal error: {e}")
        # notify_error(f'European Investment Bank scraper fatal error: {e}')
