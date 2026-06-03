from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

from src.config.settings import settings
from src.utils.logger import get_logger
from src.embeddings.cohere_bedrock_embeddings import CohereBedrockEmbedder
from src.retrieval.opensearch_retriever import OpenSearchRetriever
from src.llm.claude_bedrock_client import ClaudeBedrockClient
from src.history.chat_history_store import ChatHistoryStore
from src.history.history_summarizer import HistorySummarizer

logger = get_logger(__name__)
app = FastAPI(title="RAG Query Service")

# Instantiate dependencies once (can be swapped with DI in bigger project)
embedder = CohereBedrockEmbedder()
retriever = OpenSearchRetriever()
llm_client = ClaudeBedrockClient()
history_store = ChatHistoryStore()
history_summarizer = HistorySummarizer(llm_client)

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    session_id: str | None = None

class Source(BaseModel):
    score: float
    content: str
    has_pii: bool | None = None
    s3_bucket: str | None = None
    s3_key: str | None = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]

@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.environment}

@app.post("/query", response_model=QueryResponse)
def query_endpoint(payload: QueryRequest):
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query must not be empty")

    logger.info(f"Received query: {query}")

    # 1. Embed query
    q_vec = embedder.embed_query(query)

    # 2. Retrieve documents
    docs = retriever.retrieve(q_vec, k=payload.top_k)
    if not docs:
        logger.info("No documents retrieved from OpenSearch.")
        return QueryResponse(
            answer="I couldn't find any relevant information in the knowledge base.",
            sources=[],
        )

    contexts = [d["content"] for d in docs]

    prompt_query = query
    session_id = payload.session_id
    if session_id and settings.redis_enabled:
        history_parts = history_store.split_for_prompt(session_id)
        older = history_parts["older"]
        recent = history_parts["recent"]
        summary = history_parts["summary"]

        if older:
            summary = history_summarizer.summarize(older, existing_summary=summary)
            history_store.set_summary(session_id, summary)
            history_store.compact_to_recent(session_id)
            recent = history_store.get_messages(session_id)

        if recent or summary:
            history_text = []
            if summary:
                history_text.append(f"Prior summary:\n{summary}")
            if recent:
                recent_text = "\n".join(
                    f"{msg.get('role', 'unknown')}: {msg.get('text', '')}"
                    for msg in recent
                )
                history_text.append(f"Last 3 turns:\n{recent_text}")
            prompt_query = f"{query}\n\nChat history context:\n" + "\n\n".join(history_text)

    # 3. Call Claude LLM with contexts
    answer = llm_client.answer(prompt_query, contexts)

    if session_id and settings.redis_enabled:
        history_store.append_turn(session_id, query, answer)

    sources_response = [
        Source(
            score=d["score"],
            content=d["content"],
            has_pii=d.get("has_pii"),
            s3_bucket=d.get("s3_bucket"),
            s3_key=d.get("s3_key"),
        )
        for d in docs
    ]

    return QueryResponse(answer=answer, sources=sources_response)

