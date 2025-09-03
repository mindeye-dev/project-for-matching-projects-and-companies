from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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


BACKEND_API = os.environ.get("BACKEND_API", "http://localhost:5000/api/opportunity")
HEADLESS = os.environ.get("HEADLESS", "0") == "1"
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK", "")

def export_excel(filename, data_array):
    df = pd.DataFrame(data_array)
    df.to_excel(filename, index=False)


def notify_error(message):
    if SLACK_WEBHOOK:
        try:
            requests.post(SLACK_WEBHOOK, json={"text": message})
        except Exception as e:
            logging.error(f"Failed to send Slack notification: {e}")


def print_element_html(element, description="Element"):
    """Utility function to print detailed HTML of a Selenium element"""
    try:
        html_content = element.get_attribute("outerHTML")
        print(f"\n=== DETAILED HTML OF {description.upper()} ===")
        print(html_content)
        print(f"=== END OF {description.upper()} HTML ===\n")
    except Exception as e:
        print(f"Error printing HTML for {description}: {e}")

def setup_driver(proxy=None):
    options = FirefoxOptions()
    print("--setting up driver--1")
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

    print("--setting up driver--2")

    # Create the Firefox driver
    driver = webdriver.Firefox(options=options)

    # Enhanced stealth: remove webdriver properties
    print("--setting up driver--3")
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: ()=> undefined})"
    )
    driver.execute_script(
        "Object.defineProperty(navigator, 'plugins', {get: ()=> [1, 2, 3, 4, 5]})"
    )
    driver.execute_script(
        "Object.defineProperty(navigator, 'languages', {get: ()=> ['en-US', 'en']})"
    )

    print("--setting up driver--4")
    return driver




def solve_cloudflare_captcha(driver):
    # Wait for the Turnstile checkbox iframe or container
    try:
        wait = WebDriverWait(driver, 10)

        # 1. Wait for all iframes to appear (typically CAPTCHA checkbox is inside an iframe)
        frames = wait.until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "iframe"))
        )
        checkbox_found = False

        print("Found iframe")

        # 2. Iterate through all iframes to find the checkbox input inside
        for frame in frames:
            driver.switch_to.frame(frame)  # switch to iframe
            # 3. Try to find the checkbox input inside the iframe
            try:
                checkbox = wait.until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "input[type='checkbox']")
                    )
                )
                checkbox.click()  # click the checkbox
                checkbox_found = True
                print("CAPTCHA checkbox clicked.")
                driver.switch_to.default_content()  # back to main document
                break  # stop searching after clicking
            except TimeoutException:
                # Checkbox not found in this iframe, switch back and continue
                driver.switch_to.default_content()

        if not checkbox_found:
            print("Checkbox input not found in any iframe.")

    except TimeoutException as e:
        print("No iframes found or checkbox did not appear within timeout.")


def is_cloudflare_captcha_present(driver, timeout=5):
    search_text = (
        "www.adb.org needs to review the security of your connection before proceeding"
    )

    # Get the full page source
    page_source = driver.page_source

    if search_text in page_source:
        print("Text is present on the page.")
        return True
    else:
        print("Text not found on the page.")
        return False


def is_captcha_present(driver):
    try:
        # Example: Wait for Google's reCAPTCHA iframe or element that usually appears for CAPTCHA challenges
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "iframe[src*='recaptcha']")
            )
        )
        return True
    except TimeoutException:
        # No such element appeared, CAPTCHA likely not present
        return False


def getOpenAIResponse(prompt, query):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Send a chat completion request
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # You can use "gpt-4o", "gpt-3.5-turbo", etc.
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": query},
        ],
        temperature=0.7,  # Controls creativity; 0.0 = strict, 1.0 = more creative
    )

    # Print the result
    return response.choices[0].message.content