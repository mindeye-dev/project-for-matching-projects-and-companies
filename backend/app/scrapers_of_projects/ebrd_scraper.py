import time
import requests
import logging


from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys


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

# must click page element

# --- Config ---
EBRD_URL = "https://www.ebrd.com/home/what-we-do/projects.html#customtab-70eec7766a-item-4654c5d413-tab"

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
    # title
    try:
        print("scraping project title")
        title_elem = driver.find_element(
            By.CSS_SELECTOR,
            ".hero-block__text-wrapper",
        )
        if title_elem:
            print("Found project title")

        print(title_elem.text.strip())
        fields["title"] = title_elem.text.strip()
    except Exception:
        fields["title"] = ""
    # client
    fields["client"] = "European Bank for Reconstruction & Development"

    try:
        # Wait until the <li> tab is clickable
        tab_li = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.ID, "customtab-8dfd7f8cd9-item-f0008af8f1-tab")
            )
        )
        print("Found tab")
        print(tab_li.text)
        # Click on the element
        tab_li.click()

        wait = WebDriverWait(driver, 10)
    except Exception:
        print("Error in waiting for clicking tab")

    # country
    try:
        elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, ".project-overview__card-description")
            )
        )
        for i, row in enumerate(elements):
            print(row.text.strip())

        fields["country"] = elements[3].text.strip()

    except Exception as e:
        print("error in extracting text {e}")
        fields["country"] = ""

    # budget
    try:
        elements = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, ".text-block__details")
            )
        )

        if len(elements) >= 7:
            element_7th = elements[6]  # 0-based index
            # Now find the first <p> inside that element
            p_elem = element_7th.find_element(By.CSS_SELECTOR, "p:first-of-type")
            print(p_elem.text.strip())
            print("found budget", element_7th.text.strip())
            fields["budget"] = p_elem.text.strip()
        else:
            print("Less than 7 elements with class .text-block__details found")
    except Exception as e:
        print(f"Error extracting text of budget: {e}")

    # sector
    try:
        elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, ".project-overview__card-description")
            )
        )
        for i, row in enumerate(elements):
            print(row.text.strip())

        fields["sector"] = elements[4].text.strip()
    except Exception:
        fields["sector"] = ""

    # Summary of requested services
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, ".mainbodytextunit")
        combined_text = "\n".join(elem.text for elem in elements)
        fields["summary"] = combined_text.strip()
    except Exception as e:
        print(f"Error extracting text of summary: {e}")

    # Submission deadline
    # .main-detail, fifth .row, third li, p
    try:
        elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, ".project-overview__card-description")
            )
        )
        for i, row in enumerate(elements):
            print(row.text.strip())

        fields["deadline"] = elements[8].text.strip()
    except Exception as e:
        print(f"Error extracting text of deadline: {e}")

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
            "client": "European Bank for Reconstruction & Development",
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
                opp["url"] = row_url or EBRD_URL
            else:
                # Look for links within the row
                link = row.find_element(By.TAG_NAME, "a")
                if link:
                    opp["url"] = link.get_attribute("href") or EBRD_URL
                else:
                    opp["url"] = EBRD_URL
        except Exception:
            opp["url"] = EBRD_URL

        return opp

    except Exception as e:
        logging.warning(f"Error parsing row: {e}")
        return None


def find_and_click_next_page(driver):
    """Find and click the next page button, return True if successful"""
    try:
        search_input = driver.find_element(
            By.CSS_SELECTOR, "input.search-input[placeholder='Search...']"
        )

        # Type "africa" in the input field
        search_input.send_keys("africa")

        # Press the Enter key
        search_input.send_keys(Keys.ENTER)

        time.sleep(3)
        print("No next page button found or clickable")
        return True

    except Exception as e:
        print(f"Error finding/clicking next page: {e}")
        return False


def scrape_ebrd():
    """Main function to scrape European Bank for Reconstruction & Development projects with proper pagination"""
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
            url = EBRD_URL
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

                # Print page title and URL for debugging
                print(f"Page title: {driver.title}")
                print(f"Current URL: {driver.current_url}")

                rows = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, ".search-result__result-card")
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
                        if opp["url"] and opp["url"] != EBRD_URL:
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

                export_excel("./excel/ebrd.xlsx", opps)
                print(f"Page {page_num} completed: {page_projects} projects processed")
                print(f"Total projects processed so far: {total_projects}")

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
        logging.error(f"Fatal error in scrape_ebrd: {e}")
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
        print("I am scraping European Bank for Reconstruction & Development now.")
        scrape_ebrd()
    except Exception as e:
        logging.critical(f"Fatal error: {e}")
        # notify_error(f'European Bank for Reconstruction & Development scraper fatal error: {e}')
