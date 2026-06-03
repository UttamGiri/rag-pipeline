import hashlib
import json
import os
import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from src.utils.logger import get_logger

logger = get_logger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_db_path() -> str:
    configured = os.getenv("CONFLUENCE_EVENT_DB_PATH", "data/confluence_events.db")
    return os.path.abspath(configured)


def _ensure_parent_dir(path: str) -> None:
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)


def init_event_store(db_path: str | None = None) -> str:
    path = db_path or _default_db_path()
    _ensure_parent_dir(path)
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS confluence_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_ts TEXT NOT NULL,
                received_at TEXT NOT NULL,
                event_hash TEXT NOT NULL UNIQUE,
                payload_json TEXT,
                dispatched_at TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_confluence_events_pending "
            "ON confluence_events(dispatched_at, received_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_confluence_events_page_id "
            "ON confluence_events(page_id)"
        )
        conn.commit()
    finally:
        conn.close()
    return path


def _normalize_iso(value: str | None) -> str:
    if not value:
        return _utc_now_iso()
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _compute_event_hash(
    page_id: str,
    event_type: str,
    event_ts: str,
    payload: dict | None = None,
) -> str:
    payload_json = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"))
    raw = f"{page_id}|{event_type}|{event_ts}|{payload_json}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def store_confluence_event(
    page_id: str,
    event_type: str,
    event_ts: str | None = None,
    payload: dict | None = None,
    db_path: str | None = None,
) -> bool:
    if not page_id:
        raise ValueError("page_id is required")
    if not event_type:
        raise ValueError("event_type is required")

    path = init_event_store(db_path)
    normalized_event_ts = _normalize_iso(event_ts)
    received_at = _utc_now_iso()
    event_hash = _compute_event_hash(page_id, event_type, normalized_event_ts, payload)
    payload_json = json.dumps(payload) if payload is not None else None

    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            INSERT INTO confluence_events
            (page_id, event_type, event_ts, received_at, event_hash, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (page_id, event_type, normalized_event_ts, received_at, event_hash, payload_json),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        logger.info(
            f"Duplicate event ignored for page_id={page_id} event_hash={event_hash[:8]}..."
        )
        return False
    finally:
        conn.close()


def list_dispatchable_pages(
    interval_minutes: int = 15,
    max_pages: int = 200,
    db_path: str | None = None,
    now_iso: str | None = None,
) -> list[dict]:
    path = init_event_store(db_path)
    now_dt = datetime.fromisoformat((now_iso or _utc_now_iso()).replace("Z", "+00:00"))
    cutoff = (now_dt - timedelta(minutes=interval_minutes)).isoformat().replace("+00:00", "Z")

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                page_id,
                MAX(id) AS max_event_id,
                MAX(event_ts) AS latest_event_ts,
                COUNT(*) AS pending_event_count
            FROM confluence_events
            WHERE dispatched_at IS NULL
              AND received_at <= ?
            GROUP BY page_id
            ORDER BY latest_event_ts ASC
            LIMIT ?
            """,
            (cutoff, max_pages),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def mark_page_events_dispatched(
    page_id: str,
    max_event_id: int,
    db_path: str | None = None,
    dispatched_at: str | None = None,
) -> int:
    path = init_event_store(db_path)
    dispatched_at_iso = _normalize_iso(dispatched_at)
    conn = sqlite3.connect(path)
    try:
        cursor = conn.execute(
            """
            UPDATE confluence_events
            SET dispatched_at = ?
            WHERE page_id = ?
              AND dispatched_at IS NULL
              AND id <= ?
            """,
            (dispatched_at_iso, page_id, max_event_id),
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def dispatch_pending_events(
    process_page: Callable[[str, dict], None],
    interval_minutes: int = 15,
    max_pages: int = 200,
    db_path: str | None = None,
) -> dict:
    pages = list_dispatchable_pages(
        interval_minutes=interval_minutes,
        max_pages=max_pages,
        db_path=db_path,
    )

    processed = 0
    failed_pages = []
    dispatched_events = 0

    for page in pages:
        page_id = page["page_id"]
        max_event_id = int(page["max_event_id"])
        event_context = {
            "latest_event_id": max_event_id,
            "latest_event_ts": page.get("latest_event_ts"),
            "pending_event_count": int(page.get("pending_event_count", 0)),
        }
        try:
            process_page(page_id, event_context)
            marked = mark_page_events_dispatched(
                page_id=page_id,
                max_event_id=max_event_id,
                db_path=db_path,
            )
            dispatched_events += marked
            processed += 1
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Failed to process page_id={page_id}: {exc}")
            failed_pages.append(page_id)

    return {
        "dispatchable_pages": len(pages),
        "processed_pages": processed,
        "failed_pages": failed_pages,
        "dispatched_event_rows": dispatched_events,
    }
