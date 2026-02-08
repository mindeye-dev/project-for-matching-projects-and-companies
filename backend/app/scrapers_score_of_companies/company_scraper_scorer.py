import os
import time
import requests
import logging
import random
from dotenv import load_dotenv

from sqlalchemy import cast, String


from app.models import Opportunity, Partner, Match, db

from app.scrapers_score_of_companies.matching_scorer import getOpenAIResponse, get_matched_score_between_project_and_company


# Load environment variables from .env file
load_dotenv()

import datetime
import time

from urllib.parse import urlparse
import json

# Industry code
# https://learn.microsoft.com/en-us/linkedin/shared/references/reference-tables/industry-codes?source=recommendations

# Load industry codes for local matching
INDUSTRY_CODES = []
try:
    industry_code_path = os.path.join(os.path.dirname(__file__), "industry_code.json")
    with open(industry_code_path, "r", encoding="utf-8") as f:
        INDUSTRY_CODES = json.load(f)
except Exception as e:
    logging.warning(f"Could not load industry_code.json: {e}")
    INDUSTRY_CODES = []

LINKEDIN_ACCOUNT_ID = os.getenv("LINKEDIN_ACCOUNT_ID")
UNIPILE_API_KEY = os.getenv("UNIPILE_API_KEY")
UNIPILE_DNS = os.getenv("UNIPILE_DNS")

max_daily_profiles = 100
profiles_retrieved = 0


last_day_check = datetime.datetime.now(datetime.timezone.utc)


def is_new_day(last_check):
    return datetime.datetime.now(datetime.timezone.utc).date() != last_check.date()


def can_make_request():
    global profiles_retrieved, last_day_check
    if is_new_day(last_day_check):
        profiles_retrieved = 0
        last_day_check = datetime.datetime.now(datetime.timezone.utc)
    return profiles_retrieved < max_daily_profiles


def code_of_country(country_name):
    """
    Get LinkedIn location code for a country name.
    First tries local matching, then falls back to Perplexity API.
    """
    # Normalize country name for matching
    country_lower = country_name.lower().strip()
    
    # Try common country code mappings first (you can expand this)
    country_mappings = {
        "united states": "us",
        "usa": "us",
        "united kingdom": "gb",
        "uk": "gb",
        "canada": "ca",
        "australia": "au",
        "germany": "de",
        "france": "fr",
        "italy": "it",
        "spain": "es",
        "netherlands": "nl",
        "belgium": "be",
        "switzerland": "ch",
        "austria": "at",
        "sweden": "se",
        "norway": "no",
        "denmark": "dk",
        "finland": "fi",
        "poland": "pl",
        "portugal": "pt",
        "greece": "gr",
        "ireland": "ie",
        "new zealand": "nz",
        "south africa": "za",
        "brazil": "br",
        "mexico": "mx",
        "argentina": "ar",
        "chile": "cl",
        "colombia": "co",
        "india": "in",
        "china": "cn",
        "japan": "jp",
        "south korea": "kr",
        "singapore": "sg",
        "malaysia": "my",
        "thailand": "th",
        "indonesia": "id",
        "philippines": "ph",
        "vietnam": "vn",
        "egypt": "eg",
        "nigeria": "ng",
        "kenya": "ke",
        "ghana": "gh",
        "morocco": "ma",
        "tunisia": "tn",
        "algeria": "dz",
        "botswana": "bw",
    }
    
    # Check if we have a direct mapping
    if country_lower in country_mappings:
        return country_mappings[country_lower]
    
    # Fallback to Perplexity API
    try:
        prompt = "If an uploaded location name matches a LinkedIn location code, output only the location code. If no match is found, output only an empty string. If the match is ambiguous, output a similar or most common LinkedIn location code as per the official code table."
        result = getPerplexityResponse(prompt, country_name)
        # Clean up the result - extract just the code if it's in a sentence
        result = result.strip()
        # If result is empty or invalid, return empty string
        if not result or len(result) > 10:  # Location codes are typically short
            return ""
        return result
    except Exception as e:
        logging.error(f"Error getting country code from Perplexity: {e}")
        return ""


