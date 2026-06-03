from unittest.mock import MagicMock, patch

from src.pipelines.raw_archive import archive_confluence_page_raw


@patch("src.pipelines.raw_archive.boto3.client")
def test_archive_confluence_page_raw_uploads_when_bucket_set(mock_boto3, monkeypatch):
    monkeypatch.setenv("RAW_ARCHIVE_S3_BUCKET", "raw-bucket")
    monkeypatch.setenv("RAW_ARCHIVE_S3_PREFIX", "confluence/raw")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    mock_client = MagicMock()
    mock_boto3.return_value = mock_client

    bucket, key = archive_confluence_page_raw(
        page_id="12345",
        page={"title": "Title", "url": "https://example/wiki/12345", "text": "body"},
        event_context={"latest_event_id": 10},
    )

    assert bucket == "raw-bucket"
    assert key is not None and key.endswith(".json")
    mock_client.put_object.assert_called_once()


def test_archive_confluence_page_raw_skips_when_bucket_missing(monkeypatch):
    monkeypatch.delenv("RAW_ARCHIVE_S3_BUCKET", raising=False)
    bucket, key = archive_confluence_page_raw(
        page_id="12345",
        page={"title": "Title", "url": "https://example/wiki/12345", "text": "body"},
    )
    assert bucket is None
    assert key is None
