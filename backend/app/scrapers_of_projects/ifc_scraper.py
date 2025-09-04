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

# must click page element

# --- Config ---
IFC_URL = "https://disclosures.ifc.org/enterprise-search-results-home?f_type_description=Investment"

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
        # h1_element = WebDriverWait(driver, 10).until(
        #     EC.presence_of_element_located((By.CSS_SELECTOR, 'h1[_ngcontent-serverapp-c68=""]'))
        # )
        # fields["title"] = h1_element.text.strip()

        ath_link = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
        print(ath_link.text.strip())
        fields["title"] = ath_link.text.strip()
    except Exception:
        fields["title"] = ""
        print("failed to scrape title")
    # client
    fields["client"] = "International Finance Corporation"

    # country
    try:
        # Locate the div with class 'esrs-value' and attribute '_ngcontent-serverapp-c60'
        element = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.esrs-value[_ngcontent-serverapp-c60]")
            )
        )
        fields["country"] = element.text.strip()
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
            "client": "International Finance Corporation",
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
                opp["url"] = row_url or IFC_URL
            else:
                # Look for links within the row
                link = row.find_element(By.TAG_NAME, "a")
                if link:
                    opp["url"] = link.get_attribute("href") or IFC_URL
                else:
                    opp["url"] = IFC_URL
        except Exception:
            opp["url"] = IFC_URL

        return opp

    except Exception as e:
        logging.warning(f"Error parsing row: {e}")
        return None


def find_and_click_next_page(driver):
    """Find and click the next page button, return True if successful"""
    try:
        # Wait until the element is clickable
        element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "span.fa.fa-chevron-right"))
        )

        # Click the element
        element.click()
        print("No next page button found or clickable")
        return True

    except Exception as e:
        print(f"Error finding/clicking next page: {e}")
        return False


def scrape_ifc():
    """Main function to scrape International Finance Corporation projects with proper pagination"""
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
            url = IFC_URL
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

                # Wait until at least one <a> inside .projects inside .row.margin-top15 exists
                rows = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (
                            By.CSS_SELECTOR,
                            ".row.margin-top15.projects .col-12.padding-top5 a",
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
                        if opp["url"] and opp["url"] != IFC_URL:
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

                export_excel("./excel/ifc.xlsx", opps)
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
        logging.error(f"Fatal error in scrape_ifc: {e}")
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
        print("I am scraping International Finance Corporation now.")
        scrape_ifc()
    except Exception as e:
        logging.critical(f"Fatal error: {e}")
        # notify_error(f'International Finance Corporation scraper fatal error: {e}')
