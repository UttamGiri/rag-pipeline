# Metadata Schema Documentation

This document describes the rich metadata fields used in the RAG pipeline for enterprise/federal deployments.

## Mandatory Fields

These fields **must** be provided via environment variables:

| Field | Environment Variable | Description | Example |
|-------|---------------------|-------------|---------|
| `document_id` | `DOCUMENT_ID` | Unique identifier for the document | `policy-manual-v2` |
| `department` | `DEPARTMENT` | Organizational department | `Engineering`, `Finance`, `HR` |
| `roles_allowed` | `ROLES_ALLOWED` | Comma-separated list of allowed roles | `developer,manager,analyst` |
| `confluence_page_id` | `CONFLUENCE_PAGE_ID` | Confluence page ID | `123456789` |

**Note**: If `DOCUMENT_ID` is not provided, it will be auto-generated from the Confluence page ID.

## Recommended Fields

These fields are strongly recommended for better filtering and access control:

| Field | Environment Variable | Description | Example |
|-------|---------------------|-------------|---------|
| `division` | `DIVISION` | Sub-unit within department | `Platform`, `Infrastructure`, `Product` |
| `team` | `TEAM` | Specific team | `DevOps`, `Security`, `API Team` |
| `doc_type` | `DOC_TYPE` | Document type | `confluence_page`, `policy`, `SOP`, `manual` |
| `tags` | `TAGS` | Comma-separated tags | `onboarding,api,authentication` |

## Optional Fields

These fields enhance search, compliance, and audit capabilities:

| Field | Environment Variable | Description | Example |
|-------|---------------------|-------------|---------|
| `title` | `DOCUMENT_TITLE` | Human-readable document title | `Employee Handbook` |
| `version` | `DOCUMENT_VERSION` | Document version | `v2`, `2024-01-15` |
| `classification` | `CLASSIFICATION` | Document classification | `internal`, `public`, `confidential` |
| `security_level` | `SECURITY_LEVEL` | Security level | `low`, `medium`, `high` |
| `owner` | `OWNER` | Document owner | `john.doe@company.com` |
| `data_domain` | `DATA_DOMAIN` | Data domain | `HR`, `Finance`, `Engineering`, `API` |
| `source_url` | `SOURCE_URL` | Original source location | `https://your-org.atlassian.net/wiki/spaces/ENG/pages/123456789` |

## Auto-Generated Fields

These fields are automatically populated by the pipeline:

| Field | Description | Format |
|-------|-------------|--------|
| `chunk_id` | Unique identifier for each chunk | `{document_id}-chunk-{index}` |
| `chunk_index` | Sequential index of chunk in document | Integer (0-based) |
| `content_hash` | SHA-256 hash of original chunk text | 64-character hex string |
| `has_pii` | Boolean indicating PII presence | `true` or `false` |
| `pii_detected` | List of detected PII entity types | Array of strings |
| `ingestion_date` | Timestamp of ingestion | ISO 8601 with Z |
| `ingested_by` | User/system that performed ingestion | String (defaults to `USER` env var) |
| `embedding_model` | Embedding model used | From `BEDROCK_COHERE_MODEL` |
| `embedding_model_version` | Version of embedding model | From `EMBEDDING_MODEL_VERSION` |
| `chunker_version` | Version of chunker | From `CHUNKER_VERSION` |

## Example Environment Configuration

```bash
# Mandatory
export DEPARTMENT="Engineering"
export ROLES_ALLOWED="developer,manager,analyst"
export CONFLUENCE_PAGE_ID="123456789"
export DOCUMENT_ID="employee-handbook-v2"

# Confluence API
export CONFLUENCE_BASE_URL="https://your-org.atlassian.net"
export CONFLUENCE_EMAIL="service-account@your-org.com"
export CONFLUENCE_API_TOKEN="your-atlassian-api-token"

# Recommended
export DIVISION="Platform"
export TEAM="API Engineering"
export DOC_TYPE="policy"
export TAGS="onboarding,api,authentication"

# Optional
export DOCUMENT_TITLE="Employee Handbook"
export DOCUMENT_VERSION="v2"
export CLASSIFICATION="internal"
export SECURITY_LEVEL="medium"
export OWNER="john.doe@company.com"
export DATA_DOMAIN="HR"
```

## Access Control

The `roles_allowed` field enables Role-Based Access Control (RBAC). The RAG API can filter documents based on user roles:

- Users with role `developer` can access documents where `developer` is in `roles_allowed`
- Users with role `manager` can access documents where `manager` is in `roles_allowed`
- Department-based filtering can be done using the `department` field

## Benefits

1. **Improved Filtering**: Filter by department, division, team, tags
2. **Access Control**: Enforce RBAC/ABAC using `roles_allowed` and `department`
3. **Audit & Compliance**: Track ingestion dates, users, and PII detection
4. **Better Retrieval**: Use metadata for ranking and filtering search results
5. **Multi-tenant Support**: Isolate data by department/division
6. **Version Control**: Track document versions and review dates

