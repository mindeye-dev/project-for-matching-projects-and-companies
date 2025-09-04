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
EIB_URL = "https://www.eib.org/en/projects/pipelines/index.htm"

# --- Logging ---
logging.basicConfig(
    filename="scraper.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(message)s",
)


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


def find_and_click_next_page(driver):
    """Find and click the next page button, return True if successful"""
    try:
        # Wait until the span element is clickable
        span_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "span.fa.fa-arrow-right"))
        )

        # Click the span element
        span_element.click()
        print("No next page button found or clickable")
        return True

    except Exception as e:
        print(f"Error finding/clicking next page: {e}")
        return False


def scrape_eib():
    """Main function to scrape European Investment Bank projects with proper pagination"""
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
                                saveToDatabase(opp)
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
