"""
sql_agent.py
============
A LangGraph agent (built on the user's original Groq + LangGraph script)
that answers natural-language questions about the academic dataset in
students.db. Every SQL query it wants to run is checked by guardrails.py
first -- only read-only SELECT statements are ever executed.
"""

import sqlite3
from typing import Literal
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt.tool_node import ToolNode
from langgraph.checkpoint.memory import InMemorySaver

from db import STUDENT_DB
from guardrails import check_sql

SYSTEM_PROMPT = (
    "You are a friendly, precise SQL data-analyst assistant for a university "
    "database (Departments, Instructors, Students, Courses, Enrollments, "
    "Attendance). Always inspect the schema before writing a query. Only "
    "ever write a single read-only SELECT statement. Explain results in "
    "plain, concise language after you get them back from the tool. If a "
    "question can't be answered from this schema, say so honestly."
)


# ==========================================
# SQL TOOLS (guardrailed)
# ==========================================
@tool
def sql_db_list_tables() -> str:
    """List all tables available in the database."""
    con = sqlite3.connect(STUDENT_DB)
    try:
        cursor = con.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        )
        return ", ".join(row[0] for row in cursor.fetchall())
    finally:
        con.close()


@tool
def sql_db_schema(table_names: str) -> str:
    """Get the CREATE TABLE schema for a comma-separated list of table names."""
    con = sqlite3.connect(STUDENT_DB)
    try:
        cursor = con.cursor()
        results = []
        for table in [t.strip() for t in table_names.split(",") if t.strip()]:
            cursor.execute("SELECT sql FROM sqlite_master WHERE name=?;", (table,))
            schema = cursor.fetchone()
            if schema:
                results.append(schema[0])
        return "\n\n".join(results) if results else "No matching tables found."
    finally:
        con.close()


@tool
def sql_db_query(query: str) -> str:
    """Execute a read-only SQL SELECT query against the database and return the rows."""
    allowed, reason = check_sql(query)
    if not allowed:
        return f"Query rejected by guardrails: {reason}"

    con = sqlite3.connect(STUDENT_DB)
    try:
        cursor = con.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description] if cursor.description else []
        if not rows:
            return "Query ran successfully but returned no rows."
        preview = rows[:200]  # cap result size
        return f"Columns: {columns}\nRows: {preview}"
    except Exception as e:
        return f"Error: {e}"
    finally:
        con.close()


TOOLS = [sql_db_list_tables, sql_db_schema, sql_db_query]


# ==========================================
# BUILD THE GRAPH
# ==========================================
def build_agent(groq_api_key: str, model_name: str = "llama-3.1-8b-instant"):
    model = ChatGroq(temperature=0, groq_api_key=groq_api_key, model_name=model_name)

    def list_tables(state: MessagesState):
        result = sql_db_list_tables.invoke("")
        return {"messages": [AIMessage(content=f"Available tables: {result}")]}

    def call_get_schema(state: MessagesState):
        llm = model.bind_tools([sql_db_schema], tool_choice="any")
        return {"messages": [llm.invoke(state["messages"])]}

    def generate_query(state: MessagesState):
        system = SystemMessage(content=SYSTEM_PROMPT)
        llm = model.bind_tools([sql_db_query])
        return {"messages": [llm.invoke([system] + state["messages"])]}

    def should_continue(state: MessagesState) -> Literal["run_query", "__end__"]:
        last_message = state["messages"][-1]
        return "run_query" if getattr(last_message, "tool_calls", None) else END

    builder = StateGraph(MessagesState)

    builder.add_node("list_tables", list_tables)
    builder.add_node("call_get_schema", call_get_schema)
    builder.add_node("get_schema", ToolNode([sql_db_schema]))
    builder.add_node("generate_query", generate_query)
    builder.add_node("run_query", ToolNode([sql_db_query]))

    builder.add_edge(START, "list_tables")
    builder.add_edge("list_tables", "call_get_schema")
    builder.add_edge("call_get_schema", "get_schema")
    builder.add_edge("get_schema", "generate_query")
    builder.add_conditional_edges("generate_query", should_continue)
    builder.add_edge("run_query", "generate_query")

    return builder.compile(checkpointer=InMemorySaver())


def ask_agent(agent, thread_id: str, question: str) -> str:
    """Runs the agent for one turn and returns the final assistant text."""
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [HumanMessage(content=question)]}

    final_text = ""
    for event in agent.stream(inputs, config, stream_mode="values"):
        last_msg = event["messages"][-1]
        if isinstance(last_msg, AIMessage) and last_msg.content.strip():
            final_text = last_msg.content

    return final_text or "I wasn't able to generate a response for that question."