import boto3
import json
from typing import List

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

class ClaudeBedrockClient:
    """
    Wrapper for Anthropic Claude models via Amazon Bedrock.
    """

    def __init__(self):
        self.region = settings.aws_region
        self.model_id = settings.bedrock_claude_model
        if not self.model_id:
            raise ValueError("BEDROCK_CLAUDE_MODEL is not set")
        self.client = boto3.client("bedrock-runtime", region_name=self.region)

    def answer(self, query: str, contexts: List[str]) -> str:
        if not contexts:
            return "I could not find any relevant information in the knowledge base."

        context_text = "\n\n".join(
            f"Document {i+1}:\n{c}" for i, c in enumerate(contexts)
        )

        system_prompt = (
            "You are a helpful assistant for a retrieval-augmented QA system. "
            "Use ONLY the provided context to answer the user's question. "
            "If the answer is not clearly present in the context, say you don't know."
        )

        user_prompt = f"Context:\n{context_text}\n\nQuestion:\n{query}"

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": user_prompt}]}
            ],
            "max_tokens": 512,
            "temperature": 0.1,
        }

        logger.debug(f"Calling Claude model {self.model_id}")
        resp = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(resp["body"].read())

        result = ""
        for block in payload.get("content", []):
            if block.get("type") == "text":
                result += block.get("text", "")
        return result.strip()

    def summarize(self, prompt: str) -> str:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "system": "You summarize chat history faithfully and concisely.",
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ],
            "max_tokens": 256,
            "temperature": 0.0,
        }
        resp = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(resp["body"].read())
        result = ""
        for block in payload.get("content", []):
            if block.get("type") == "text":
                result += block.get("text", "")
        return result.strip()

