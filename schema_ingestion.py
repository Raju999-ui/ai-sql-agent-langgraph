"""Schema ingestion module to fetch Snowflake schema and create embeddings in ChromaDB."""

try:
    import pysqlite3
    import sys
    sys.modules['sqlite3'] = pysqlite3
except ImportError:
    pass

import logging
import os
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import chromadb
from chromadb.config import Settings
from langchain_openai import OpenAIEmbeddings
from config import SnowflakeConfig, get_env_var
from database import SnowflakeDB

logger = logging.getLogger(__name__)


class SchemaIngestion:
    """Fetch Snowflake schema and create embeddings in ChromaDB."""

    def __init__(
        self,
        snowflake_config: SnowflakeConfig,
        embedding_model: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
        chroma_db_path: str = "./chroma_db",
        collection_name: str = "snowflake_schema"
    ):
        """Initialize schema ingestion."""
        self.snowflake_config = snowflake_config
        self.embedding_model = embedding_model
        resolved_api_key = api_key or get_env_var("OPENAI_API_KEY") or get_env_var("OPEN_ROUTER") or ""
        self.api_key = resolved_api_key
        self.chroma_db_path = chroma_db_path
        self.collection_name = collection_name
        
        os.makedirs(chroma_db_path, exist_ok=True)
        
        # Initialize embeddings
        if resolved_api_key:
            try:
                self.embeddings = OpenAIEmbeddings(
                    model=embedding_model,
                    api_key=resolved_api_key
                )
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAIEmbeddings: {e}")
                self.embeddings = None
        else:
            self.embeddings = None

        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={
                "description": "Snowflake schema embeddings",
                "created_at": datetime.now().isoformat()
            }
        )

    def fetch_snowflake_schema(self) -> Dict[str, Any]:
        """Fetch table and column information from Snowflake."""
        try:
            db = SnowflakeDB(self.snowflake_config)
            db.connect()
            connection = db.connection
            
            cursor = connection.cursor()
            
            # Fetch tables from information schema
            cursor.execute(f"""
                SELECT TABLE_NAME, COMMENT
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = '{self.snowflake_config.schema}'
                    AND TABLE_CATALOG = '{self.snowflake_config.database}'
            """)
            
            tables_raw = cursor.fetchall()
            schema_info = {"tables": []}
            
            for table_row in tables_raw:
                table_name = table_row[0]
                table_comment = table_row[1] or f"Table containing {table_name} data"
                
                # Fetch columns for this table
                cursor.execute(f"""
                    SELECT COLUMN_NAME, DATA_TYPE, COMMENT
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = '{self.snowflake_config.schema}'
                        AND TABLE_CATALOG = '{self.snowflake_config.database}'
                        AND TABLE_NAME = '{table_name}'
                    ORDER BY ORDINAL_POSITION
                """)
                
                columns_raw = cursor.fetchall()
                columns = []
                
                for col_row in columns_raw:
                    col_name = col_row[0]
                    col_type = col_row[1]
                    col_comment = col_row[2] or f"{col_name} column of type {col_type}"
                    
                    columns.append({
                        "name": col_name,
                        "type": col_type,
                        "description": col_comment
                    })
                
                table_info = {
                    "name": table_name,
                    "description": table_comment,
                    "columns": columns
                }
                
                schema_info["tables"].append(table_info)
            
            cursor.close()
            db.connection.close()
            
            logger.info(f"Fetched schema for {len(schema_info['tables'])} tables")
            return schema_info
            
        except Exception as e:
            logger.error(f"Error fetching Snowflake schema: {e}")
            raise

    def fetch_sqlite_schema(self) -> Dict[str, Any]:
        """Fetch table and column information from local SQLite database."""
        try:
            from database import SQLiteDB
            db = SQLiteDB()
            db.connect()
            
            cursor = db.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view');")
            tables_raw = cursor.fetchall()
            
            schema_info = {"tables": []}
            
            for table_row in tables_raw:
                table_name = table_row[0]
                if table_name.startswith("sqlite_"):
                    continue
                
                table_comment = f"Table containing {table_name} data"
                
                # Fetch columns for this table
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns_raw = cursor.fetchall()
                columns = []
                
                for col_row in columns_raw:
                    col_name = col_row[1]
                    col_type = col_row[2]
                    col_comment = f"{col_name} column of type {col_type}"
                    
                    columns.append({
                        "name": col_name,
                        "type": col_type,
                        "description": col_comment
                    })
                
                table_info = {
                    "name": table_name,
                    "description": table_comment,
                    "columns": columns
                }
                
                schema_info["tables"].append(table_info)
            
            cursor.close()
            db.disconnect()
            
            logger.info(f"Fetched SQLite schema for {len(schema_info['tables'])} tables")
            return schema_info
        except Exception as e:
            logger.error(f"Error fetching SQLite schema: {e}")
            raise

    def create_schema_embeddings(self, schema_info: Dict[str, Any]) -> None:
        """Create embeddings for tables and columns and store in ChromaDB."""
        try:
            documents = []
            metadatas = []
            ids = []
            
            # Create embeddings for tables and their columns
            for table in schema_info.get("tables", []):
                table_name = table["name"]
                table_description = table.get("description", "")
                
                # Create document for table
                table_doc = f"TABLE: {table_name}\nDescription: {table_description}\n"
                
                # Add column information
                columns_desc = "Columns: "
                for col in table.get("columns", []):
                    columns_desc += f"{col['name']} ({col['type']}), "
                
                table_doc += columns_desc.rstrip(", ")
                
                # Add table-level document
                table_id = f"table_{table_name}"
                documents.append(table_doc)
                metadatas.append({
                    "type": "table",
                    "table_name": table_name,
                    "description": table_description
                })
                ids.append(table_id)
                
                # Create documents for each column
                for col in table.get("columns", []):
                    col_name = col["name"]
                    col_type = col["type"]
                    col_desc = col.get("description", "")
                    
                    col_doc = f"COLUMN: {col_name}\nTable: {table_name}\nType: {col_type}\nDescription: {col_desc}"
                    
                    col_id = f"column_{table_name}_{col_name}"
                    documents.append(col_doc)
                    metadatas.append({
                        "type": "column",
                        "table_name": table_name,
                        "column_name": col_name,
                        "data_type": col_type,
                        "description": col_desc
                    })
                    ids.append(col_id)
            
            # Add documents to ChromaDB
            if documents:
                if self.embeddings:
                    try:
                        embeddings_list = self.embeddings.embed_documents(documents)
                        self.collection.add(
                            documents=documents,
                            embeddings=embeddings_list,
                            metadatas=metadatas,
                            ids=ids
                        )
                    except Exception as e:
                        logger.warning(f"Failed to generate embeddings via OpenAI, adding documents directly: {e}")
                        self.collection.add(
                            documents=documents,
                            metadatas=metadatas,
                            ids=ids
                        )
                else:
                    self.collection.add(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                
                logger.info(f"Created {len(documents)} embeddings in ChromaDB")
            
        except Exception as e:
            logger.error(f"Error creating schema embeddings: {e}")
            raise

    def ingest_schema(self, db_type: str = "snowflake") -> None:
        """Full pipeline: fetch schema and create embeddings."""
        try:
            logger.info(f"Starting schema ingestion for {db_type}...")
            
            # Fetch schema from Snowflake or SQLite
            if db_type == "sqlite":
                schema_info = self.fetch_sqlite_schema()
            else:
                schema_info = self.fetch_snowflake_schema()
            
            # Clear existing collection
            try:
                self.collection.delete(where={})
                logger.info("Cleared existing schema embeddings")
            except Exception as e:
                logger.warning(f"Could not clear existing collection: {e}")
            
            # Create and store embeddings
            self.create_schema_embeddings(schema_info)
            
            logger.info("Schema ingestion completed successfully")
            
        except Exception as e:
            logger.error(f"Schema ingestion failed: {e}")
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the ChromaDB collection."""
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "total_documents": count,
                "embedding_model": self.embedding_model,
                "storage_path": self.chroma_db_path
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            raise


# Standalone functions for easy use
def ingest_schema_from_env(chroma_db_path: str = "./chroma_db") -> SchemaIngestion:
    """Create SchemaIngestion instance from environment variables."""
    from config import SnowflakeConfig, AppConfig
    
    try:
        config = AppConfig.from_env()
        snowflake_config = config.snowflake
    except Exception:
        # Fallback config if Snowflake env vars are missing
        snowflake_config = SnowflakeConfig(
            user="", password="", account="", warehouse="", database="", schema=""
        )
    
    ingestion = SchemaIngestion(
        snowflake_config=snowflake_config,
        chroma_db_path=chroma_db_path
    )
    
    return ingestion


def run_schema_ingestion_cli():
    """CLI command to run schema ingestion."""
    import sys
    
    try:
        chroma_db_path = sys.argv[1] if len(sys.argv) > 1 else "./chroma_db"
        
        ingestion = ingest_schema_from_env(chroma_db_path)
        ingestion.ingest_schema()
        
        stats = ingestion.get_collection_stats()
        print("\n✓ Schema ingestion completed!")
        print(f"Collection: {stats['collection_name']}")
        print(f"Documents: {stats['total_documents']}")
        print(f"Storage: {stats['storage_path']}")
        
    except Exception as e:
        logger.error(f"CLI error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_schema_ingestion_cli()
