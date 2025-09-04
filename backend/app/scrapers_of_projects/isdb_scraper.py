import time
import requests
import logging


from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


from scraper_helpers import (
    setup_driver,
    export_excel,
    notify_error,
    print_element_html,
    getOpenAIResponse,
    solve_cloudflare_captcha,
    is_cloudflare_captcha_present,
    is_captcha_present,
    saveToDatabase,
)


page_num = 0

# --- Config ---
ISDB_URL = "https://www.isdb.org/project-procurement/tenders"

# --- Logging ---
logging.basicConfig(
    filename="scraper.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(message)s",
)


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
        page_num += 1
        return True

    except Exception as e:
        print(f"Error finding/clicking next page: {e}")
        return False


def get_url():
    return f"https://www.adb.org/projects/tenders?page={page_num}"


def scrape_isdb():
    """Main function to scrape African Development Bank projects with proper pagination"""
    driver = None
    total_projects = 0

    try:
        while True:
            print(f"\n{'='*50}")
            print(f"SCRAPING PAGE {page_num}")
            print(f"{'='*50}")

            print(f"Setting up driver for page {page_num}")
            driver = setup_driver()
            url = get_url()
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
                                saveToDatabase(opp)
                                print(
                                    f"Added detail fields: {list(detail_fields.keys())}"
                                )
                                print(opp)
                            except Exception as e:
                                logging.warning(f"Failed to scrape detail page: {e}")

                        time.sleep(1)

                    except Exception as e:
                        print(f"Error processing row {i+1}: {e}")
                        continue

                export_excel("./excel/isdb.xlsx", opps)

                # Check for next page
                print("Checking for next page...")
                if find_and_click_next_page(driver):
                    print("Successfully navigated to next page")
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
