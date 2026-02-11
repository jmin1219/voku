from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = "development"
    groq_api_key: str = ""  # Required only for LLM calls

    # Frontend origin for CORS
    frontend_url: str = "http://localhost:5173"

    # SQLite database (single file, portable)
    db_path: str = "./data/voku.db"

    class Config:
        env_file = ".env"


settings = Settings()
