import logging
import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .bank_scraper import BankScraperBase

class EuropeanBankScraper(BankScraperBase):
    def __init__(self) -> None:
        super().__init__()
        self.page_num=0

    def get_url(self):
        return "https://www.ebrd.com/home/what-we-do/projects.html#customtab-70eec7766a-item-4654c5d413-tab"
        
    
    def get_name(self):
        return "European Bank"


    def extract_projects_data(self):
        # Try multiple approaches to find project data
        project_data = None

        rows = []
        try:
            rows = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, ".search-result__result-card")
                )
            )
            print(f"Found {len(rows)} urls of european bank projects!")
        except Exception:
            print("No urls of european bank projects found")

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
        
        # finished founding new projects


    def find_and_click_next_page(self):
        """Find and click the next page button, return True if successful"""
        try:
            search_input = self.driver.find_element(
                By.CSS_SELECTOR, "input.search-input[placeholder='Search...']"
            )

            # Type "africa" in the input field
            search_input.send_keys("africa")

            # Press the Enter key
            search_input.send_keys(Keys.ENTER)

            time.sleep(3)
            print("No next page button found or clickable")
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
            title_elem = self.driver.find_element(
                By.CSS_SELECTOR,
                ".hero-block__text-wrapper",
            )
            if title_elem:
                print("Found project title")

            print(title_elem.text.strip())
            fields["title"] = title_elem.text.strip()
        except Exception:
            fields["title"] = ""
        # client
        fields["client"] = "European Bank"

        try:
            # Wait until the <li> tab is clickable
            tab_li = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.ID, "customtab-8dfd7f8cd9-item-f0008af8f1-tab")
                )
            )
            print("Found tab")
            print(tab_li.text)
            # Click on the element
            tab_li.click()

            wait = WebDriverWait(self.driver, 10)
        except Exception:
            print("Error in waiting for clicking tab")

        # country
        try:
            elements = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, ".project-overview__card-description")
                )
            )
            for i, row in enumerate(elements):
                print(row.text.strip())

            fields["country"] = elements[3].text.strip()

        except Exception as e:
            print("error in extracting text {e}")
            fields["country"] = ""

        # budget
        try:
            elements = WebDriverWait(self.driver, 20).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, ".text-block__details")
                )
            )

            if len(elements) >= 7:
                element_7th = elements[6]  # 0-based index
                # Now find the first <p> inside that element
                p_elem = element_7th.find_element(By.CSS_SELECTOR, "p:first-of-type")
                print(p_elem.text.strip())
                print("found budget", element_7th.text.strip())
                fields["budget"] = p_elem.text.strip()
            else:
                print("Less than 7 elements with class .text-block__details found")
        except Exception as e:
            print(f"Error extracting text of budget: {e}")

        # sector
        try:
            elements = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, ".project-overview__card-description")
                )
            )
            for i, row in enumerate(elements):
                print(row.text.strip())

            fields["sector"] = elements[4].text.strip()
        except Exception:
            fields["sector"] = ""

        # Summary of requested services
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, ".mainbodytextunit")
            combined_text = "\n".join(elem.text for elem in elements)
            fields["summary"] = combined_text.strip()
        except Exception as e:
            print(f"Error extracting text of summary: {e}")

        # Submission deadline
        # .main-detail, fifth .row, third li, p
        try:
            elements = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, ".project-overview__card-description")
                )
            )
            for i, row in enumerate(elements):
                print(row.text.strip())

            fields["deadline"] = elements[8].text.strip()
        except Exception as e:
            print(f"Error extracting text of deadline: {e}")

        # Program/Project
        fields["program"] = ""

        # Project URL
        fields["url"] = url
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        return fields



if __name__ == "__main__":
    try:
        print("I am scraping European Bank now.")

        scraper_undp= EuropeanBankScraper();
        scraper_undp.scrape_page();
    except Exception as e:
        logging.critical(f"Fatal error: {e}")