from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./meeting_assistant.db"
    upload_dir: str = "./uploads"
    chroma_dir: str = "./chroma_db"

    asr_provider: str = "custom"
    asr_api_key: str = ""
    asr_api_base_url: str = ""
    asr_model: str = "custom-asr"
    asr_enable_speaker_diarization: bool = True

    llm_provider: str = "openai_compatible"
    llm_api_key: str = ""
    llm_api_base_url: str = ""
    llm_model: str = "deepseek-chat"

    embedding_provider: str = "openai_compatible"
    embedding_api_key: str = ""
    embedding_api_base_url: str = ""
    embedding_model: str = "text-embedding-3-small"

    ai_request_timeout: int = 60
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir)

    @property
    def chroma_path(self) -> Path:
        return Path(self.chroma_dir)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    return settings
