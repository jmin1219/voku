from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = "development"
    groq_api_key: str = ""  # Required only for LLM calls
    anthropic_api_key: str = ""  # Required only for LLM calls

    # Provider: "groq" (cloud) or "local" (Ollama)
    voku_provider: str = "groq"

    # Frontend origin for CORS
    frontend_url: str = "http://localhost:5173"

    # SQLite databases
    db_path: str = "./data/voku.db"  # conversations + messages
    propositions_db_path: str = "./data/m2_conversation.db"  # propositions + embeddings

    class Config:
        env_file = ".env"


settings = Settings()
