import json
import os

import typer
from dotenv import load_dotenv

from src.pipelines.confluence_event_store import (
    dispatch_pending_events,
    store_confluence_event,
)
from src.pipelines.ingestion_pipeline import ingest_page

app = typer.Typer(help="Confluence event store + 15-minute dispatch workflow.")


def load_env():
    env = os.getenv("ENVIRONMENT", "dev")
    env_file = f"env/.env.{env}"
    if os.path.exists(env_file):
        load_dotenv(env_file)
    else:
        load_dotenv()


@app.command("add")
def add_event(
    page_id: str = typer.Option(..., help="Confluence page ID"),
    event_type: str = typer.Option("page_updated", help="Confluence event type"),
    event_ts: str = typer.Option("", help="Event timestamp (ISO-8601, UTC preferred)"),
    payload_json: str = typer.Option(
        "", help="Optional raw payload JSON string to persist for audit/replay"
    ),
):
    """Persist one Confluence event into local event store."""
    load_env()
    payload = json.loads(payload_json) if payload_json else None
    inserted = store_confluence_event(
        page_id=page_id,
        event_type=event_type,
        event_ts=event_ts or None,
        payload=payload,
    )
    if inserted:
        typer.secho("Stored event.", fg="green")
    else:
        typer.secho("Duplicate event skipped.", fg="yellow")


@app.command("dispatch")
def dispatch(
    interval_minutes: int = typer.Option(
        15,
        help="Dispatch only events older than this many minutes for debounce/coalescing",
    ),
    max_pages: int = typer.Option(200, help="Maximum unique pages per run"),
):
    """Dispatch deduplicated page IDs and run ingestion once per page."""
    load_env()
    def _process_page(page_id: str, event_context: dict):
        ingest_page(page_id, event_context=event_context)

    result = dispatch_pending_events(
        process_page=_process_page,
        interval_minutes=interval_minutes,
        max_pages=max_pages,
    )
    typer.echo(
        "Dispatch complete: "
        f"pages={result['processed_pages']}/{result['dispatchable_pages']} "
        f"event_rows_marked={result['dispatched_event_rows']} "
        f"failed={len(result['failed_pages'])}"
    )
    if result["failed_pages"]:
        typer.secho(f"Failed pages: {', '.join(result['failed_pages'])}", fg="red")


if __name__ == "__main__":
    app()
