"""Schema retriever module for RAG-based schema lookup."""

import logging
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings
from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)


class SchemaRetriever:
    """Retrieve relevant schema information from ChromaDB based on user queries."""

    def __init__(
        self,
        embedding_model: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
        chroma_db_path: str = "./chroma_db",
        collection_name: str = "snowflake_schema",
        top_k: int = 5
    ):
        """Initialize schema retriever.
        
        Args:
            embedding_model: OpenAI embedding model
            api_key: OpenAI API key (optional, uses env var if not provided)
            chroma_db_path: Path to ChromaDB storage
            collection_name: Name of ChromaDB collection
            top_k: Number of top results to retrieve
        """
        self.embedding_model = embedding_model
        self.api_key = api_key
        self.chroma_db_path = chroma_db_path
        self.collection_name = collection_name
        self.top_k = top_k
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            model=embedding_model,
            api_key=api_key
        )
        
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=False
            )
        )
        
        # Get collection
        self.collection = self.chroma_client.get_collection(
            name=collection_name
        )

    def retrieve_relevant_schema(
        self,
        query: str,
        top_k: Optional[int] = None,
        include_all_columns: bool = True
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Retrieve relevant schema information based on query.
        
        Args:
            query: Natural language query from user
            top_k: Number of results to retrieve (uses instance top_k if None)
            include_all_columns: If True, include all columns for retrieved tables
            
        Returns:
            Tuple of:
                - Formatted schema context string for LLM
                - List of matching documents with metadata
        """
        try:
            k = top_k or self.top_k
            
            # Query ChromaDB for relevant documents
            results = self.collection.query(
                query_texts=[query],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )
            
            logger.info(f"Retrieved {len(results['documents'][0])} documents for query: {query}")
            
            # Parse results and group by table
            retrieved_tables = {}
            retrieved_columns = {}
            raw_results = []
            
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                
                raw_result = {
                    "document": doc,
                    "metadata": metadata,
                    "distance": distance
                }
                raw_results.append(raw_result)
                
                if metadata["type"] == "table":
                    table_name = metadata["table_name"]
                    retrieved_tables[table_name] = metadata
                
                elif metadata["type"] == "column":
                    table_name = metadata["table_name"]
                    column_name = metadata["column_name"]
                    
                    if table_name not in retrieved_columns:
                        retrieved_columns[table_name] = []
                    
                    retrieved_columns[table_name].append(metadata)
            
            # Build schema context for LLM
            schema_context = self._build_schema_context(
                retrieved_tables,
                retrieved_columns,
                include_all_columns
            )
            
            return schema_context, raw_results
            
        except Exception as e:
            logger.error(f"Error retrieving schema: {e}")
            # Return empty schema context on error
            return "", []

    def _build_schema_context(
        self,
        retrieved_tables: Dict[str, Any],
        retrieved_columns: Dict[str, List[Any]],
        include_all_columns: bool = True
    ) -> str:
        """Build formatted schema context string for LLM.
        
        Args:
            retrieved_tables: Dictionary of table metadata
            retrieved_columns: Dictionary mapping tables to column metadata
            include_all_columns: If True, include all columns; if False, only retrieved ones
            
        Returns:
            Formatted schema context string
        """
        schema_text = "RELEVANT SCHEMA:\n\n"
        
        for table_name in sorted(retrieved_tables.keys()):
            table_meta = retrieved_tables[table_name]
            schema_text += f"Table: {table_name}\n"
            schema_text += f"Description: {table_meta.get('description', 'N/A')}\n"
            schema_text += "Columns:\n"
            
            # Add columns
            if include_all_columns and table_name in retrieved_columns:
                for col_meta in retrieved_columns[table_name]:
                    col_name = col_meta.get("column_name", "")
                    col_type = col_meta.get("data_type", "")
                    col_desc = col_meta.get("description", "")
                    schema_text += f"  - {col_name} ({col_type}): {col_desc}\n"
            
            schema_text += "\n"
        
        return schema_text

    def format_schema_for_prompt(
        self,
        query: str,
        top_k: Optional[int] = None
    ) -> str:
        """Format retrieved schema as a prompt fragment.
        
        Args:
            query: User query
            top_k: Number of results to retrieve
            
        Returns:
            Formatted schema prompt fragment
        """
        schema_context, _ = self.retrieve_relevant_schema(query, top_k)
        
        if not schema_context:
            return "No relevant schema found."
        
        return schema_context

    def get_all_tables(self) -> List[str]:
        """Get list of all available tables.
        
        Returns:
            List of table names
        """
        try:
            results = self.collection.get(
                where={"type": "table"}
            )
            
            table_names = []
            for meta in results["metadatas"]:
                if meta["type"] == "table":
                    table_names.append(meta["table_name"])
            
            return sorted(list(set(table_names)))
        
        except Exception as e:
            logger.error(f"Error getting all tables: {e}")
            return []

    def get_table_columns(self, table_name: str) -> Dict[str, str]:
        """Get all columns for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary mapping column names to their types
        """
        try:
            results = self.collection.get(
                where={"table_name": table_name, "type": "column"}
            )
            
            columns = {}
            for meta in results["metadatas"]:
                col_name = meta.get("column_name", "")
                col_type = meta.get("data_type", "")
                columns[col_name] = col_type
            
            return columns
        
        except Exception as e:
            logger.error(f"Error getting columns for {table_name}: {e}")
            return {}

    def test_retriever(self) -> None:
        """Test retriever with sample queries."""
        test_queries = [
            "Show all movies",
            "Find TV shows from 2020",
            "Count by genre",
            "Movies directed by someone",
            "Cast members",
        ]
        
        print("\n🧪 Testing Schema Retriever\n")
        print("=" * 80)
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            print("-" * 80)
            
            schema_context, raw_results = self.retrieve_relevant_schema(query, top_k=3)
            
            print(f"Retrieved {len(raw_results)} documents:")
            for result in raw_results:
                meta = result["metadata"]
                distance = result["distance"]
                print(f"  - Type: {meta.get('type')}, Distance: {distance:.4f}")
                if meta.get("type") == "table":
                    print(f"    Table: {meta.get('table_name')}")
                elif meta.get("type") == "column":
                    print(f"    Column: {meta.get('column_name')} ({meta.get('data_type')})")
            
            print("\nSchema Context for LLM:")
            print(schema_context[:300] + "..." if len(schema_context) > 300 else schema_context)


def create_retriever_from_env(
    chroma_db_path: str = "./chroma_db",
    top_k: int = 5
) -> SchemaRetriever:
    """Create SchemaRetriever instance from environment variables.
    
    Args:
        chroma_db_path: Path to ChromaDB storage
        top_k: Number of top results to retrieve
        
    Returns:
        SchemaRetriever instance
    """
    retriever = SchemaRetriever(
        chroma_db_path=chroma_db_path,
        top_k=top_k
    )
    
    return retriever


def run_test_cli():
    """CLI command to test schema retriever."""
    import sys
    
    try:
        chroma_db_path = sys.argv[1] if len(sys.argv) > 1 else "./chroma_db"
        
        retriever = create_retriever_from_env(chroma_db_path)
        
        # Print available tables
        tables = retriever.get_all_tables()
        print(f"\n📋 Available Tables: {len(tables)}")
        for table in tables:
            columns = retriever.get_table_columns(table)
            print(f"  - {table}: {len(columns)} columns")
        
        # Run test queries
        retriever.test_retriever()
        
    except Exception as e:
        logger.error(f"CLI error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_test_cli()
