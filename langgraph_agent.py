"""
langgraph_agent.py

LangGraph-based agent for RAG-powered SQL generation and execution with conversation memory.
"""
import logging
from typing import TypedDict, Literal, Optional
from langgraph.graph import StateGraph, START, END
from sql_generator import SQLGenerator, SQLValidator
from safe_sql_executor import SafeSQLExecutor
from schema_retriever import SchemaRetriever
from config import AppConfig
from database import SnowflakeDB, SQLiteDB

logger = logging.getLogger("langgraph_agent")

# Global instances to maintain state across invocations
_generator_instance = None
_retriever_instance = None


def get_generator() -> SQLGenerator:
    """Get or create the SQL generator with persistent memory."""
    global _generator_instance
    if _generator_instance is None:
        config = AppConfig.from_env()
        _generator_instance = SQLGenerator(config.llm)
    return _generator_instance


def get_retriever() -> SchemaRetriever:
    """Get or create the schema retriever."""
    global _retriever_instance
    if _retriever_instance is None:
        try:
            _retriever_instance = SchemaRetriever(
                chroma_db_path="./chroma_db",
                top_k=5
            )
        except Exception as e:
            logger.warning(f"Schema retriever initialization failed: {e}. RAG will be disabled.")
            _retriever_instance = None
    return _retriever_instance


class AgentState(TypedDict):
    """State schema for the RAG-powered LangGraph agent."""
    user_input: str
    schema_context: str  # Retrieved schema from RAG
    sql: str
    result: Optional[list]
    error: str
    previous_error: str  # For self-correction
    db_type: str  # "snowflake" or "sqlite"


def node_retrieve_schema(state: AgentState) -> AgentState:
    """Retrieve relevant schema using RAG based on user input."""
    try:
        db_type = state.get("db_type", "snowflake")
        retriever = get_retriever()
        
        # If retriever is not available, try direct SQLite schema query as fallback, or return empty schema
        if retriever is None:
            logger.warning("Schema retriever not available, proceeding without RAG")
            if db_type == "sqlite":
                try:
                    db = SQLiteDB()
                    db.connect()
                    schema_context = db.get_schema()
                    db.disconnect()
                    logger.info("Loaded SQLite schema directly from database as fallback")
                    return {**state, "schema_context": schema_context}
                except Exception as e:
                    logger.error(f"Failed to fetch SQLite schema directly: {e}")
            return {**state, "schema_context": ""}
        
        # Retrieve relevant schema
        schema_context = retriever.format_schema_for_prompt(
            state["user_input"],
            top_k=5
        )
        
        logger.info(f"Retrieved schema context ({len(schema_context)} chars) for query")
        return {**state, "schema_context": schema_context}
        
    except Exception as e:
        logger.warning(f"Schema retrieval failed: {e}. Continuing without RAG context.")
        return {**state, "schema_context": ""}


def node_generate_sql(state: AgentState) -> AgentState:
    """Generate SQL from user input with conversation memory and RAG context."""
    try:
        generator = get_generator()
        
        # Pass previous error to enable self-correction and schema context from RAG
        previous_error = state.get("previous_error", "")
        schema_context = state.get("schema_context", "")
        db_type = state.get("db_type", "snowflake")
        
        sql = generator.generate(
            state["user_input"],
            previous_error=previous_error if previous_error else None,
            schema_context=schema_context if schema_context else None,
            db_type=db_type
        )
        
        logger.info(f"Generated SQL: {sql}")
        return {**state, "sql": sql, "result": None, "error": "", "previous_error": ""}
    except Exception as e:
        error_msg = str(e)
        logger.error(f"SQL generation error: {error_msg}")
        return {**state, "sql": "", "result": None, "error": error_msg, "previous_error": ""}


def node_execute_sql(state: AgentState) -> AgentState:
    """Execute the generated SQL."""
    if not state.get("sql"):
        return {**state, "error": "No SQL to execute.", "previous_error": ""}
    
    try:
        db_type = state.get("db_type", "snowflake")
        if db_type == "sqlite":
            db = SQLiteDB()
        else:
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
    if state.get("result") is not None:
        return "format_result"
    return "execute_sql"


def build_langgraph_agent():
    """Build and compile the RAG-powered LangGraph agent."""
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("retrieve_schema", node_retrieve_schema)
    graph.add_node("generate_sql", node_generate_sql)
    graph.add_node("execute_sql", node_execute_sql)
    graph.add_node("format_result", node_format_result)
    graph.add_node("handle_error", node_handle_error)
    
    # Set entry point to schema retrieval (RAG step)
    graph.add_edge(START, "retrieve_schema")
    
    # Add edges in RAG-powered workflow
    graph.add_edge("retrieve_schema", "generate_sql")  # Always go from retrieval to generation
    
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


def run_agent(user_input: str, db_type: str = "snowflake") -> dict:
    """Run the RAG-powered agent with a user input and return results."""
    agent = build_langgraph_agent()
    initial_state = {
        "user_input": user_input,
        "schema_context": "",
        "sql": "",
        "result": None,
        "error": "",
        "previous_error": "",
        "db_type": db_type
    }
    final_state = agent.invoke(initial_state)
    return final_state
