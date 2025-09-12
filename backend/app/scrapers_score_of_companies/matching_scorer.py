from openai import OpenAI
from dotenv import load_dotenv

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
        prompt = "I will upload project and company data. Plz analyze it and then give me matching score only. output must be only score in integer(min:1, max:100). for example output is '50'. output must be integer."
        data = f"This data is project data. ~~~~{project}~~~. And this data is company data. ~~~~{company}~~~."
        return getOpenAIResponse(prompt, data)

    except Exception as e:
        print(f"Error extracting text: {e}")
        return 1
