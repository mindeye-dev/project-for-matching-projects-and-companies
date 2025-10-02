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

    async def handle_cloudflare_captcha(self):
        """Handle Cloudflare CAPTCHA"""
        start_time = time.time()
        
        # Keep solving CAPTCHA until the timeout is reached or CAPTCHA disappears
        while await self.is_cloudflare_captcha_present(30):
            await self.solve_cloudflare_captcha()
            
            # Sleep to allow for the CAPTCHA solving to process
            time.sleep(2)  # You can adjust this depending on how long CAPTCHA solving takes

            # Check if CAPTCHA is still present after attempting to solve it
            if time.time() - start_time > 180:  # If it takes longer than 3 minutes, break the loop
                print("Timeout reached. CAPTCHA was not solved.")
                break
            
        # Verify if CAPTCHA was solved successfully
        if not await self.is_cloudflare_captcha_present(30):
            print("CAPTCHA solved successfully.")
        else:
            print("Failed to solve CAPTCHA.")
    
    async def solve_cloudflare_captcha(self):
        """Solve Cloudflare CAPTCHA with improved detection and handling"""
        try:
            print("Attempting to solve Cloudflare CAPTCHA...")
            
            # Wait for page to load and check for CAPTCHA elements
            wait = WebDriverWait(self.driver, 15)
            
            # Multiple selectors for Cloudflare challenge elements
            cloudflare_selectors = [
                "iframe[src*='challenges.cloudflare.com']",
                "iframe[src*='cf-chl-widget']",
                "iframe[id*='cf-chl-widget']",
                "iframe[class*='cf-chl-widget']",
                "iframe[src*='turnstile']"
            ]
            
            challenge_frame = None
            for selector in cloudflare_selectors:
                try:
                    challenge_frame = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    print(f"Found Cloudflare challenge frame with selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not challenge_frame:
                print("No Cloudflare challenge frame found")
                return False
            
            # Switch to the challenge frame
            self.driver.switch_to.frame(challenge_frame)
            
            # Multiple selectors for the checkbox
            checkbox_selectors = [
                "input[type='checkbox']",
                "input[type='checkbox'][id*='challenge']",
                "input[type='checkbox'][class*='challenge']",
                "input[type='checkbox'][id*='cf-chl-widget']",
                "input[type='checkbox'][class*='cf-chl-widget']",
                "input[type='checkbox'][id*='turnstile']",
                "input[type='checkbox'][class*='turnstile']"
            ]
            
            checkbox_clicked = False
            for selector in checkbox_selectors:
                try:
                    checkbox = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    print(f"Found checkbox with selector: {selector}")
                    
                    # Scroll to element if needed
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                    time.sleep(1)
                    
                    # Click the checkbox
                    checkbox.click()
                    checkbox_clicked = True
                    print("CAPTCHA checkbox clicked successfully")
                    break
                except (TimeoutException, ElementClickInterceptedException):
                    continue
            
            # Switch back to default content
            self.driver.switch_to.default_content()
            
            if not checkbox_clicked:
                print("No clickable checkbox found in challenge frame")
                return False
            
            # Wait for CAPTCHA to complete (multiple indicators)
            print("Waiting for CAPTCHA to complete...")
            
            # Wait up to 30 seconds for completion
            for i in range(30):
                try:
                    # Check if challenge frame is gone (indicator of completion)
                    self.driver.find_element(By.CSS_SELECTOR, "iframe[src*='challenges.cloudflare.com']")
                except:
                    print("Challenge frame disappeared - CAPTCHA likely completed")
                    return True
                
                # Check for success indicators
                try:
                    success_elements = [
                        "div[class*='cf-chl-widget'][class*='success']",
                        "div[class*='challenge-success']",
                        "div[class*='turnstile-success']"
                    ]
                    for selector in success_elements:
                        if self.driver.find_element(By.CSS_SELECTOR, selector):
                            print("CAPTCHA completed successfully")
                            return True
                except:
                    pass
                
                time.sleep(1)
            
            print("CAPTCHA completion timeout - may need manual intervention")
            return False
            
        except Exception as e:
            print(f"Error solving Cloudflare CAPTCHA: {e}")
            # Ensure we're back to default content
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False

    async def wait_for_captcha_completion(self, timeout=30):
        """Wait for CAPTCHA to complete with better detection"""
        print("Waiting for CAPTCHA to complete...")
        
        for i in range(timeout):
            try:
                # Check if challenge frame is gone (indicator of completion)
                self.driver.find_element(By.CSS_SELECTOR, "iframe[src*='challenges.cloudflare.com']")
            except:
                print("Challenge frame disappeared - CAPTCHA likely completed")
                return True
            
            # Check for success indicators
            try:
                success_elements = [
                    "div[class*='cf-chl-widget'][class*='success']",
                    "div[class*='challenge-success']",
                    "div[class*='turnstile-success']"
                ]
                for selector in success_elements:
                    if self.driver.find_element(By.CSS_SELECTOR, selector):
                        print("CAPTCHA completed successfully")
                        return True
            except:
                pass
            
            time.sleep(1)
        
        print("CAPTCHA completion timeout - may need manual intervention")
        return False

    
    async def is_cloudflare_captcha_present(self, timeout=50):
        """Check if Cloudflare CAPTCHA is present with multiple detection methods"""
        try:
            # Method 1: Check for specific Cloudflare elements
            cloudflare_selectors = [
                "iframe[src*='challenges.cloudflare.com']",
                "iframe[src*='cf-chl-widget']",
                "iframe[id*='cf-chl-widget']",
                "iframe[class*='cf-chl-widget']",
                "iframe[src*='turnstile']",
                "div[class*='cf-chl-widget']",
                "div[id*='cf-chl-widget']",
                "div[class*='challenge']",
                "div[id*='challenge']"
            ]
            
            for selector in cloudflare_selectors:
                try:
                    WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    print(f"Cloudflare CAPTCHA detected with selector: {selector}")
                    return True
                except TimeoutException:
                    continue
            
            # Method 2: Check page source for Cloudflare indicators
            page_source = self.driver.page_source.lower()
            cloudflare_indicators = [
                "challenges.cloudflare.com",
                "cf-chl-widget",
                "cloudflare challenge",
                "checking your browser",
                "please wait while we check your browser",
                "ddos protection by cloudflare",
                "security check",
                "turnstile"
            ]
            
            for indicator in cloudflare_indicators:
                if indicator in page_source:
                    print(f"Cloudflare CAPTCHA detected in page source: {indicator}")
                    return True
            
            # Method 3: Check for specific text patterns
            text_patterns = [
                "www.adb.org needs to review the security of your connection before proceeding",
                "just a moment",
                "checking your browser",
                "please wait",
                "security check",
                "ddos protection"
            ]
            
            for pattern in text_patterns:
                if pattern.lower() in page_source:
                    print(f"Cloudflare CAPTCHA detected with text pattern: {pattern}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error checking for Cloudflare CAPTCHA: {e}")
            return False

    async def is_captcha_present(self):
        """Check if any CAPTCHA is present (Cloudflare, reCAPTCHA, hCaptcha, etc.)"""
        try:
            # Check for various CAPTCHA types
            captcha_selectors = [
                # reCAPTCHA
                "iframe[src*='recaptcha']",
                "div[class*='recaptcha']",
                "div[id*='recaptcha']",
                # hCaptcha
                "iframe[src*='hcaptcha']",
                "div[class*='hcaptcha']",
                "div[id*='hcaptcha']",
                # Cloudflare
                "iframe[src*='challenges.cloudflare.com']",
                "iframe[src*='cf-chl-widget']",
                "div[class*='cf-chl-widget']",
                # Turnstile
                "iframe[src*='turnstile']",
                "div[class*='turnstile']",
                # Generic CAPTCHA
                "iframe[src*='captcha']",
                "div[class*='captcha']",
                "div[id*='captcha']",
                "input[type='checkbox'][id*='captcha']",
                "input[type='checkbox'][class*='captcha']"
            ]
            
            for selector in captcha_selectors:
                try:
                    WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    print(f"CAPTCHA detected with selector: {selector}")
                    return True
                except TimeoutException:
                    continue
            
            # Check page source for CAPTCHA indicators
            page_source = self.driver.page_source.lower()
            captcha_indicators = [
                "recaptcha",
                "hcaptcha",
                "cloudflare",
                "turnstile",
                "captcha",
                "challenge",
                "security check",
                "verify you are human",
                "prove you are not a robot"
            ]
            
            for indicator in captcha_indicators:
                if indicator in page_source:
                    print(f"CAPTCHA detected in page source: {indicator}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error checking for CAPTCHA: {e}")
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
            
    async def opportunity_of_url(self, input_url):
        # Query for the first match (returns None if no match is found)
        opportunity = Opportunity.query.filter_by(url=input_url).first()
        print("Opportunity is ",opportunity)
        return opportunity

    async def save_to_database(self, project):
        """Save project data to the database"""
        print("saving database now.")
        existing_opportunity=await self.opportunity_of_url(project["url"]);
        if existing_opportunity is not None:
            print("URL already exists. Updating the existing project...")
    
            # Update the fields with new data from the project dictionary
            existing_opportunity.project_name = project["title"]
            existing_opportunity.client = project["client"]
            existing_opportunity.country = project["country"]
            existing_opportunity.sector = project["sector"]
            existing_opportunity.summary = project["summary"]
            existing_opportunity.deadline = project["deadline"]
            existing_opportunity.program = project["program"]
            existing_opportunity.budget = project["budget"]
            existing_opportunity.found = False  # You can modify this as needed
            
            # Reset the three_matched_scores_and_recommended_partners_ids field
            existing_opportunity.set_three_matched_scores_and_recommended_partners_ids([])

            # Save the updates to the database
            db.session.commit()

            print("Existing project updated successfully.")
        else:
            print("adding new project to database")
            try:
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
            except Exception as e:
                print("Error in saving database", e)


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
                if not self.is_next_page_by_click():
                    await self.setup_driver()
                elif self.page_num == 0:
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

    async def is_next_page_by_click(self):
        """Return whether next page is transacted by clicking button"""
        raise NotImplementedError("The 'is_next_page_by_click' method must be implemented in subclasses.")


    async def extract_project_data(self, url):
        """extract project data in page with url"""
        raise NotImplementedError("The 'extract_project_data' method must be implemented in subclasses.")
