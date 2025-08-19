import os
import time
import requests
import logging
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
WB_URL = "https://projects.worldbank.org/en/projects-operations/projects-home"
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


def print_element_html(element, description="Element"):
    """Utility function to print detailed HTML of a Selenium element"""
    try:
        html_content = element.get_attribute("outerHTML")
        print(f"\n=== DETAILED HTML OF {description.upper()} ===")
        print(html_content)
        print(f"=== END OF {description.upper()} HTML ===\n")
    except Exception as e:
        print(f"Error printing HTML for {description}: {e}")


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
            By.ID,
            "projects-title",
        )
        if title_elem:
            print("Found project title")

        print(title_elem.text.strip())
        fields["title"] = title_elem.text.strip()
    except Exception:
        fields["title"] = ""
    # client
    fields["client"] = "World Bank"

    # country
    try:
        # Wait until at least one country link is present
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "a.dropdown-item[href*='/country/']")
            )
        )
        # Find all country links
        elements = driver.find_elements(
            By.CSS_SELECTOR, "a[href*='www.worldbank.org/en/country/']"
        )
        for elem in elements:
            text = elem.text.strip()
            if text:  # ignore blank
                fields["country"] = text
    except Exception:
        fields["country"] = ""

    # budget
    try:
        # Wait until the main-detail element is present
        main_detail = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".main-detail"))
        )

        # Find all <ul> children inside main-detail
        ul_elements = main_detail.find_elements(By.TAG_NAME, "ul")

        # Check if there are at least 4 ul elements
        if len(ul_elements) >= 4:
            fourth_ul = ul_elements[3]  # zero-based index

            # Find first <li> inside fourth ul
            first_li = fourth_ul.find_element(By.TAG_NAME, "li")

            # Find the <p> inside the first li
            p_elem = first_li.find_element(By.TAG_NAME, "p")

            # Get the text content
            fields["budget"] = p_elem.text.strip()
            print("Extracted text:", text)
        else:
            print("Less than 4 <ul> elements found inside .main-detail")

    except Exception as e:
        print(f"Error extracting text: {e}")

    # sector
    try:
        # Wait until the main-detail element is present
        main_detail = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".main-detail"))
        )

        # Find all <ul> children inside main-detail
        ul_elements = main_detail.find_elements(By.TAG_NAME, "ul")

        # Check if there are at least 4 ul elements
        if len(ul_elements) >= 3:
            fourth_ul = ul_elements[2]  # zero-based index

            # Find second <li> inside fourth ul
            second_li = fourth_ul.find_elements(By.TAG_NAME, "li")[1]

            # Find the <p> inside the first li
            p_elem = second_li.find_element(By.TAG_NAME, "p")

            # Get the text content
            fields["sector"] = p_elem.text.strip()
            print("Extracted text:", text)
        else:
            print("Less than 3 <ul> elements found inside .main-detail")

    except Exception as e:
        print(f"Error extracting text: {e}")

    # Summary of requested services
    # #abstract, .container, second .row, ._loop_lead_paragraph_sm, a  // show more button
    # #abstract, .container, second .row, ._loop_lead_paragraph_sm, first text
    # 1. Try clicking the "Show more" button if it exists
    try:
        # Wait until the <a> element is clickable
        show_more_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//section[@id='abstract']//div[contains(@class,'container')]/div[contains(@class,'row')][2]//div[contains(@class,'_loop_lead_paragraph_sm')]//a",
                )
            )
        )
        show_more_link.click()
        print("Clicked the 'Show More' link inside abstract.")
    except Exception as e:
        print(f"Failed to click the link: {e}")
    try:
        # Wait until #abstract is present
        abstract = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "abstract"))
        )

        # Find .container inside #abstract
        container = abstract.find_element(By.CLASS_NAME, "container")

        # Find all .row inside container
        rows = container.find_elements(By.CLASS_NAME, "row")

        if len(rows) >= 2:
            second_row = rows[1]

            # Find element with class _loop_lead_paragraph_sm inside second row
            target_elem = second_row.find_element(
                By.CLASS_NAME, "_loop_lead_paragraph_sm"
            )

            # Get the first direct text node inside target_elem using JavaScript execution
            first_text = driver.execute_script(
                """
                var elem = arguments[0];
                for (var i = 0; i < elem.childNodes.length; i++) {
                    var node = elem.childNodes[i];
                    if (node.nodeType === Node.TEXT_NODE) {
                        var text = node.textContent.trim();
                        if(text.length > 0){
                            return text;
                        }
                    }
                }
                return '';
            """,
                target_elem,
            )

            fields["summary"] = first_text
        else:
            print("Less than 2 .row elements inside .container")

    except Exception as e:
        print("Error:", e)

    # Submission deadline
    # .main-detail, fifth .row, third li, p
    try:
        # Wait until .main-detail is present
        main_detail = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".main-detail"))
        )

        # Find all .row children inside .main-detail
        rows = main_detail.find_elements(By.CSS_SELECTOR, ".row")

        # Check if we have at least 5 rows
        if len(rows) >= 5:
            fifth_row = rows[4]  # zero-based index

            # Find all <li> elements inside the fifth row
            li_elements = fifth_row.find_elements(By.TAG_NAME, "li")

            # Check if we have at least 3 <li> elements
            if len(li_elements) >= 3:
                third_li = li_elements[2]

                # Find the <p> inside this li
                p_elem = third_li.find_element(By.TAG_NAME, "p")

                # Extract and print the text
                text = p_elem.text.strip()
                fields["deadline"] = text
            else:
                print("Less than 3 <li> elements found in fifth .row")
        else:
            print("Less than 5 .row elements found inside .main-detail")

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
            "client": "World Bank",
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
                opp["url"] = row_url or WB_URL
            else:
                # Look for links within the row
                link = row.find_element(By.TAG_NAME, "a")
                if link:
                    opp["url"] = link.get_attribute("href") or WB_URL
                else:
                    opp["url"] = WB_URL
        except Exception:
            opp["url"] = WB_URL

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


