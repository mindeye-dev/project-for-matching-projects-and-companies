import logging
import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .bank_scraper import BankScraperBase

class EuropeanInvestmentBankScraper(BankScraperBase):
    def __init__(self) -> None:
        super().__init__()
        self.page_num=0

    def get_url(self):
        return "https://www.eib.org/en/projects/pipelines/index.htm"
        
    
    def get_name(self):
        return "European Invement Bank"


    async def extract_projects_data(self):
        # Try multiple approaches to find project data
        project_data = None

        # First, try to find the main project container
        selectors = [
            (By.CSS_SELECTOR, ".search-filter__results"),
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
                        (By.CSS_SELECTOR, ".search-filter__results .row-title a")
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
            rows = project_data.find_elements(By.CSS_SELECTOR, ".row-title a")
            print(f"Found {len(rows)} urls of european investment bank projects!")
        except Exception:
            print("No urls of european investment bank projects found")

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

                print(row_url)
                if await self.opportunity_of_url(row_url) is None:
                    await self.extract_project_data(row_url)

            except Exception as e:
                print(f"Error processing row {i+1}: ", e)
                continue
        
        # finished founding new projects
    def is_next_page_by_click(self):
        return True

    async def find_and_click_next_page(self):
        """Find and click the next page button, return True if successful"""
        try:
            
            # Wait until the span element is clickable
            span_element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "span.fa.fa-arrow-right"))
            )

            # Click the span element
            span_element.click()
            print("No next page button found or clickable")
            return True

        except Exception as e:
            print(f"Error finding/clicking next page: {e}")
            return False

    async def extract_project_data(self, url):
        self.driver.execute_script("window.open('');")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        self.driver.get(url)
        fields = {}

        try:
            # title
            # Wait for page to load completely
            WebDriverWait(self.driver, 50).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            # Wait for the element to be present and visible on the page
            title_elem = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, ".eib-typography__title")
                )
            )
            # Extract and print the visible text
            fields["title"] = title_elem.text
            print("title:", fields["title"])

            fields["client"] = "European Investment Bank"

            # country
            # #pipeline-overview, first .bulleted-list--blue, a
            # Wait until the #pipeline-overview element is present
            pipeline_overview = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "pipeline-overview"))
            )
            # Within that element, find the first .bulleted-list--blue
            bulleted_lists = pipeline_overview.find_elements(
                By.CSS_SELECTOR, ".bulleted-list--blue"
            )
            # Find the first <a> inside that bulleted list
            first_link = bulleted_lists[0].find_element(By.TAG_NAME, "a")
            # Get the text of that <a> element
            fields["country"] = first_link.text
            print("country:", fields["country"])

            # budget
            # .totalAmount 's next sibling
            # Find the element with class "totalAmount"
            total_amount_elem = self.driver.find_element(By.CSS_SELECTOR, ".totalAmount")
            # Use JavaScript to get the next sibling element (element node)
            next_sibling = self.driver.execute_script(
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
            else:
                print("No next sibling element found after .totalAmount")
            print("budget:", fields["budget"])

            # sector
            # Find the first <a> inside that bulleted list
            second_link = bulleted_lists[1].find_element(By.TAG_NAME, "a")
            # Get the text of that <a> element
            fields["sector"] = second_link.text
            print("sector:", fields["sector"])

            # summary
            #pipeline-overview, div,10 th and 11 th sibling
            # Find the #pipeline-overview element
            container=self.driver.find_element(
                By.CSS_SELECTOR, "#content"
            )
            container_text=container.text.strip()
            prompt = "I will upload contract content. Plz analyze it and then give me summary only. Summary must be detailed. Output must be only summary without any comment and prefix such as `summary:`"
            fields["summary"] = await self.get_openai_response(prompt, container_text)
            print("summary:", fields["summary"])

            # deadline
            # .pipeline-ref, 4th span
            # Wait until the .pipeline-ref div is present
            pipeline_ref = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".pipeline-ref"))
            )
            # Find all span elements inside .pipeline-ref
            spans = pipeline_ref.find_elements(By.CSS_SELECTOR, "span")
            # Iterate to find the span containing "Release date:" and get the next span's text
            for i, span in enumerate(spans):
                if span.text.strip() == "Release date:":
                    # The next span holds the date
                    if i + 1 < len(spans):
                        fields["deadline"] = spans[i + 1].text.strip()
                    break
            print("deadline:", fields["deadline"])

            # program
            fields["program"] = "Not defined"
            fields["url"] = url

        except Exception as e:
            print(f"Failed to scrape project content")

        # Always switch back to top-level document
        self.driver.switch_to.default_content()

        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        print(fields)
        await self.save_to_database(fields)

        print("saved successfully!")
        return fields






if __name__ == "__main__":
    try:
        print("I am scraping European Investment Bank now.")

        scraper_undp= EuropeanInvestmentBankScraper();
        scraper_undp.scrape_page();
    except Exception as e:
        logging.critical(f"Fatal error: {e}")