from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from src.api.fastapi_app import app

client = TestClient(app)

@patch("src.api.fastapi_app.llm_client")
@patch("src.api.fastapi_app.retriever")
@patch("src.api.fastapi_app.embedder")
@patch("src.api.fastapi_app.settings")
def test_query_endpoint_success(mock_settings, mock_embedder, mock_retriever, mock_llm):
    mock_settings.redis_enabled = False
    mock_embedder.embed_query.return_value = [0.1, 0.2]

    mock_retriever.retrieve.return_value = [
        {
            "score": 1.0,
            "content": "Context doc",
            "has_pii": False,
            "s3_bucket": "bucket",
            "s3_key": "key",
        }
    ]

    mock_llm.answer.return_value = "Final answer"

    response = client.post(
        "/query",
        json={"query": "What is this?", "top_k": 3},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Final answer"
    assert len(data["sources"]) == 1

@patch("src.api.fastapi_app.history_summarizer")
@patch("src.api.fastapi_app.history_store")
@patch("src.api.fastapi_app.llm_client")
@patch("src.api.fastapi_app.retriever")
@patch("src.api.fastapi_app.embedder")
@patch("src.api.fastapi_app.settings")
def test_query_endpoint_with_session_summarizes_and_compacts(
    mock_settings,
    mock_embedder,
    mock_retriever,
    mock_llm,
    mock_history_store,
    mock_history_summarizer,
):
    mock_settings.redis_enabled = True
    mock_embedder.embed_query.return_value = [0.1, 0.2]
    mock_retriever.retrieve.return_value = [
        {
            "score": 0.9,
            "content": "Context doc",
            "has_pii": False,
            "s3_bucket": "bucket",
            "s3_key": "key",
        }
    ]
    mock_history_store.split_for_prompt.return_value = {
        "older": [{"role": "user", "text": "old question"}],
        "recent": [
            {"role": "assistant", "text": "recent answer"},
            {"role": "user", "text": "recent question"},
        ],
        "summary": "existing summary",
    }
    mock_history_summarizer.summarize.return_value = "updated summary"
    mock_history_store.get_messages.return_value = [
        {"role": "assistant", "text": "recent answer"},
        {"role": "user", "text": "recent question"},
    ]
    mock_llm.answer.return_value = "Answer with history"

    response = client.post(
        "/query",
        json={"query": "What did we decide?", "session_id": "chat-123"},
    )

    assert response.status_code == 200
    mock_history_summarizer.summarize.assert_called_once_with(
        [{"role": "user", "text": "old question"}],
        existing_summary="existing summary",
    )
    mock_history_store.set_summary.assert_called_once_with("chat-123", "updated summary")
    mock_history_store.compact_to_recent.assert_called_once_with("chat-123")
    mock_history_store.get_messages.assert_called_once_with("chat-123")
    mock_llm.answer.assert_called_once()
    called_prompt = mock_llm.answer.call_args[0][0]
    assert "Prior summary:\nupdated summary" in called_prompt
    assert "Last 3 turns:" in called_prompt
    mock_history_store.append_turn.assert_called_once_with(
        "chat-123",
        "What did we decide?",
        "Answer with history",
    )


@patch("src.api.fastapi_app.history_summarizer")
@patch("src.api.fastapi_app.history_store")
@patch("src.api.fastapi_app.llm_client")
@patch("src.api.fastapi_app.retriever")
@patch("src.api.fastapi_app.embedder")
@patch("src.api.fastapi_app.settings")
def test_query_endpoint_with_session_recent_only_no_summarize(
    mock_settings,
    mock_embedder,
    mock_retriever,
    mock_llm,
    mock_history_store,
    mock_history_summarizer,
):
    mock_settings.redis_enabled = True
    mock_embedder.embed_query.return_value = [0.1, 0.2]
    mock_retriever.retrieve.return_value = [
        {
            "score": 0.8,
            "content": "Context doc",
            "has_pii": False,
            "s3_bucket": "bucket",
            "s3_key": "key",
        }
    ]
    mock_history_store.split_for_prompt.return_value = {
        "older": [],
        "recent": [
            {"role": "user", "text": "hello"},
            {"role": "assistant", "text": "hi"},
        ],
        "summary": "",
    }
    mock_llm.answer.return_value = "Answer with only recent history"

    response = client.post(
        "/query",
        json={"query": "Continue", "session_id": "chat-456"},
    )

    assert response.status_code == 200
    mock_history_summarizer.summarize.assert_not_called()
    mock_history_store.set_summary.assert_not_called()
    mock_history_store.compact_to_recent.assert_not_called()
    mock_history_store.get_messages.assert_not_called()
    called_prompt = mock_llm.answer.call_args[0][0]
    assert "Last 3 turns:" in called_prompt
    assert "Prior summary:" not in called_prompt