def code_of_sector(sector_name):
    """
    Get LinkedIn industry code for a sector name.
    First tries local matching using industry_code.json, then falls back to Perplexity API.
    """
    # Normalize sector name for matching
    sector_lower = sector_name.lower().strip()
    
    # Try to match against industry_code.json first
    best_match = None
    best_score = 0
    
    for industry in INDUSTRY_CODES:
        label_lower = industry.get("label", "").lower()
        industry_id = industry.get("industry_id")
        
        # Exact match
        if label_lower == sector_lower:
            return str(industry_id)
        
        # Partial match - check if sector name contains industry label or vice versa
        if sector_lower in label_lower or label_lower in sector_lower:
            # Calculate a simple similarity score
            common_words = set(sector_lower.split()) & set(label_lower.split())
            score = len(common_words) / max(len(sector_lower.split()), len(label_lower.split()))
            if score > best_score:
                best_score = score
                best_match = industry_id
    
    # If we found a good match (score > 0.3), use it
    if best_match and best_score > 0.3:
        return str(best_match)
    
    # Fallback to Perplexity API
    try:
        prompt = "If an uploaded industry name matches a LinkedIn industry code, output only the industry code as a number. If no match is found, output only an empty string. If the match is ambiguous, output a similar or most common LinkedIn industry code as per the official code table. Only output the numeric industry code, nothing else."
        result = getPerplexityResponse(prompt, sector_name)
        # Clean up the result - extract just the number
        result = result.strip()
        # Remove any non-numeric characters except digits
        result = ''.join(filter(str.isdigit, result))
        if result:
            return result
        return ""
    except Exception as e:
        logging.error(f"Error getting sector code from Perplexity: {e}")
        return ""


def get_all_linkinurls_of_companies(country, sector):
    print(f"Searching for companies in country: {country}, sector: {sector}")
    country_code = code_of_country(country)
    sector_code = code_of_sector(sector)

    url = (
        f"https://{UNIPILE_DNS}/api/v1/linkedin/search?account_id={LINKEDIN_ACCOUNT_ID}"
    )
    total_urls = []
    print(f"Country code: {country_code}, Sector code: {sector_code}")

    # Only include codes if they are not empty
    payload = {
        "api": "classic",
        "category": "companies",
    }
    
    if sector_code:
        payload["industry"] = [sector_code]
    if country_code:
        payload["location"] = [country_code]
    
    # If both codes are empty, log a warning
    if not sector_code and not country_code:
        logging.warning(f"Both country and sector codes are empty for country={country}, sector={sector}")
        return []
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-API-KEY": UNIPILE_API_KEY,
    }

    response_json = requests.post(url, json=payload, headers=headers).json()
    print("got all company urls")

    print(response_json)

    if "items" in response_json and isinstance(response_json["items"], list):
        total_urls = [
            company["profile_url"]
            for company in response_json["items"]
            if "profile_url" in company
        ]
    else:
        total_urls = []

    print("parsed all")

    return total_urls


def act_as_human_to_avoid_rate_limit():
    num = random.randint(3, 9)

    time.sleep(
        num
    )  # Sleep for random seconds in range{3,...,9} to mimic human behavior


def get_companydata_from_linkedinurl(company_url):
    global profiles_retrieved
    act_as_human_to_avoid_rate_limit()

    if can_make_request() == False:
        raise Exception("Daily profile request limit reached")

    path = urlparse(company_url).path
    company_identifier = path.strip("/").split("/")[-1]

    print("company name is ", company_identifier)

    url = f"https://{UNIPILE_DNS}/api/v1/linkedin/company/{company_identifier}?account_id={LINKEDIN_ACCOUNT_ID}"

    headers = {"accept": "application/json", "X-API-KEY": UNIPILE_API_KEY}

    response = requests.get(url, headers=headers)

    # print(response.text)
    profiles_retrieved += 1
    return response.json()


