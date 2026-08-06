# RAG-Powered SQL Agent - Setup Guide

## Quick Start (5 minutes)

### 1. Install Dependencies
```bash
# Activate your virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all required packages
pip install -r requirements.txt
```

### 2. Configure Environment Variables (.env)
```bash
# Copy .env template and update with your credentials
# Required variables:

# Snowflake Configuration
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ACCOUNT=your_account_id
SNOWFLAKE_WAREHOUSE=YOUR_WAREHOUSE
SNOWFLAKE_DATABASE=YOUR_DATABASE
SNOWFLAKE_SCHEMA=YOUR_SCHEMA

# OpenAI Configuration (for embeddings & LLM)
OPENAI_API_KEY=sk-...

# Optional: If using OpenRouter instead of direct OpenAI
# OPENROUTER_API_KEY=...
```

### 3. Initialize RAG Schema (One-time setup)
```bash
# This fetches your Snowflake schema and creates embeddings
python schema_ingestion.py

# Or specify ChromaDB path:
python schema_ingestion.py ./my_chroma_db
```

**What happens:**
- Connects to Snowflake
- Fetches all table and column metadata
- Creates embeddings using OpenAI
- Stores in ChromaDB (./chroma_db by default)

**You should see:**
```
✓ Schema ingestion completed!
Collection: snowflake_schema
Documents: 45
Storage: ./chroma_db
```

### 4. Verify RAG Setup
```bash
# Test the schema retriever
python schema_retriever.py

# Or specify ChromaDB path:
python schema_retriever.py ./my_chroma_db
```

**Expected output:**
```
📋 Available Tables: 5
  - NETFLIX_MOVIES: 12 columns
  - USERS: 8 columns
  ...

🧪 Testing Schema Retriever

Query: Show all movies
Retrieved 5 documents:
  ...
```

### 5. Run the Application
```bash
# Start Streamlit app
streamlit run streamlit_app.py

# App opens at http://localhost:8501
```

**In the UI:**
1. Click "Initialize/Update Schema" button
2. Click "Test RAG Retriever" button
3. Ask a question: "Show me movies from 2020"
4. View the generated SQL and results


## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Web Interface                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│   ┌─────────────┐         ┌────────────────────────────┐   │
│   │  User Input │────────>│  LangGraph Agent           │   │
│   └─────────────┘         │  (Orchestrates workflow)   │   │
│                           └────────┬────────────────────┘   │
│                                    │                         │
│         ┌──────────────────────────┼──────────────────────┐ │
│         │                          │                      │ │
│         ▼                          ▼                      ▼ │
│   ┌──────────────┐      ┌──────────────────┐    ┌──────────┐
│   │Schema        │      │SQL Generator     │    │SQL       │
│   │Retriever     │      │(with RAG)        │    │Executor  │
│   └──────────────┘      └──────────────────┘    └──────────┘
│         │                      ▲                      │
│         │                      │                      │
│         ▼                      │                      ▼
│   ┌──────────────┐             │             ┌──────────────┐
│   │ChromaDB      │             │             │Snowflake     │
│   │(Vector DB)   │             │             │Database      │
│   └──────────────┘             │             └──────────────┘
│                                │
│                     ┌──────────┘
│                     │
│         ┌───────────▼────────────┐
│         │Conversation History    │
│         │(For context)           │
│         └────────────────────────┘
│
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
d:\projectfinal\
├── .env                          # Environment variables (create this)
├── .env.example                  # Template (optional)
├── requirements.txt              # Dependencies
├── README.md                      # Original project readme
├── RAG_EXPLANATION.md           # This file - RAG details
├── SETUP_GUIDE.md               # This file - Setup instructions
│
├── # Core Application Files
├── streamlit_app.py              # Web UI (updated with RAG)
├── langgraph_agent.py            # Agent orchestration (updated with RAG)
├── sql_generator.py              # SQL generation (now RAG-aware)
├── safe_sql_executor.py          # SQL validation & execution
├── database.py                   # Snowflake connection
├── config.py                     # Configuration management
├── logger_config.py              # Logging setup
│
├── # New RAG Components
├── schema_ingestion.py           # Fetch schema & create embeddings
├── schema_retriever.py           # Retrieve relevant schema
│
├── # Data Storage
├── chroma_db/                    # Vector database (created after ingestion)
│   ├── .chroma/
│   ├── data/
│   └── ...
│
└── logs/                         # Application logs
    └── ...
```

## File Changes Summary

### New Files Created:
1. **schema_ingestion.py** (290 lines)
   - Fetches Snowflake schema
   - Creates embeddings
   - Stores in ChromaDB

2. **schema_retriever.py** (240 lines)
   - Queries ChromaDB
   - Retrieves relevant schema
   - Formats for LLM

### Updated Files:
1. **sql_generator.py**
   - Added `schema_context` parameter
   - System prompt includes RAG instructions
   - Accepts dynamic schema context

2. **langgraph_agent.py**
   - Added `retrieve_schema` node
   - Updated state with `schema_context`
   - Graph now: retrieve → generate → execute

3. **streamlit_app.py**
   - Added RAG management section
   - Schema ingestion button
   - RAG testing interface
   - Schema context display

4. **requirements.txt**
   - Added chromadb>=0.5.0
   - Added chroma-hnswlib>=0.4.0

## Step-by-Step Usage

### First Time Using RAG:

```bash
# 1. Set up environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Create .env file with your credentials
# (See Configuration section above)

# 3. Ingest schema
python schema_ingestion.py

# 4. Start app
streamlit run streamlit_app.py

# 5. In UI: Click "Initialize/Update Schema"
```

### Regular Usage:

```bash
# Just run the app
streamlit run streamlit_app.py

