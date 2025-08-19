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
ISDB_URL = "https://www.isdb.org/project-procurement/tenders"
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


def extract_field_by_label(driver, label_texts):
    for label in label_texts:
        try:
            elem = driver.find_element(
                By.XPATH, f"//*[contains(text(),'{label}')]/following-sibling::*[1]"
            )
            return elem.text.strip()
        except Exception:
            pass
        try:
            elem = driver.find_element(
                By.XPATH, f"//tr[th[contains(text(),'{label}')]]/td"
            )
            return elem.text.strip()
        except Exception:
            pass
    return ""


def wait_for_dynamic_content(driver, timeout=30):
    """Wait for dynamic content to load on the page"""
    try:
        # Wait for any AJAX requests to complete
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return jQuery.active == 0")
        )
    except Exception:
        # jQuery might not be available, continue anyway
        pass

    try:
        # Wait for any loading indicators to disappear
        loading_selectors = [
            ".loading",
            ".spinner",
            ".loader",
            "[class*='loading']",
            "[class*='spinner']",
            "[class*='loader']",
        ]
        for selector in loading_selectors:
            try:
                WebDriverWait(driver, 5).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, selector))
                )
            except Exception:
                pass
    except Exception:
        pass

    # Additional wait for any animations to complete
    time.sleep(2)


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
    time.sleep(2)
    fields = {}

    # Wait until at least one link matching the full selector is present
    main_element = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located(
            (
                By.CSS_SELECTOR,
                ".block-isdb-index-view-results .views-row .container-huge .field-title a",
            )
        )
    )

    # title
    try:
        print("scraping project title")
        link = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".field-title h1"))
        )
        fields["title"] = link.text
    except Exception:
        fields["title"] = ""
    # client
    fields["client"] = "African Development Bank"

    # country
    try:
        container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".field--name-field-description")
            )
        )
        # Get all <p> tags inside
        paragraphs = container.find_elements(By.TAG_NAME, "p")
        if len(paragraphs) >= 7:
            strong_elem = paragraphs[6].find_element(
                By.TAG_NAME, "strong"
            )  # index 6 = 7th paragraph
            fields["country"] = strong_elem.text
        else:
            print("Less than 7 paragraphs found in .field--name-field-description")
    except Exception:
        fields["country"] = ""

    # budget
    prompt = "I will upload contract content. Plz analyze it and then give me budget only. Output must be only budget without any comment and prefix such as `budget:`. If budget is not specified, plz return `Not defined`"
    fields["budget"] = getOpenAIResponse(prompt, main_element.text)

    # sector
    try:
        container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".field--name-field-description")
            )
        )
        # Get all <p> tags inside
        paragraphs = container.find_elements(By.TAG_NAME, "p")
        if len(paragraphs) >= 9:
            strong_elem = paragraphs[8].find_element(
                By.TAG_NAME, "strong"
            )  # index 6 = 7th paragraph
            fields["country"] = strong_elem.text
        else:
            print("Less than 9 paragraphs found in .field--name-field-description")

    except Exception as e:
        print(f"Error extracting text: {e}")

    # Summary of requested servicesprompt="I will upload contract content. Plz analyze it and then give me summary only. Output must be only summary without any comment and prefix such as `summary:`"
    prompt = "I will upload contract content. Plz analyze it and then give me summary only. Output must be only summary without any comment and prefix such as `summary:`"
    fields["summary"] = getOpenAIResponse(prompt, pdf_text)

    # Submission deadline
    # .main-detail, fifth .row, third li, p
    try:
        # Wait until the <time> element inside .field--name-field-close-date is present
        ime_elem = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".field--name-field-close-date time")
            )
        )

        fields["deadline"] = ime_elem.text

    except Exception as e:
        print(f"Error extracting text: {e}")

    # Program/Project
    fields["program"] = ""

    # Project URL
    fields["url"] = url
    driver.close()
    driver.switch_to.window(driver.window_handles[0])
    return fields


