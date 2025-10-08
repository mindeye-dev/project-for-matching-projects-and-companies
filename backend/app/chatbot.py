from flask import current_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from langchain_experimental.sql import SQLDatabaseChain
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains.llm import LLMChain
from langchain_core.prompts import ChatPromptTemplate
from typing_extensions import Annotated, TypedDict
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langgraph.graph import START, StateGraph
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model


import getpass
import os



from app.models import Session, Message, db


_engine = None
_session = None
_db = None
_llm = None
_sql_chain = None



class State(TypedDict):
    question: str
    query: str
    result: str
    answer: str

class QueryOutput(TypedDict):
    """Generated SQL query."""

    query: Annotated[str, ..., "Syntactically valid SQL query."]



# Create SQLALchemy engine
def _get_engine():
    global _engine
    if _engine is None:
        try:
            db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
            print("engine db url is ", db_uri)
            _engine = create_engine(db_uri, echo = False, connect_args={"check_same_thread": False})
        except Exception as e:
            print(f"Error creating engine: {e}")
            # Fallback to direct SQLite connection
            _engine = create_engine('sqlite:///app.db', echo = False, connect_args={"check_same_thread": False})
    return _engine

# SQLAlchemy session(optional)
def _get_session():
    global _session
    if _session is None:
        engine = _get_engine()
        Session = sessionmaker(bind=engine)
        _session = Session()
    return _session

# LangChain SQLDatabase wrapper
def _get_db():
    global _db
    if _db is None:
        engine = db.get_engine()  # Use Flask-SQLAlchemy engine from app config
        _db = SQLDatabase(engine, sample_rows_in_table_info=3)
    return _db

# OpenAI LLM
def _get_llm():
    global _llm
    if _llm is None:
        _llm = init_chat_model("gpt-4o-2024-08-06", model_provider="openai")
    return _llm

def write_query(state: State):
    """Generate SQL query to fetch information."""
    _get_db()
    global query_prompt_template
    print("writing query")
    system_message = """
    Given an input question, create a syntactically correct {dialect} query to
    run to help find the answer. Unless the user specifies in his question a
    specific number of examples they wish to obtain, always limit your query to
    at most {top_k} results. You can order the results by a relevant column to
    return the most interesting examples in the database.

    Never query for all the columns from a specific table, only ask for a the
    few relevant columns given the question.

    Pay attention to use only the column names that you can see in the schema
    description. Be careful to not query for columns that do not exist. Also,
    pay attention to which column is in which table.

    Only use the following tables:
    {table_info}
    """

    user_prompt = "Question: {input}"

    query_prompt_template = ChatPromptTemplate(
        [("system", system_message), ("user", user_prompt)]
    )
    prompt = query_prompt_template.invoke(
        {
            "dialect": _db.dialect,
            "top_k": 10,
            "table_info": _db.get_table_info(),
            "input": state["question"],
        }
    )
    _get_llm()
    structured_llm = _llm.with_structured_output(QueryOutput)
    result = structured_llm.invoke(prompt)
    return {"query": result["query"]}

def execute_query(state: State):
    """Execute SQL query."""
    _get_db()
    execute_query_tool = QuerySQLDatabaseTool(db=_db)
    return {"result": execute_query_tool.invoke(state["query"])}

def generate_answer(state: State):
    """Answer question using retrieved information as context."""
    global _llm
    prompt = (
        "Given the following user question, corresponding SQL query, "
        "and SQL result, answer the user question.\n\n"
        f"Question: {state['question']}\n"
        f"SQL Query: {state['query']}\n"
        f"SQL Result: {state['result']}"
    )
    response = _llm.invoke(prompt)
    return {"answer": response.content}

# SQLDatabaseChain
def _get_sql_chain_lang_graph():

    graph_builder = StateGraph(State).add_sequence(
        [write_query, execute_query, generate_answer]
    )

    graph_builder.add_edge(START, "write_query")
    graph = graph_builder.compile()

    return graph

# Ask chatbot a question
def get_AI_message(message: str):
    try:
        result = None
        sql_chain_lang_graph = _get_sql_chain_lang_graph()
        config = {"configurable": {"thread_id": "1"}}

        for step in sql_chain_lang_graph.stream(
            {"question": message},
            config,
            stream_mode="updates",
        ):
            # Access the emitted data of each step
            if 'generate_answer' in step:
                result = step['generate_answer']['answer']
        
        print(f"AI result: {result}")
        return result
        
    except Exception as e:
        print(f"Error in get_AI_message: {str(e)}")
        return None



# Following are database management part

def chat_with_AI(user_id, user_message, session_id):
    try:
        # Save user message
        user_msg = Message(session_id=session_id, role="user", content=user_message)
        db.session.add(user_msg)
        db.session.commit()
        
        # Get AI response
        ai_response = get_AI_message(user_message)
        
        if ai_response is None:
            ai_response = "Sorry, I couldn't process your request. Please try again."
        
        # Save AI message (add timestamp to avoid duplicate constraint)
        import datetime
        ai_msg = Message(
            session_id=session_id, 
            role="assistant", 
            content=ai_response + f" [Generated at {datetime.datetime.now()}]"
        )
        db.session.add(ai_msg)
        db.session.commit()
        
        print("AI response=", ai_response)
        return ai_response
        
    except Exception as e:
        print(f"Error in chat_with_AI: {str(e)}")
        db.session.rollback()
        return f"An error occurred: {str(e)}"

def create_user_session(user_id):
    session_obj = Session(user_id= user_id)
    db.session.add(session_obj)
    db.session.commit()
    print(session_obj)
    return session_obj.to_dict()

# delete user session
def delete_user_session(user_id, session_id):
    # Get all sessions for the user
    sessions = Session.query.filter_by(user_id=user_id).all()

    # If only one session exists, can not delete
    if len(sessions) <= 1:
        return {"success": False, "message": "Sesssion not found."}

    # Get the session to delete
    session_to_delete = Session.query.filter_by(id=session_id, user_id=user_id).first()
    if not session_to_delete:
        return {"success": False, "message": "Session not found."}
    
    # Delete the session and cascade delete its messages 
    db.session.delete(session_to_delete)
    db.session.commit()

    return {"success": True, "message": "Session deleted successfully."}


def get_session_messages_dict(session_id):
    messages = Message.query.filter_by(session_id=session_id).order_by(Message.created_at).all()
    return [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in messages]


def get_user_sessions_dict(user_id):
    sessions = Session.query.filter_by(user_id=user_id).order_by(Session.started_at.desc()).all()
    return [
        s.to_dict()
        for s in sessions
    ]


