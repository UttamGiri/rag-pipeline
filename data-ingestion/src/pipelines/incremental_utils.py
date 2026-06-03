def should_reindex(existing_meta: dict | None, doc_hash: str) -> bool:
    if not existing_meta:
        return True
    return existing_meta.get("document_hash") != doc_hash
