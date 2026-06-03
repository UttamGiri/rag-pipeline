# data-ingestion/admin/delete_chunks.py

import typer
import os
from dotenv import load_dotenv
from src.vectorstore.opensearch_client import OpenSearchVectorStore
from src.utils.logger import get_logger

app = typer.Typer(help="Delete all chunks for a specific document from OpenSearch")
logger = get_logger(__name__)

def load_env():
    """Load environment variables from .env file."""
    env = os.getenv("ENVIRONMENT", "dev")
    env_file = f"env/.env.{env}"
    
    if os.path.exists(env_file):
        load_dotenv(env_file)
    else:
        load_dotenv()  # Fallback to default .env if exists

@app.command()
def delete(page_id: str):
    """Delete all chunks for one specific Confluence page ID."""
    
    load_env()
    
    # Reuse existing OpenSearchVectorStore for connection
    os_client = OpenSearchVectorStore()
    index = os_client.index
    
    typer.echo(f"\nDeleting chunks for Confluence page_id={page_id}\n")
    
    if not typer.confirm("Confirm delete?"):
        raise typer.Abort()
    
    query = {
        "query": {
            "term": {"confluence_page_id": page_id}
        }
    }
    
    logger.info(f"Deleting chunks for Confluence page_id={page_id}")
    response = os_client.client.delete_by_query(index=index, body=query)
    deleted = response.get("deleted", 0)
    
    typer.secho(f"\n✓ Deleted {deleted} chunks.\n", fg="green")
    logger.info(f"Successfully deleted {deleted} chunks")

if __name__ == "__main__":
    app()

