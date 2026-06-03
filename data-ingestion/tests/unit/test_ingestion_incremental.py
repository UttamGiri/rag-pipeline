from src.pipelines.incremental_utils import should_reindex


def test_should_reindex_when_no_metadata():
    assert should_reindex(None, "abc123") is True


def test_should_reindex_when_hash_changed():
    existing = {"document_hash": "old-hash"}
    assert should_reindex(existing, "new-hash") is True


def test_should_not_reindex_when_hash_matches():
    existing = {"document_hash": "same-hash"}
    assert should_reindex(existing, "same-hash") is False
