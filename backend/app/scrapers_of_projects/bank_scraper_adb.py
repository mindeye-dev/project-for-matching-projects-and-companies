import logging
import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .bank_scraper import BankScraperBase

class AsianDevelopmentBankScraper(BankScraperBase):
    def __init__(self) -> None:
        super().__init__()
        self.page_num=0

    def get_url(self):
        return f"https://www.adb.org/projects/tenders?page={self.page_num}"
        
    
    def get_name(self):
        return "Asian Development Bank"


    def extract_projects_data(self):
        
        rows = []

        try:
            rows =  WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (
                        By.CSS_SELECTOR,
                        ".views-element-container .list .item.linked .item-title a",
                    )
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
            print("scraping project title")
            title_elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".x1f"))
            )
            fields["title"] = title_elem.text.strip()
        except Exception:
            fields["title"] = ""
        # client
        fields["client"] = self.get_name()

        # country
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, "#mstCtryOfAssignAll__xc_")
            fields["country"] = element.text
        except Exception:
            fields["country"] = ""

        # budget
        try:
            budget_elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#rlConsultingBudget"))
            )
            prompt = "I will upload contract content. Plz analyze it and then give me applied sector only. Output must be only applied sector without any comment and prefix such as `sector:`"
            fields["budget"] = budget_elem.text.strip()

        except Exception as e:
            print(f"Error extracting text: {e}")

        # Wait until the element is clickable, then click it
        link_element = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#lnk_tor"))
        )
        link_element.click()

        main_container = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#slTor"))
        )

        main_container_text = main_container.text.strip()
        # sector
        try:
            prompt = "I will upload contract content. Plz analyze it and then give me applied sector only. Output must be only applied sector without any comment and prefix such as `sector:`"
            fields["sector"] = self.getOpenAIResponse(prompt, main_container_text)

        except Exception as e:
            print(f"Error extracting text: {e}")

        # Summary of requested services
        try:
            prompt = "I will upload contract content. Plz analyze it and then give me summary only. Output must be only summary without any comment and prefix such as `summary:`"
            fields["summary"] = self.getOpenAIResponse(prompt, main_container_text)

        except Exception as e:
            print("Error:", e)

        # Submission deadline
        # .main-detail, fifth .row, third li, p
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#POATable\\:POAEndDateInput\\:0"))
            )
            fields["deadline"] = element.text.strip()

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
        print("I am scraping Asian Development Bank now.")

        scraper_adb= AsianDevelopmentBankScraper();
        scraper_adb.scrape_page();
    except Exception as e:
        logging.critical(f"Fatal error: {e}")