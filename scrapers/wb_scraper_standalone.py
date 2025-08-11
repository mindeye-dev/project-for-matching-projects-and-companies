#!/usr/bin/env python3
"""
Standalone World Bank Scraper - No backend dependency
This version saves data to local files and handles single-page project listings
"""

import os
import time
import json
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options as FirefoxOptions

# --- Config ---
WB_URL = "https://projects.worldbank.org/en/projects-operations/projects-home"
HEADLESS = os.environ.get("HEADLESS", "0") == "1"
OUTPUT_DIR = "wb_data"
CSV_FILE = os.path.join(OUTPUT_DIR, f"wb_projects_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
JSON_FILE = os.path.join(OUTPUT_DIR, f"wb_projects_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

def setup_driver():
    """Setup Firefox driver with enhanced stealth"""
    options = FirefoxOptions()
    if HEADLESS:
        options.add_argument("--headless")
    
    # Enhanced stealth settings
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)
    options.set_preference("general.useragent.override", 
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Additional stealth preferences
    options.set_preference("dom.webnotifications.enabled", False)
    options.set_preference("media.volume_scale", "0.0")
    options.set_preference("network.proxy.type", 0)
    options.set_preference("privacy.resistFingerprinting", False)
    options.set_preference("browser.cache.disk.enable", False)
    options.set_preference("browser.cache.memory.enable", False)
    
    driver = webdriver.Firefox(options=options)
    
    # Enhanced stealth: remove webdriver properties
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: ()=> undefined})")
    driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: ()=> [1, 2, 3, 4, 5]})")
    driver.execute_script("Object.defineProperty(navigator, 'languages', {get: ()=> ['en-US', 'en']})")
    
    return driver

def wait_for_dynamic_content(driver, timeout=30):
    """Wait for dynamic content to load on the page"""
    try:
        # Wait for any AJAX requests to complete
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return jQuery.active == 0")
        )
    except Exception:
        # jQuery might not be available, continue anyway
        pass
    
    try:
        # Wait for any loading indicators to disappear
        loading_selectors = [
            ".loading", ".spinner", ".loader", "[class*='loading']", 
            "[class*='spinner']", "[class*='loader']"
        ]
        for selector in loading_selectors:
            try:
                WebDriverWait(driver, 5).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, selector))
                )
            except Exception:
                pass
    except Exception:
        pass
    
    # Additional wait for any animations to complete
    time.sleep(3)

def extract_field_by_label(driver, label_texts):
    """Extract field values by looking for label text"""
    for label in label_texts:
        try:
            elem = driver.find_element(
                By.XPATH, f"//*[contains(text(),'{label}')]/following-sibling::*[1]"
            )
            return elem.text.strip()
        except Exception:
            pass
        try:
            elem = driver.find_element(
                By.XPATH, f"//tr[th[contains(text(),'{label}')]]/td"
            )
            return elem.text.strip()
        except Exception:
            pass
    return ""

def scrape_detail_page(driver, url):
    """Scrape detailed information from project detail page"""
    driver.execute_script("window.open('');")
    driver.switch_to.window(driver.window_handles[-1])
    driver.get(url)
    time.sleep(2)
    
    fields = {}
    
    # Summary/description
    try:
        summary_elem = driver.find_element(
            By.CSS_SELECTOR,
            ".project-summary, .description, .summary, .wb-project-details__description",
        )
        fields["summary"] = summary_elem.text.strip()
    except Exception:
        fields["summary"] = ""
    
    # Budget/Cost
    fields["budget"] = extract_field_by_label(
        driver, ["Total Project Cost", "Budget", "Estimated Cost"]
    )
    
    # Program/Project
    fields["program"] = extract_field_by_label(driver, ["Program", "Project"])
    
    # Procurement Method
    fields["procurement_method"] = extract_field_by_label(
        driver, ["Procurement Method"]
    )
    
    # Notice Type
    fields["notice_type"] = extract_field_by_label(driver, ["Notice Type"])
    
    # Published Date
    fields["published_date"] = extract_field_by_label(
        driver, ["Published Date", "Publication Date"]
    )
    
    # Closing Date
    fields["closing_date"] = extract_field_by_label(
        driver, ["Closing Date", "Deadline"]
    )
    
    # Reference Number
    fields["reference_number"] = extract_field_by_label(
        driver, ["Reference Number", "Notice No"]
    )
    
    # Contact Info
    fields["contact_info"] = extract_field_by_label(
        driver, ["Contact", "Contact Information", "Contact Person"]
    )
    
    driver.close()
    driver.switch_to.window(driver.window_handles[0])
    return fields

