import os
from datetime import datetime
from dotenv import load_dotenv
from src.loaders.confluence_loader import read_confluence_page
from src.chunking.semantic_chunker import semantic_split
from src.pii.pii_presidio import PiiPresidioService
from src.hashing.hash_utils import sha256_hash
from src.embeddings.cohere_bedrock_embeddings import CohereBedrockEmbedder
from src.vectorstore.opensearch_client import OpenSearchVectorStore
from src.pipelines.incremental_utils import should_reindex
from src.pipelines.raw_archive import archive_confluence_page_raw
from src.utils.logger import get_logger

logger = get_logger(__name__)

def _parse_list_env(env_var: str, default=None):
    """Parse comma-separated environment variable into list."""
    value = os.getenv(env_var, "")
    if not value:
        return default or []
    return [item.strip() for item in value.split(",") if item.strip()]

def _build_metadata():
    """Build comprehensive metadata from environment variables."""
    # Mandatory fields
    document_id = os.getenv("DOCUMENT_ID")
    if not document_id:
        page_id = os.getenv("CONFLUENCE_PAGE_ID", "")
        document_id = f"confluence-{page_id}" if page_id else "unknown-doc"
    
    department = os.getenv("DEPARTMENT", "")
    if not department:
        raise ValueError("DEPARTMENT environment variable is required")
    
    roles_allowed = _parse_list_env("ROLES_ALLOWED", [])
    if not roles_allowed:
        raise ValueError("ROLES_ALLOWED environment variable is required (comma-separated)")
    
    # Build metadata dictionary
    meta = {
        # Document metadata (mandatory)
        "document_id": document_id,
        "confluence_page_id": os.getenv("CONFLUENCE_PAGE_ID"),
        "doc_type": os.getenv("DOC_TYPE", "confluence_page"),
        
        # Organizational metadata (mandatory)
        "department": department,
        "division": os.getenv("DIVISION", ""),
        "team": os.getenv("TEAM", ""),
        "roles_allowed": roles_allowed,
        
        # Compliance & audit metadata
        "ingestion_date": datetime.utcnow().isoformat() + "Z",
        "ingested_by": os.getenv("INGESTED_BY", os.getenv("USER", "unknown")),
        "embedding_model": os.getenv("BEDROCK_COHERE_MODEL", "cohere.embed-english-v2"),
        "embedding_model_version": os.getenv("EMBEDDING_MODEL_VERSION", "2.0"),
        "chunker_version": os.getenv("CHUNKER_VERSION", "semantic-1.0"),
        
        # Optional metadata
        "title": os.getenv("DOCUMENT_TITLE", ""),
        "version": os.getenv("DOCUMENT_VERSION", ""),
        "tags": _parse_list_env("TAGS", []),
        "classification": os.getenv("CLASSIFICATION", ""),
        "security_level": os.getenv("SECURITY_LEVEL", ""),
        "owner": os.getenv("OWNER", ""),
        "data_domain": os.getenv("DATA_DOMAIN", ""),
        "source_url": os.getenv("SOURCE_URL", ""),
    }
    
    # Remove empty optional fields
    meta = {k: v for k, v in meta.items() if v or k in [
        "document_id", "confluence_page_id", "department", "roles_allowed",
        "ingestion_date", "ingested_by", "embedding_model"
    ]}
    
    return meta


def ingest_page(page_id: str, event_context: dict | None = None):
    logger.info(f"Starting ingestion for Confluence page_id={page_id}")
    page = read_confluence_page(page_id)
    s3_bucket, s3_key = archive_confluence_page_raw(
        page_id=page_id,
        page=page,
        event_context=event_context,
    )
    text = page["text"]
    document_hash = sha256_hash(text)

    # semantic chunking
    chunks = semantic_split(text)
    logger.info(f"Split document into {len(chunks)} chunks")

    # PII Redaction
    pii = PiiPresidioService()
    redacted = []
    pii_flags = []
    pii_detected_list = []
    hashes = []

    for ch in chunks:
        r, flag, detected = pii.redact(ch)
        redacted.append(r)
        pii_flags.append(flag)
        pii_detected_list.append(detected)
        hashes.append(sha256_hash(ch))

    # embeddings
    embedder = CohereBedrockEmbedder()
    vectors = embedder.embed(redacted)
    dim = len(vectors[0])
    logger.info(f"Generated embeddings with dimension {dim}")

    # Build metadata
    meta = _build_metadata()
    meta["confluence_page_id"] = page_id
    meta["title"] = meta.get("title") or page.get("title", "")
    meta["source_url"] = meta.get("source_url") or page.get("url", "")
    meta["document_hash"] = document_hash
    if s3_bucket and s3_key:
        meta["s3_bucket"] = s3_bucket
        meta["s3_key"] = s3_key

    # Create chunk metadata (chunk_index for each chunk)
    chunk_metadata_list = [
        {"chunk_index": idx}
        for idx in range(len(chunks))
    ]

    # index
    os_client = OpenSearchVectorStore()
    os_client.create_if_not_exists(dim)
    os_client.create_metadata_index_if_not_exists()

    existing_doc_meta = os_client.get_document_metadata(meta["document_id"])
    if not should_reindex(existing_doc_meta, document_hash):
        logger.info(
            f"No change detected for document {meta['document_id']}. "
            "Skipping delete and re-index."
        )
        return

    if existing_doc_meta:
        deleted = os_client.delete_chunks_by_document(meta["document_id"])
        logger.info(
            f"Document hash changed for {meta['document_id']}. "
            f"Deleted {deleted} old chunks before re-index."
        )

    chunk_ids = os_client.index_docs(
        chunks=redacted,
        vectors=vectors,
        hashes=hashes,
        pii_flags=pii_flags,
        pii_detected_list=pii_detected_list,
        meta=meta,
        chunk_metadata_list=chunk_metadata_list
    )

    doc_metadata = {
        "document_id": meta["document_id"],
        "document_hash": document_hash,
        "confluence_page_id": meta.get("confluence_page_id"),
        "source_url": meta.get("source_url"),
        "s3_bucket": meta.get("s3_bucket"),
        "s3_key": meta.get("s3_key"),
        "chunk_ids": chunk_ids,
        "chunk_hashes": hashes,
        "chunk_count": len(chunk_ids),
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "embedding_model": meta.get("embedding_model"),
        "chunker_version": meta.get("chunker_version"),
    }
    os_client.upsert_document_metadata(meta["document_id"], doc_metadata)

    logger.info(
        f"Ingestion complete. Indexed {len(chunks)} chunks for document {meta.get('document_id')}"
    )

def run_pipeline():
    # Load environment variables
    env = os.getenv("ENVIRONMENT", "dev")
    env_file = f"env/.env.{env}"
    if os.path.exists(env_file):
        load_dotenv(env_file)
    else:
        load_dotenv()  # Fallback to default .env if exists
    
    page_id = os.getenv("CONFLUENCE_PAGE_ID")
    
    if not page_id:
        raise ValueError("CONFLUENCE_PAGE_ID must be set")

    ingest_page(page_id)

if __name__ == "__main__":
    run_pipeline()

