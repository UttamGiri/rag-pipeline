from datetime import datetime, timezone


def _safe_get(data: dict, *keys):
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _normalize_event_ts(value: str | None) -> str:
    if value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def extract_event_from_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Webhook payload must be a JSON object")

    page_id = (
        _safe_get(payload, "page", "id")
        or _safe_get(payload, "content", "id")
        or _safe_get(payload, "data", "page", "id")
        or _safe_get(payload, "data", "content", "id")
    )
    if page_id is None:
        raise ValueError("Could not extract page_id from payload")

    event_type = payload.get("webhookEvent") or payload.get("eventType") or "unknown_event"

    event_ts = (
        _safe_get(payload, "timestamp")
        or _safe_get(payload, "eventTimestamp")
        or _safe_get(payload, "data", "timestamp")
    )
    event_ts = _normalize_event_ts(str(event_ts) if event_ts else None)

    return {
        "page_id": str(page_id),
        "event_type": str(event_type),
        "event_ts": event_ts,
    }
