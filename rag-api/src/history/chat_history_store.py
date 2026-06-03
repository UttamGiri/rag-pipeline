import os
import json
from typing import List, Dict

import redis


class ChatHistoryStore:
    def __init__(self):
        self.enabled = os.getenv("REDIS_ENABLED", "false").lower() == "true"
        self.ttl_seconds = int(os.getenv("REDIS_HISTORY_TTL_SECONDS", "86400"))
        self.max_messages = int(os.getenv("CHAT_HISTORY_MAX_MESSAGES", "50"))
        self.keep_last = int(os.getenv("CHAT_HISTORY_KEEP_LAST", "3"))

        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        db = int(os.getenv("REDIS_DB", "0"))
        password = os.getenv("REDIS_PASSWORD")

        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
        ) if self.enabled else None

    @staticmethod
    def _history_key(session_id: str) -> str:
        return f"chat:history:{session_id}"

    @staticmethod
    def _summary_key(session_id: str) -> str:
        return f"chat:summary:{session_id}"

    def get_messages(self, session_id: str) -> List[Dict[str, str]]:
        if not self.client:
            return []

        raw_messages = self.client.lrange(self._history_key(session_id), 0, -1)
        return [json.loads(msg) for msg in raw_messages]

    def append_turn(self, session_id: str, user_query: str, assistant_answer: str):
        if not self.client:
            return

        history_key = self._history_key(session_id)
        self.client.rpush(history_key, json.dumps({"role": "user", "text": user_query}))
        self.client.rpush(history_key, json.dumps({"role": "assistant", "text": assistant_answer}))
        self.client.ltrim(history_key, -self.max_messages, -1)
        self.client.expire(history_key, self.ttl_seconds)

    def get_summary(self, session_id: str) -> str:
        if not self.client:
            return ""
        return self.client.get(self._summary_key(session_id)) or ""

    def set_summary(self, session_id: str, summary: str):
        if not self.client:
            return
        self.client.setex(self._summary_key(session_id), self.ttl_seconds, summary)

    def compact_to_recent(self, session_id: str):
        """
        Keep only the most recent turns in raw history after summarization.
        This prevents repeatedly summarizing the same older messages.
        """
        if not self.client:
            return
        keep = max(1, self.keep_last * 2)
        history_key = self._history_key(session_id)
        self.client.ltrim(history_key, -keep, -1)
        self.client.expire(history_key, self.ttl_seconds)

    def split_for_prompt(self, session_id: str):
        messages = self.get_messages(session_id)
        if not messages:
            return {"recent": [], "older": [], "summary": ""}

        keep = max(1, self.keep_last * 2)
        if len(messages) <= keep:
            return {"recent": messages, "older": [], "summary": self.get_summary(session_id)}

        older = messages[:-keep]
        recent = messages[-keep:]
        return {"recent": recent, "older": older, "summary": self.get_summary(session_id)}