# Ask questions in the UI
# - Questions are automatically RAG-enhanced
# - Conversation history is maintained
# - Schema context is retrieved dynamically
```

### Update Schema (When database changes):

```bash
# Re-run ingestion to update embeddings
python schema_ingestion.py

# Or in UI: Click "Initialize/Update Schema" button
```

## Testing & Validation

### Test 1: Schema Ingestion
```bash
python schema_ingestion.py

# Should output:
# ✓ Schema ingestion completed!
# Collection: snowflake_schema
# Documents: X
```

### Test 2: Schema Retrieval
```bash
# In Streamlit UI:
# 1. Navigate to sidebar
# 2. Click "Test RAG Retriever"
# 3. Should show retrieved documents
```

### Test 3: End-to-End Query
```bash
# In Streamlit UI:
# 1. Ask: "Show me movies from 2020"
# 2. Should retrieve schema for tables/columns
# 3. Should generate SQL with correct column names
# 4. Should execute and return results
```

### Test 4: Conversation Memory
```bash
# In Streamlit UI:
# Query 1: "Movies from India"
# Query 2: "Only count them"
# Query 2 should reference Query 1's filters
```

## Troubleshooting

### Error: "Missing required environment variables"
**Solution:** Create `.env` file with all required Snowflake and OpenAI credentials

### Error: "ChromaDB collection not found"
**Solution:** Run `python schema_ingestion.py` to initialize the database

### Error: "OPENAI_API_KEY invalid"
**Solution:** Check your OpenAI API key in `.env` file

### Error: "Snowflake connection failed"
**Solution:**
- Verify credentials in `.env`
- Check network/firewall access to Snowflake
- Verify warehouse/database/schema exist

### Error: "RAG not initialized"
**Solution:** Click "Initialize/Update Schema" button in Streamlit UI

### Poor SQL Generation Quality
**Solution:**
- Run schema ingestion again: `python schema_ingestion.py`
- Verify schema is being retrieved (enable "Show RAG Schema Context")
- Check if column names are exact matches in Snowflake

### Slow Response Times
**Likely causes:**
- Large schema with many tables
- Network latency to Snowflake/OpenAI
- ChromaDB indexing

**Solutions:**
- Check network connectivity
- Consider reducing top_k in schema_retriever.py
- Run on a faster machine

## Configuration Options

### ChromaDB Path
```python
# In schema_retriever.py, line X:
retriever = SchemaRetriever(
    chroma_db_path="./chroma_db",  # Change this path
    top_k=5
)
```

### Number of Retrieved Results
```python
# In schema_retriever.py:
retriever = SchemaRetriever(
    top_k=5  # Change to retrieve more/fewer documents
)
```

### Embedding Model
```python
# In schema_ingestion.py and schema_retriever.py:
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"  # Options: small, large
)
```

### SQL Generator Temperature
```python
# In config.py:
class LLMConfig:
    temperature: float = 0  # 0=deterministic, 1=creative
```

## Example Queries to Try

```
1. "Show me Indian TV shows"
2. "Action movies from 2020"
3. "Count movies by rating"
4. "Top 5 most recent releases"
5. "Shows from USA only"
6. "Only from 2015"  (refers to previous query)
7. "Count them"      (uses conversation context)
8. "Same country, but movies"
9. "Dramas directed by someone"
10. "How many total?"
```

## Performance Benchmarks

On typical setup:
- Schema ingestion: 30-60 seconds
- Schema retrieval: 200-500ms
- SQL generation: 1-3 seconds
- SQL execution: Varies (typically 1-10 seconds)
- Total latency per query: 2-15 seconds

Factors affecting performance:
- Schema size (number of tables/columns)
- Snowflake warehouse size
- LLM response time
- Network latency

## Monitoring & Debugging

### Enable Debug Mode in UI
- Check "Debug Mode" in Streamlit sidebar
- Shows generated SQL in sidebar

### Enable Schema Context Display
- Check "Show RAG Schema Context" in sidebar
- Shows retrieved schema for each query

### Check Logs
```bash
# View application logs
tail -f logs/app.log

# Or in Python:
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Monitor ChromaDB
```bash
# Check ChromaDB stats
python -c "from schema_retriever import create_retriever_from_env; r = create_retriever_from_env(); print(r.get_all_tables())"
```

## Production Deployment

### Before Deploying:
1. ✓ Test all queries thoroughly
2. ✓ Verify Snowflake connection settings
3. ✓ Ensure OpenAI API key is valid
4. ✓ Set appropriate temperature/max_tokens
5. ✓ Configure max_rows in SafeSQLExecutor

### For Production:
```bash
# Use gunicorn with Streamlit (if deploying as web service)
# Or use streamlit Cloud: https://streamlit.io/cloud

# Set environment variables securely (don't commit .env)
# Use secrets manager (AWS Secrets Manager, Azure Key Vault, etc.)

# Monitor costs:
# - OpenAI API calls for embeddings + generation
# - Snowflake query execution
# - ChromaDB storage
```

## Support & Additional Resources

- **Streamlit Docs:** https://docs.streamlit.io
- **LangChain Docs:** https://python.langchain.com
- **ChromaDB Docs:** https://docs.trychroma.com
- **LangGraph Docs:** https://langchain-ai.github.io/langgraph
- **OpenAI Embeddings:** https://platform.openai.com/docs/guides/embeddings

## Next Steps

1. ✓ Follow setup guide above
2. ✓ Test with sample queries
3. ✓ Customize example queries in Streamlit UI
4. ✓ Fine-tune temperature and max_tokens
5. ✓ Deploy to production
6. ✓ Monitor and optimize performance

Enjoy your RAG-powered SQL agent! 🚀
