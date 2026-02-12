"""
langgraph_agent.py

LangGraph-based agent for SQL generation and execution with conversation memory.
"""
import logging
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from sql_generator import SQLGenerator, SQLValidator
from safe_sql_executor import SafeSQLExecutor
from config import AppConfig
from database import SnowflakeDB

logger = logging.getLogger("langgraph_agent")

# Global generator instance to maintain conversation memory across invocations
_generator_instance = None


def get_generator() -> SQLGenerator:
    """Get or create the SQL generator with persistent memory."""
    global _generator_instance
    if _generator_instance is None:
        config = AppConfig.from_env()
        _generator_instance = SQLGenerator(config.llm)
    return _generator_instance


class AgentState(TypedDict):
    """State schema for the LangGraph agent."""
    user_input: str
    sql: str
    result: list
    error: str
    previous_error: str  # For self-correction


def node_generate_sql(state: AgentState) -> AgentState:
    """Generate SQL from user input with conversation memory."""
    try:
        generator = get_generator()
        
        # Pass previous error to enable self-correction
        previous_error = state.get("previous_error", "")
        sql = generator.generate(state["user_input"], previous_error=previous_error if previous_error else None)
        
        logger.info(f"Generated SQL: {sql}")
        return {"sql": sql, "user_input": state["user_input"], "result": [], "error": "", "previous_error": ""}
    except Exception as e:
        logger.error(f"SQL generation error: {e}")
        return {"sql": "", "user_input": state["user_input"], "result": [], "error": str(e), "previous_error": ""}


def node_execute_sql(state: AgentState) -> AgentState:
    """Execute the generated SQL."""
    if not state.get("sql"):
        return {**state, "error": "No SQL to execute.", "previous_error": ""}
    
    try:
        config = AppConfig.from_env()
        db = SnowflakeDB(config.snowflake)
        db.connect()
        
        executor = SafeSQLExecutor(db.connection)
        result = executor.execute(state["sql"])
        
        logger.info(f"Execution result: {len(result) if result else 0} rows")
        return {**state, "result": result, "error": "", "previous_error": ""}
    except Exception as e:
        error_msg = str(e)
        logger.error(f"SQL execution error: {error_msg}")
        # Return error as previous_error so next generate call can self-correct
        return {**state, "error": error_msg, "result": [], "previous_error": error_msg}


def node_format_result(state: AgentState) -> AgentState:
    """Format and return the result."""
    return state


def node_handle_error(state: AgentState) -> AgentState:
    """Handle errors in the workflow."""
    return state


def router(state: AgentState) -> Literal["handle_error", "execute_sql", "format_result"]:
    """Route to next node based on state."""
    if state.get("error"):
        return "handle_error"
    if state.get("sql") and not state.get("result"):
        return "execute_sql"
    if state.get("result"):
        return "format_result"
    return "execute_sql"


def build_langgraph_agent():
    """Build and compile the LangGraph agent."""
    graph = StateGraph(AgentState)
    
    graph.add_node("generate_sql", node_generate_sql)
    graph.add_node("execute_sql", node_execute_sql)
    graph.add_node("format_result", node_format_result)
    graph.add_node("handle_error", node_handle_error)
    
    graph.set_entry_point("generate_sql")
    graph.add_conditional_edges(
        "generate_sql",
        router,
        {"execute_sql": "execute_sql", "handle_error": "handle_error"}
    )
    graph.add_conditional_edges(
        "execute_sql",
        router,
        {"format_result": "format_result", "handle_error": "handle_error"}
    )
    graph.add_edge("format_result", END)
    graph.add_edge("handle_error", END)
    
    return graph.compile()


def run_agent(user_input: str) -> dict:
    """Run the agent with a user input and return results."""
    agent = build_langgraph_agent()
    initial_state = {
        "user_input": user_input,
        "sql": "",
        "result": [],
        "error": "",
        "previous_error": ""
    }
    final_state = agent.invoke(initial_state)
    return final_state
