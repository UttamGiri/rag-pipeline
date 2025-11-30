# RAG Pipeline

A production-ready Retrieval-Augmented Generation (RAG) pipeline for enterprise document processing and intelligent query answering. This system processes PDF documents, extracts and indexes content with PII/PHI redaction, and provides a secure API for semantic search and question answering.

## Requirements & Objectives

### Business Requirements

- **Secure Document Processing**: Handle sensitive documents with automatic PII/PHI detection and redaction
- **Semantic Search**: Enable natural language queries over large document collections
- **Enterprise-Grade Security**: Meet federal and banking industry standards for data protection
- **Scalable Architecture**: Support high-volume document ingestion and query processing
- **Observability**: Full traceability and monitoring for compliance and debugging
- **Multi-Environment Support**: Separate configurations for dev, staging, and production

### Technical Objectives

- **Modular Design**: Independent, testable microservices
- **Cloud-Native**: Built for AWS (S3, Bedrock, OpenSearch)
- **Production-Ready**: Comprehensive testing, error handling, and logging
- **Compliance**: PII/PHI redaction using Microsoft Presidio
- **Performance**: Sub-2-second P95 latency for queries
- **Reliability**: Robust error handling and graceful degradation

## Solution Overview

The RAG pipeline consists of three main components:

1. **Data Ingestion Service**: Processes PDFs from S3, extracts text, chunks semantically, redacts PII/PHI, generates embeddings, and indexes into OpenSearch
2. **RAG API Service**: FastAPI service that accepts queries, retrieves relevant documents, and generates answers using Claude via Bedrock
3. **Integration Tests**: Comprehensive end-to-end test suite validating the entire pipeline

### Architecture Flow

```
PDF (S3) 
  → Data Ingestion Service
    → Text Extraction (PyPDF)
    → Semantic Chunking (LangChain + Cohere)
    → PII/PHI Redaction (Presidio)
    → Embedding Generation (Cohere Bedrock)
    → Vector Indexing (OpenSearch)
  → RAG API Service
    → Query Embedding (Cohere Bedrock)
    → Vector Retrieval (OpenSearch)
    → Answer Generation (Claude Bedrock)
  → Response with Sources
```

## Components

### 1. Data Ingestion Service (`data-ingestion/`)

**Purpose**: Process and index documents for retrieval

**Key Features**:
- Downloads PDFs from Amazon S3
- Extracts text using PyPDF
- Performs semantic chunking using LangChain with Cohere Bedrock embeddings
- Redacts PII/PHI using Microsoft Presidio (50+ entity types supported)
- Hashes raw text using SHA-256 for deduplication
- Generates embeddings using Cohere `embed-english-v2` via Bedrock
- Indexes redacted chunks and vectors into OpenSearch with KNN support
- Rich metadata support for enterprise/federal deployments (RBAC, ABAC, compliance)

**Technology Stack**:
- Python 3.11
- LangChain (semantic chunking)
- Microsoft Presidio (PII/PHI detection)
- Cohere Bedrock (embeddings)
- OpenSearch (vector store)
- PyPDF (PDF extraction)

**Configuration**:
- Environment-aware: `env/.env.dev`, `env/.env.staging`, `env/.env.prod`
- Configurable chunk sizes and breakpoint thresholds
- Docker-based deployment
- Rich metadata fields for access control and compliance

**Admin Tools** (`data-ingestion/admin/`):
- `delete_chunks.py` - Delete chunks for a specific document
- `reingest_document.py` - Delete and re-ingest a document
- Supports in-place updates for production indexes
- See [`data-ingestion/admin/README.md`](data-ingestion/admin/README.md) for details

**Testing**:
- Unit tests for all components
- Integration tests for end-to-end pipeline

**Documentation**: 
- See [`data-ingestion/README.md`](data-ingestion/README.md)
- See [`data-ingestion/METADATA.md`](data-ingestion/METADATA.md) for metadata schema
- See [`data-ingestion/admin/README.md`](data-ingestion/admin/README.md) for admin tools

---

### 2. RAG API Service (`rag-api/`)

**Purpose**: Provide REST API for querying indexed documents

**Key Features**:
- FastAPI-based REST API
- Query embedding using Cohere `embed-english-v3` via Bedrock
- Vector similarity search in OpenSearch
- Answer generation using Anthropic Claude via Bedrock
- Returns answers with source metadata and confidence scores
- Health check endpoint
- Environment-aware configuration

**API Endpoints**:
- `POST /query` - Submit natural language queries
- `GET /health` - Service health check

**Technology Stack**:
- FastAPI (REST API framework)
- Cohere Bedrock (query embeddings)
- Anthropic Claude Bedrock (LLM)
- OpenSearch (vector retrieval)
- Pydantic (data validation)

**LLM Configuration**:
- Temperature: 0.1 (factual, deterministic)
- Claude 3 Haiku/Sonnet/Opus support
- System prompts optimized for RAG
- Context-aware answer generation

**Testing**:
- Unit tests with mocks for all components
- TestClient for API endpoint testing

**Documentation**: See [`rag-api/README.md`](rag-api/README.md)

---

### 3. Integration Tests (`rag-integration-test/`)

