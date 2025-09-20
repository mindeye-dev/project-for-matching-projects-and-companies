from langchain_experimental.sql import SQLDatabaseChain
from langchain_community.utilities import SQLDatabase
from langchain_community.llms import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Opportunity, User
from flask import current_app

_engine = None
_session = None
_db = None
_llm = None
_sql_chain = None

def _get_engine():
    global _engine
    if _engine is None:
        db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
        print(db_uri)
        _engine = create_engine(db_uri)
    return _engine

def _get_session():
    global _session
    if _session is None:
        engine = _get_engine()
        Session = sessionmaker(bind=engine)
        _session = Session()
    return _session

def _get_db():
    global _db
    if _db is None:
        engine = _get_engine()
        _db = SQLDatabase(engine)
    return _db

def _get_llm():
    global _llm
    if _llm is None:
        _llm = OpenAI(model='gpt-3.5-turbo', temperature=0)
    return _llm

def _get_sql_chain():
    global _sql_chain
    if _sql_chain is None:
        llm = _get_llm()
        db = _get_db()
        _sql_chain = SQLDatabaseChain(llm=llm, database=db, version=True)
    return _sql_chain

def get_AI_message(message):
    sql_chain = _get_sql_chain()
    result = sql_chain.run(message)
    print('Query Result:', result)
    return result
