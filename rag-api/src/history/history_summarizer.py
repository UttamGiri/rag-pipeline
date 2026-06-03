from typing import List, Dict

from src.llm.claude_bedrock_client import ClaudeBedrockClient


class HistorySummarizer:
    def __init__(self, llm_client: ClaudeBedrockClient):
        self.llm_client = llm_client

    def summarize(self, older_messages: List[Dict[str, str]], existing_summary: str = "") -> str:
        if not older_messages:
            return existing_summary or ""

        older_text = "\n".join(
            f"{msg.get('role', 'unknown')}: {msg.get('text', '')}" for msg in older_messages
        )

        prompt = (
            "Summarize this chat history concisely for future QA context. "
            "Keep key facts, decisions, unresolved asks, and constraints. "
            "Do not invent details.\n\n"
            f"Existing summary:\n{existing_summary or '(none)'}\n\n"
            f"History:\n{older_text}"
        )
        return self.llm_client.summarize(prompt)
