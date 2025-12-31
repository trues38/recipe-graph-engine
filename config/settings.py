from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    # Neo4j
    neo4j_uri: str = "bolt://localhost:17687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "test1234"

    # OpenRouter (LLM)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # LLM 모델 (우선순위 순)
    llm_models: list[str] = [
        "xiaomi/mimo-v2-flash:free",
        "x-ai/grok-4.1-fast",
        "openai/gpt-4o-mini",
        "deepseek/deepseek-chat",
    ]

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # 공공데이터 API
    data_go_kr_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


_settings: Settings | None = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
