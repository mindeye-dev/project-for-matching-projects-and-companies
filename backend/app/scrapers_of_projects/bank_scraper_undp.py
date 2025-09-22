import logging
import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .bank_scraper import BankScraperBase

class UnitedNationsDevelopmentProgrammeScraper(BankScraperBase):
    def __init__(self) -> None:
        super().__init__()
        self.os_num=0

    def get_url(self, page_num):
        return f"https://procurement-notices.undp.org";
    
    def get_name(self):
        return "United Nations Development Programme"


    def extract_projects_data(self):
        # Try multiple approaches to find project data
        project_data = None

        # First, try to find the main project container
        selectors = [
            (By.CSS_SELECTOR, ".vacanciesTable"),
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
                        (By.CSS_SELECTOR, ".vacanciesTable a")
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
            print(f"Found {len(rows)} urls of united nations development programme projects!")
        except Exception:
            print("No urls of world bank projects found")

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
            # Try multiple selectors for next page buttons
            next_selectors = [
                (By.LINK_TEXT, "Next"),
                (By.XPATH, "//a[contains(text(), 'Next')]"),
                (By.XPATH, "//button[contains(text(), 'Next')]"),
                (By.CSS_SELECTOR, "[class*='next']"),
                (By.CSS_SELECTOR, "[class*='pagination'] a:last-child"),
                (By.CSS_SELECTOR, ".pagination .next"),
                (By.CSS_SELECTOR, ".pagination a[aria-label='Next']"),
                (By.XPATH, "//a[@aria-label='Next']"),
                (By.XPATH, "//a[contains(@class, 'next')]"),
                (By.XPATH, "//a[contains(@class, 'pagination') and position()=last()]"),
            ]

            for selector_type, selector in next_selectors:
                try:
                    next_btn = self.driver.find_element(selector_type, selector)
                    if next_btn.is_enabled() and next_btn.is_displayed():
                        print(f"Found next page button: {selector}")

                        # Scroll to the button to ensure it's clickable
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView(true);", next_btn
                        )
                        time.sleep(1)

                        # Try to click the button
                        next_btn.click()
                        print("Clicked next page button")

                        # Wait for page to load
                        time.sleep(3)
                        return True

                except Exception as e:
                    print(f"Selector {selector_type}: {selector} failed: {e}")
                    continue

            print("No next page button found or clickable")
            return False

        except Exception as e:
            print(f"Error finding/clicking next page: {e}")
            return False

    def extract_project_data(self, url):
        self.driver.execute_script("window.open('');")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        self.driver.get(url)
        time.sleep(2)
        fields = {}
        container = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".grid-container.fluid.mt-h"))
        )

        # title
        try:
            print("scraping project title")
            # Wait for the <nav> element with class 'breadcrumb' containing the <ul> and second <li>
            title_elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "nav.breadcrumb ul li:nth-of-type(2)")
                )
            )
            fields["title"] = title_elem.text.strip()
        except Exception:
            fields["title"] = ""
        # client
        fields["client"] = "United Nations Development Bank"

        # country
        try:
            # Wait for the first .postMetadata__category inside .postMetadata to be present
            p_elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        ".postMetadata .postMetadata__category:first-of-type p",
                    )
                )
            )
            fields["country"] = p_elem.text
        except Exception:
            fields["country"] = ""

        # budget
        try:
            fields["budget"] = ""
        except Exception as e:
            print(f"Error extracting text: {e}")

        # sector
        try:
            prompt = "I will upload contract content. Plz analyze it and then give me applied sector only. You will find applied sector(field). Output must be only sector without any comment and prefix such as `sector:`. If sector is not defined, plz return `Not defined`"
            fields["sector"] = ""  # getOpenAIResponse(prompt, container.text.strip())

        except Exception as e:
            print(f"Error extracting text: {e}")

        # Summary of requested services
        try:
            summary_elems = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, ".cell.large-8.medium-offset-1.medium-10.postContent")
                )
            )
            fields["summary"] = " ".join(
                elem.text.strip() for elem in summary_elems if elem.text.strip()
            )
        except Exception as e:
            print(f"Error extracting summary: {e}")

        # Submission deadline
        try:
            p_elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        ".postMetadata .postMetadata__category:nth-of-type(2) p",
                    )
                )
            )

            # Get the text of the <p> element and strip whitespace
            fields["deadline"] = p_elem.text.strip()
        except Exception as e:
            print(f"Error extracting deadline date: {e}")

        # Program/Project
        fields["program"] = ""

        # Project URL
        fields["url"] = url
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        return fields



if __name__ == "__main__":
    try:
        print("I am scraping United Nations Development Programme now.")

        scraper_undp= UnitedNationsDevelopmentProgrammeScraper();
        scraper_undp.scrape_page();
    except Exception as e:
        logging.critical(f"Fatal error: {e}")