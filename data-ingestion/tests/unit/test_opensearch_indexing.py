from unittest.mock import patch, MagicMock
from src.vectorstore.opensearch_client import OpenSearchVectorStore

@patch("src.vectorstore.opensearch_client.OpenSearch")
def test_index_created(mock_os, monkeypatch):
    monkeypatch.setenv("OPENSEARCH_ENDPOINT","https://host")
    monkeypatch.setenv("OPENSEARCH_INDEX","index")

    mock_client = MagicMock()
    mock_client.indices.exists.return_value = False
    mock_os.return_value = mock_client

    store = OpenSearchVectorStore()
    store.create_if_not_exists(10)

    mock_client.indices.create.assert_called_once()

@patch("src.vectorstore.opensearch_client.OpenSearch")
def test_delete_chunks_by_document_returns_deleted_count(mock_os, monkeypatch):
    monkeypatch.setenv("OPENSEARCH_ENDPOINT", "https://host")
    monkeypatch.setenv("OPENSEARCH_INDEX", "index")

    mock_client = MagicMock()
    mock_client.delete_by_query.return_value = {"deleted": 4}
    mock_os.return_value = mock_client

    store = OpenSearchVectorStore()
    deleted = store.delete_chunks_by_document("doc-123")

    assert deleted == 4
    mock_client.delete_by_query.assert_called_once()

@patch("src.vectorstore.opensearch_client.OpenSearch")
def test_index_docs_returns_chunk_ids(mock_os, monkeypatch):
    monkeypatch.setenv("OPENSEARCH_ENDPOINT", "https://host")
    monkeypatch.setenv("OPENSEARCH_INDEX", "index")

    mock_client = MagicMock()
    mock_os.return_value = mock_client

    store = OpenSearchVectorStore()
    chunk_ids = store.index_docs(
        chunks=["one", "two"],
        vectors=[[0.1], [0.2]],
        hashes=["h1", "h2"],
        pii_flags=[False, False],
        pii_detected_list=[[], []],
        meta={"document_id": "doc-1"},
        chunk_metadata_list=[{"chunk_index": 0}, {"chunk_index": 1}],
    )

    assert chunk_ids == ["doc-1-chunk-0", "doc-1-chunk-1"]
    assert mock_client.index.call_count == 2

@patch("src.vectorstore.opensearch_client.logger")
@patch("src.vectorstore.opensearch_client.OpenSearch")
def test_get_document_metadata_returns_none_on_client_exception(mock_os, mock_logger, monkeypatch):
    monkeypatch.setenv("OPENSEARCH_ENDPOINT", "https://host")
    monkeypatch.setenv("OPENSEARCH_INDEX", "index")

    mock_client = MagicMock()
    mock_client.get.side_effect = RuntimeError("temporary failure")
    mock_os.return_value = mock_client

    store = OpenSearchVectorStore()
    metadata = store.get_document_metadata("doc-789")

    assert metadata is None
    mock_logger.warning.assert_called_once()