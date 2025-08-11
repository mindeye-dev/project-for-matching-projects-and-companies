#!/usr/bin/env python3
"""
Advanced debugging script for World Bank page structure
This will analyze the exact HTML structure to understand why projects aren't being found
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options as FirefoxOptions

def setup_driver():
    """Setup Firefox driver with debugging enabled"""
    options = FirefoxOptions()
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)
    options.set_preference("general.useragent.override",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Firefox(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: ()=> undefined})")
    return driver

def print_element_details(element, description="Element"):
    """Print detailed information about an element"""
    try:
        print(f"\n=== {description.upper()} DETAILS ===")
        print(f"Tag: {element.tag_name}")
        print(f"Class: {element.get_attribute('class')}")
        print(f"ID: {element.get_attribute('id')}")
        print(f"Text length: {len(element.text)}")
        print(f"Text (first 300 chars): {element.text[:300]}...")
        
        # Check for children
        children = element.find_elements(By.XPATH, "./*")
        print(f"Number of direct children: {len(children)}")
        
        if children:
            print("Direct children:")
            for i, child in enumerate(children[:5]):  # Show first 5 children
                print(f"  {i+1}. {child.tag_name}: {child.get_attribute('class')}")
                if child.text.strip():
                    print(f"     Text: {child.text[:100]}...")
        
        # Check for specific project-related elements
        project_elements = element.find_elements(By.CSS_SELECTOR, "[class*='project'], [class*='item'], [class*='row']")
        print(f"Project-related elements found: {len(project_elements)}")
        
        if project_elements:
            for i, proj_elem in enumerate(project_elements[:3]):
                print(f"  Project element {i+1}: {proj_elem.tag_name} - {proj_elem.get_attribute('class')}")
                print(f"    Text: {proj_elem.text[:150]}...")
        
        print(f"=== END {description.upper()} DETAILS ===\n")
        
    except Exception as e:
        print(f"Error printing element details: {e}")

def analyze_wb_structure():
    """Analyze the World Bank page structure in detail"""
    driver = None
    try:
        print("Setting up driver...")
        driver = setup_driver()
        
        url = "https://projects.worldbank.org/en/projects-operations/projects-home"
        print(f"Navigating to: {url}")
        
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        # Wait for dynamic content
        time.sleep(5)
        
        print(f"Page title: {driver.title}")
        print(f"Current URL: {driver.current_url}")
        
        # Find the project_recentdata element
        try:
            project_container = driver.find_element(By.CLASS_NAME, "project_recentdata")
            print("Found project_recentdata element!")
            print_element_details(project_container, "PROJECT_RECENTDATA")
            
            # Look deeper into the structure
            print("\n=== DEEP STRUCTURE ANALYSIS ===")
            
            # Check for iframes
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            print(f"Found {len(iframes)} iframes")
            
            if iframes:
                for i, iframe in enumerate(iframes):
                    print(f"Iframe {i+1}: src={iframe.get_attribute('src')}")
                    try:
                        driver.switch_to.frame(iframe)
                        print(f"  Iframe {i+1} content:")
                        iframe_body = driver.find_element(By.TAG_NAME, "body")
                        print(f"    Text length: {len(iframe_body.text)}")
                        print(f"    Text preview: {iframe_body.text[:200]}...")
                        driver.switch_to.default_content()
                    except Exception as e:
                        print(f"  Error accessing iframe {i+1}: {e}")
                        driver.switch_to.default_content()
            
            # Check for shadow DOM
            print("\nChecking for shadow DOM...")
            try:
                shadow_hosts = driver.execute_script("""
                    return Array.from(document.querySelectorAll('*'))
                        .filter(el => el.shadowRoot)
                        .map(el => ({tag: el.tagName, class: el.className}));
                """)
                if shadow_hosts:
                    print(f"Found {len(shadow_hosts)} shadow DOM hosts:")
                    for host in shadow_hosts:
                        print(f"  {host['tag']}: {host['class']}")
                else:
                    print("No shadow DOM found")
            except Exception as e:
                print(f"Error checking shadow DOM: {e}")
            
            # Check for specific project patterns
            print("\n=== PROJECT PATTERN SEARCH ===")
            
            # Look for any text that might contain project information
            all_text = project_container.text
            if all_text:
                lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                print(f"Total text lines: {len(lines)}")
                print("First 10 non-empty lines:")
                for i, line in enumerate(lines[:10]):
                    print(f"  {i+1}. {line}")
            
            # Look for specific project indicators
            project_indicators = ["project", "funding", "procurement", "tender", "opportunity"]
            for indicator in project_indicators:
                count = all_text.lower().count(indicator)
                print(f"'{indicator}' appears {count} times")
            
            # Check for hidden elements
            print("\n=== HIDDEN ELEMENTS CHECK ===")
            hidden_elements = project_container.find_elements(By.CSS_SELECTOR, "[style*='display: none'], [style*='visibility: hidden'], [hidden]")
            print(f"Found {len(hidden_elements)} hidden elements")
            
            if hidden_elements:
                for i, hidden in enumerate(hidden_elements[:3]):
                    print(f"  Hidden element {i+1}: {hidden.tag_name} - {hidden.get_attribute('class')}")
                    print(f"    Style: {hidden.get_attribute('style')}")
                    print(f"    Text: {hidden.text[:100]}...")
            
            # Check for elements with specific data attributes
            print("\n=== DATA ATTRIBUTES CHECK ===")
            data_elements = project_container.find_elements(By.CSS_SELECTOR, "[data-*]")
            print(f"Found {len(data_elements)} elements with data attributes")
            
            if data_elements:
                for i, data_elem in enumerate(data_elements[:5]):
                    attrs = data_elem.get_attribute("outerHTML")
                    print(f"  Data element {i+1}: {attrs[:200]}...")
            
            # Check for JavaScript-rendered content
            print("\n=== JAVASCRIPT CONTENT CHECK ===")
            try:
                # Check if there are any script tags that might be loading content
                scripts = project_container.find_elements(By.TAG_NAME, "script")
                print(f"Found {len(scripts)} script tags in project container")
                
                # Check for common loading patterns
                loading_patterns = [
                    "loading", "spinner", "loader", "ajax", "fetch", "xmlhttprequest"
                ]
                
                for pattern in loading_patterns:
                    elements = project_container.find_elements(By.CSS_SELECTOR, f"[class*='{pattern}'], [id*='{pattern}']")
                    if elements:
                        print(f"Found {len(elements)} elements with '{pattern}' pattern")
                        for elem in elements[:2]:
                            print(f"  {elem.tag_name}: {elem.get_attribute('class')}")
                
            except Exception as e:
                print(f"Error checking JavaScript content: {e}")
            
        except Exception as e:
            print(f"Error finding project_recentdata: {e}")
        
        # Also check the entire page for project-related content
        print("\n=== ENTIRE PAGE PROJECT SEARCH ===")
        
        # Look for any elements that might contain project data
        project_selectors = [
            "[class*='project']", "[class*='opportunity']", "[class*='tender']",
            "[class*='procurement']", "[class*='funding']", "[class*='row']",
            "table", "tr", "li", "div[class*='item']"
        ]
        
        for selector in project_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"Selector '{selector}': Found {len(elements)} elements")
                    # Show first few elements
                    for i, elem in enumerate(elements[:3]):
                        text = elem.text.strip()
                        if text and len(text) > 10:
                            print(f"  Element {i+1}: {elem.tag_name} - {text[:100]}...")
            except Exception as e:
                print(f"Selector '{selector}' failed: {e}")
        
        print("\n=== DEBUGGING COMPLETED ===")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()
            print("Driver closed")

if __name__ == "__main__":
    print("Starting World Bank structure analysis...")
    analyze_wb_structure()
    print("Analysis completed.") 