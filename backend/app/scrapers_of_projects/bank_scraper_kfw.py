import logging
import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .bank_scraper import BankScraperBase

class KfWEntwicklungsBankScraper(BankScraperBase):
    def __init__(self) -> None:
        super().__init__()
        self.page_num=0

    def get_url(self):
        return f"https://www.kfw-entwicklungsbank.de/Internationale-Finanzierung/KfW-Entwicklungsbank/Projekte/Projektdatenbank/index.jsp?query=*%3A*&page={page_num}&rows=10&sortBy=relevance&sortOrder=desc&facet.filter.language=de&dymFailover=true&groups=1"
        
    
    def get_name(self):
        return "KfW Entwicklungsbank"


    def extract_projects_data(self):
        # Try multiple approaches to find project data
        project_data = None

        # First, try to find the main project container
        selectors = [
            (By.CSS_SELECTOR, ".search-result-content--default"),
        ]

        for selector_type, selector in selectors:
            try:
                # trying to get urls container
                project_temp_data = self.driver.find_element(selector_type, selector)
                # Scroll the element into view to appear all projects urls.
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    project_temp_data,
                )

                # Wait to appear project url.
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, ".search-result-content--default .search-result-item .title a")
                    )
                )

                # finding project data
                project_data = self.driver.find_element(selector_type, selector)
                break
            except Exception as e:
                print(f"Selector {selector_type}: {selector} failed: {e}")
                continue

        rows = []

        try:
            rows = project_data.find_elements(By.CSS_SELECTOR, ".search-result-item .title a")
            print(f"Found {len(rows)} urls of kfw projects!")
        except Exception:
            print("No urls of kfw projects found")

        print(f"Processing {len(rows)} project rows on page {self.os_num}")

        # Process each row

        for i, row in enumerate(rows):
            try:
                # finding row url
                row_url=None;
                if row.tag_name == "a":
                    row_url = row.get_attribute("href")
                else:
                    # Look for links within the row
                    link = row.find_element(By.CSS_SELECTOR, "a")
                    if link:
                        row_url = link.get_attribute("href")

                self.extract_project_data(row_url)

            except Exception as e:
                print(f"Error processing row {i+1}: {e}")
                continue
        
        # finished founding new projects


    def find_and_click_next_page(self):
        """Find and click the next page button, return True if successful"""
        try:
            page_num += 1
            return True

        except Exception as e:
            print(f"Error finding/clicking next page: {e}")
            return False

    def extract_project_data(self, url):
        self.driver.execute_script("window.open('');")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        self.driver.get(url)
        time.sleep(2)
        fields = {}
        # title
        try:
            print("scraping project title")
            # Wait until an element with class hl-1 is present in the DOM
            hl1_elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".hl-1"))
            )
            # Get its text
            fields["title"] = hl1_elem.text.strip()
        except Exception:
            fields["title"] = ""

        # client
        fields["client"] = "KfW Development Bank"

        # country
        try:
            fields["country"] = (
                WebDriverWait(self.driver, 10)
                .until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "table tr:first-of-type td")
                    )
                )
                .text
            )
        except Exception:
            fields["country"] = ""

        # budget
        try:
            fields["budget"] = (
                WebDriverWait(self.driver, 10)
                .until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "table tr:nth-of-type(8) td")
                    )
                )
                .text
            )

        except Exception as e:
            print(f"Error extracting text: {e}")

        # sector
        try:
            fields["sector"] = (
                WebDriverWait(self.driver, 10)
                .until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "table tr:nth-of-type(4) td")
                    )
                )
                .text
            )
        except Exception as e:
            print(f"Error extracting text: {e}")

        # Summary of requested services
        try:
            # Wait until at least one .text-image-text element is present
            elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".text-image-text"))
            )
            # Get and clean its visible text
            fields["summary"] = elem.text.strip()
        except Exception as e:
            print(f"Failed to click the link: {e}")

        # Submission deadline
        # .main-detail, fifth .row, third li, p
        try:
            fields["deadline"] = ""
        except Exception as e:
            print(f"Error extracting text: {e}")

        # Program/Project
        try:
            fields["program"] = (
                WebDriverWait(self.driver, 10)
                .until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "table tr:nth-of-type(11) td")
                    )
                )
                .text
            )
        except Exception as e:
            print(f"Error extracting text: {e}")

        # Project URL
        fields["url"] = url
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        return fields



if __name__ == "__main__":
    try:
        print("I am scraping KfW Entwicklungsbank now.")

        scraper_kfw= KfWEntwicklungsBankScraper();
        scraper_kfw.scrape_page();
    except Exception as e:
        logging.critical(f"Fatal error: {e}")