## summary and deadline is error


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
from export_excel import export_excel


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
            {"role": "user", "content": query},
        ],
        temperature=0.7,  # Controls creativity; 0.0 = strict, 1.0 = more creative
    )

    # Print the result
    return response.choices[0].message.content


def scrape_detail_page(driver, url):
    driver.execute_script("window.open('');")
    driver.switch_to.window(driver.window_handles[-1])
    driver.get(url)
    fields = {}

    try:
        # title
        # Wait for page to load completely
        WebDriverWait(driver, 50).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        # Wait for the element to be present and visible on the page
        title_elem = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, ".eib-typography__title")
            )
        )
        # Extract and print the visible text
        fields["title"] = title_elem.text

        # country
        # #pipeline-overview, first .bulleted-list--blue, a
        # Wait until the #pipeline-overview element is present
        pipeline_overview = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "pipeline-overview"))
        )
        # Within that element, find the first .bulleted-list--blue
        bulleted_list = pipeline_overview.find_element(
            By.CSS_SELECTOR, ".bulleted-list--blue"
        )
        # Find the first <a> inside that bulleted list
        first_link = bulleted_list.find_element(By.TAG_NAME, "a")
        # Get the text of that <a> element
        fields["country"] = first_link.text

        # budget
        # .totalAmount 's next sibling
        # Find the element with class "totalAmount"
        total_amount_elem = driver.find_element(By.CSS_SELECTOR, ".totalAmount")
        # Use JavaScript to get the next sibling element (element node)
        next_sibling = driver.execute_script(
            """
            let elem = arguments[0];
            let sibling = elem.nextElementSibling;  // gets next element sibling, skips text nodes
            return sibling;
        """,
            total_amount_elem,
        )
        # Get the text of the next sibling if it exists
        if next_sibling:
            fields["budget"] = next_sibling.text
            print("Text of next sibling:", text)
        else:
            print("No next sibling element found after .totalAmount")

        # sector

        # summary
        # #pipeline-overview, div,10 th and 11 th sibling
        # Find the #pipeline-overview element
        # pipeline_overview_elem = driver.find_element(By.ID, "pipeline-overview")
        # # Use XPath to find the 10th following sibling which is a div element
        # tenth_div_sibling = driver.find_element(
        #     By.XPATH, "//*[@id='pipeline-overview']/following-sibling::div[10]"
        # )
        # eleventh_div_sibling = driver.find_element(
        #     By.XPATH, "//*[@id='pipeline-overview']/following-sibling::div[11]"
        # )
        # # Get its text
        # fields['summary'] = tenth_div_sibling.text+eleventh_div_sibling

        print(">>>>> scraping deadline date now.")

        # deadline
        # .pipeline-ref, 4th span
        # Wait until the .pipeline-ref div is present
        pipeline_ref = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".pipeline-ref"))
        )
        # Find all span elements inside .pipeline-ref
        spans = pipeline_ref.find_elements(By.TAG_NAME, "span")
        # Iterate to find the span containing "Release date:" and get the next span's text
        for i, span in enumerate(spans):
            if span.text.strip() == "Release date:":
                # The next span holds the date
                if i + 1 < len(spans):
                    fields["deadline"] = spans[i + 1].text.strip()
                break

        # program
        fields["program"] = "Not defined"

    except Exception as e:
        print(f"Failed to scrape project content")

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
            "deadline": "",
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
                    lambda d: d.execute_script("return document.readyState")
                    == "complete"
                )

                # Wait until the .search-filter__results element is present and visible
                search_filter_elem = WebDriverWait(driver, 120).until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, ".search-filter__results")
                    )
                )

                # Scroll the element into view smoothly, centered vertically
                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    search_filter_elem,
                )
                # Wait until at least one link appears inside .view-content .field-content
                # Wait until at least one link appears inside .search-filter__results
                rows = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, ".search-filter__results .row-title a")
                    )
                )
                print(f"Found {len(rows)} rows:")
                print(f"Processing {len(rows)} project rows on page {page_num}")

                # Process each row
                page_projects = 0
                opps = []
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
                                opps.append(opp)
                                print(
                                    f"Added detail fields: {list(detail_fields.keys())}"
                                )
                                print(opp)
                            except Exception as e:
                                logging.warning(f"Failed to scrape detail page: {e}")
                    except Exception as e:
                        print(f"Error processing row {i+1}: {e}")
                        continue

                export_excel("./excel/eib.xlsx", opps)
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
