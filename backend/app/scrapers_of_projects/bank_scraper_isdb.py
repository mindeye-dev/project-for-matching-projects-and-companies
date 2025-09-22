import logging
import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .bank_scraper import BankScraperBase




class IslamicDevelopmentBankScraper(BankScraperBase):
    def __init__(self) -> None:
        super().__init__()
        self.page_num=0

    def get_url(self):
        return f"https://www.isdb.org/project-procurement/tenders?page={self.page_num}"
        
    
    def get_name(self):
        return "Islamic Development Bank"


    def extract_projects_data(self):
        # Try multiple approaches to find project data
        project_data = None

        # First, try to find the main project container
        selectors = [
            (By.CSS_SELECTOR, ".block-isdb-index-view-results"),
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
                        (By.CSS_SELECTOR, ".block-isdb-index-view-results .views-row .container-huge .field-title a")
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
            rows = project_data.find_elements(By.TAG_NAME, ".views-row .container-huge .field-title a")
            print(f"Found {len(rows)} urls of islamic development bank projects!")
        except Exception:
            print("No urls of islamic development bank projects found")

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

        # Wait until at least one link matching the full selector is present
        main_element = WebDriverWait(self.driver, 10).until(
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
            link = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".field-title h1"))
            )
            fields["title"] = link.text
        except Exception:
            fields["title"] = ""
        # client
        fields["client"] = "African Development Bank"

        # country
        try:
            container = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".field--name-field-description")
                )
            )
            # Get all <p> tags inside
            paragraphs = container.find_elements(By.CSS_SELECTOR, "p")
            if len(paragraphs) >= 7:
                strong_elem = paragraphs[6].find_element(
                    By.CSS_SELECTOR, "strong"
                )  # index 6 = 7th paragraph
                fields["country"] = strong_elem.text
            else:
                print("Less than 7 paragraphs found in .field--name-field-description")
        except Exception:
            fields["country"] = ""

        # budget
        prompt = "I will upload contract content. Plz analyze it and then give me budget only. Output must be only budget without any comment and prefix such as `budget:`. If budget is not specified, plz return `Not defined`"
        fields["budget"] = self.getOpenAIResponse(prompt, main_element.text)

        # sector
        try:
            container = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".field--name-field-description")
                )
            )
            # Get all <p> tags inside
            paragraphs = container.find_elements(By.CSS_SELECTOR, "p")
            if len(paragraphs) >= 9:
                strong_elem = paragraphs[8].find_element(
                    By.CSS_SELECTOR, "strong"
                )  # index 6 = 7th paragraph
                fields["country"] = strong_elem.text
            else:
                print("Less than 9 paragraphs found in .field--name-field-description")

        except Exception as e:
            print(f"Error extracting text: {e}")

        # Summary of requested servicesprompt="I will upload contract content. Plz analyze it and then give me summary only. Output must be only summary without any comment and prefix such as `summary:`"

        entire_container = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".container .outer")
            )
        )

        prompt = "I will upload contract content. Plz analyze it and then give me summary only. Output must be only summary without any comment and prefix such as `summary:`"
        fields["summary"] = self.getOpenAIResponse(prompt, entire_container.text)

        # Submission deadline
        # .main-detail, fifth .row, third li, p
        try:
            # Wait until the <time> element inside .field--name-field-close-date is present
            ime_elem = WebDriverWait(self.driver, 10).until(
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
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        return fields


if __name__ == "__main__":
    try:
        print("I am scraping Islamic Development Bank now.")

        scraper_isdb= IslamicDevelopmentBankScraper();
        scraper_isdb.scrape_page();
    except Exception as e:
        logging.critical(f"Fatal error: {e}")