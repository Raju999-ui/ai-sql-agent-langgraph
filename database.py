"""Database layer for Snowflake interactions."""

import logging
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
        # Return sample data for any query
        self.results = list(self.mock_data['shows'])  # Convert to list to ensure it's mutable
        self.description = [('title',)]
        return self
    
    def fetchall(self):
        """Fetch all results."""
        return self.results
    
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
            if not SNOWFLAKE_AVAILABLE:
                logger.warning(f"Snowflake unavailable, falling back to mock: {str(e)}")
                self.connection = MockSnowflakeConnection()
            else:
                logger.error(f"Failed to connect to Snowflake: {str(e)}")
                raise

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
        """Get table schema information.
        
        Returns:
            Schema information as string
        """
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
