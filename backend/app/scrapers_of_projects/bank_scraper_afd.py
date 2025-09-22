import logging
import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .bank_scraper import BankScraperBase

class FrenchDevelopmentAgencyScraper(BankScraperBase):
    def __init__(self) -> None:
        super().__init__()
        self.page_num=0

    def get_url(self):
        return f"https://www.afd.fr/en/projects/list?page={self.page_num}"
        
    
    def get_name(self):
        return "French Development Agency"


    def extract_projects_data(self):
        
        rows = []

        try:
            rows = self.driver.find_elements(
                By.CSS_SELECTOR,
                ".fr-card__link",
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

                self.extract_project_data(row_url)

            except Exception as e:
                print(f"Error processing row {i+1}: {e}")
                continue
        
        # finished founding new projects


    def find_and_click_next_page(self):
        """Find and click the next page button, return True if successful"""
        try:
            self.page_num += 1
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
            meta_elem = self.driver.find_element(By.CSS_SELECTOR, 'meta[property="og:title"]')
            fields["title"] = meta_elem.get_attribute("content")
        except Exception:
            fields["title"] = ""
        # client
        fields["client"] = self.get_name()

        elements = self.driver.find_elements(By.CSS_SELECTOR, "dd")

        # country
        try:
            fields["country"] = elements[4].text.strip()
        except Exception:
            fields["country"] = ""

        # budget
        try:
            fields["budget"] = elements[3].text.strip()
        except Exception as e:
            print(f"Error extracting text: {e}")

        # sector
        try:  #
            fields["sector"] = elements[5].text.strip()
        except Exception as e:
            print(f"Error extracting text: {e}")

        # Summary of requested services
        try:
            summary_elements = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, ".my-8.print-para-space")
                )
            )
            fields["summary"] = ""
            for i, summary_element in enumerate(summary_elements):
                try:
                    fields["summary"] += summary_element.text.strip()
                except Exception:
                    print("Exception on summary processing")
        except Exception as e:
            print(f"Failed to scrape summary: {e}")

        # Submission deadline
        try:
            fields["deadline"] = elements[1].text.strip()
        except Exception as e:
            print(f"Error extracting text: {e}")

        # Program/Project
        fields["program"] = ""

        # Project URL
        fields["url"] = url
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        return fields



if __name__ == "__main__":
    try:
        print("I am scraping French Development Agency now.")

        scraper_afd= FrenchDevelopmentAgencyScraper();
        scraper_afd.scrape_page();
    except Exception as e:
        logging.critical(f"Fatal error: {e}")