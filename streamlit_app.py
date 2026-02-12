"""Streamlit UI for the AI SQL Agent with conversation memory."""

import streamlit as st
import logging
import json
from datetime import datetime
from config import AppConfig
from logger_config import setup_logging
from langgraph_agent import run_agent

# Setup logging
logger = setup_logging("INFO", False)

# Page configuration
st.set_page_config(
    page_title="Netflix AI SQL Agent",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Initialize session state (no agent object needed for stateless run_agent)
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    st.session_state.conversation_context = ""
    st.session_state.last_query = None
    st.session_state.last_results = None

# Sidebar
with st.sidebar:
    st.header("🎬 Netflix AI SQL Agent")
    st.markdown("---")
    
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
            st.rerun()
    
    st.markdown("---")
    st.subheader("📊 Conversation Stats")
    st.metric("Messages", len(st.session_state.chat_history))
    if st.session_state.chat_history:
        user_msgs = sum(1 for m in st.session_state.chat_history if m["role"] == "user")
        assistant_msgs = sum(1 for m in st.session_state.chat_history if m["role"] == "assistant")
        st.metric("Your Questions", user_msgs)
        st.metric("Agent Responses", assistant_msgs)
    
    st.markdown("---")
    st.subheader("Instructions")
    st.markdown("""
    1. Ask a natural language question about Netflix shows/movies
    2. The agent remembers previous context
    3. You can reference earlier queries
    4. View the results in a formatted table
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

# Main content
st.title("🎬 Netflix AI SQL Agent")
st.markdown("Ask natural language questions about Netflix movies and TV shows")

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
user_input = st.chat_input("Ask your question...", key="user_input")

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
    
    # Process the query
    with st.spinner("🔄 Processing your question..."):
        try:
            # Use LangGraph agent (stateless)
            agent_result = run_agent(user_input)
            sql_query = agent_result.get("sql")
            results = agent_result.get("result")
            error = agent_result.get("error")

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
