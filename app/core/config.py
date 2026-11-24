from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5433
    DB_NAME: str = "rag_database"
    DB_USER: str = "rag_app"
    DB_PASSWORD: str

    GCS_BUCKET_NAME: str = "gcp-rag-system-documents"
    GCS_SIGNING_SERVICE_ACCOUNT: str | None = None
    UPLOAD_URL_EXPIRES_MINUTES: int = 10
    MAX_DOCUMENT_SIZE_BYTES: int = 25 * 1024 * 1024

    GOOGLE_CLOUD_PROJECT: str = "gcp-rag-system"
    GOOGLE_CLOUD_LOCATION: str = "asia-south1"
    EMBEDDING_MODEL: str = "text-embedding-005"
    EMBEDDING_BATCH_SIZE: int = 32
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 150

    CLOUD_TASKS_ENABLED: bool = False
    CLOUD_TASKS_QUEUE: str = "document-ingestion"
    CLOUD_TASKS_LOCATION: str = "asia-south1"
    INGESTION_WORKER_URL: str | None = None
    TASK_INVOKER_SERVICE_ACCOUNT: str | None = None
    TASK_OIDC_AUDIENCE: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
