import logging
import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .bank_scraper import BankScraperBase

class AfricanDevelopmeBankScraper(BankScraperBase):
    def __init__(self) -> None:
        super().__init__()
        self.page_num=0
        

    def get_url(self):
        return f"https://www.afdb.org/en/projects-and-operations/procurement?page={self.page_num}"
        
    
    def get_name(self):
        return "African Development Bank"


    def extract_projects_data(self):
        
        rows = []

        try:
            rows = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, ".view-content .field-content a")
                )
            )
            print(f"Found {len(rows)} urls of world bank projects!")
        except Exception:
            print("No urls of world bank projects found")

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
        fields = {}

        try:
            # Wait for page to load completely
            WebDriverWait(self.driver, 50).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # Wait until iframe with class "pdf" is present
            iframe = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.pdf"))
            )

            # Switch into iframe
            self.driver.switch_to.frame(iframe)

            # Wait for the PDF viewer to be present
            viewer_elem = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#viewer"))
            )
            # CRITICAL: Wait for PDF content to fully load and render
            # PDF viewers typically need time to convert PDF to HTML
            print("Waiting for PDF content to fully render...")
            # print(viewer_elem.text.strip())

            # Wait for PDF rendering to complete - look for actual content
            WebDriverWait(self.driver, 60).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "*"))
                > 10  # Wait for multiple elements to appear
            )

            # Additional wait for PDF-specific content to appear
            try:
                # Wait for text content to be available (PDF converted to HTML)
                WebDriverWait(self.driver, 30).until(
                    lambda d: len(d.find_element(By.CSS_SELECTOR, "#viewer").text.strip()) > 50
                )
                print("PDF content has rendered with sufficient text")
            except Exception as e:
                print(f"Warning: PDF text content may not be fully loaded: {e}")

            # Now extract the rendered HTML content
            viewer_elem = self.driver.find_element(By.CSS_SELECTOR, "#viewer")
            print("Element with id 'viewer':")
            # print(viewer_elem.text)

            pdf_text = viewer_elem.text

            prompt = "I will upload contract content. Plz analyze it and then give me project title only. Output must be only project title without any comment and prefix such as `project title:`"
            fields["title"] = getOpenAIResponse(prompt, pdf_text)

            prompt = "I will upload contract content. Plz analyze it and then give me applied country only. Output must be only country name without any comment and prefix such as `country:`"
            fields["country"] = getOpenAIResponse(prompt, pdf_text)

            prompt = "You are given a contract document. Extract the contract budget only.  Return the budget amount exactly as written in the document (e.g., `US$317.5 million`).  If no budget is mentioned, return only `Not defined`.  Do not add any comments, explanations, or prefixes."
            fields["budget"] = getOpenAIResponse(prompt, pdf_text)

            prompt = "I will upload contract content. Plz analyze it and then give me applied sector only. Output must be only applied sector without any comment and prefix such as `sector:`"
            fields["sector"] = getOpenAIResponse(prompt, pdf_text)

            prompt = "I will upload contract content. Plz analyze it and then give me summary only. Output must be only summary without any comment and prefix such as `summary:`"
            fields["summary"] = getOpenAIResponse(prompt, pdf_text)

            prompt = "I will upload contract content. Plz analyze it and then give me last deadline date only. Output must be only last deadline date without any comment and prefix such as `deadline date:`"
            fields["deadline"] = getOpenAIResponse(prompt, pdf_text)

            prompt = "I will upload contract content. Plz analyze it and then give me related program and project only. Output must be only related program and project without any comment and prefix such as `related program/project:`"
            fields["program"] = getOpenAIResponse(prompt, pdf_text)

            print(fields["client"])
            print(fields["title"])
            print(fields["country"])
            print(fields["budget"])
            print(fields["sector"])
            print(fields["summary"])
            print(fields["deadline"])
            print(fields["program"])

        except Exception as e:
            print(f"Failed to scrape pdf content")

        # Always switch back to top-level document
        self.driver.switch_to.default_content()

        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        return fields



if __name__ == "__main__":
    try:
        print("I am scraping African Development Bank now.")

        scraper_undp= AfricanDevelopmeBankScraper();
        scraper_undp.scrape_page();
    except Exception as e:
        logging.critical(f"Fatal error: {e}")