from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = "development"
    groq_api_key: str = ""  # Required only for LLM calls

    # Frontend origin for CORS
    frontend_url: str = "http://localhost:5173"

    db_path: str = "./data/voku.db"  # Path to Kuzu database file

    class Config:
        env_file = ".env"


settings = Settings()
