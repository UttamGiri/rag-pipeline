import os
from dotenv import load_dotenv
try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for pydantic < 2.0
    from pydantic import BaseSettings

class Settings(BaseSettings):
    environment: str = "dev"
    aws_region: str = "us-east-1"

    opensearch_endpoint: str
    opensearch_index: str

    bedrock_cohere_model: str
    bedrock_claude_model: str
    redis_enabled: bool = False
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_history_ttl_seconds: int = 86400
    chat_history_max_messages: int = 50
    chat_history_keep_last: int = 3

    log_level: str = "INFO"

    class Config:
        env_file = None

def load_settings() -> Settings:
    env = os.getenv("ENVIRONMENT", "dev")
    env_file = f"env/.env.{env}"
    if os.path.exists(env_file):
        load_dotenv(env_file)
    else:
        load_dotenv()  # fallback: .env at root if someone uses it locally

    return Settings(
        environment=os.getenv("ENVIRONMENT", "dev"),
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        opensearch_endpoint=os.getenv("OPENSEARCH_ENDPOINT", ""),
        opensearch_index=os.getenv("OPENSEARCH_INDEX", "rag_documents"),
        bedrock_cohere_model=os.getenv("BEDROCK_COHERE_MODEL", ""),
        bedrock_claude_model=os.getenv("BEDROCK_CLAUDE_MODEL", ""),
        redis_enabled=os.getenv("REDIS_ENABLED", "false").lower() == "true",
        redis_host=os.getenv("REDIS_HOST", "localhost"),
        redis_port=int(os.getenv("REDIS_PORT", "6379")),
        redis_db=int(os.getenv("REDIS_DB", "0")),
        redis_password=os.getenv("REDIS_PASSWORD", ""),
        redis_history_ttl_seconds=int(os.getenv("REDIS_HISTORY_TTL_SECONDS", "86400")),
        chat_history_max_messages=int(os.getenv("CHAT_HISTORY_MAX_MESSAGES", "50")),
        chat_history_keep_last=int(os.getenv("CHAT_HISTORY_KEEP_LAST", "3")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )

settings = load_settings()

