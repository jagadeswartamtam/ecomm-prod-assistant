from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration settings for the RAG Application.
    Loads values from environment variables or a .env file.
    """
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application Settings
    app_name: str = Field(" Agentic RAG Application", validation_alias="APP_NAME")
    app_env: str = Field("development", validation_alias="APP_ENV")
    app_debug: bool = Field(True, validation_alias="APP_DEBUG")

    # LLM Settings
    llm_provider: str = Field(
    default="groq",
    validation_alias="LLM_PROVIDER"
    )

    llm_model: str = Field(
    default="llama-3.3-70b-versatile",
    validation_alias="LLM_MODEL"
    )

    llm_temperature: float = Field(
    default=0.7,
    validation_alias="LLM_TEMPERATURE"
    )

    # Embedding Settings
    embedding_provider: str = Field("huggingface", validation_alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field("sentence-transformers/all-MiniLM-L6-v2", validation_alias="EMBEDDING_MODEL")

    # Vector DB Settings
    groq_api_key: str = Field(
    None,
    validation_alias="GROQ_API_KEY"
    )
    gemini_api_key: str | None = Field(
    default=None,
    validation_alias="GEMINI_API_KEY"
    )

    # API Keys
    
    openai_api_key: Optional[str] = Field(None, validation_alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, validation_alias="ANTHROPIC_API_KEY")

    # PostgreSQL + pgvector
    database_url: Optional[str] = Field(None, validation_alias="DATABASE_URL")
    
    db_api_endpoint: Optional[str] = Field(None, validation_alias="ASTRA_DB_API_ENDPOINT")
    db_application_token: Optional[str] = Field(None, validation_alias="ASTRA_DB_APPLICATION_TOKEN")
    db_keyspace: Optional[str] = Field(None, validation_alias="ASTRA_DB_KEYSPACE")
    astra_db: Optional[str] = Field(None, validation_alias="astra_db")

    # Redis Cache Settings
    redis_url: Optional[str] = Field(None, validation_alias="REDIS_URL")

    # Embedding dimensions — must match the model used
    # text-embedding-004 (Gemini) = 768 | text-embedding-ada-002 (OpenAI) = 1536
    embedding_dimensions: int = Field(384, validation_alias="EMBEDDING_DIMENSIONS")
    top_k:int=Field(None, validation_alias="top_k")
    collection_name: Optional[str] = Field(None, validation_alias="astra_db" )

    @property
    def is_development(self) -> bool:
        """Helper property to check if the app is running in development mode."""
        return self.app_env.lower() in ("development", "dev")

    @property
    def is_production(self) -> bool:
        """Helper property to check if the app is running in production mode."""
        return self.app_env.lower() in ("production", "prod")


# Global settings instance
settings = Settings()
