from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = "development"
    groq_api_key: str

    # Frontend origin for CORS
    frontend_url: str = "http://localhost:5173"

    class Config:
        env_file = ".env"


settings = Settings()
