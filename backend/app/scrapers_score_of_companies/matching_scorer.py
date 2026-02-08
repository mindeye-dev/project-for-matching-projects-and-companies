from openai import OpenAI
from dotenv import load_dotenv
import os
import logging

# Load environment variables from .env file
load_dotenv()


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


def get_matched_score_between_project_and_company(project, company):
    try:
        prompt = "I will upload project and company data. Please analyze it and then give me matching score only. Output must be only the score as an integer (min:1, max:100). For example, output is '50'. Output must be only the integer number, nothing else."
        
        # Format project data
        project_str = f"Project: {project.project_name if hasattr(project, 'project_name') else project.get('project_name', '')} - {project.summary if hasattr(project, 'summary') else project.get('summary', '')} - Country: {project.country if hasattr(project, 'country') else project.get('country', '')} - Sector: {project.sector if hasattr(project, 'sector') else project.get('sector', '')}"
        
        # Format company data
        company_str = f"Company: {company.name if hasattr(company, 'name') else company.get('name', '')} - Country: {company.country if hasattr(company, 'country') else company.get('country', '')} - Sector: {company.sector if hasattr(company, 'sector') else company.get('sector', '')}"
        
        data = f"{project_str}. {company_str}."
        response = getOpenAIResponse(prompt, data)
        
        # Extract numeric score from response
        import re
        score_match = re.search(r'\d+', str(response))
        if score_match:
            score = int(score_match.group())
            # Ensure score is between 1 and 100
            score = max(1, min(100, score))
            return score
        else:
            logging.warning(f"Could not extract score from response: {response}")
            return 50  # Default score if parsing fails
    except Exception as e:
        logging.error(f"Error getting matched score: {e}")
        return 1
