import logging
import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .bank_scraper import BankScraperBase

class InternationalFinanceCorporationScraper(BankScraperBase):
    def __init__(self) -> None:
        super().__init__()
        self.page_num=0

    def get_url(self):
        return "https://disclosures.ifc.org/enterprise-search-results-home?f_type_description=Investment"
        
    
    def get_name(self):
        return "International Finance Corporation"


    async def extract_projects_data(self):

        rows = []
        try:
            # Wait until at least one <a> inside .projects inside .row.margin-top15 exists
            rows = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (
                        By.CSS_SELECTOR,
                        ".row.margin-top15.projects .col-12.padding-top5 a",
                    )
                )
            )
            print(f"Found {len(rows)} urls of international finance corporation projects!")
        except Exception:
            print("No urls of international finance corporation projects found")

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
                print(f"Error processing row {i+1}: {e}")
                continue
        
        # finished founding new projects

    def is_next_page_by_click(self):
        return True

    async def find_and_click_next_page(self):
        """Find and click the next page button, return True if successful"""
        try:
            # Wait until the element is clickable
            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "span.fa.fa-chevron-right"))
            )

            # Click the element
            element.click()
            print("No next page button found or clickable")
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

        try:
            # Use the base class waiting method
            await self.wait_for_completed_loading()

            # Wait for the specific container to be present and visible
            container = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".container.project-detail.padding-large0")
                )
            )
            
            # Wait for the container to be visible
            WebDriverWait(self.driver, 30).until(
                EC.visibility_of(container)
            )

            # Additional wait to ensure all dynamic content is loaded
            # Wait for any loading indicators to disappear
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, ".loading, .spinner, .loader"))
                )
            except:
                pass  # No loading indicators found, continue

            # Wait for any AJAX requests to complete
            WebDriverWait(self.driver, 20).until(
                lambda d: d.execute_script("return window.jQuery ? jQuery.active == 0 : true")
            )

            # Wait for any pending network requests to complete
            WebDriverWait(self.driver, 20).until(
                lambda d: d.execute_script("""
                    return window.performance.getEntriesByType('navigation')[0].loadEventEnd > 0
                """)
            )

            # Additional wait for any dynamic content that might be loading
            time.sleep(3)

            # Scroll to ensure all content is loaded
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)

            # Now get the outerHTML
            outer_html = self.driver.execute_script("return arguments[0].outerHTML;", container)
            container_text = outer_html

            # print(container_text)
            # title
            prompt = "I will upload contract content. Plz analyze it and then give me project title only. First sentence before `back to search` is project title. Output must be only project title without any comment and prefix such as `project title:`"
            fields["title"] = await self.get_openai_response(prompt, container_text)

            prompt = "I will upload contract content. Plz analyze it and then give me applied country only. Country is next of `Country` word. Output must be only country name without any comment and prefix such as `country:`"
            fields["country"] = await self.get_openai_response(prompt, container_text)

            prompt = "You are given a contract document. Extract the contract budget only.  Return the budget amount exactly as written in the document (e.g., `US$317.5 million`).  If no budget is mentioned, return only `Not defined`.  Do not add any comments, explanations, or prefixes."
            fields["budget"] = await self.get_openai_response(prompt, container_text)

            prompt = "I will upload contract content. Plz analyze it and then give me applied sector only. Output must be only applied sector without any comment and prefix such as `sector:`"
            fields["sector"] = await self.get_openai_response(prompt, container_text)

            prompt = "I will upload contract content. Plz analyze it and then give me summary only. Summary must be detailed. Output must be only summary without any comment and prefix such as `summary:`"
            fields["summary"] = await self.get_openai_response(prompt, container_text)

            prompt = "I will upload contract content. Plz analyze it and then give me last deadline date only. Output must be only last deadline date without any comment and prefix such as `deadline date:`"
            fields["deadline"] = await self.get_openai_response(prompt, container_text)

            prompt = "I will upload contract content. Plz analyze it and then give me related program and project only. Output must be only related program and project without any comment and prefix such as `related program/project:`"
            fields["program"] = await self.get_openai_response(prompt, container_text)        

            # Project URL
            fields["url"] = url
        except Exception as e:
            print(f"Failed to scrape container content", e)
        print(fields)
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        await self.save_to_database(fields)
        return fields



if __name__ == "__main__":
    try:
        print("I am scraping International Finance Corporation now.")

        scraper_ifc= InternationalFinanceCorporationScraper();
        scraper_ifc.scrape_page();
    except Exception as e:
        logging.critical(f"Fatal error: {e}")