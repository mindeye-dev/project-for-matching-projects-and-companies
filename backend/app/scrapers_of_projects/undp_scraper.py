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


# do not need to control page number as all projects are in one page

# --- Config ---
UNDP_URL = "https://procurement-notices.undp.org"

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
    container = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".grid-container.fluid.mt-h"))
    )

    # title
    try:
        print("scraping project title")
        # Wait for the <nav> element with class 'breadcrumb' containing the <ul> and second <li>
        title_elem = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "nav.breadcrumb ul li:nth-of-type(2)")
            )
        )
        fields["title"] = title_elem.text.strip()
    except Exception:
        fields["title"] = ""
    # client
    fields["client"] = "United Nations Development Bank"

    # country
    try:
        # Wait for the first .postMetadata__category inside .postMetadata to be present
        p_elem = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    ".postMetadata .postMetadata__category:first-of-type p",
                )
            )
        )
        fields["country"] = p_elem.text
    except Exception:
        fields["country"] = ""

    # budget
    try:
        fields["budget"] = ""
    except Exception as e:
        print(f"Error extracting text: {e}")

    # sector
    try:
        prompt = "I will upload contract content. Plz analyze it and then give me applied sector only. You will find applied sector(field). Output must be only sector without any comment and prefix such as `sector:`. If sector is not defined, plz return `Not defined`"
        fields["sector"] = ""  # getOpenAIResponse(prompt, container.text.strip())

    except Exception as e:
        print(f"Error extracting text: {e}")

    # Summary of requested services
    try:
        summary_elems = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, ".cell.large-8.medium-offset-1.medium-10.postContent")
            )
        )
        fields["summary"] = " ".join(
            elem.text.strip() for elem in summary_elems if elem.text.strip()
        )
    except Exception as e:
        print(f"Error extracting summary: {e}")

    # Submission deadline
    try:
        p_elem = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    ".postMetadata .postMetadata__category:nth-of-type(2) p",
                )
            )
        )

        # Get the text of the <p> element and strip whitespace
        fields["deadline"] = p_elem.text.strip()
    except Exception as e:
        print(f"Error extracting deadline date: {e}")

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
                opp["url"] = row_url or UNDP_URL
            else:
                # Look for links within the row
                link = row.find_element(By.TAG_NAME, "a")
                if link:
                    opp["url"] = link.get_attribute("href") or UNDP_URL
                else:
                    opp["url"] = UNDP_URL
        except Exception:
            opp["url"] = UNDP_URL

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


def scrape_undp():
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
            url = UNDP_URL
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
                        (By.CSS_SELECTOR, ".vacanciesTable a")
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
                        if opp["url"] and opp["url"] != UNDP_URL:
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

                export_excel("./excel/undp.xlsx", opps)

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
        logging.error(f"Fatal error in scrape_undp: {e}")
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
        print("I am scraping United Nations Development Programme now.")
        scrape_undp()
    except Exception as e:
        logging.critical(f"Fatal error: {e}")
