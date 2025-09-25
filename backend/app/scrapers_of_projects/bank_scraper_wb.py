import logging
import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


from .bank_scraper import BankScraperBase


class WorldBankScraper(BankScraperBase):
    def __init__(self) -> None:
        super().__init__()
        self.os_num=0

    def get_url(self):
        return f"https://projects.worldbank.org/en/projects-operations/projects-list?os={self.os_num}";

    def get_name(self):
        return "World Bank";

    async def extract_projects_data(self):
        # Try multiple approaches to find project data
        # project_data = None

        # # First, try to find the main project container
        # selectors = [
        #     (By.CSS_SELECTOR, ".project_recentdata"),
        # ]

        # for selector_type, selector in selectors:
        #     try:
        #         # trying to get urls container
        #         project_temp_data = self.driver.find_element(selector_type, selector)
        #         # Scroll the element into view to appear all projects urls.
        #         self.driver.execute_script(
        #             "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
        #             project_temp_data,
        #         )

        #         # Wait to appear project url.
        #         WebDriverWait(self.driver, 15).until(
        #             EC.presence_of_all_elements_located(
        #                 (By.CSS_SELECTOR, ".project_recentdata a")
        #             )
        #         )

        #         # finding project data
        #         project_data = self.driver.find_element(selector_type, selector)
        #         break
        #     except Exception as e:
        #         print(f"Selector {selector_type}: {selector} failed: {e}")
        #         continue

        rows = []


        try:
            rows = WebDriverWait(self.driver, 50).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "tr.ng-tns-c1-0.ng-star-inserted")
                )
            )
            print(f"Found {len(rows)} urls of world bank projects!")
        except Exception:
            print("No urls of world bank projects found")

        print(f"Processing {len(rows)} project rows on page {self.os_num}")

        # Process each row

        for i, row in enumerate(rows):
            try:
                tdElements = row.find_elements(By.CSS_SELECTOR, "td")
                    
                row_url = f"https://projects.worldbank.org/en/projects-operations/project-detail/{tdElements[2].text}"
                print(row_url)

                await self.extract_project_data(row_url)

            except Exception as e:
                print(f"Error processing row {i+1}: {e}")
                continue
        
        # finished founding projects


    async def find_and_click_next_page(self):
        """Find and click the next page button, return True if successful"""
        try:
            self.os_num += 20
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
                "#projects-title",
            )
            if title_elem:
                print("Found project title")

            print(title_elem.text.strip())
            fields["title"] = title_elem.text.strip()
        except Exception:
            fields["title"] = ""
        # client
        fields["client"] = "World Bank"

        # country
        try:
            # Wait until at least one country link is present
            # WebDriverWait(self.driver, 10).until(
            #     EC.presence_of_all_elements_located(
            #         (By.CSS_SELECTOR, "a.dropdown-item[href*='/country/']")
            #     )
            # )
            # Find all country links
            # Find all country links
            elements = self.driver.find_elements(By.CSS_SELECTOR, ".detail-download-section .main-detail a")

            # Safely get the first one if available
            if elements:
                print(elements[0].get_attribute("outerHTML"))
                fields["country"] = elements[0].text.strip()

                print(fields["country"])
            else:
                fields["country"] = None  # or some fallback value
        except Exception:
            fields["country"] = ""

        # budget
        try:
            # Wait until the main-detail element is present
            main_detail = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".main-detail"))
            )

            # Find all <ul> children inside main-detail
            ul_elements = main_detail.find_elements(By.TAG_NAME, "ul")

            # Check if there are at least 4 ul elements
            if len(ul_elements) >= 4:
                fouth_ul = ul_elements[3]  # zero-based index

                # Find first <li> inside third ul
                first_li = fouth_ul.find_element(By.TAG_NAME, "li")

                # Find the <p> inside the first li
                p_elem = first_li.find_element(By.TAG_NAME, "p")

                print(p_elem.get_attribute("outerHTML"))

                # Get the text content
                fields["budget"] = p_elem.text.strip()
                print(fields["budget"])
            else:
                print("Less than 4 <ul> elements found inside .main-detail")

        except Exception as e:
            print(f"Error extracting text: {e}")

        # sector
        try:
            # Wait until the main-detail element is present
            development_objective = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#development-objective"))
            )

            development_objective_text=development_objective.text.strip()

            prompt = "I will upload development objective. Plz analyze it and then give me sector of development objective only. Output must be only sector without any comment and prefix such as `sector:`"
            fields["sector"] = await self.get_openai_response(prompt, development_objective_text)
            print(fields["sector"])

        except Exception as e:
            print(f"Error extracting text: {e}")

        # Summary of requested services
        # #abstract, .container, second .row, ._loop_lead_paragraph_sm, a  // show more button
        # #abstract, .container, second .row, ._loop_lead_paragraph_sm, first text
        # 1. Try clicking the "Show more" button if it exists
        try:
            # Wait until the <a> element is clickable
            show_more_link = abstract = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#abstract a"))
            )
            show_more_link.click()
            print("Clicked the 'Show More' link inside abstract.")
            try:
                # Wait until #abstract is present
                abstract = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#abstract"))
                )

                # Find .container inside #abstract
                container = abstract.find_element(By.CSS_SELECTOR, ".container")

                # Find all .row inside container
                rows = container.find_elements(By.CSS_SELECTOR, ".row")

                if len(rows) >= 2:
                    second_row = rows[1]
                    fields["summary"] = second_row.text
                    print(fields["summary"])
                else:
                    print("Less than 2 .row elements inside .container")

            except Exception as e:
                print("Error:", e)
        except Exception as e:
            development_objective = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#development-objective"))
            )

            fields["summary"]=development_objective.text.strip()
            print(f"Failed to click the link: {e}")
        

        # Submission deadline
        # .main-detail, fifth .row, third li, p
        try:
            # Wait until .main-detail is present
            main_detail = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".main-detail"))
            )

            # Find all .row children inside .main-detail
            rows = main_detail.find_elements(By.CSS_SELECTOR, ".row")

            # Check if we have at least 4 rows
            if len(rows) >= 4:
                fouth_row = rows[3]  # zero-based index

                # Find all <li> elements inside the fifth row
                li_elements = fouth_row.find_elements(By.CSS_SELECTOR, "li")

                # Check if we have at least 4 <li> elements
                if len(li_elements) >= 4:
                    fouth_li = li_elements[3]

                    # Find the <p> inside this li
                    p_elem = fouth_li.find_element(By.CSS_SELECTOR, "p")

                    # Extract and print the text
                    text = p_elem.text.strip()
                    fields["deadline"] = text
                    print(fields["deadline"])
                else:
                    print("Less than 4 <li> elements found in fifth .row")
            else:
                print("Less than 4 .row elements found inside .main-detail")

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
        import asyncio
        print("I am scraping world bank now.")
        scraper_wb = WorldBankScraper()
        asyncio.run(scraper_wb.scrape_page())
    except Exception as e:
        logging.critical(f"Fatal error: {e}")
        # notify_error(f'World Bank scraper fatal error: {e}')