"""Application configuration."""
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Settings
    API_TITLE: str = "GraphRAG API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Graph-based Retrieval Augmented Generation API"
    API_PREFIX: str = "/api/v1"

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # Neo4j Settings
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # Storage Settings
    DATA_DIR: str = "data"

    # OCR (Mistral)
    MISTRAL_API_KEY: str = ""
    MISTRAL_API_BASE: str = "https://api.mistral.ai/v1"
    MISTRAL_OCR_MODEL: str = "mistral-ocr-latest"
    MISTRAL_INCLUDE_IMAGE_BASE64: bool = False
    MISTRAL_DELETE_REMOTE_FILE: bool = True
    MISTRAL_OCR_CHUNK_SIZE_PAGES: int = 100
    MISTRAL_API_TIMEOUT_SECONDS: int = 300
    MISTRAL_EXTRACT_HEADER: bool = True
    MISTRAL_EXTRACT_FOOTER: bool = True
    MISTRAL_TABLE_FORMAT: str = "markdown"  # or "html"

    MISTRAL_DOCUMENT_ANNOTATION_PROMPT: str = ""
    MISTRAL_DOCUMENT_ANNOTATION_FORMAT: dict = {}
    MISTRAL_BBOX_ANNOTATION_FORMAT: dict = {}
        # Embedding Settings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    EMBEDDING_BATCH_SIZE: int = 24
    OLLAMA_BASE_URL: str = ""
    NGROK_URL: str = ""
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text-v2-moe"
    OLLAMA_TIMEOUT_SECONDS: int = 120

    # LLM Settings
    LLM_MODEL: str = "gpt-3.5-turbo"
    LLM_API_KEY: str = ""

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # External automation pipeline
    USE_JOB_AUTOMATION_PIPELINE: bool = True
    JOB_AUTOMATION_DIR: str = r"C:\Users\Admin\Downloads\job_automation"
    JOB_SCRIPT_TIMEOUT_SECONDS: int = 7200
    JOB_PYTHON_EXECUTABLE: str = ""

    @property
    def data_path(self) -> Path:
        """Return the absolute data directory path."""
        return Path(self.DATA_DIR).resolve()

    @property
    def documents_path(self) -> Path:
        """Return the absolute documents storage path."""
        return self.data_path / "documents"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_value(cls, value):
        """Allow DEBUG values like 'release' / 'production' in shell environments."""
        if isinstance(value, bool):
            return value
        if value is None:
            return False

        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on", "debug"}:
            return True
        if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
            return False
        return False

    class Config:
        env_file = (".env", "../.env", "../../.env")

        case_sensitive = False
        extra = "ignore"


settings = Settings()
