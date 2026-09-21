from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["local", "test", "demo", "prod"] = "local"
    app_name: str = "management-star-backend"
    app_version: str = "0.1.0"
    database_url: str = "postgresql+psycopg://app_rw:app_rw@localhost:5432/management_star"
    migration_database_url: str | None = None
    query_database_url: str = (
        "postgresql+psycopg://text2sql_ro:text2sql_ro@localhost:5432/management_star"
    )
    model_secret_key: str = ""
    default_model_config: Literal["fake", "real"] = "real"
    real_model_base_url: str = ""
    real_model_api_key: SecretStr | None = None
    real_model_name: str = ""
    real_model_protocol: Literal["responses", "chat_completions"] = "responses"
    real_model_timeout_seconds: int = Field(default=60, ge=1, le=120)
    log_level: str = "INFO"
    sql_timeout_seconds: int = Field(default=10, ge=1, le=30)
    database_connect_timeout_seconds: int = Field(default=1, ge=1, le=10)
    sql_lock_timeout_seconds: int = Field(default=2, ge=1, le=10)
    sql_max_rows: int = Field(default=500, ge=1, le=10_000)
    sql_max_response_bytes: int = Field(default=5 * 1024 * 1024, ge=1024)
    fixed_user_id: str = "demo-user"
    max_data_source_selection: int = Field(default=8, ge=1, le=8)
    graph_version: str = "langgraph-v2"
    graph_recursion_limit: int = Field(default=30, ge=10, le=100)
    execution_deadline_seconds: int = Field(default=120, ge=1, le=600)
    execution_worker_id: str = Field(default="", max_length=128)
    execution_lease_seconds: int = Field(default=120, ge=10, le=600)
    execution_heartbeat_seconds: int = Field(default=20, ge=1, le=300)
    execution_recovery_batch_size: int = Field(default=20, ge=1, le=100)
    execution_event_poll_interval_seconds: float = Field(default=0.25, ge=0.05, le=5)
    execution_event_heartbeat_seconds: int = Field(default=15, ge=1, le=60)
    execution_event_batch_size: int = Field(default=100, ge=1, le=500)
    execution_event_retention_days: int = Field(default=7, ge=1, le=365)
    model_call_budget: int = Field(default=8, ge=1, le=10)
    model_http_attempt_budget: int = Field(default=12, ge=1, le=30)
    model_http_max_attempts_per_call: int = Field(default=3, ge=1, le=3)
    clarification_max_rounds: int = Field(default=2, ge=1, le=2)
    rag_embedding_model: str = "BAAI/bge-small-zh-v1.5"
    rag_embedding_dimension: int = Field(default=512, ge=1, le=4096)
    rag_vector_top_k: int = Field(default=10, ge=1, le=50)
    rag_keyword_top_k: int = Field(default=10, ge=1, le=50)
    rag_final_top_k: int = Field(default=5, ge=1, le=20)
    rag_max_objects: int = Field(default=6, ge=1, le=20)
    rag_hnsw_threshold: int = Field(default=1000, ge=100)
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @model_validator(mode="after")
    def validate_model_mode(self) -> "Settings":
        if self.app_env in ("demo", "prod") and self.default_model_config == "fake":
            raise ValueError("demo/prod 环境禁止使用 Fake 模型模式")
        if self.execution_heartbeat_seconds >= self.execution_lease_seconds:
            raise ValueError("execution heartbeat must be shorter than lease")
        return self

    @property
    def checkpoint_database_url(self) -> str:
        return self.database_url.replace("postgresql+psycopg://", "postgresql://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