def parse_opportunity_row(row):
    """Parse project information from a table row or div"""
    try:
        # Initialize opportunity data
        opp = {
            "project_name": "",
            "client": "World Bank",
            "country": "",
            "sector": "",
            "summary": "",
            "deadline": "",
            "program": "",
            "budget": "",
            "url": "",
            "scraped_date": datetime.now().isoformat()
        }
        
        # Try to get URL from the row
        try:
            if row.tag_name == "a":
                row_url = row.get_attribute("href")
                opp["url"] = row_url or WB_URL
            else:
                # Look for links within the row
                link = row.find_element(By.TAG_NAME, "a")
                if link:
                    opp["url"] = link.get_attribute("href") or WB_URL
                else:
                    opp["url"] = WB_URL
        except Exception:
            opp["url"] = WB_URL
        
        # Extract project name
        try:
            if row.tag_name == "a":
                opp["project_name"] = row.text.strip()
            else:
                # Try to find text content in the row
                text_content = row.text.strip()
                if text_content:
                    # Split by newlines and take the first non-empty line as project name
                    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                    if lines:
                        opp["project_name"] = lines[0]
                        
                # If no text content, try to find specific elements
                if not opp["project_name"]:
                    # Look for project name in various selectors
                    name_selectors = [
                        ".project-name", ".project-title", ".title", 
                        "h1", "h2", "h3", "h4", "h5", "h6",
                        "[class*='name']", "[class*='title']"
                    ]
                    for selector in name_selectors:
                        try:
                            name_elem = row.find_element(By.CSS_SELECTOR, selector)
                            if name_elem.text.strip():
                                opp["project_name"] = name_elem.text.strip()
                                break
                        except Exception:
                            continue
        except Exception as e:
            print(f"Error extracting project name: {e}")
            opp["project_name"] = "Unknown Project"
        
        # Extract country information
        try:
            country_selectors = [
                ".country", ".location", ".region", "[class*='country']", 
                "[class*='location']", "[class*='region']"
            ]
            for selector in country_selectors:
                try:
                    country_elem = row.find_element(By.CSS_SELECTOR, selector)
                    if country_elem.text.strip():
                        opp["country"] = country_elem.text.strip()
                        break
                except Exception:
                    continue
        except Exception:
            pass
        
        # Extract sector information
        try:
            sector_selectors = [
                ".sector", ".category", "[class*='sector']", "[class*='category']"
            ]
            for selector in sector_selectors:
                try:
                    sector_elem = row.find_element(By.CSS_SELECTOR, selector)
                    if sector_elem.text.strip():
                        opp["sector"] = sector_elem.text.strip()
                        break
                except Exception:
                    continue
        except Exception:
            pass
        
        # Extract deadline/date information
        try:
            date_selectors = [
                ".date", ".deadline", ".closing", "[class*='date']", 
                "[class*='deadline']", "[class*='closing']"
            ]
            for selector in date_selectors:
                try:
                    date_elem = row.find_element(By.CSS_SELECTOR, selector)
                    if date_elem.text.strip():
                        opp["deadline"] = date_elem.text.strip()
                        break
                except Exception:
                    continue
        except Exception:
            pass
        
        # Extract budget information
        try:
            budget_selectors = [
                ".budget", ".cost", ".amount", "[class*='budget']", 
                "[class*='cost']", "[class*='amount']"
            ]
            for selector in budget_selectors:
                try:
                    budget_elem = row.find_element(By.CSS_SELECTOR, selector)
                    if budget_elem.text.strip():
                        opp["budget"] = budget_elem.text.strip()
                        break
                except Exception:
                    continue
        except Exception:
            pass
        
        # Extract program information
        try:
            program_selectors = [
                ".program", ".type", "[class*='program']", "[class*='type']"
            ]
            for selector in program_selectors:
                try:
                    program_elem = row.find_element(By.CSS_SELECTOR, selector)
                    if program_elem.text.strip():
                        opp["program"] = program_elem.text.strip()
                        break
                except Exception:
                    continue
        except Exception:
            pass
        
        # If we still don't have a project name, try to get it from the row's HTML
        if not opp["project_name"] or opp["project_name"] == "Unknown Project":
            try:
                # Look for any text that might be a project name
                all_text = row.text.strip()
                if all_text:
                    # Take the first meaningful line
                    lines = [line.strip() for line in all_text.split('\n') if line.strip() and len(line.strip()) > 3]
                    if lines:
                        opp["project_name"] = lines[0]
            except Exception:
                pass
        
        # Validate that we have at least a project name
        if not opp["project_name"] or opp["project_name"] == "Unknown Project":
            print(f"Could not extract project name from row")
            return None
            
        return opp
        
    except Exception as e:
        print(f"Error parsing row: {e}")
        return None

