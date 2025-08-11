#!/usr/bin/env python3
"""
Dynamic World Bank Scraper - Handles JavaScript-loaded content
This version waits for dynamic content to actually appear before scraping
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

def wait_for_dynamic_content(driver, max_wait=60):
    """Wait for dynamic content to actually appear on the page"""
    print("Waiting for dynamic content to load...")
    
    start_time = time.time()
    last_content_length = 0
    stable_count = 0
    
    while time.time() - start_time < max_wait:
        try:
            # Check if project content has appeared
            project_selectors = [
                ".project_recentdata",
                "[class*='project']",
                "table",
                "tr",
                "div[class*='item']",
                "div[class*='row']"
            ]
            
            total_content_length = 0
            for selector in project_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        total_content_length += len(elem.text)
                except Exception:
                    continue
            
            print(f"Current content length: {total_content_length}")
            
            # Check if content is stable (not changing)
            if total_content_length == last_content_length:
                stable_count += 1
                if stable_count >= 3:  # Content stable for 3 consecutive checks
                    print(f"Content appears stable at {total_content_length} characters")
                    break
            else:
                stable_count = 0
                last_content_length = total_content_length
            
            # Wait before next check
            time.sleep(2)
            
        except Exception as e:
            print(f"Error checking content: {e}")
            time.sleep(2)
    
    # Final wait for any remaining animations
    time.sleep(3)
    print("Dynamic content wait completed")

def wait_for_projects_to_appear(driver, timeout=60):
    """Wait specifically for project data to appear"""
    print("Waiting for project data to appear...")
    
    try:
        # Wait for any element that might contain project data
        WebDriverWait(driver, timeout).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "tr, div[class*='project'], div[class*='item']")) > 0
        )
        print("Project elements detected!")
        return True
    except Exception:
        print("Timeout waiting for project elements")
        return False

def find_project_container(driver):
    """Find the container that actually holds project data"""
    print("Searching for project container...")
    
    # Wait for projects to appear first
    if not wait_for_projects_to_appear(driver):
        print("No projects appeared, trying alternative approach")
    
    # Try multiple approaches to find the project container
    containers = []
    
    # Method 1: Look for elements with project-related content
    project_selectors = [
        "table",
        "div[class*='project']",
        "div[class*='recent']",
        "div[class*='content']",
        "main",
        ".content",
        ".main-content"
    ]
    
    for selector in project_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for elem in elements:
                text_length = len(elem.text.strip())
                if text_length > 100:  # Only consider elements with substantial content
                    containers.append((elem, text_length, selector))
        except Exception:
            continue
    
    # Sort by content length (most content first)
    containers.sort(key=lambda x: x[1], reverse=True)
    
    if containers:
        best_container = containers[0]
        print(f"Selected container: {best_container[2]} with {best_container[1]} characters")
        return best_container[0]
    
    # Fallback: use body if no good container found
    print("Using body as fallback container")
    return driver.find_element(By.TAG_NAME, "body")

def extract_project_data(driver, container):
    """Extract project data from the container"""
    print("Extracting project data...")
    
    projects = []
    
    # Try multiple approaches to find project rows
    rows = []
    
    # Method 1: Table rows
    try:
        if container.tag_name == "table":
            rows = container.find_elements(By.TAG_NAME, "tr")
            print(f"Found {len(rows)} table rows")
        else:
            # Look for tables within the container
            tables = container.find_elements(By.TAG_NAME, "table")
            if tables:
                rows = tables[0].find_elements(By.TAG_NAME, "tr")
                print(f"Found {len(rows)} table rows in container")
    except Exception:
        print("No table found, trying other methods")
    
    # Method 2: Project divs
    if not rows:
        try:
            project_divs = container.find_elements(By.CSS_SELECTOR, "div[class*='project'], div[class*='item'], div[class*='row']")
            rows = project_divs
            print(f"Found {len(project_divs)} project divs")
        except Exception:
            print("No project divs found")
    
    # Method 3: Any clickable elements
    if not rows:
        try:
            clickable = container.find_elements(By.CSS_SELECTOR, "a, button, [onclick], [role='button']")
            rows = clickable
            print(f"Found {len(clickable)} clickable elements")
        except Exception:
            print("No clickable elements found")
    
    # Method 4: Any elements with substantial text
    if not rows:
        try:
            all_elements = container.find_elements(By.XPATH, ".//*")
            substantial_elements = []
            for elem in all_elements:
                text = elem.text.strip()
                if len(text) > 20 and any(keyword in text.lower() for keyword in ['project', 'funding', 'procurement', 'tender']):
                    substantial_elements.append(elem)
            rows = substantial_elements
            print(f"Found {len(substantial_elements)} substantial elements")
        except Exception:
            print("No substantial elements found")
    
    if not rows:
        print("No project rows found")
        return []
    
    print(f"Processing {len(rows)} potential project rows")
    
    # Process each row
    for i, row in enumerate(rows):
        try:
            # Skip elements with very little text
            text = row.text.strip()
            if len(text) < 10:
                continue
            
            # Skip navigation/menu elements
            if any(keyword in text.lower() for keyword in ['menu', 'navigation', 'search', 'browse', 'what we do']):
                continue
            
            print(f"\nProcessing row {i+1}:")
            print(f"  Tag: {row.tag_name}")
            print(f"  Class: {row.get_attribute('class')}")
            print(f"  Text: {text[:100]}...")
            
            # Extract basic project information
            project = {
                "project_name": "",
                "client": "World Bank",
                "country": "",
                "sector": "",
                "summary": "",
                "deadline": "",
                "program": "",
                "budget": "",
                "url": "",
                "raw_text": text,
                "scraped_date": datetime.now().isoformat()
            }
            
            # Try to extract project name from text
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if lines:
                # First substantial line is likely the project name
                for line in lines:
                    if len(line) > 10 and not any(keyword in line.lower() for keyword in ['search', 'browse', 'menu', 'navigation']):
                        project["project_name"] = line
                        break
            
            # Try to extract URL
            try:
                if row.tag_name == "a":
                    project["url"] = row.get_attribute("href") or WB_URL
                else:
                    link = row.find_element(By.TAG_NAME, "a")
                    if link:
                        project["url"] = link.get_attribute("href") or WB_URL
                    else:
                        project["url"] = WB_URL
            except Exception:
                project["url"] = WB_URL
            
            # Try to extract other fields from text
            text_lower = text.lower()
            
            # Look for country patterns
            country_patterns = ['republic of', 'united states', 'united kingdom', 'south africa', 'india', 'china']
            for pattern in country_patterns:
                if pattern in text_lower:
                    project["country"] = pattern.title()
                    break
            
            # Look for date patterns
            import re
            date_pattern = r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}\b'
            dates = re.findall(date_pattern, text, re.IGNORECASE)
            if dates:
                project["deadline"] = dates[0]
            
            # Look for budget patterns
            budget_pattern = r'\$[\d,]+(?:\.\d{2})?|\d+(?:\.\d{2})?\s*(?:million|billion|thousand)'
            budgets = re.findall(budget_pattern, text, re.IGNORECASE)
            if budgets:
                project["budget"] = budgets[0]
            
            # Validate project
            if project["project_name"] and len(project["project_name"]) > 5:
                projects.append(project)
                print(f"  ✓ Added project: {project['project_name']}")
            else:
                print(f"  ✗ Skipped (no valid project name)")
            
        except Exception as e:
            print(f"  ✗ Error processing row {i+1}: {e}")
            continue
    
    return projects

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

def scrape_wb_dynamic():
    """Main scraping function that handles dynamic content"""
    driver = None
    
    try:
        print("Setting up driver...")
        driver = setup_driver()
        
        print(f"Navigating to: {WB_URL}")
        driver.get(WB_URL)
        
        # Wait for page to load completely
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        print(f"Page title: {driver.title}")
        print(f"Current URL: {driver.current_url}")
        
        # Wait for dynamic content to load
        wait_for_dynamic_content(driver)
        
        # Find the project container
        project_container = find_project_container(driver)
        
        # Extract project data
        projects = extract_project_data(driver, project_container)
        
        print(f"\nTotal projects found: {len(projects)}")
        
        # Save projects to files
        if projects:
            save_to_csv(projects, CSV_FILE)
            save_to_json(projects, JSON_FILE)
        
        return projects
        
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
    print("Starting World Bank scraper (dynamic content mode)...")
    projects = scrape_wb_dynamic()
    
    print(f"\n{'='*50}")
    print(f"SCRAPING COMPLETED")
    print(f"Total projects found: {len(projects)}")
    if projects:
        print(f"Data saved to:")
        print(f"  CSV: {CSV_FILE}")
        print(f"  JSON: {JSON_FILE}")
    print(f"{'='*50}") 