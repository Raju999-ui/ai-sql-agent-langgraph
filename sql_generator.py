"""SQL generation engine using LLM with conversation memory and self-correction."""

import logging
from typing import Optional, List, Dict
from langchain_openai import ChatOpenAI
from config import LLMConfig

logger = logging.getLogger(__name__)


class SQLGenerator:
    """Generate SQL queries using LLM."""

    def __init__(self, config: LLMConfig):
        """Initialize SQL generator.
        
        Args:
            config: LLM configuration
        """
        self.config = config
        self.llm = ChatOpenAI(
            model=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
        
        self.schema_description = """
You are an advanced Snowflake SQL generation agent with conversation memory and self-correction ability.

Table: NETFLIX_MOVIES

Columns:
- show_id (STRING): Unique identifier
- type (STRING): 'Movie' or 'TV Show'
- title (STRING): Title of the show/movie
- director (STRING): Director name(s)
- cast (STRING): Cast members
- country (STRING): Country/countries
- date_added (STRING): Date added to Netflix
- release_year (INTEGER): Release year
- rating (STRING): Content rating
- duration (STRING): Duration
- listed_in (STRING): Categories/genres
- description (STRING): Description

RESPONSIBILITIES:

1. Use conversation history to maintain context.
2. If user says context-dependent phrases like:
   - "only from 2010" → filter release_year
   - "same country" → use previous country filter
   - "those movies" → reference previous result set
   - "count them" → use COUNT(*)
   - "top 5" → use ORDER BY + LIMIT 5
   - "only TV shows" → filter type = 'TV Show'
   Intelligently modify the PREVIOUS SQL query instead of starting from scratch.
3. Preserve previous filters unless user changes topic.
4. If user resets topic completely, ignore old context.
5. Handle self-correction: analyze errors and regenerate corrected SQL.
6. For counts: SELECT COUNT(*) FROM NETFLIX_MOVIES WHERE ...
7. For top/best: add ORDER BY column DESC LIMIT n
8. For text filters: use LIKE '%value%' for flexibility.
9. Always use valid Snowflake SQL syntax with correct comma placement.

STRICT RULES:

- Generate ONLY raw SQL (nothing else).
- Do NOT use markdown, backticks, or code blocks.
- Do NOT include explanations or comments.
- Do NOT use SELECT *.
- Do NOT generate INSERT, UPDATE, DELETE, DROP, ALTER, or TRUNCATE.
- Output ONLY the final corrected SQL query.
- Ensure column names match exactly: show_id, type, title, director, cast, country, date_added, release_year, rating, duration, listed_in, description.
- Ensure proper comma placement in SELECT and WHERE clauses.
- No trailing commas or syntax errors.

EXAMPLES:

SELECT title, director FROM NETFLIX_MOVIES WHERE country LIKE '%USA%'
SELECT title, release_year FROM NETFLIX_MOVIES WHERE type = 'Movie' AND release_year >= 2020
SELECT COUNT(*) FROM NETFLIX_MOVIES WHERE listed_in LIKE '%Action%'
SELECT title, rating FROM NETFLIX_MOVIES WHERE director LIKE '%Nolan%' ORDER BY release_year DESC LIMIT 5
"""
        
        # Conversation history to maintain context
        self.conversation_history: List[Dict[str, str]] = []

    def generate(self, question: str, previous_error: Optional[str] = None) -> str:
        """Generate SQL query from natural language question with conversation memory.
        
        Args:
            question: Natural language question about the data
            previous_error: Error from previous query execution (for self-correction)
            
        Returns:
            Generated SQL query
            
        Raises:
            Exception: If generation fails
        """
        try:
            # Check if question is too vague
            vague_keywords = ["show", "list", "get", "all", "everything", "movies", "shows", "tv"]
            question_lower = question.lower().strip()
            
            # If question is just generic without filters, ask for specifics
            if question_lower in vague_keywords or (
                len(question.split()) < 3 and 
                not any(keyword in question_lower for keyword in [
                    "where", "filter", "from", "by", "with", "in", "2020", "2021", "2022", "2023", 
                    "2024", "2025", "2026", "director", "actor", "genre", "rating", "india", "usa", 
                    "action", "drama", "comedy", "horror", "animated", "netflix", "count", "top", "best",
                    "only", "same", "those", "them"
                ])
            ):
                raise ValueError("""Please provide more specific filters. 

Try asking with details like:
• Time period: "movies from 2020"
• Country: "shows from India"
• Genre: "action movies"
• Type: "TV shows only"
• Director/Actor: "movies by Christopher Nolan"
• Count: "how many movies"
• Top: "top 5 rated movies"
• Context: "only from 2010", "same country", "count them"

What specific Netflix content are you looking for?""")
            
            logger.debug(f"Generating SQL for question: {question}")
            
            # Build context from conversation history
            context_str = self._build_context_string()
            
            # Handle self-correction if there was a previous error
            error_context = ""
            if previous_error:
                error_context = f"\n\nPrevious query error: {previous_error}\nGenerate corrected SQL query that fixes this error."
            
            # Detect if this is a context-dependent query that should modify previous
            is_context_dependent = self._is_context_dependent_query(question_lower)
            modification_hint = ""
            if is_context_dependent and self.conversation_history:
                modification_hint = "\n\nHint: This appears to be a context-dependent request. Consider intelligently modifying the previous SQL if applicable."
            
            prompt = f"""{self.schema_description}

{context_str}

User question: {question}{modification_hint}{error_context}

Generate the SQL query now:"""
            
            response = self.llm.invoke(prompt)
            sql_query = response.content.strip()
            
            # Check if LLM returned an error message instead of SQL
            if "error" in sql_query.lower() or "no results" in sql_query.lower() or "not found" in sql_query.lower():
                raise ValueError("No results found.")
            
            # Clean up markdown formatting if present
            if sql_query.startswith("```"):
                sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            
            # Validate it's actually SQL
            if not sql_query.upper().startswith("SELECT"):
                raise ValueError("No results found.")
            
            logger.debug(f"Generated SQL: {sql_query}")
            
            # Track in conversation history
            self._track_query(question, sql_query)
            
            return sql_query
        except Exception as e:
            logger.error(f"SQL generation failed: {str(e)}")
            raise
    
    def _build_context_string(self) -> str:
        """Build context string from conversation history.
        
        Returns:
            Formatted conversation context
        """
        if not self.conversation_history:
            return "Conversation History: None (starting fresh)"
        
        context_lines = ["Conversation History:"]
        for i, entry in enumerate(self.conversation_history[-3:], 1):  # Last 3 exchanges
            context_lines.append(f"{i}. User: {entry['question']}")
            context_lines.append(f"   SQL: {entry['sql']}")
        
        return "\n".join(context_lines)
    
    def _is_context_dependent_query(self, question_lower: str) -> bool:
        """Detect if query is context-dependent and should modify previous.
        
        Args:
            question_lower: Lowercased question
            
        Returns:
            True if query appears context-dependent
        """
        context_keywords = [
            "only from", "same", "those", "them", "count them",
            "top 5", "top 10", "best", "more", "less",
            "also", "additionally", "and then", "now", "then",
            "similar", "like the", "such as"
        ]
        return any(keyword in question_lower for keyword in context_keywords)
    
    def _track_query(self, question: str, sql: str) -> None:
        """Track question and SQL in conversation history.
        
        Args:
            question: User's question
            sql: Generated SQL
        """
        self.conversation_history.append({
            "question": question,
            "sql": sql
        })
        logger.debug(f"Tracked query in history. Total: {len(self.conversation_history)}")
    
    def reset_history(self) -> None:
        """Reset conversation history (when topic changes completely)."""
        self.conversation_history = []
        logger.debug("Conversation history reset")


class SQLValidator:
    """Validate SQL queries before execution."""

    @staticmethod
    def validate(query: str) -> bool:
        """Validate SQL query syntax.
        
        Args:
            query: SQL query to validate
            
        Returns:
            True if query is valid
            
        Raises:
            ValueError: If query is invalid
        """
        query = query.strip()
        
        # Remove trailing semicolon
        if query.endswith(";"):
            query = query[:-1].strip()
        
        # Basic checks
        if not query.upper().startswith("SELECT"):
            raise ValueError("Query must be a SELECT statement")
        
        if "DROP" in query.upper() or "DELETE" in query.upper() or "UPDATE" in query.upper():
            raise ValueError("Only SELECT queries are allowed")
        
        logger.debug(f"Query validation passed: {query[:50]}...")
        return True
