from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = "development"
    secret_key: str

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen3:8b"
    embedding_model: str = "nomic-embed-text"

    n8n_webhook_secret: str = ""
    admin_secret_key: str = "change-me-admin"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()