**Purpose**: End-to-end validation of the complete RAG pipeline

**Test Coverage**:
- **Data Ingestion Pipeline**: Full flow validation
- **Chunking Quality**: Semantic chunking accuracy
- **PII Redaction**: Security and privacy validation
- **Retrieval Accuracy**: Vector search quality with golden Q&A pairs
- **RAG Query Functional**: End-to-end query functionality
- **LLM Safety**: Jailbreak defense and bias testing
- **Performance**: P95 latency under 2 seconds
- **Observability**: Trace propagation and monitoring
- **Security Controls**: Input validation, rate limiting, content leakage prevention

**Running Tests**:
- **Option 1 (Recommended)**: Run locally against deployed staging environment
- **Option 2**: Run via CI/CD pipeline
- **Option 3**: Run in container/remote environment

**Technology Stack**:
- pytest (test framework)
- requests (HTTP client)
- Parametrized tests for multiple scenarios

**Documentation**: See [`rag-integration-test/README.md`](rag-integration-test/README.md)

---

## Quick Start

### Prerequisites

- Python 3.11+
- AWS credentials configured
- OpenSearch cluster accessible
- Docker (optional, for containerized deployment)

### Setup

1. **Data Ingestion Service**:
   ```bash
   cd data-ingestion
   pip install -r requirements.txt
   export ENVIRONMENT=dev
   python -m src.pipelines.ingestion_pipeline
   ```

2. **RAG API Service**:
   ```bash
   cd rag-api
   pip install -r requirements.txt
   export ENVIRONMENT=dev
   uvicorn src.api.fastapi_app:app --reload
   ```

3. **Integration Tests**:
   ```bash
   cd rag-integration-test
   export RAG_BASE_URL="https://rag-staging.myagency.gov"
   pytest -m integration -vv
   ```

## Project Structure

```
rag-pipeline/
├── data-ingestion/          # Document processing and indexing service
│   ├── src/                # Source code
│   ├── admin/              # Admin tools for document updates
│   │   ├── delete_chunks.py
│   │   ├── reingest_document.py
│   │   └── README.md
│   ├── tests/              # Unit and integration tests
│   ├── env/                # Environment configurations
│   ├── METADATA.md         # Metadata schema documentation
│   └── Dockerfile          # Container definition
├── rag-api/                # Query API service
│   ├── src/                # Source code
│   ├── tests/              # Unit tests
│   ├── env/                # Environment configurations
│   └── Dockerfile          # Container definition
└── rag-integration-test/   # End-to-end integration tests
    ├── test_*.py          # Integration test files
    └── conftest.py        # Test fixtures
```





## Production Index Management

### In-Place Updates (Small Changes)

For normal day-to-day operations:
- **New PDFs** coming in
- **A few PDFs** updated
- **Background ingestion**
- **Incremental changes**

**Approach**: Write directly into the live production index (`prod_v1`)

- OpenSearch is built for continuous indexing + searching
- **No downtime** when adding/updating docs
- Users keep searching normally during updates
- Brief 1-2 second window where updated doc might not show up (acceptable)

**Use admin scripts** (`data-ingestion/admin/`) for single document updates:
```bash
python admin/reingest_document.py reingest --bucket mybucket --key path/doc.pdf
```

### Blue-Green Index (Large Changes)

For breaking changes or full rebuilds:
- **New embedding model** (dimension changes)
- **Index mapping changes**
- **Major chunking redesign**
- **Full corpus rebuild**

**Approach**: Create new index (`prod_v2`) with alias switching

1. Create `prod_v2` alongside `prod_v1`
2. Ingest all data into `prod_v2` in background
3. Test against `prod_v2`
4. Atomically flip alias (`rag_current`) from `prod_v1` → `prod_v2`
5. Users never see half-baked results

**Decision Matrix**:

| Scenario | Approach | Index | Downtime |
|----------|----------|-------|----------|
| Update 1-10 PDFs | In-place | `prod_v1` | None |
| New PDFs (incremental) | In-place | `prod_v1` | None |
| Change embedding model | Blue-green | `prod_v2` + alias | None |
| Change index mapping | Blue-green | `prod_v2` + alias | None |
| Full corpus rebuild | Blue-green | `prod_v2` + alias | None |

See [`data-ingestion/admin/README.md`](data-ingestion/admin/README.md) for detailed production index management guidance.

## Security & Compliance

- **PII/PHI Redaction**: Microsoft Presidio with 50+ entity types
- **Content Hashing**: SHA-256 for deduplication and audit trails
- **Secure Configuration**: Environment-based secrets management
- **Input Validation**: Comprehensive API input validation
- **Rate Limiting**: Protection against abuse
- **HTTPS Only**: Enforced secure connections

## Performance

- **Ingestion**: Configurable chunk sizes (200-2500 characters)
- **Query Latency**: P95 under 2 seconds
- **Retrieval**: Top-k similarity search with configurable k
- **Embedding**: Cohere Bedrock for high-quality vectors

## Monitoring & Observability

- Structured logging with configurable levels
- Trace ID propagation for distributed tracing
- Health check endpoints
- Performance metrics collection

## License

MIT License
