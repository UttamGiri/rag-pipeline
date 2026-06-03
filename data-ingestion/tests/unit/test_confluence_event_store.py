from datetime import datetime, timedelta, timezone

from src.pipelines.confluence_event_store import (
    dispatch_pending_events,
    list_dispatchable_pages,
    mark_page_events_dispatched,
    store_confluence_event,
)


def _iso(minutes_ago: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return dt.isoformat().replace("+00:00", "Z")


def test_store_confluence_event_deduplicates_exact_retries(tmp_path):
    db_path = str(tmp_path / "events.db")
    inserted = store_confluence_event(
        page_id="123",
        event_type="page_updated",
        event_ts="2026-06-02T20:00:00Z",
        payload={"foo": "bar"},
        db_path=db_path,
    )
    duplicate = store_confluence_event(
        page_id="123",
        event_type="page_updated",
        event_ts="2026-06-02T20:00:00Z",
        payload={"foo": "bar"},
        db_path=db_path,
    )
    assert inserted is True
    assert duplicate is False


def test_list_dispatchable_pages_coalesces_by_page(tmp_path):
    db_path = str(tmp_path / "events.db")
    # Two events for same page, one for a second page.
    store_confluence_event("111", "page_updated", event_ts=_iso(30), db_path=db_path)
    store_confluence_event("111", "page_updated", event_ts=_iso(25), db_path=db_path)
    store_confluence_event("222", "page_updated", event_ts=_iso(30), db_path=db_path)

    dispatchable = list_dispatchable_pages(
        interval_minutes=0,
        max_pages=10,
        db_path=db_path,
    )

    pages = sorted([row["page_id"] for row in dispatchable])
    assert pages == ["111", "222"]
    counts = {row["page_id"]: row["pending_event_count"] for row in dispatchable}
    assert counts["111"] == 2
    assert counts["222"] == 1


def test_dispatch_pending_events_marks_rows_and_processes_once_per_page(tmp_path):
    db_path = str(tmp_path / "events.db")
    store_confluence_event("111", "page_updated", event_ts=_iso(30), db_path=db_path)
    store_confluence_event("111", "page_updated", event_ts=_iso(20), db_path=db_path)
    store_confluence_event("222", "page_updated", event_ts=_iso(30), db_path=db_path)

    processed_pages = []

    def _process(page_id: str, event_context: dict):
        processed_pages.append(page_id)
        assert "latest_event_id" in event_context
        assert "latest_event_ts" in event_context
        assert "pending_event_count" in event_context

    result = dispatch_pending_events(
        process_page=_process,
        interval_minutes=0,
        max_pages=10,
        db_path=db_path,
    )

    assert sorted(processed_pages) == ["111", "222"]
    assert result["processed_pages"] == 2
    assert result["failed_pages"] == []
    assert result["dispatched_event_rows"] == 3


def test_mark_page_events_dispatched_marks_up_to_max_event_id(tmp_path):
    db_path = str(tmp_path / "events.db")
    store_confluence_event("111", "page_updated", event_ts=_iso(30), db_path=db_path)
    store_confluence_event("111", "page_updated", event_ts=_iso(20), db_path=db_path)
    rows = list_dispatchable_pages(interval_minutes=0, db_path=db_path)
    row = next(r for r in rows if r["page_id"] == "111")

    marked = mark_page_events_dispatched(
        page_id="111",
        max_event_id=int(row["max_event_id"]),
        db_path=db_path,
    )
    assert marked == 2
