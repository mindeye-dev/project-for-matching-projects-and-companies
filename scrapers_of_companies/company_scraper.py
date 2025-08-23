import os
import time
import requests
import logging
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
from export_excel import export_excel

from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()



def get_all_linkinurls_of_companies(country, sector):
    """Main function to get all of linkedin urls of companies"""
    page_num = 1
    driver = None
    total_projects = 0
    
    total_urls=[]

    try:
        search_url=`https://www.linkedin.com/search/results/companies/?companyHqGeo=%5B"{country}"%5D&industryCompanyVertical=%5B"{sector}"%5D&keywords={sector}&origin=FACETED_SEARCH`
        while True:
            print(f"\n{'='*50}")
            print(f"SCRAPING PAGE {page_num}")
            print(f"{'='*50}")

            print(f"Setting up driver for page {page_num}")
            driver = setup_driver()
            url = search_url
            print(f"Preparing to scrape linkedin company searching of {page_num}")
            logging.info(f"Scraping page {page_num}")

            try:
                driver.get(url)

                driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )  # Scroll to bottom

                # Wait for page to load completely
                WebDriverWait(driver, 50).until(
                    lambda d: d.execute_script("return document.readyState")
                    == "complete"
                )

                driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )  # Scroll to bottom

                # Wait for dynamic content to load
                wait_for_dynamic_content(driver)

                
                # I have to change this links.

                # Find all such rows/links
                rows = driver.find_elements(
                    By.CSS_SELECTOR,
                    ".fr-card__link",
                )

                print(f"found several rows {len(rows)}")
                
                for i, row in enumerate(rows):
                    try:
                        print(row)
                        # Extract project information
                        opp = parse_opportunity_row(row)
                        total_urls.append(opp[url])

                    except Exception as e:
                        print(f"Error processing row {i+1}: {e}")
                        continue

                print(f"Page {page_num} completed: {page_projects} projects processed")
                print(f"Total projects processed so far: {total_projects}")

                # Check for next page
                print("Checking for next page...")
                if find_and_click_next_page(driver):
                    print("Successfully navigated to next page")
                    page_num += 1
                    driver.quit()
                    driver = None
                    time.sleep(3)  # Wait before next page
                    continue
                else:
                    print("No next page available, ending pagination.")
                    logging.info("No next page button found, ending.")
                    break

            except Exception as e:
                logging.error(f"Error scraping page {page_num}: {e}")
                print(f"Error on page {page_num}: {e}")

                # Print additional debugging info
                if driver:
                    try:
                        print(f"Current page title: {driver.title}")
                        print(f"Current URL: {driver.current_url}")
                        print(f"Page source length: {len(driver.page_source)}")
                    except Exception:
                        pass
                break
    except Exception as e:
        logging.error(f"Fatal error in scrape_afd: {e}")
        print(f"Fatal error: {e}")
    finally:
        if driver:
            driver.quit()
            print("Driver closed")

        print(f"\n{'='*50}")
        print(f"SCRAPING COMPLETED")
        print(f"Total pages processed: {page_num}")
        print(f"Total projects processed: {total_projects}")
        print(f"{'='*50}")
    return total_urls

def get_companydata_from_linkedinurl(company_url):
    api_key=os.getenv("SCRAPINGDOG_API_KEY")
    company_only = company_url.split("/")[-1]
    
    url="https://api.scrapingdog.com/linkedin"
    params = {
        "api_key": api_key,
        "type": "company",
        "linkId": company_only,
        "premium": "false"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        return ""
        
        


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

def get_score_between_project_and_company(project, company):
    try:
        prompt = "I will upload project and company data. Plz analyze it and then give me matching score only. output must be only score in integer(min:1, max:100). for example output is '50'"
        return getOpenAIResponse(project, company)

    except Exception as e:
        print(f"Error extracting text: {e}")
        return 1


def get_3suitable_companies_data(project):
    company_urls=get_all_linkinurls_of_companies(project["country"], project["sector"])
    scored_projects=[]
    for i, company_url in enumerate(company_urls):
        # Extract project information
        company_data=get_companydata_from_linkedinurl(company_url)
        matching_score=get_score_between_project_and_company(project, company_data)
        scored_projects.append({matching_score: matching_score, company_data})
    
    # finally get 3 top matched company data
    sorted_data = sorted(scored_projects, key=lambda x: x['matching_score'], reverse=True)
    
    # Get top 3 company_data
    top_3_companies = [item['company_data'] for item in sorted_data[:3]]
    
    return top_3_companies


if __name__ == "__main__":
    try:
        project = {
            "title": "Public Investment Programme Implementation Diagnosis and Skills Capacity Assessment",
            "client": "African Development Bank",
            "country": "Botswana",
            "budget": "Not defined",
            "sector": "Public Investment Sector",
            "summary": "The Botswana Government has received a grant from the African Development Bank to finance a consultancy project aimed at improving the Public Investment Programme (PIP) implementation. The project seeks to develop a robust framework for PIP to enhance its contribution to socio-economic development. Key objectives include reviewing the current PIP implementation for strengths and weaknesses, assessing the capacity of coordinating agencies, and developing an implementation plan with risk management and skills development strategies. Services involved include literature review, stakeholder consultations, diagnostic analysis, and capacity assessments to identify gaps and recommend improvements in the PIP processes.",
            "deadline": "The document does not mention a specific deadline date.",
            "program": "Public Investment Programme Implementation Diagnosis and Skills Capacity Assessment",
            "url": "https://www.afdb.org/en/documents/gpn-botswana-public-investment-programme-implementation-diagnosis-and-skills-capacity-assessment",
        }
        suitable_3projects=get_3suitable_companies_data(project)
        
        print(suitable_3projects)
    except Exception as e:
        logging.critical(f"Fatal error: {e}")




