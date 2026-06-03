import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from dotenv import load_dotenv

from src.pipelines.confluence_event_store import store_confluence_event
from src.pipelines.confluence_webhook_parser import extract_event_from_payload
from src.utils.logger import get_logger

logger = get_logger(__name__)


def load_env():
    env = os.getenv("ENVIRONMENT", "dev")
    env_file = f"env/.env.{env}"
    if os.path.exists(env_file):
        load_dotenv(env_file)
    else:
        load_dotenv()


def _is_authorized(headers) -> bool:
    expected = os.getenv("CONFLUENCE_WEBHOOK_TOKEN", "")
    if not expected:
        return True

    provided = headers.get("X-Webhook-Token", "")
    if provided == expected:
        return True

    auth_header = headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[len("Bearer "):] == expected

    return False


class ConfluenceWebhookHandler(BaseHTTPRequestHandler):
    def _send_json(self, code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(HTTPStatus.OK, {"status": "ok", "service": "confluence-webhook"})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/webhooks/confluence":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

        if not _is_authorized(self.headers):
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "Unauthorized"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length) if content_length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON payload"})
            return

        try:
            event = extract_event_from_payload(payload)
            inserted = store_confluence_event(
                page_id=event["page_id"],
                event_type=event["event_type"],
                event_ts=event["event_ts"],
                payload=payload,
            )
            self._send_json(
                HTTPStatus.ACCEPTED,
                {
                    "accepted": True,
                    "inserted": inserted,
                    "page_id": event["page_id"],
                    "event_type": event["event_type"],
                },
            )
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            logger.exception(f"Unexpected webhook server error: {exc}")
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Internal server error"})


def run_server(host: str = "0.0.0.0", port: int = 8081):
    load_env()
    server = ThreadingHTTPServer((host, port), ConfluenceWebhookHandler)
    logger.info(f"Confluence webhook server listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    host = os.getenv("CONFLUENCE_WEBHOOK_HOST", "0.0.0.0")
    port = int(os.getenv("CONFLUENCE_WEBHOOK_PORT", "8081"))
    run_server(host=host, port=port)
