import json
import os
from datetime import datetime, timezone

import boto3

from src.utils.logger import get_logger

logger = get_logger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_page_id(page_id: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "-" for c in page_id)


def archive_confluence_page_raw(
    page_id: str,
    page: dict,
    event_context: dict | None = None,
) -> tuple[str | None, str | None]:
    """
    Archive raw Confluence page payload to S3 for replay/audit.
    Returns (bucket, key) when enabled, otherwise (None, None).
    """
    bucket = os.getenv("RAW_ARCHIVE_S3_BUCKET", "").strip()
    if not bucket:
        return (None, None)

    prefix = os.getenv("RAW_ARCHIVE_S3_PREFIX", "confluence/raw").strip().strip("/")
    sse = os.getenv("RAW_ARCHIVE_S3_SSE", "AES256").strip()
    now = _utc_now()
    timestamp = now.strftime("%Y%m%dT%H%M%SZ")
    safe_page_id = _safe_page_id(page_id)
    key = f"{prefix}/{now:%Y/%m/%d}/{safe_page_id}/{timestamp}.json"

    payload = {
        "page_id": page_id,
        "archived_at": now.isoformat().replace("+00:00", "Z"),
        "event_context": event_context or {},
        "page": {
            "title": page.get("title", ""),
            "url": page.get("url", ""),
            "text": page.get("text", ""),
        },
    }
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")

    client = boto3.client("s3", region_name=os.getenv("AWS_REGION"))
    put_args = {
        "Bucket": bucket,
        "Key": key,
        "Body": body,
        "ContentType": "application/json",
    }
    if sse:
        put_args["ServerSideEncryption"] = sse

    client.put_object(**put_args)
    logger.info(f"Archived Confluence page raw payload to s3://{bucket}/{key}")
    return (bucket, key)
