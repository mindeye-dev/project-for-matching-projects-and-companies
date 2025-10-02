import logging
import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .bank_scraper import BankScraperBase


class DutchEnterpreneurialDevelopmentBankScraper(BankScraperBase):
    def __init__(self) -> None:
        super().__init__()
        self.page_num=1

    def get_url(self):
        return f"https://www.fmo.nl/project-list?page={self.page_num}"
        
    
    def get_name(self):
        return "Dutch Enterpreneurial Development Bank"


    async def extract_projects_data(self):
        # Try multiple approaches to find project data
        project_data = None

        rows = []
        try:
            rows = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, ".ProjectList__projectLink")
                )
            )
            print(f"Found {len(rows)} urls of {self.get_name()} projects!")
        except Exception:
            print(f"No urls of {self.get_name()} projects found")

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
                    link = row.find_element(By.TAG_NAME, "a")
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
            print("scraping project title")
            title_elem = self.driver.find_element(
                By.CSS_SELECTOR,
                ".ProjectDetail__title",
            )
            if title_elem:
                print("Found project title")

            print(title_elem.text.strip())
            fields["title"] = title_elem.text.strip()
        except Exception:
            fields["title"] = ""
        # client
        fields["client"] = "FMO"

        # finding elements

        container_elems = WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, ".ProjectDetail__asideInner")
            )
        )
        elements = []

        if container_elems:
            container_elem = container_elems[1]  # get the first matching container

            # Find the <dd> element that is the 3rd of its type inside the container
            elements = container_elem.find_elements(By.CSS_SELECTOR, "dd")

        # country
        try:
            fields["country"] = elements[2].text.strip()
        except Exception:
            fields["country"] = ""
        # budget
        try:
            fields["budget"] = elements[6].text.strip()
        except Exception:
            fields["budget"] = ""

        # sector
        try:
            fields["sector"] = elements[3].text.strip()
        except Exception:
            fields["sector"] = ""

        # Summary of requested services
        try:
            summary_elem = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        ".ProjectDetail__main",
                    )
                )
            )
            fields["summary"] = summary_elem.text.strip()
        except Exception as e:
            print(f"Failed to scrap text: {e}")

        # Submission deadline
        try:
            fields["deadline"] = elements[5].text.strip()
        except Exception:
            fields["deadline"] = ""

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
        print("I am scraping Dutch Enterpreneurial Development Bank now.")
        scraper_fmo= DutchEnterpreneurialDevelopmentBankScraper();
        scraper_fmo.scrape_page();
    except Exception as e:
        logging.critical(f"Fatal error: {e}")