def scrape_wb():
    """Main function to scrape World Bank projects with proper pagination"""
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
            url = WB_URL
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

                # Additional debugging: Check if we're on the right page
                if (
                    "projects" not in driver.title.lower()
                    and "world bank" not in driver.title.lower()
                ):
                    print(
                        f"Warning: Page title doesn't seem to be a World Bank projects page: {driver.title}"
                    )

                # Try multiple approaches to find project data
                project_data = None

                # First, try to find the main project container
                selectors = [
                    (By.CLASS_NAME, "project_recentdata"),
                ]

                for selector_type, selector in selectors:
                    try:
                        project_temp_data = driver.find_element(selector_type, selector)
                        # Scroll the element into view
                        driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                            project_temp_data,
                        )
                        WebDriverWait(driver, 15).until(
                            EC.presence_of_all_elements_located(
                                (By.CSS_SELECTOR, ".project_recentdata a")
                            )
                        )
                        project_data = driver.find_element(selector_type, selector)

                        print(f"Found project data using {selector_type}: {selector}")
                        print(f"Element tag: {project_data.tag_name}")
                        print(f"Element class: {project_data.get_attribute('class')}")
                        print(f"Element text length: {len(project_data.text)}")
                        break
                    except Exception as e:
                        print(f"Selector {selector_type}: {selector} failed: {e}")
                        continue

                print("Project data container found.")

                # Try multiple approaches to find project links/rows
                rows = []

                # Method 1: Look for links directly
                print(
                    "---------------Preparing to get project links directly.-------------"
                )
                try:
                    rows = project_data.find_elements(By.TAG_NAME, "a")

                    print(f"Found {len(rows)} links directly")
                except Exception:
                    print("No links found directly")

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
                        if opp["url"] and opp["url"] != WB_URL:
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

                export_excel("./excel/wb.xlsx", opps)
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
        logging.error(f"Fatal error in scrape_wb: {e}")
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
        print("I am scraping world bank now.")
        scrape_wb()
    except Exception as e:
        logging.critical(f"Fatal error: {e}")
        # notify_error(f'World Bank scraper fatal error: {e}')
