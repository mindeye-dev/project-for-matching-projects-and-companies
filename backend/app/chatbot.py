from langchain_experimental.sql import SQLDatabaseChain


from langchain_community.utilities import SQLDatabase
from langchain_community.llms import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Opportunity, User  # Assuming your models are in models.py
from flask import current_app


db_uri = current_app.config["SQLALCHEMY_DATABASE_URI"]

# Create SQLAlchemy engine connectd to your database
engine = create_engine(db_uri) # Update with your DB URL
Session = sessionmaker(bind=engine) 
session = Session()

# Initialize LangChain SQLDatabase from SQLAlchemy engine
db = SQLDatabase(engine)

# Initialize OpenAI LLM
llm = OpenAI(model="gpt-3.5-turbo", temperature=0)

# Create a LangChain SQLDatabaseChain to query database with natural language questions
sql_chain = SQLDatabaseChain(llm=llm, database=db, version=True)

# Initialize OpenAI LLM

def get_AI_message(message):
    result = sql_chain.run(message)
    print("Query Result:", result)
    return result
