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
        db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
        print("engine db url is ", db_uri)
        _engine = create_engine(db_uri, echo = False, connect_args={"check_same_thread": False})
    return _engine

# SQLAlchemy session(optional)
def _get_session():
    global _session
    if _session is None:
        engine = _get_engine()
        Session = sessionmaker(bing=engine)
        _session = Session()
    return _session

# LangChain SQLDatabase wrapper
def _get_db():
    global _db
    if _db is None:
        engine = _get_engine()
        _db = SQLDatabase(engine)
    return _db

# OpenAI LLM
def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0,
            api_key=current_app.config['OPENAI_API_KEY']
        )
    return _llm

def write_query(state: State):
    """Generate SQL query to fetch information."""
    global llm
    global query_prompt_template
    print("writing query")
    prompt = query_prompt_template.invoke(
        {
            "dialect": _db.dialect,
            "top_k": 10,
            "table_info": _db.get_table_info(),
            "input": state["question"],
        }
    )
    structured_llm = llm.with_structured_output(QueryOutput)
    result = structured_llm.invoke(prompt)
    return {"query": result["query"]}

def execute_query(state: State):
    """Execute SQL query."""
    execute_query_tool = QuerySQLDatabaseTool(db=_db)
    return {"result": execute_query_tool.invoke(state["query"])}

def generate_answer(state: State):
    """Answer question using retrieved information as context."""
    global llm
    prompt = (
        "Given the following user question, corresponding SQL query, "
        "and SQL result, answer the user question.\n\n"
        f"Question: {state['question']}\n"
        f"SQL Query: {state['query']}\n"
        f"SQL Result: {state['result']}"
    )
    response = llm.invoke(prompt)
    return {"answer": response.content}

# SQLDatabaseChain
def _get_sql_chain_lang_graph():
    global _sql_chain
    global llm
    global _db
    global query_prompt_template
    if _sql_chain is None:
        llm = init_chat_model("gpt-4o-2024-08-06", model_provider="openai")
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

        _db = _get_db()

        print("initialized database")

        # schema_str = """TABLE opportunity (id, project_name, client, country, sector, summary, deadline, program, budget, url, found)
        #     TABLE partner (id, name, country, sector, website, linkedin_url, linkedin_data)
        #     TABLE match (id, opportunity, partner, score)
        #     TABLE user (id, email, password, role, created_at, last_login)
        #     TABLE session (id, user_id, started_at, ended_at)
        #     TABLE message (id, session_id, role, content, created_at)
        #     """  # <-- USE PLAIN TEXT TABLE/LAYOUT, DON’T INCLUDE THE ORM CODE

        sql_agent_prompt_template = """You are an expert data analyst. Given an input question, first create a syntactically correct {dialect} query to run, then look at the results of the query and describe the answer.
        Use the following format:

        Question: Question here
        SQLQuery: SQL Query to run
        SQLResult: Result of the SQLQuery
        Answer: Final answer here

        Only use the following tables:
        {table_info}

        Question: {input}"""

        # Use input variables the chain expects
        sql_prompt  = PromptTemplate(input_variables=["input", "table_info", "dialect"], template=sql_agent_prompt_template)


        _sql_chain = SQLDatabaseChain.from_llm(
            llm,
            db=_db,
            prompt=sql_prompt,
            verbose=True
        )



    graph_builder = StateGraph(State).add_sequence(
        [write_query, execute_query, generate_answer]
    )

    graph_builder.add_edge(START, "write_query")
    graph = graph_builder.compile()

    return graph

# Ask chatbot a question
def get_AI_message(message: str):
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
    print(result)
    return result



# Following are database management part

def chat_with_AI(user_id, user_message, session_id):

    # Create session if none

    # Save user message
    db.session.add(Message(session_id=session_id, role="user", content=user_message))
    db.session.commit()

    # Get AI response
    ai_response = get_AI_message(user_message)

    # Save AI message
    db.session.add(Message(session_id=session_id, role="assistant", content=ai_response))
    db.session.commit()


    print("AI response=", ai_response)

    return ai_response

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


