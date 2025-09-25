import os
import requests
import time
import logging
import atexit
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
)
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

from app.models import db, Opportunity

# --- Logging ---
logging.basicConfig(
    filename="scraper.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(message)s",
)


HEADLESS = os.environ.get("HEADLESS", "0") == "1"
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK", "")

class BankScraperBase:
    def __init__(self) -> None:
        """Initialize the base scraper class"""
        self.driver = None
        atexit.register(self.cleanup_webdriver)

    def cleanup_webdriver(self):
        """Cleanup WebDriver on exit"""
        if self.driver:
            try:
                self.driver.quit()
                logging.info("WebDriver cleaned up.")
            except Exception as e:
                logging.error(f"Error during WebDriver cleanup: {e}")
        else:
            logging.info("No WebDriver instance to clean up.")

    async def setup_driver(self, proxy=None):
        """Set up the Firefox driver with necessary configurations"""
        options = FirefoxOptions()
        if HEADLESS:
            options.add_argument("--headless")

        # Enhanced stealth settings
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        options.set_preference(
            "general.useragent.override",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        # Additional stealth preferences
        options.set_preference("dom.webnotifications.enabled", False)
        options.set_preference("media.volume_scale", "0.0")
        options.set_preference("network.proxy.type", 0)
        options.set_preference("privacy.resistFingerprinting", False)
        options.set_preference("browser.cache.disk.enable", False)
        options.set_preference("browser.cache.memory.enable", False)

        # Create the Firefox driver
        self.driver = webdriver.Firefox(options=options)

        # Enhanced stealth: remove webdriver properties
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: ()=> undefined})"
        )
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'plugins', {get: ()=> [1, 2, 3, 4, 5]})"
        )
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'languages', {get: ()=> ['en-US', 'en']})"
        )

        print("-- Driver set up for scraping --")

    
    def solve_cloudflare_captcha(self):
        """Solve Cloudflare CAPTCHA"""
        try:
            wait = WebDriverWait(self.driver, 10)
            frames = wait.until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "iframe"))
            )
            checkbox_found = False

            print("Found iframe")

            for frame in frames:
                self.driver.switch_to.frame(frame)
                try:
                    checkbox = wait.until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, "input[type='checkbox']")
                        )
                    )
                    checkbox.click()
                    checkbox_found = True
                    print("CAPTCHA checkbox clicked.")
                    self.driver.switch_to.default_content()
                    break
                except TimeoutException:
                    self.driver.switch_to.default_content()

            if not checkbox_found:
                print("Checkbox input not found in any iframe.")
        except TimeoutException:
            print("No iframes found or checkbox did not appear within timeout.")

    
    def is_cloudflare_captcha_present(self, timeout=5):
        """Check if Cloudflare CAPTCHA is present"""
        search_text = "www.adb.org needs to review the security of your connection before proceeding"
        page_source = self.driver.page_source
        return search_text in page_source

    def is_captcha_present(self):
        """Check if any CAPTCHA is present (e.g., Google's reCAPTCHA)"""
        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "iframe[src*='recaptcha']")
                )
            )
            return True
        except TimeoutException:
            return False
        
    async def wait_for_completed_loading(self, timeout=30):
        """Wait for dynamic content (AJAX) to load"""
        try:
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )  # Scroll to bottom

            # Wait for page to load completely
            WebDriverWait(self.driver, 50).until(
                lambda d: d.execute_script("return document.readyState")
                == "complete"
            )

            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )  # Scroll to bottom
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return jQuery.active == 0")
            )
        except Exception:
            pass  # jQuery might not be available, continue

        try:
            loading_selectors = [
                ".loading", ".spinner", ".loader", "[class*='loading']",
                "[class*='spinner']", "[class*='loader']"
            ]
            for selector in loading_selectors:
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.invisibility_of_element_located((By.CSS_SELECTOR, selector))
                    )
                except Exception:
                    pass
        except Exception:
            pass
        # Allow additional time for animations or content loading
        time.sleep(2)

    def export_excel(self, filename, data_array):
        """Export data to an Excel file"""
        df = pd.DataFrame(data_array)
        df.to_excel(filename, index=False)

    def notify_error(self, message):
        """Notify via Slack in case of an error"""
        if SLACK_WEBHOOK:
            try:
                requests.post(SLACK_WEBHOOK, json={"text": message})
            except Exception as e:
                logging.error(f"Failed to send Slack notification: {e}")

    def print_element_html(self, element, description="Element"):
        """Utility function to print detailed HTML of a Selenium element"""
        try:
            html_content = element.get_attribute("outerHTML")
            print(f"\n=== DETAILED HTML OF {description.upper()} ===")
            print(html_content)
            print(f"=== END OF {description.upper()} HTML ===\n")
        except Exception as e:
            print(f"Error printing HTML for {description}: {e}")
            
    async def save_to_database(self, project):
        """Save project data to the database"""
        print("saving database now.")
        opp = Opportunity(
            project_name=project["title"],
            client=project["client"],
            country=project["country"],
            sector=project["sector"],
            summary=project["summary"],
            deadline=project["deadline"],
            program=project["program"],
            budget=project["budget"],
            url=project["url"],
            found=False,
        )

        print("Saving project to database...")
        # Custom function to convert Opportunity object to dictionary
        def opportunity_to_dict(opp):
            return {
                "project_name": opp.project_name,
                "client": opp.client,
                "country": opp.country,
                "sector": opp.sector,
                "summary": opp.summary,
                "deadline": opp.deadline,
                "program": opp.program,
                "budget": opp.budget,
                "url": opp.url,
                "found": opp.found,
            }

        opp.set_three_matched_scores_and_recommended_partners_ids([])  # Initialize with empty list
        opp_json = json.dumps(opportunity_to_dict(opp), indent=4)

        print(opp_json)
        db.session.add(opp)
        db.session.commit()

        print("Project saved successfully.")


    async def get_openai_response(self, prompt, query):
        """Get response from OpenAI API"""
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # You can use "gpt-4", "gpt-3.5-turbo", etc.
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query},
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content
    


    async def scrape_page(self):
        """Main function to scrape projects with proper pagination"""

        try:
            while True:
                await self.setup_driver()
                try:
                    self.driver.get(self.get_url())
                    # Wait for all of page to load
                    await self.wait_for_completed_loading()

                    # Print page title and URL for debugging
                    print(f"Page title: {self.driver.title}")
                    print(f"Current URL: {self.driver.current_url}")

                    await self.extract_projects_data();

                    # Check for next page
                    print("Checking for next page...")
                    if await self.find_and_click_next_page():
                        print("Successfully navigated to next page")
                        self.driver.quit()
                        self.driver = None
                        time.sleep(3)  # Wait before next page
                        continue
                    else:
                        print(f"No next page available in {self.get_name()}, ending pagination.")
                        logging.info("No next page button found, ending.")
                        break

                except Exception as e:
                    logging.error(f"Error scraping page {self.os_num}: {e}")
                    print(f"Error on page {self.os_num}: {e}")

        except Exception as e:
            logging.error(f"Fatal error in scrape_page: {e}")
            print(f"Fatal error: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                print("Driver closed")


    # class that must be implemented

    def get_url(self):
        """Generate URL for pagination"""
        raise NotImplementedError("The 'get_url' method must be implemented in subclasses.")

    def get_name(self):
        """Return name of site"""
        raise NotImplementedError("The 'get_name' method must be implemented in subclasses.")

    async def extract_projects_data(self):
        """Abstract method for extracting a projects data"""
        raise NotImplementedError("The 'extract_projects_data' method must be implemented in subclasses.")

    async def find_and_click_next_page(self):
        """Find and click the 'Next Page' button"""
        raise NotImplementedError("The 'find_and_click_next_page' method must be implemented in subclasses.")

    async def extract_project_data(self, url):
        """extract project data in page with url"""
        raise NotImplementedError("The 'extract_project_data' method must be implemented in subclasses.")
