import os
import time
import requests
import logging
import random
from dotenv import load_dotenv

from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

import datetime
import time

from urllib.parse import urlparse


# Industry code
# https://learn.microsoft.com/en-us/linkedin/shared/references/reference-tables/industry-codes?source=recommendations



LINKEDIN_ACCOUNT_ID = os.getenv("LINKEDIN_ACCOUNT_ID")
UNIPILE_API_KEY = os.getenv("UNIPILE_API_KEY")
UNIPILE_DNS = os.getenv("UNIPILE_DNS")

max_daily_profiles = 100
profiles_retrieved = 0


last_day_check = datetime.datetime.now(datetime.timezone.utc)

def is_new_day(last_check):
    return (datetime.datetime.now(datetime.timezone.utc).date() != last_check.date())

def can_make_request():
    global profiles_retrieved, last_day_check
    if is_new_day(last_day_check):
        profiles_retrieved = 0
        last_day_check = datetime.datetime.now(datetime.timezone.utc)
    return profiles_retrieved < max_daily_profiles


def code_of_country(country_name):
    
    prompt = "If I upload location name, plz give me linkedin location code. output must be only location code. If there is not matching, output must be only empty"
    return getPerplexityResponse(prompt, country_name)
    
def code_of_sector(sector_name):
    prompt = "If I upload industry name, plz give me linkedin industry code. output must be only industry code. If there is not matching, output must be only empty"
    return getPerplexityResponse(prompt, sector_name)

def get_all_linkinurls_of_companies(country, sector):
    print(country)
    print(sector)
    country_code = f"{code_of_country(country)}"
    sector_code = f"{code_of_sector(sector)}"


    url = f"https://{UNIPILE_DNS}/api/v1/linkedin/search?account_id={LINKEDIN_ACCOUNT_ID}"
    total_urls = []
    print(country_code)
    print(sector_code)
    
    payload = {
        "api": "classic",
        "category": "companies",
        "industry": [sector_code],
        "location": [country_code]
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-API-KEY": UNIPILE_API_KEY
    }

    response_json = requests.post(url, json=payload, headers=headers).json()
    print("got all company urls")

    print(response_json)

    if "items" in response_json and isinstance(response_json["items"], list):
        total_urls = [company["profile_url"] for company in response_json["items"] if "profile_url" in company]
    else:
        total_urls = []
    
    print("parsed all")

    return total_urls

def act_as_human_to_avoid_rate_limit():
    num = random.randint(3, 9)

    time.sleep(num)  # Sleep for random seconds in range{3,...,9} to mimic human behavior
    

def get_companydata_from_linkedinurl(company_url):
    global profiles_retrieved
    act_as_human_to_avoid_rate_limit()
    
    if(can_make_request()==False):
        raise Exception("Daily profile request limit reached")
    

    path = urlparse(company_url).path
    company_name = path.strip("/").split("/")[-1]

    print("company name is ", company_name)

    url = f"https://{UNIPILE_DNS}/api/v1/linkedin/company/{company_name}?account_id={LINKEDIN_ACCOUNT_ID}"

    headers = {
        "accept": "application/json",
        "X-API-KEY": UNIPILE_API_KEY
    }

    response = requests.get(url, headers=headers)

    #print(response.text)
    profiles_retrieved+=1
    return response.text

def getPerplexityResponse(prompt, query):
    client = OpenAI(
        api_key=os.getenv("PERPLEXITY_API_KEY"),
        base_url="https://api.perplexity.ai"
    )
    response = client.chat.completions.create(
        model="sonar-pro",  # Perplexity model name
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": query},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content

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
        data=f"This data is project data. ~~~~{project}~~~. And this data is company data. ~~~~{company}~~~."
        return getOpenAIResponse(prompt, data)

    except Exception as e:
        print(f"Error extracting text: {e}")
        return 1


def get_3suitable_companies_data(project):
    try:
        company_urls=get_all_linkinurls_of_companies(project["country"], project["sector"])
        print(company_urls)
        scored_projects=[]
        for i, company_url in enumerate(company_urls):
            # Extract project information
            company_data=get_companydata_from_linkedinurl(company_url)
            matching_score=get_score_between_project_and_company(project, company_data)
            scored_projects.append({"matching_score": matching_score, "company_data": company_data})
            print("matching score is ", matching_score)
        
        # finally get 3 top matched company data
        sorted_data = sorted(scored_projects, key=lambda x: x['matching_score'], reverse=True)
        
        # Get top 3 company_data
        top_3_companies = [item['company_data'] for item in sorted_data[:3]]
        

        print(top_3_companies)
        return top_3_companies
    except Exception as e:
        logging.error(f"Error in get_3suitable_companies_data: {e}")
        return []


if __name__ == "__main__":
    try:
        project = {
            "title": "Public Investment Programme Implementation Diagnosis and Skills Capacity Assessment",
            "client": "African Development Bank",
            "country": "egypt",
            "budget": "Not defined",
            "sector": "Public Investment Sector",
            "summary": "The Botswana Government has received a grant from the African Development Bank to finance a consultancy project aimed at improving the Public Investment Programme (PIP) implementation. The project seeks to develop a robust framework for PIP to enhance its contribution to socio-economic development. Key objectives include reviewing the current PIP implementation for strengths and weaknesses, assessing the capacity of coordinating agencies, and developing an implementation plan with risk management and skills development strategies. Services involved include literature review, stakeholder consultations, diagnostic analysis, and capacity assessments to identify gaps and recommend improvements in the PIP processes.",
            "deadline": "The document does not mention a specific deadline date.",
            "program": "Public Investment Programme Implementation Diagnosis and Skills Capacity Assessment",
            "url": "https://www.afdb.org/en/documents/gpn-botswana-public-investment-programme-implementation-diagnosis-and-skills-capacity-assessment",
        }
        suitable_3projects=get_3suitable_companies_data(project)
        
        print(suitable_3projects)
        print(len(suitable_3projects))
    except Exception as e:
        logging.critical(f"Fatal error: {e}")




