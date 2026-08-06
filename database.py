"""Database layer for Snowflake interactions."""

import logging
import sqlite3
from typing import List, Tuple, Any
from safe_sql_executor import SafeSQLExecutor
from config import SnowflakeConfig

logger = logging.getLogger(__name__)

# Try to import snowflake, fall back to mock if not available
try:
    import snowflake.connector
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False
    logger.warning("Snowflake connector not available, using mock mode")


class MockSnowflakeConnection:
    """Mock Snowflake connection for testing without actual Snowflake."""
    
    def __init__(self):
        """Initialize mock connection."""
        self.mock_data = {
            'shows': [
                ('Breaking Bad',),
                ('Stranger Things',),
                ('The Crown',),
                ('Money Heist',),
                ('Dark',),
                ('Peaky Blinders',),
                ('The Mandalorian',),
                ('Squid Game',),
                ('Wednesday',),
                ('The Witcher',),
                ('Ozark',),
                ('Better Call Saul',),
                ('Mindhunter',),
                ('Russian Doll',),
                ('The Last of Us',),
                ('Andor',),
                ('The Last Kingdom',),
                ('Viking',),
                ('Game of Thrones',),
                ('House of Dragons',),
            ]
        }
    
    def cursor(self):
        """Return a mock cursor."""
        return MockCursor(self.mock_data)
    
    def close(self):
        """Close the connection."""
        pass


class MockCursor:
    """Mock cursor for executing queries."""
    
    def __init__(self, mock_data):
        """Initialize mock cursor."""
        self.mock_data = mock_data
        self.results = []
        self.description = None
    
    def execute(self, query):
        """Mock execute - return sample data."""
        self.results = list(self.mock_data['shows'])
        self.description = [('title',)]
        return self
    
    def fetchall(self):
        """Fetch all results."""
        return self.results
    
    def fetchmany(self, size=None):
        """Fetch many results."""
        if size is None:
            return self.fetchall()
        return self.results[:size]
    
    def close(self):
        """Close the cursor."""
        pass


class SnowflakeDB:
    """Snowflake database interface."""

    def __init__(self, config: SnowflakeConfig):
        """Initialize database connection.
        
        Args:
            config: Snowflake configuration
        """
        self.config = config
        self.connection = None

    def connect(self) -> None:
        """Establish connection to Snowflake."""
        if not SNOWFLAKE_AVAILABLE or not self.config.user or not self.config.account:
            logger.warning("Snowflake credentials not fully configured or driver unavailable; falling back to mock mode")
            self.connection = MockSnowflakeConnection()
            return

        try:
            logger.info(f"Connecting to Snowflake account: {self.config.account}")
            self.connection = snowflake.connector.connect(
                user=self.config.user,
                password=self.config.password,
                account=self.config.account,
                warehouse=self.config.warehouse,
                database=self.config.database,
                schema=self.config.schema,
            )
            logger.info("Successfully connected to Snowflake")
        except Exception as e:
            logger.warning(f"Failed to connect to Snowflake, falling back to mock mode: {str(e)}")
            self.connection = MockSnowflakeConnection()

    def disconnect(self) -> None:
        """Close connection to Snowflake."""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from Snowflake")

    def execute_query(self, query: str) -> List[Tuple[Any, ...]]:
        """Execute a SQL query.
        
        Args:
            query: SQL query to execute
            
        Returns:
            List of result rows
            
        Raises:
            Exception: If query execution fails
        """
        if not self.connection:
            raise RuntimeError("Not connected to Snowflake. Call connect() first.")
        
        try:
            logger.debug(f"Executing query: {query}")

            # For mock connections, return sample data
            if isinstance(self.connection, MockSnowflakeConnection):
                logger.info("Using mock data for testing")
                cursor = self.connection.cursor()
                results = cursor.execute(query).fetchall()
                cursor.close()
            else:
                # Use SafeSQLExecutor to run the read-only query with protections
                safe_executor = SafeSQLExecutor(self.connection)
                results = safe_executor.execute(query)

            logger.info(f"Query executed successfully, returned {len(results)} rows")
            return results
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}\nQuery: {query}")
            raise

    def get_schema(self) -> str:
        """Get table schema information."""
        try:
            query = f"""
            SELECT COLUMN_NAME, DATA_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'NETFLIX_MOVIES' 
            AND TABLE_SCHEMA = '{self.config.schema}'
            ORDER BY ORDINAL_POSITION
            """
            results = self.execute_query(query)
            schema_info = "\n".join([f"- {row[0]} ({row[1]})" for row in results])
            return schema_info
        except Exception as e:
            logger.error(f"Failed to get schema: {str(e)}")
            raise

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


class SQLiteDB:
    """SQLite database interface for local CSV querying."""

    def __init__(self, db_path: str = "local_data.db"):
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection = None

    def connect(self) -> None:
        """Establish connection to SQLite."""
        try:
            logger.info(f"Connecting to SQLite database: {self.db_path}")
            self.connection = sqlite3.connect(self.db_path)
            logger.info("Successfully connected to SQLite")
        except Exception as e:
            logger.error(f"Failed to connect to SQLite: {str(e)}")
            raise

    def disconnect(self) -> None:
        """Close connection to SQLite."""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from SQLite")

    def execute_query(self, query: str) -> List[Tuple[Any, ...]]:
        """Execute a SQL query.
        
        Args:
            query: SQL query to execute
            
        Returns:
            List of result rows
            
        Raises:
            Exception: If query execution fails
        """
        if not self.connection:
            raise RuntimeError("Not connected to SQLite. Call connect() first.")
        
        try:
            logger.debug(f"Executing query: {query}")
            safe_executor = SafeSQLExecutor(self.connection)
            results = safe_executor.execute(query)
            logger.info(f"Query executed successfully, returned {len(results)} rows")
            return results
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}\nQuery: {query}")
            raise

    def get_schema(self) -> str:
        """Get all table and column information."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view');")
            tables = cursor.fetchall()
            
            schema_parts = []
            for table_row in tables:
                table_name = table_row[0]
                schema_parts.append(f"Table: {table_name}")
                
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                for col in columns:
                    col_name = col[1]
                    col_type = col[2]
                    schema_parts.append(f"  - {col_name} ({col_type})")
                schema_parts.append("")
                
            cursor.close()
            return "\n".join(schema_parts)
        except Exception as e:
            logger.error(f"Failed to get SQLite schema: {str(e)}")
            raise

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
