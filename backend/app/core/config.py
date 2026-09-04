from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    market_provider: str = "mock"

    class Config:
        env_file = ".env"

settings = Settings()