def save_to_csv(projects, filename):
    """Save projects to CSV file"""
    if not projects:
        print("No projects to save")
        return
    
    fieldnames = projects[0].keys()
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for project in projects:
            writer.writerow(project)
    
    print(f"Saved {len(projects)} projects to {filename}")

def save_to_json(projects, filename):
    """Save projects to JSON file"""
    if not projects:
        print("No projects to save")
        return
    
    with open(filename, 'w', encoding='utf-8') as jsonfile:
        json.dump(projects, jsonfile, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(projects)} projects to {filename}")

def scrape_wb_standalone():
    """Main scraping function for World Bank projects"""
    driver = None
    all_projects = []
    
    try:
        print("Setting up driver...")
        driver = setup_driver()
        
        print(f"Navigating to: {WB_URL}")
        driver.get(WB_URL)
        
        # Wait for page to load completely
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        # Wait for dynamic content to load
        wait_for_dynamic_content(driver)

        print(f"Page title: {driver.title}")
        print(f"Current URL: {driver.current_url}")

        # Try to find the main project container
        project_data = None
        selectors = [
            (By.CLASS_NAME, "project_recentdata"),
            (By.CSS_SELECTOR, ".project_recentdata"),
            (By.CSS_SELECTOR, "[class*='project']"),
            (By.CSS_SELECTOR, "[class*='recent']"),
            (By.CSS_SELECTOR, ".projects-container"),
            (By.CSS_SELECTOR, ".projects-list"),
            (By.CSS_SELECTOR, ".recent-projects"),
            (By.CSS_SELECTOR, "main"),
            (By.CSS_SELECTOR, ".content"),
            (By.CSS_SELECTOR, ".main-content"),
        ]

        for selector_type, selector in selectors:
            try:
                project_data = driver.find_element(selector_type, selector)
                print(f"Found project data using {selector_type}: {selector}")
                print(f"Element tag: {project_data.tag_name}")
                print(f"Element class: {project_data.get_attribute('class')}")
                print(f"Element text length: {len(project_data.text)}")
                break
            except Exception as e:
                print(f"Selector {selector_type}: {selector} failed: {e}")
                continue

        if not project_data:
            print("Could not find main project container. Available elements:")
            elements = driver.find_elements(
                By.CSS_SELECTOR, "[class*='project'], [class*='recent'], [class*='content']"
            )
            for i, elem in enumerate(elements[:10]):
                print(f"  - {elem.tag_name}: {elem.get_attribute('class')}")

            # Try to find any table or list structure
            tables = driver.find_elements(By.TAG_NAME, "table")
            lists = driver.find_elements(By.TAG_NAME, "ul")
            divs = driver.find_elements(By.CSS_SELECTOR, "div[class*='project']")
            
            print(f"Found {len(tables)} tables, {len(lists)} lists, {len(divs)} project divs")
            
            # Use the first available container
            if tables:
                project_data = tables[0]
                print("Using first table as project container")
            elif divs:
                project_data = divs[0]
                print("Using first project div as container")
            else:
                # Fallback to body if nothing else works
                project_data = driver.find_element(By.TAG_NAME, "body")
                print("Using body as fallback container")

        print("Project data container found.")

        # Try multiple approaches to find project rows
        rows = []
        
        # Method 1: Look for table rows
        try:
            if project_data.tag_name == "table":
                rows = project_data.find_elements(By.TAG_NAME, "tr")
                print(f"Found {len(rows)} table rows")
            else:
                # Try to find table within the container
                table = project_data.find_element(By.TAG_NAME, "table")
                rows = table.find_elements(By.TAG_NAME, "tr")
                print(f"Found {len(rows)} table rows in container")
        except Exception:
            print("No table found, trying other methods")
        
        # Method 2: Look for links directly
        if not rows:
            try:
                rows = project_data.find_elements(By.TAG_NAME, "a")
                print(f"Found {len(rows)} links directly")
            except Exception:
                print("No links found directly")
        
        # Method 3: Look for divs with project information
        if not rows:
            try:
                project_divs = project_data.find_elements(By.CSS_SELECTOR, "div[class*='project'], div[class*='item'], div[class*='card']")
                rows = project_divs
                print(f"Found {len(project_divs)} project divs")
            except Exception:
                print("No project divs found")
        
        # Method 4: Look for any clickable elements that might contain project info
        if not rows:
            try:
                clickable = project_data.find_elements(By.CSS_SELECTOR, "a, button, [onclick], [role='button']")
                rows = clickable
                print(f"Found {len(clickable)} clickable elements")
            except Exception:
                print("No clickable elements found")

        if not rows:
            print("No project rows found. Available elements in container:")
            container_text = project_data.text.strip()
            if container_text:
                print(f"Container text (first 500 chars): {container_text[:500]}...")
            return []

        print(f"Processing {len(rows)} project rows")
        
        # Process each row
        for i, row in enumerate(rows):
            try:
                # Skip header rows if it's a table
                if row.tag_name == "tr":
                    # Check if this row has headers
                    headers = row.find_elements(By.TAG_NAME, "th")
                    if headers:
                        print(f"Skipping header row {i+1}")
                        continue
                
                # Extract project information
                opp = parse_opportunity_row(row)
                
                if not opp:
                    print(f"Could not parse row {i+1}")
                    continue
                    
                print(f"Processing project {i+1}: {opp['project_name']}")
                
                # Scrape detail page for more info if a detail link exists
                if opp["url"] and opp["url"] != WB_URL:
                    try:
                        detail_fields = scrape_detail_page(driver, opp["url"])
                        opp.update(detail_fields)
                        print(f"Added detail fields: {list(detail_fields.keys())}")
                    except Exception as e:
                        print(f"Failed to scrape detail page: {e}")
                
                all_projects.append(opp)
                print(f"Successfully processed project {i+1}")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"Error processing row {i+1}: {e}")
                continue
        
        print(f"Total projects processed: {len(all_projects)}")
        
        # Save projects to files
        if all_projects:
            save_to_csv(all_projects, CSV_FILE)
            save_to_json(all_projects, JSON_FILE)
        
        return all_projects
        
    except Exception as e:
        print(f"Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if driver:
            driver.quit()
            print("Driver closed")

if __name__ == "__main__":
    print("Starting World Bank scraper (standalone mode)...")
    projects = scrape_wb_standalone()
    
    print(f"\n{'='*50}")
    print(f"SCRAPING COMPLETED")
    print(f"Total projects found: {len(projects)}")
    if projects:
        print(f"Data saved to:")
        print(f"  CSV: {CSV_FILE}")
        print(f"  JSON: {JSON_FILE}")
    print(f"{'='*50}") 