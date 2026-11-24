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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
