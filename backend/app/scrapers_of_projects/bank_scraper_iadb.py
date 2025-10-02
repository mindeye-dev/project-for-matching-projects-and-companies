import logging
import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .bank_scraper import BankScraperBase


class InterAmericanDevelopmentBankScraper(BankScraperBase):
    def __init__(self) -> None:
        super().__init__()
        self.page_num=0

    def get_url(self):
        return f"https://www.iadb.org/en/project-search?page={self.page_num}"
        
    
    def get_name(self):
        return "Inter American Development Bank"


    async def extract_projects_data(self):
        # Try multiple approaches to find project data
        project_data = None

        # First, try to find the main project container
        selectors = [
            (By.CSS_SELECTOR, ".views-element-container"),
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
                        (By.CSS_SELECTOR, '.views-element-container tbody a')
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
            rows = project_data.find_elements(By.CSS_SELECTOR, 'tbody a')
            print(f"Found {len(rows)} urls of inter american development bank projects!")
        except Exception:
            print("No urls of inter american development bank projects found")

        print(f"Processing {len(rows)} project rows on page {self.page_num}")

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

                if await self.opportunity_of_url(row_url) is None:
                    await self.extract_project_data(row_url)

            except Exception as e:
                print(f"Error processing row {i+1}: {e}")
                continue
        
        # finished founding new projects

    def is_next_page_by_click(self):
        return False

    async def find_and_click_next_page(self):
        """Find and click the next page button, return True if successful"""
        try:
            self.page_num += 1
            self.driver.quit()
            self.driver = None
            return True

        except Exception as e:
            print(f"Error finding/clicking next page: {e}")
            return False

    async def extract_project_data(self, url):
        self.driver.execute_script("window.open('');")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        self.driver.get(url)
        time.sleep(2)
        fields = {}
        # title
        try:
            meta_elem = self.driver.find_element(By.CSS_SELECTOR, 'meta[property="og:title"]')
            fields["title"] = meta_elem.get_attribute("content")
        except Exception:
            fields["title"] = ""
        # client
        fields["client"] = "Inter-American Development Bank"

        elements = self.driver.find_elements(
            By.CSS_SELECTOR, 'idb-project-table-row p[slot="stat-data"]'
        )

        # country
        try:
            fields["country"] = elements[0].text.strip()
        except Exception:
            fields["country"] = ""

        # budget
        try:
            fields["budget"] = elements[12].text.strip()
        except Exception as e:
            print(f"Error extracting text: {e}")

        # sector
        try:
            fields["sector"] = elements[5].text.strip()
        except Exception as e:
            print(f"Error extracting text: {e}")

        # Summary of requested services
        try:
            summary_elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "idb-styled-text"))
            )
            fields["summary"] = summary_elem.text.strip()
        except Exception as e:
            print(f"Failed to scrape summary: {e}")

        # Submission deadline
        fields["deadline"]=""
        try:
            fields["deadline"] = elements[2].text.strip()
        except Exception as e:
            print(f"Error extracting text: {e}")

        # Program/Project
        fields["program"] = ""

        # Project URL
        fields["url"] = url
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        await self.save_to_database(fields)
        return fields



if __name__ == "__main__":
    try:
        print("I am scraping Inter American Development Bank now.")

        scraper_iadb= InterAmericanDevelopmentBankScraper();
        scraper_iadb.scrape_page();
    except Exception as e:
        logging.critical(f"Fatal error: {e}")