def parse_opportunity_row(row):
    try:
        # Initialize opportunity data
        opp = {
            "title": "",
            "client": "African Development Bank",
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
                opp["url"] = row_url or ISDB_URL
            else:
                # Look for links within the row
                link = row.find_element(By.TAG_NAME, "a")
                if link:
                    opp["url"] = link.get_attribute("href") or ISDB_URL
                else:
                    opp["url"] = ISDB_URL
        except Exception:
            opp["url"] = ISDB_URL

        return opp

    except Exception as e:
        logging.warning(f"Error parsing row: {e}")
        return None


def find_and_click_next_page(driver):
    """Find and click the next page button, return True if successful"""
    try:
        # Try multiple selectors for next page buttons
        next_selectors = [
            (By.LINK_TEXT, "Next"),
            (By.XPATH, "//a[contains(text(), 'Next')]"),
            (By.XPATH, "//button[contains(text(), 'Next')]"),
            (By.CSS_SELECTOR, "[class*='next']"),
            (By.CSS_SELECTOR, "[class*='pagination'] a:last-child"),
            (By.CSS_SELECTOR, ".pagination .next"),
            (By.CSS_SELECTOR, ".pagination a[aria-label='Next']"),
            (By.XPATH, "//a[@aria-label='Next']"),
            (By.XPATH, "//a[contains(@class, 'next')]"),
            (By.XPATH, "//a[contains(@class, 'pagination') and position()=last()]"),
        ]

        for selector_type, selector in next_selectors:
            try:
                next_btn = driver.find_element(selector_type, selector)
                if next_btn.is_enabled() and next_btn.is_displayed():
                    print(f"Found next page button: {selector}")

                    # Scroll to the button to ensure it's clickable
                    driver.execute_script(
                        "arguments[0].scrollIntoView(true);", next_btn
                    )
                    time.sleep(1)

                    # Try to click the button
                    next_btn.click()
                    print("Clicked next page button")

                    # Wait for page to load
                    time.sleep(3)
                    return True

            except Exception as e:
                print(f"Selector {selector_type}: {selector} failed: {e}")
                continue

        print("No next page button found or clickable")
        return False

    except Exception as e:
        print(f"Error finding/clicking next page: {e}")
        return False


def scrape_isdb():
    """Main function to scrape African Development Bank projects with proper pagination"""
    page_num = 1
    driver = None
    total_projects = 0

    try:
        while True:
            print(f"\n{'='*50}")
            print(f"SCRAPING PAGE {page_num}")
            print(f"{'='*50}")

            print(f"Setting up driver for page {page_num}")
            driver = setup_driver()
            url = ISDB_URL
            print(f"Preparing to scrape WB page {page_num}")
            logging.info(f"Scraping page {page_num}")

            try:
                driver.get(url)

                driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )  # Scroll to bottom

                # Wait for page to load completely
                WebDriverWait(driver, 50).until(
                    lambda d: d.execute_script("return document.readyState")
                    == "complete"
                )

                driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )  # Scroll to bottom

                # Wait for dynamic content to load
                wait_for_dynamic_content(driver)

                # Wait until at least one link matching the full selector is present
                rows = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (
                            By.CSS_SELECTOR,
                            ".block-isdb-index-view-results .views-row .container-huge .field-title a",
                        )
                    )
                )
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
                        if opp["url"] and opp["url"] != ISDB_URL:
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

                        # Submit to backend
                        logging.info(f"Submitting: {opp['title']} ({opp['country']})")
                        try:
                            r = requests.post(BACKEND_API, json=opp)
                            logging.info(f"Submitted: {r.status_code}")
                            print(f"Successfully submitted project {i+1}")
                            page_projects += 1
                            total_projects += 1
                        except Exception as e:
                            logging.error(f"Error submitting: {e}")
                            notify_error(f"Error submitting opportunity: {e}")

                        time.sleep(1)

                    except Exception as e:
                        print(f"Error processing row {i+1}: {e}")
                        continue

                export_excel("./excel/isdb.xlsx", opps)
                print(f"Page {page_num} completed: {page_projects} projects processed")
                print(f"Total projects processed so far: {total_projects}")

                # Check for next page
                print("Checking for next page...")
                if find_and_click_next_page(driver):
                    print("Successfully navigated to next page")
                    page_num += 1
                    driver.quit()
                    driver = None
                    time.sleep(3)  # Wait before next page
                    continue
                else:
                    print("No next page available, ending pagination.")
                    logging.info("No next page button found, ending.")
                    break

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
        logging.error(f"Fatal error in scrape_isdb: {e}")
        print(f"Fatal error: {e}")
    finally:
        if driver:
            driver.quit()
            print("Driver closed")

        print(f"\n{'='*50}")
        print(f"SCRAPING COMPLETED")
        print(f"Total pages processed: {page_num}")
        print(f"Total projects processed: {total_projects}")
        print(f"{'='*50}")


if __name__ == "__main__":
    try:
        print("I am scraping African development bank now.")
        scrape_isdb()
    except Exception as e:
        logging.critical(f"Fatal error: {e}")
        # notify_error(f'African Development Bank scraper fatal error: {e}')