def getPerplexityResponse(prompt, query):
    client = OpenAI(
        api_key=os.getenv("PERPLEXITY_API_KEY"), base_url="https://api.perplexity.ai"
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


def get_three_suitable_matched_scores_and_companies_data(project):
    try:

        # Get companies urls at linkedin
        company_urls = get_all_linkinurls_of_companies(
            project["country"], project["sector"]
        )

        # Find three best matched urls
        matched_scores_and_companies_data = []
        for i, company_url in enumerate(company_urls):
            # Extract project information

            # company_data is json type.
            # get company data of url
            company_data = get_companydata_from_linkedinurl(company_url)

            # Find matched partner in Partner table
            # Try to get profile_url from linkedin_data JSON field
            profile_url = company_data.get("profile_url") or company_data.get("url", "")
            result = Partner.query.filter(
                cast(Partner.linkedindata["profile_url"], String) == profile_url
            ).all() if profile_url else []

            # if there is several partners in Partner table, remove all without first one and then update first one with new data
            if len(result) > 1:
                # Error, remove another elements without one element
                # Keep the first element
                first_partner = result[0]

                # Collect IDs of other elements to delete
                ids_to_delete = [partner.id for partner in result[1:]]

                # Delete partners with these ids from Partner table
                Partner.query.filter(Partner.id.in_(ids_to_delete)).delete(
                    synchronize_session=False
                )

                # replace linkedin data of first_partner
                first_partner.linkedindata = company_data

                db.session.commit()

                # Now result contains only one element logically (you can reassign if needed)
                result = [first_partner]
            # if there is several partners in Partner table, remove all without first one
            elif len(result) == 1:
                # result[0] is one partner data of Partner database, so let update linkedindata if it is different from original linkedindata of Partner database.
                result[0].linkedindata = company_data
                db.session.commit()  # Commit changes to the database

            else:
                new_partner = Partner(
                    # Assign other fields as needed, example:
                    name=company_data.get("name", ""),
                    country=company_data.get("location", {}).get("country", "") if isinstance(company_data.get("location"), dict) else company_data.get("country", ""),
                    sector=company_data.get("industry", ""),
                    website=company_data.get("website", ""),
                    linkedindata=company_data,  # assign JSON data here
                )
                db.session.add(new_partner)
                db.session.commit()
                result.append(new_partner)


            # if there is data in Partner database, update it.
            matched_score = get_matched_score_between_project_and_company(
                project, result[0]
            )
            matched_scores_and_companies_data.append(
                {"matched_score": matched_score, "company_data": result[0]}
            )
            print("matching score is ", matched_score)

        # finally get 3 top matched company data
        sorted_data = sorted(
            matched_scores_and_companies_data,
            key=lambda x: x["matched_score"],
            reverse=True,
        )

        three_suitable_matched_scores_and_companies_data = sorted_data[:3]

        three_companies=[]

        # Only save matches if project has an id (existing opportunity)
        project_id = project.get("id") if isinstance(project, dict) else (project.id if hasattr(project, "id") else None)
        
        if project_id:
            # find matches of project and then delete all
            Match.query.filter_by(opportunity=project_id).delete()
            db.session.commit()

            for item in three_suitable_matched_scores_and_companies_data:
                score = item["matched_score"]
                company = item["company_data"]

                new_match = Match(
                    opportunity=project_id,
                    partner=company.id,
                    score=score
                )
                db.session.add(new_match)

                three_companies.append({
                    "id": company.id,
                    "name": company.name,
                    "country": company.country,
                    "website": company.website,
                    "sector": company.sector,
                    "matched_score": score
                })

            # Commit once after the loop
            db.session.commit()

            # set found of project to true.
            Opportunity.query.filter_by(id=project_id).update({"found": True})
            db.session.commit()
        else:
            # If no project id, just return the companies without saving matches
            for item in three_suitable_matched_scores_and_companies_data:
                score = item["matched_score"]
                company = item["company_data"]

                three_companies.append({
                    "id": company.id,
                    "name": company.name,
                    "country": company.country,
                    "website": company.website,
                    "sector": company.sector,
                    "matched_score": score
                })

        return three_companies
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
        three_suitable_matched_scores_and_companies_data = (
            get_three_suitable_matched_scores_and_companies_data(project)
        )  # @ array of matched scores and companies data

        print(three_suitable_matched_scores_and_companies_data)
        print(len(three_suitable_matched_scores_and_companies_data))
    except Exception as e:
        logging.critical(f"Fatal error: {e}")
