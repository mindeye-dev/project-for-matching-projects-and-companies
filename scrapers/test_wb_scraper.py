#!/usr/bin/env python3
"""
Test script for World Bank scraper to help debug issues
"""

import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options as FirefoxOptions

def setup_test_driver():
    """Setup a test driver with debugging enabled"""
    options = FirefoxOptions()
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)
    options.set_preference("general.useragent.override", 
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Firefox(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: ()=> undefined})")
    return driver

def test_wb_page_structure():
    """Test the World Bank page structure to understand what elements are available"""
    driver = None
    try:
        print("Setting up test driver...")
        driver = setup_test_driver()
        
        url = "https://projects.worldbank.org/en/projects-operations/projects-home"
        print(f"Navigating to: {url}")
        
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        # Wait for dynamic content
        time.sleep(5)
        
        print(f"\nPage Title: {driver.title}")
        print(f"Current URL: {driver.current_url}")
        
        # Check for common project-related elements
        print("\n=== SEARCHING FOR PROJECT ELEMENTS ===")
        
        # Look for elements with 'project' in class name
        project_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='project']")
        print(f"Found {len(project_elements)} elements with 'project' in class name:")
        for i, elem in enumerate(project_elements[:5]):
            print(f"  {i+1}. {elem.tag_name}: {elem.get_attribute('class')}")
            print(f"     Text: {elem.text[:100]}...")
        
        # Look for elements with 'recent' in class name
        recent_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='recent']")
        print(f"\nFound {len(recent_elements)} elements with 'recent' in class name:")
        for i, elem in enumerate(recent_elements[:5]):
            print(f"  {i+1}. {elem.tag_name}: {elem.get_attribute('class')}")
            print(f"     Text: {elem.text[:100]}...")
        
        # Look for tables
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"\nFound {len(tables)} tables:")
        for i, table in enumerate(tables[:3]):
            print(f"  {i+1}. Table class: {table.get_attribute('class')}")
            rows = table.find_elements(By.TAG_NAME, "tr")
            print(f"     Rows: {len(rows)}")
            if rows:
                print(f"     First row text: {rows[0].text[:100]}...")
        
        # Look for links
        links = driver.find_elements(By.TAG_NAME, "a")
        project_links = [link for link in links if "project" in link.text.lower() or "project" in (link.get_attribute("href") or "")]
        print(f"\nFound {len(project_links)} project-related links:")
        for i, link in enumerate(project_links[:5]):
            print(f"  {i+1}. Text: {link.text[:50]}...")
            print(f"     Href: {link.get_attribute('href')}")
        
        # Look for specific class names mentioned in the original scraper
        specific_classes = ["project_recentdata", "projects-container", "projects-list", "recent-projects"]
        for class_name in specific_classes:
            try:
                elem = driver.find_element(By.CLASS_NAME, class_name)
                print(f"\nFound element with class '{class_name}':")
                print(f"  Tag: {elem.tag_name}")
                print(f"  Text length: {len(elem.text)}")
                print(f"  First 200 chars: {elem.text[:200]}...")
            except Exception as e:
                print(f"\nClass '{class_name}' not found: {e}")
        
        # Check for pagination
        print("\n=== CHECKING FOR PAGINATION ===")
        pagination_selectors = [
            ".pagination", "[class*='pagination']", 
            "[class*='next']", "[class*='page']"
        ]
        for selector in pagination_selectors:
            try:
                elems = driver.find_elements(By.CSS_SELECTOR, selector)
                if elems:
                    print(f"Found pagination with selector '{selector}': {len(elems)} elements")
                    for elem in elems[:2]:
                        print(f"  Text: {elem.text[:100]}...")
            except Exception:
                pass
        
        # Look for next page buttons
        next_buttons = driver.find_elements(By.XPATH, "//a[contains(text(), 'Next')]")
        if next_buttons:
            print(f"\nFound {len(next_buttons)} 'Next' buttons:")
            for i, btn in enumerate(next_buttons):
                print(f"  {i+1}. Text: {btn.text}")
                print(f"     Enabled: {btn.is_enabled()}")
                print(f"     Displayed: {btn.is_displayed()}")
        
        # Check page source for clues
        print("\n=== PAGE SOURCE ANALYSIS ===")
        page_source = driver.page_source
        print(f"Page source length: {len(page_source)}")
        
        # Look for project-related text in page source
        project_keywords = ["project", "opportunity", "tender", "procurement", "funding"]
        for keyword in project_keywords:
            count = page_source.lower().count(keyword)
            print(f"  '{keyword}' appears {count} times in page source")
        
        # Look for specific patterns
        if "project_recentdata" in page_source:
            print("  'project_recentdata' found in page source")
        else:
            print("  'project_recentdata' NOT found in page source")
        
        print("\n=== TEST COMPLETED ===")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()
            print("Test driver closed")

if __name__ == "__main__":
    print("Starting World Bank scraper test...")
    test_wb_page_structure()
    print("Test completed.") 