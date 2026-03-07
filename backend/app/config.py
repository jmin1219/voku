from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = "development"
    groq_api_key: str = ""  # Required only for LLM calls
    anthropic_api_key: str = ""  # Required only for LLM calls

    # Provider: "groq" (cloud) or "local" (Ollama)
    voku_provider: str = "groq"

    # Frontend origin for CORS
    frontend_url: str = "http://localhost:5173"

    # Production CORS origins (comma-separated)
    cors_origins: str = ""

    # SQLite database (unified — all tables in one file)
    db_path: str = "./data/voku.db"

    class Config:
        env_file = ".env"


settings = Settings()
