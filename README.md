# Netflix AI SQL Agent 🎬

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)
![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-1.0+-green.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

A production-grade AI-powered SQL agent for querying Netflix movies and TV shows database using **natural language**. Powered by **LangGraph** for advanced workflow orchestration. Ask questions in English, get SQL queries automatically generated and executed with conversation memory and self-correction.

## 🌟 Features

✅ **Natural Language to SQL** - Convert plain English questions to SQL queries automatically  
✅ **LangGraph Workflow** - Multi-node agent pipeline with sophisticated state management  
✅ **Conversation Memory** - Agent remembers previous queries and maintains context across exchanges  
✅ **Self-Correction** - Automatically fixes SQL errors based on execution feedback  
✅ **Intelligent Query Modification** - Context-aware refinement ("only from 2010", "count them", etc.)  
✅ **Production-Grade Code** - Logging, configuration management, error handling, security  
✅ **Streamlit UI** - Beautiful, responsive web interface with full chat history and download  
✅ **Snowflake Support** - Direct connection to Snowflake data warehouse  
✅ **Safe SQL Execution** - Read-only queries with injection protection and validation  
✅ **Mock Mode** - Works with demo data if Snowflake unavailable  
✅ **Docker Ready** - Easy containerization and deployment  
✅ **CI/CD Workflow** - GitHub Actions for automated testing and deployment  

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- Snowflake account with database access
- OpenRouter API key

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/netflix-ai-sql-agent.git
cd netflix-ai-sql-agent

# 2. Create virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your Snowflake and API credentials

# 5. Run the app
streamlit run streamlit_app.py
```

The app opens at **http://localhost:8501**

## 📋 Configuration

Create a `.env` file with your credentials:

```env
# Snowflake Configuration
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ACCOUNT=your_account_id
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=your_database
SNOWFLAKE_SCHEMA=PUBLIC

# LLM Configuration (OpenRouter)
OPEN_ROUTER=your_api_key

# Optional
LOG_LEVEL=INFO
DEBUG=False
```

**Getting Credentials:**
1. **Snowflake Account ID**: Found in Snowflake URL (e.g., `xy12345.us-east-1`)
2. **OpenRouter API Key**: Get from https://openrouter.ai/keys

## 📂 Project Structure

```
.
├── streamlit_app.py           # Streamlit UI with chat interface and memory
├── langgraph_agent.py         # LangGraph agent orchestration
├── sql_generator.py           # SQL generation with conversation memory & self-correction
├── database.py                # Snowflake connection (with mock fallback)
├── safe_sql_executor.py       # SQL execution safety & validation
├── config.py                  # Configuration management
├── logger_config.py           # Logging setup
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
├── Dockerfile                 # Docker containerization
├── docker-compose.yml         # Docker Compose setup
├── .github/workflows/         # GitHub Actions CI/CD
│   └── python-tests.yml
├── LICENSE                    # MIT License
└── logs/                      # Application logs (auto-generated)
```

## 🏗️ Architecture

### LangGraph Workflow

The agent uses a multi-node LangGraph pipeline:

```
User Input
    ↓
[Generate SQL] → LLM with conversation history
    ↓
[Execute SQL] → SafeSQLExecutor (read-only)
    ↓
[Format Result] → Return results
    ↓
Chat Display (maintains full history)
```

**Key Components:**

- **langgraph_agent.py**: Multi-node LangGraph workflow with intelligent routing
- **sql_generator.py**: Maintains conversation history, enables self-correction
- **streamlit_app.py**: Chat interface with session state management
- **database.py**: Snowflake connection with mock fallback support
- **safe_sql_executor.py**: Query validation and safe read-only execution

## 💬 Example Queries & Conversation Memory

### Single Queries
- "Show me all action movies from 2020"
- "List Indian TV shows"
- "How many movies are there?"
- "What are the top-rated dramas?"

### Multi-turn Conversation (Demonstrates Memory & Self-Correction)

```
User: "Show me action movies"
Agent: [Generates SQL, executes, returns results]

User: "only from 2020"
Agent: [Intelligently modifies previous query, adds WHERE release_year = 2020]

User: "count them"
Agent: [Updates to COUNT(*) while preserving filters]

User: "top 5 rated"
Agent: [Adds ORDER BY rating DESC LIMIT 5]
```

The agent intelligently:
✅ Maintains previous filters ("same country", "those movies")  
✅ Modifies queries context-dependingly ("only from 2010", "top 5")  
✅ Self-corrects if SQL execution fails  
✅ Tracks full conversation history in the UI

## 🧠 Advanced Features

### Conversation Memory
- **Persistent Context**: Agent remembers last 3 exchanges
- **Context-Aware Generation**: Uses previous queries to understand follow-ups
- **Intelligent Modifications**: Detects and applies context-dependent requests

### Self-Correction
- **Error Analysis**: Captures SQL execution errors
- **Automatic Recovery**: Regenerates corrected SQL based on error feedback
- **Validation Layer**: Pre-execution validation prevents many common errors

### Smart Query Refinement
Supports natural query modifications:
- **Refinement**: "only from 2010", "same country", "those movies"
- **Aggregation**: "count them", "average rating"
- **Ordering**: "top 5", "best rated", "newest first"
- **Type Filter**: "only TV shows", "movies only"

## 🌐 Deployment Options

### Option 1: Streamlit Cloud (Recommended for Sharing)
```bash
# 1. Push to GitHub
git add .
git commit -m "Initial commit"
git push origin main

# 2. Visit https://share.streamlit.io
# 3. Deploy from your GitHub repo
# 4. Add these secrets in the dashboard:
#    SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, SNOWFLAKE_ACCOUNT,
#    SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA, OPEN_ROUTER
```

### Option 2: Docker Deployment
```bash
docker build -t netflix-ai-agent .
docker run -p 8501:8501 --env-file .env netflix-ai-agent
```

### Option 3: Local Network Sharing
1. Share project folder with team members
2. They each follow the Quick Start steps
3. Each person uses their own `.env` file

## 🔒 Security

⚠️ **Important:**
- **Never** commit `.env` file to Git
- `.env` is in `.gitignore` (protected)
- Each user needs their own credentials
- Only read-only SQL queries are executed
- SQL injection protection included

## ⚙️ How It Works

1. **User Input** → Natural language question from chat
2. **SQL Generation** → LangChain generates SQL query
3. **Validation** → Query is validated for safety
4. **Execution** → SafeSQLExecutor runs read-only query
5. **Results** → Display results in formatted table
6. **Memory** → Store in conversation history

## 🛠️ Development

### Code Quality
```bash
# Format code
black .

# Lint check
flake8 .

# Type checking
mypy .
```

### Logs
Application logs stored in `logs/` directory (auto-created)

## 🧪 Testing

The app includes:
- Mock Database mode (runs without Snowflake)
- Graceful error handling
- Input validation
- SQL safety checks

## 📚 Additional Resources

- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Detailed setup for different scenarios
- [Streamlit Documentation](https://docs.streamlit.io)
- [LangChain Docs](https://python.langchain.com)
- [Snowflake Documentation](https://docs.snowflake.com)

## 🐛 Troubleshooting

**Port Already in Use:**
```bash
streamlit run streamlit_app.py --server.port=8502
```

**Snowflake Connection Error:**
- Verify credentials in `.env`
- Check if Snowflake account is active
- App will fall back to mock data if connection fails

**Dependencies Issue:**
```bash
pip install -r requirements.txt --upgrade
```

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 💬 Support

For issues or questions:
1. Check [Troubleshooting](#-troubleshooting) section
2. Review logs in `logs/` directory
3. [Open an issue](https://github.com/yourusername/netflix-ai-sql-agent/issues)

## 👥 Authors

- Your Name - [Profile](https://github.com/yourusername)

## 🙏 Acknowledgments

- **LangChain** - Natural language to SQL
- **Streamlit** - Web UI framework
- **Snowflake** - Cloud data warehouse
- **OpenRouter** - LLM API access

---

**⭐ If you found this helpful, please star the repository!**

For detailed setup instructions, see [SETUP_GUIDE.md](SETUP_GUIDE.md)


Edit `.env`:
```dotenv
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=NETFLIX_DB
SNOWFLAKE_SCHEMA=PUBLIC

OPEN_ROUTER=sk-or-v1-xxxxx  # Your OpenRouter API key
```

## Usage

### Option 1: Web UI (Recommended)

```bash
streamlit run streamlit_app.py
```

Then open your browser to `http://localhost:8501`

### Option 2: Command Line

```bash
python ai_sql_agent_v2.py
```

Example interaction:
```
Ask your question (or 'quit' to exit): Indian TV shows

Generated SQL:
SELECT title, description FROM NETFLIX_MOVIES WHERE country = 'India' AND type = 'TV Show'

Results:
Kota Factory | In a city of coaching centers...
Chhota Bheem | A brave, energetic little boy...
...
```

### Option 3: Test Script

```bash
python test_agent.py
```

## Architecture

### Components

1. **Config Management** (`config.py`)
   - Centralized environment variable loading
   - Dataclass-based configuration
   - Validation of required settings

2. **Logging** (`logger_config.py`)
   - Structured logging to console and file
   - Debug mode support
   - Automatic log directory creation

3. **Database Layer** (`database.py`)
   - Snowflake connection management
   - Query execution with error handling
   - Schema introspection
   - Context manager support

4. **SQL Generation** (`sql_generator.py`)
   - LLM-based SQL query generation
   - SQL validation and sanitization
   - Security checks (prevent DROP/DELETE)

5. **Main Agent** (`ai_sql_agent_v2.py`)
   - Orchestrates SQL generation and execution
   - Error handling and logging
   - CLI interface

6. **Streamlit UI** (`streamlit_app.py`)
   - Chat-like interface
   - Query history management
   - Results display and export
   - Debug mode for SQL inspection

## Deployment

### Streamlit Cloud

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo and deploy
4. Set environment variables in Streamlit Cloud secrets

### Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["streamlit", "run", "streamlit_app.py"]
```

Build and run:
```bash
docker build -t netflix-ai-agent .
docker run -p 8501:8501 --env-file .env netflix-ai-agent
```

### Cloud Platforms

- **Render**: Deploy Streamlit apps easily
- **Hugging Face Spaces**: Free hosting with GPU support
- **Heroku**: Traditional hosting with automatic scaling
- **AWS/Azure**: Enterprise deployment options

## Configuration

### Environment Variables

- `SNOWFLAKE_USER`: Snowflake username
- `SNOWFLAKE_PASSWORD`: Snowflake password
- `SNOWFLAKE_ACCOUNT`: Snowflake account identifier
- `SNOWFLAKE_WAREHOUSE`: Warehouse name
- `SNOWFLAKE_DATABASE`: Database name
- `SNOWFLAKE_SCHEMA`: Schema name
- `OPEN_ROUTER`: OpenRouter API key
- `LLM_MODEL`: Model name (default: openrouter/auto)
- `LLM_TEMPERATURE`: Temperature for LLM (default: 0)
- `DEBUG`: Enable debug mode (default: false)
- `LOG_LEVEL`: Logging level (default: INFO)

## Example Queries

- "Indian TV shows"
- "Action movies from 2020"
- "Movies directed by Christopher Nolan"
- "Shows with rating PG-13"
- "Recent releases in 2023"
- "Movies with more than 100 minutes duration"

## Security

- SQL queries are validated before execution
- Only SELECT statements are allowed
- Input validation and sanitization
- Secure credential management via .env
- No SQL injection vulnerabilities

## Performance

- Efficient database connection pooling
- Optimized SQL queries with specific column selection
- Query result caching in session state
- Lazy loading of dependencies

## Troubleshooting

### "Missing required environment variables"
Ensure all required variables are set in `.env`

### "Connection refused"
Check Snowflake credentials and network connectivity

### "Query generation fails"
Verify OpenRouter API key and balance

### "Streamlit not starting"
Run: `pip install streamlit` or `pip install -r requirements.txt`

## Future Enhancements

- [ ] LangGraph integration for complex workflows
- [ ] Multi-turn conversation support
- [ ] Query result caching
- [ ] Advanced query optimization
- [ ] Natural language to data visualization
- [ ] Batch query processing
- [ ] Query performance analytics

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details

## Support

For issues or questions:
- Open an issue on GitHub
- Check existing documentation
- Review logs in `logs/` directory

---

**Made with ❤️ using LangChain, Streamlit, and OpenRouter**
