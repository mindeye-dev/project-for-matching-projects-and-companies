import logging
import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .bank_scraper import BankScraperBase

class WorldBankGroupGuaranteesScraper(BankScraperBase):
    def __init__(self) -> None:
        super().__init__()
        self.page_num=0

    def get_url(self):
        return f"https://www.miga.org/projects/list?page={self.page_num}"
        
    
    def get_name(self):
        return "World Bank Group Guarantees"


    def extract_projects_data(self):
        # Try multiple approaches to find project data
        project_data = None

        # First, try to find the main project container
        selectors = [
            (By.CSS_SELECTOR, ".teaser-list.view.view-featured-projects .view-content .page-title"),
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
                        (By.CSS_SELECTOR, ".teaser-list.view.view-featured-projects .view-content .page-title a")
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
            rows = project_data.find_elements(By.TAG_NAME, "a")
            print(f"Found {len(rows)} urls of world bank group guarantees projects!")
        except Exception:
            print("No urls of world bank group guarantees projects found")

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
                    link = row.find_element(By.TAG_NAME, "a")
                    if link:
                        row_url = link.get_attribute("href")

                self.extract_project_data(row_url)

            except Exception as e:
                print(f"Error processing row {i+1}: {e}")
                continue
        
        # finished founding projects


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

        try:
            container_elem = self.driver.find_element(
                By.CSS_SELECTOR,
                ".paragraph__column",
            )

            container_text = container_elem.text.strip()
            print(container_text)
            prompt = "I will upload contract content. Plz analyze it and then give me project title only. Output must be only project title without any comment and prefix such as `project title:`"
            fields["title"] = self.getOpenAIResponse(prompt, container_text)

            prompt = "I will upload contract content. Plz analyze it and then give me applied country only. Output must be only country name without any comment and prefix such as `country:`"
            fields["country"] = self.getOpenAIResponse(prompt, container_text)

            prompt = "You are given a contract document. Extract the contract budget only.  Return the budget amount exactly as written in the document (e.g., `US$317.5 million`).  If no budget is mentioned, return only `Not defined`.  Do not add any comments, explanations, or prefixes."
            fields["budget"] = self.getOpenAIResponse(prompt, container_text)

            prompt = "I will upload contract content. Plz analyze it and then give me applied sector only. Output must be only applied sector without any comment and prefix such as `sector:`"
            fields["sector"] = self.getOpenAIResponse(prompt, container_text)

            prompt = "I will upload contract content. Plz analyze it and then give me summary only. Output must be only summary without any comment and prefix such as `summary:`"
            fields["summary"] = self.getOpenAIResponse(prompt, container_text)

            prompt = "I will upload contract content. Plz analyze it and then give me last deadline date only. Output must be only last deadline date without any comment and prefix such as `deadline date:`"
            fields["deadline"] = self.getOpenAIResponse(prompt, container_text)

            prompt = "I will upload contract content. Plz analyze it and then give me related program and project only. Output must be only related program and project without any comment and prefix such as `related program/project:`"
            fields["program"] = self.getOpenAIResponse(prompt, container_text)

            # Project URL
            fields["url"] = url
        except Exception:
            print("error in scraping fields")
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        return fields



if __name__ == "__main__":
    try:
        print("I am scraping World Bank Group Guarantees now.")

        scraper_miga= WorldBankGroupGuaranteesScraper();
        scraper_miga.scrape_page();
    except Exception as e:
        logging.critical(f"Fatal error: {e}")