"""Safe SQL executor to run read-only queries with protections."""

import logging
import re
from typing import List, Tuple, Any

logger = logging.getLogger(__name__)


class SQLSecurityException(Exception):
    """Exception for SQL security violations."""
    pass


class SafeSQLExecutor:
    """Production-safe SQL executor for read-only queries.
    
    Features:
    - Ensures only SELECT statements are run
    - Blocks dangerous SQL keywords (DROP, DELETE, etc.)
    - Prevents multiple statements and comments
    - Limits returned rows to `max_rows`
    """

    FORBIDDEN_KEYWORDS = [
        "drop", "delete", "update", "insert", "alter",
        "truncate", "create", "replace", "grant", "revoke"
    ]

    def __init__(self, connection, max_rows: int = 1000):
        """Initialize executor with database connection.
        
        Args:
            connection: Database connection object
            max_rows: Maximum rows to return (default: 1000)
        """
        self.connection = connection
        self.max_rows = max_rows

    def validate_query(self, sql: str) -> str:
        """Validate SQL query for safety.
        
        Args:
            sql: SQL query to validate
            
        Returns:
            Validated SQL query
            
        Raises:
            SQLSecurityException: If query fails security checks
        """
        if not sql or not isinstance(sql, str):
            raise SQLSecurityException("Invalid SQL query provided")

        clean_sql = sql.strip().lower()

        # Only allow SELECT
        if not clean_sql.startswith("select"):
            raise SQLSecurityException("Only SELECT queries are allowed")

        # Block multiple statements
        if ";" in clean_sql:
            raise SQLSecurityException("Multiple SQL statements are not allowed")

        # Block comments
        if "--" in clean_sql or "/*" in clean_sql:
            raise SQLSecurityException("SQL comments are not allowed")

        # Block dangerous keywords
        for keyword in self.FORBIDDEN_KEYWORDS:
            if re.search(rf"\b{keyword}\b", clean_sql):
                raise SQLSecurityException(f"Dangerous keyword not allowed: {keyword}")

        return sql

    def execute(self, query: str) -> List[Tuple[Any, ...]]:
        """Execute validated SELECT query and return results as tuples.
        
        Args:
            query: SQL query to execute
            
        Returns:
            List of result tuples (one tuple per row)
            
        Raises:
            SQLSecurityException: If query fails security validation
            RuntimeError: If execution fails
        """
        try:
            # Validate query
            safe_sql = self.validate_query(query)
            
            logger.debug(f"Executing validated query: {safe_sql}")
            
            cursor = self.connection.cursor()
            cursor.execute(safe_sql)

            # Fetch up to max_rows + 1 to detect overflow
            results = cursor.fetchmany(self.max_rows + 1)
            cursor.close()

            if not results:
                logger.debug("Query returned no rows")
                return []

            # Trim if exceeded max_rows
            if len(results) > self.max_rows:
                logger.warning(f"Query returned {len(results)} rows; truncating to {self.max_rows}")
                return results[:self.max_rows]

            logger.info(f"Query executed successfully, returned {len(results)} rows")
            return results

        except SQLSecurityException as e:
            logger.error(f"Query validation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise RuntimeError(f"Database error: {str(e)}")
