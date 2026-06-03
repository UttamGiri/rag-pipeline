import pytest

from src.pipelines.confluence_webhook_parser import extract_event_from_payload


def test_extract_event_from_payload_page_shape():
    payload = {
        "webhookEvent": "page_updated",
        "timestamp": "2026-06-02T20:10:00Z",
        "page": {"id": 12345},
    }
    event = extract_event_from_payload(payload)
    assert event["page_id"] == "12345"
    assert event["event_type"] == "page_updated"
    assert event["event_ts"] == "2026-06-02T20:10:00Z"


def test_extract_event_from_payload_content_shape():
    payload = {
        "eventType": "content_created",
        "eventTimestamp": "2026-06-02T20:10:00+00:00",
        "content": {"id": "abc-123"},
    }
    event = extract_event_from_payload(payload)
    assert event["page_id"] == "abc-123"
    assert event["event_type"] == "content_created"
    assert event["event_ts"] == "2026-06-02T20:10:00Z"


def test_extract_event_from_payload_raises_when_page_id_missing():
    payload = {"webhookEvent": "page_updated"}
    with pytest.raises(ValueError):
        extract_event_from_payload(payload)
