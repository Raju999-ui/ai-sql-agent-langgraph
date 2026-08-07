"""Streamlit UI for the RAG-powered AI SQL Agent with conversation memory."""

# Fix SQLite version requirement for ChromaDB on Linux / Streamlit Cloud
try:
    import pysqlite3
    import sys
    sys.modules['sqlite3'] = pysqlite3
except ImportError:
    pass

import streamlit as st
import logging
import json
import os
from datetime import datetime
from config import AppConfig
from logger_config import setup_logging
from langgraph_agent import run_agent
from schema_ingestion import SchemaIngestion, ingest_schema_from_env
from schema_retriever import SchemaRetriever, create_retriever_from_env

# Setup logging
logger = setup_logging("INFO", False)

# Page configuration
st.set_page_config(
    page_title="Netflix AI SQL Agent (RAG-Powered)",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Auto-initialize RAG schema on startup if ChromaDB folder is empty or missing
@st.cache_resource
def auto_init_rag_schema():
    if not os.path.exists("./chroma_db") or not os.listdir("./chroma_db"):
        with st.spinner("Initializing RAG schema..."):
            ingestion = ingest_schema_from_env()
            ingestion.ingest_schema(db_type="snowflake")

auto_init_rag_schema()


# Initialize session state (no agent object needed for stateless run_agent)
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    st.session_state.conversation_context = ""
    st.session_state.last_query = None
    st.session_state.last_results = None
    st.session_state.schema_context = ""
    st.session_state.rag_enabled = True
    st.session_state.db_source = "snowflake"
    st.session_state.query_count = 0
    st.session_state.active_sqlite_table = None

if "query_count" not in st.session_state:
    st.session_state.query_count = 0

if "active_sqlite_table" not in st.session_state:
    st.session_state.active_sqlite_table = None

# Sidebar
with st.sidebar:
    st.header("🎬 Netflix AI SQL Agent (RAG)")
    st.markdown("---")
    
    # Database Settings
    st.subheader("⚙️ Database Settings")
    st.session_state.db_source = st.selectbox(
        "Active Database Source",
        options=["snowflake", "sqlite"],
        format_func=lambda x: "Snowflake Cloud" if x == "snowflake" else "Local SQLite (CSV Uploads)",
        index=0 if st.session_state.db_source == "snowflake" else 1
    )
    
    st.markdown("---")
    
    # CSV Upload Section
    st.subheader("📂 CSV Upload & Ingestion")
    uploaded_file = st.file_uploader("Upload CSV file to SQLite", type=["csv"])
    if uploaded_file is not None:
        try:
            import re
            import pandas as pd
            raw_name = uploaded_file.name.rsplit(".", 1)[0]
            table_name = re.sub(r'[^a-zA-Z0-9_]', '_', raw_name).lower()
            
            df = pd.read_csv(uploaded_file)
            
            import sqlite3
            conn = sqlite3.connect("local_data.db")
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            conn.close()
            
            st.session_state.active_sqlite_table = table_name
            st.success(f"✓ Saved to SQLite table: `{table_name}` ({len(df)} rows)")
            
            # Switch source and refresh if necessary
            if st.session_state.db_source != "sqlite":
                st.session_state.db_source = "sqlite"
                st.rerun()
                
            # Trigger schema ingestion automatically
            with st.spinner("🔄 Ingesting SQLite schema for RAG..."):
                try:
                    ingestion = ingest_schema_from_env()
                    ingestion.ingest_schema(db_type="sqlite")
                    st.toast("✓ RAG schema updated for SQLite!")
                except Exception as e:
                    st.warning(f"RAG embedding failed (embeddings require OPENAI_API_KEY): {e}. Falling back to direct database schema querying.")
            
        except Exception as e:
            st.error(f"❌ Failed to process CSV: {e}")
            
    st.markdown("---")
    
    # RAG Management Section
    st.subheader("🔄 RAG Schema Management")
    
    # Check schema status
    try:
        retriever = create_retriever_from_env()
        tables = retriever.get_all_tables()
        if tables:
            rag_status = f"✓ RAG Ready ({len(tables)} tables)"
            st.success(rag_status)
        else:
            st.warning("⚠️ RAG initialized but collection is empty.")
    except Exception as e:
        st.warning(f"⚠️ RAG not initialized. Ingest schema or upload CSV first.")
    
    # Schema ingestion option
    if st.button("🌱 Initialize/Update Schema", use_container_width=True):
        try:
            with st.spinner(f"📥 Ingesting schema from {st.session_state.db_source}..."):
                ingestion = ingest_schema_from_env()
                ingestion.ingest_schema(db_type=st.session_state.db_source)
                stats = ingestion.get_collection_stats()
                st.success(f"✓ Schema ingested!\n\nDocuments: {stats['total_documents']}\nStorage: {stats['storage_path']}")
        except Exception as e:
            st.error(f"❌ Schema ingestion failed: {e}")
    
    # Test RAG retriever
    if st.button("🧪 Test RAG Retriever", use_container_width=True):
        try:
            retriever = create_retriever_from_env()
            test_query = "Show all movies from 2020"
            schema_context, results = retriever.retrieve_relevant_schema(test_query)
            
            st.info(f"""
**RAG Test Results:**
- Query: {test_query}
- Retrieved Documents: {len(results)}
- Schema Context Length: {len(schema_context)} chars
            """)
            
            if results:
                st.caption("Sample Retrieved Documents:")
                for i, doc in enumerate(results[:3], 1):
                    st.caption(f"{i}. {doc['metadata'].get('type', 'unknown')} - Distance: {doc['distance']:.4f}")
                    
        except Exception as e:
            st.error(f"❌ RAG test failed: {e}")
    
    st.markdown("---")
    
    # Conversation Management
    st.subheader("📝 Conversation Memory")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save Chat", use_container_width=True):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"netflix_chat_{timestamp}.json"
            chat_data = {
                "timestamp": datetime.now().isoformat(),
                "conversation_count": len(st.session_state.chat_history),
                "history": st.session_state.chat_history,
            }
            st.download_button(
                label="📥 Download JSON",
                data=json.dumps(chat_data, indent=2),
                file_name=filename,
                mime="application/json",
            )
    with col2:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.conversation_context = ""
            st.session_state.last_query = None
            st.session_state.last_results = None
            st.session_state.query_count = 0
            st.rerun()
    
    st.markdown("---")
    st.subheader("📊 Conversation Stats")
    st.metric("Queries Used", f"{st.session_state.get('query_count', 0)} / 20")
    st.metric("Messages", len(st.session_state.chat_history))
    if st.session_state.chat_history:
        user_msgs = sum(1 for m in st.session_state.chat_history if m["role"] == "user")
        assistant_msgs = sum(1 for m in st.session_state.chat_history if m["role"] == "assistant")
        st.metric("Your Questions", user_msgs)
        st.metric("Agent Responses", assistant_msgs)
    
    st.markdown("---")
    st.subheader("Instructions")
    st.markdown("""
    1. Initialize schema using 'Initialize/Update Schema' button
    2. Ask natural language questions
    3. The RAG system retrieves relevant schema
    4. The LLM generates SQL with schema context
    5. View results in a formatted table
    """)
    
    st.markdown("---")
    st.subheader("Example Queries")
    examples = [
        "Indian TV shows",
        "Action movies from 2020",
        "Movies directed by Christopher Nolan",
        "Only from 2010",
        "Show count",
    ]
    for example in examples:
        st.caption(f"• {example}")
    
    st.markdown("---")
    st.subheader("Settings")
    debug_mode = st.checkbox("Debug Mode", value=False)
    show_context = st.checkbox("Show Context Memory", value=False)
    show_rag_context = st.checkbox("Show RAG Schema Context", value=False)

# Main content
st.title("🎬 Netflix AI SQL Agent (RAG-Powered)")
st.markdown("""
**Enhanced with Retrieval-Augmented Generation (RAG)**
- Dynamic schema retrieval using ChromaDB
- Semantic schema search based on queries
- Context-aware SQL generation
""")

# Display RAG context if enabled
if show_rag_context and st.session_state.schema_context:
    with st.expander("📍 RAG Schema Context", expanded=False):
        st.info(f"Retrieved Schema:\n\n{st.session_state.schema_context}")

# Display conversation context if enabled and exists
if show_context and st.session_state.conversation_context:
    with st.expander("📍 Conversation Context", expanded=False):
        st.info(st.session_state.conversation_context)
        if st.session_state.last_query:
            col1, col2 = st.columns(2)
            with col1:
                st.caption(f"Last Query: {st.session_state.last_query}")
            with col2:
                st.caption(f"Last Results: {st.session_state.last_results} records")

# Chat interface
st.subheader("Chat")

# Display chat history
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input area
user_input = st.chat_input("Ask your question about Netflix...", key="user_input")

if user_input:
    # Add user message to history
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now().isoformat(),
    })
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Check query limit per session
    if st.session_state.get("query_count", 0) >= 20:
        limit_msg = "Demo limit reached for this session — refresh to continue"
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": limit_msg,
            "timestamp": datetime.now().isoformat(),
        })
        with st.chat_message("assistant"):
            st.warning(limit_msg)
    else:
        st.session_state.query_count = st.session_state.get("query_count", 0) + 1
        # Process the query
        try:
            with st.spinner("🔄 Processing your question... (Retrieving schema → Generating SQL → Executing)"):
                # Use RAG-powered LangGraph agent
                agent_result = run_agent(
                    user_input, 
                    db_type=st.session_state.db_source,
                    table_name=st.session_state.get("active_sqlite_table")
                )
                sql_query = agent_result.get("sql")
                results = agent_result.get("result")
                error = agent_result.get("error")
                schema_context = agent_result.get("schema_context", "")

            # Store schema context for display
            st.session_state.schema_context = schema_context

            if error:
                response_text = f"❌ Error: {error}"
            else:
                response_text = f"""
**Generated SQL:**
```sql
{sql_query}
```

**Results:** Found {len(results) if results else 0} matching records

{"View results in the table below ↓" if results else "No results found for your query."}
                """

            # Add agent message to history
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now().isoformat(),
                "sql_query": sql_query,
                "results": results,
            })

            # Update conversation context for next iteration
            st.session_state.last_query = user_input
            st.session_state.last_results = len(results) if results else 0
            st.session_state.conversation_context = f"Previous query: {user_input}\nFound {len(results) if results else 0} records using:\n{sql_query}"

            # Display agent response
            with st.chat_message("assistant"):
                st.markdown(response_text)
                # Display results table
                if results:
                    st.subheader("Query Results")
                    
                    # Format results into a clean table
                    table_data = []
                    for idx, row in enumerate(results):
                        if isinstance(row, (list, tuple)):
                            # Convert tuple/list rows to simple values
                            row_values = [str(val) if val is not None else "NULL" for val in row]
                            table_data.append(row_values)
                        else:
                            # Single value
                            table_data.append([str(row) if row is not None else "NULL"])
                    
                    # Display as a simple table without showing column names
                    if table_data:
                        # Try using pandas for better formatting
                        try:
                            import pandas as pd
                            # Create column names based on number of columns
                            num_cols = len(table_data[0]) if table_data else 1
                            columns = [f"Result {i+1}" for i in range(num_cols)]
                            df = pd.DataFrame(table_data, columns=columns)
                            st.dataframe(df, use_container_width=True, hide_index=True)
                        except:
                            # Fallback to markdown table
                            for row in table_data:
                                st.write(" | ".join(row))
                    
                    # Download button
                    csv_data = "\n".join([
                        " | ".join(str(col) for col in row)
                        for row in results
                    ])
                    st.download_button(
                        label="📥 Download Results (CSV)",
                        data=csv_data,
                        file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain",
                    )
            
            # Show SQL in sidebar
            if debug_mode or user_input:
                with st.sidebar:
                    st.subheader("Generated SQL")
                    st.code(sql_query, language="sql")
        
        except Exception as e:
            error_msg = str(e)
            
            # Check if it's a "no results" case
            if "no" in error_msg.lower() and "result" in error_msg.lower():
                user_message = "No results found."
            elif "mars" in error_msg.lower() or "not found" in error_msg.lower():
                user_message = "No results found."
            else:
                # Check if error is about vague query (ask for filters)
                if "Please provide more specific filters" in error_msg:
                    user_message = error_msg
                else:
                    user_message = f"❌ Error: {error_msg}"
            
            # Add message to history
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": user_message,
                "timestamp": datetime.now().isoformat(),
            })
            
            with st.chat_message("assistant"):
                if user_message.startswith("❌"):
                    st.error(user_message)
                else:
                    st.info(user_message)
            
            logger.error(f"Query failed: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray; font-size: 0.85em;">
    AI SQL Agent powered by LLM • Dataset: Netflix Movies/TV Shows
</div>
""", unsafe_allow_html=True)
