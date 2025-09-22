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


    def extract_projects_data(self):

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

    def extract_project_data(self, url):
        self.driver.execute_script("window.open('');")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        self.driver.get(url)
        time.sleep(2)
        fields = {}
        # title
        try:
            # h1_element = WebDriverWait(driver, 10).until(
            #     EC.presence_of_element_located((By.CSS_SELECTOR, 'h1[_ngcontent-serverapp-c68=""]'))
            # )
            # fields["title"] = h1_element.text.strip()

            ath_link = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
            print(ath_link.text.strip())
            fields["title"] = ath_link.text.strip()
        except Exception:
            fields["title"] = ""
            print("failed to scrape title")
        # client
        fields["client"] = "International Finance Corporation"

        # country
        try:
            # Locate the div with class 'esrs-value' and attribute '_ngcontent-serverapp-c60'
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.esrs-value[_ngcontent-serverapp-c60]")
                )
            )
            fields["country"] = element.text.strip()
        except Exception:
            fields["country"] = ""

        # budget
        try:
            # Wait until the main-detail element is present
            main_detail = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".main-detail"))
            )

            # Find all <ul> children inside main-detail
            ul_elements = main_detail.find_elements(By.CSS_SELECTOR, "ul")

            # Check if there are at least 4 ul elements
            if len(ul_elements) >= 4:
                fourth_ul = ul_elements[3]  # zero-based index

                # Find first <li> inside fourth ul
                first_li = fourth_ul.find_element(By.CSS_SELECTOR, "li")

                # Find the <p> inside the first li
                p_elem = first_li.find_element(By.CSS_SELECTOR, "p")

                # Get the text content
                fields["budget"] = p_elem.text.strip()
                print("Extracted text:", text)
            else:
                print("Less than 4 <ul> elements found inside .main-detail")

        except Exception as e:
            print(f"Error extracting text: {e}")

        # sector
        try:
            # Wait until the main-detail element is present
            main_detail = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".main-detail"))
            )

            # Find all <ul> children inside main-detail
            ul_elements = main_detail.find_elements(By.CSS_SELECTOR, "ul")

            # Check if there are at least 4 ul elements
            if len(ul_elements) >= 3:
                fourth_ul = ul_elements[2]  # zero-based index

                # Find second <li> inside fourth ul
                second_li = fourth_ul.find_elements(By.CSS_SELECTOR, "li")[1]

                # Find the <p> inside the first li
                p_elem = second_li.find_element(By.CSS_SELECTOR, "p")

                # Get the text content
                fields["sector"] = p_elem.text.strip()
                print("Extracted text:", text)
            else:
                print("Less than 3 <ul> elements found inside .main-detail")

        except Exception as e:
            print(f"Error extracting text: {e}")

        # Summary of requested services
        # #abstract, .container, second .row, ._loop_lead_paragraph_sm, a  // show more button
        # #abstract, .container, second .row, ._loop_lead_paragraph_sm, first text
        # 1. Try clicking the "Show more" button if it exists
        try:
            # Wait until the <a> element is clickable
            show_more_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//section[@id='abstract']//div[contains(@class,'container')]/div[contains(@class,'row')][2]//div[contains(@class,'_loop_lead_paragraph_sm')]//a",
                    )
                )
            )
            show_more_link.click()
            print("Clicked the 'Show More' link inside abstract.")
        except Exception as e:
            print(f"Failed to click the link: {e}")
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

                # Find element with class _loop_lead_paragraph_sm inside second row
                target_elem = second_row.find_element(
                    By.CSS_SELECTOR, "._loop_lead_paragraph_sm"
                )

                # Get the first direct text node inside target_elem using JavaScript execution
                first_text = self.driver.execute_script(
                    """
                    var elem = arguments[0];
                    for (var i = 0; i < elem.childNodes.length; i++) {
                        var node = elem.childNodes[i];
                        if (node.nodeType === Node.TEXT_NODE) {
                            var text = node.textContent.trim();
                            if(text.length > 0){
                                return text;
                            }
                        }
                    }
                    return '';
                """,
                    target_elem,
                )

                fields["summary"] = first_text
            else:
                print("Less than 2 .row elements inside .container")

        except Exception as e:
            print("Error:", e)

        # Submission deadline
        # .main-detail, fifth .row, third li, p
        try:
            # Wait until .main-detail is present
            main_detail = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".main-detail"))
            )

            # Find all .row children inside .main-detail
            rows = main_detail.find_elements(By.CSS_SELECTOR, ".row")

            # Check if we have at least 5 rows
            if len(rows) >= 5:
                fifth_row = rows[4]  # zero-based index

                # Find all <li> elements inside the fifth row
                li_elements = fifth_row.find_elements(By.CSS_SELECTOR, "li")

                # Check if we have at least 3 <li> elements
                if len(li_elements) >= 3:
                    third_li = li_elements[2]

                    # Find the <p> inside this li
                    p_elem = third_li.find_element(By.CSS_SELECTOR, "p")

                    # Extract and print the text
                    text = p_elem.text.strip()
                    fields["deadline"] = text
                else:
                    print("Less than 3 <li> elements found in fifth .row")
            else:
                print("Less than 5 .row elements found inside .main-detail")

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
        print("I am scraping International Finance Corporation now.")

        scraper_ifc= InternationalFinanceCorporationScraper();
        scraper_ifc.scrape_page();
    except Exception as e:
        logging.critical(f"Fatal error: {e}")