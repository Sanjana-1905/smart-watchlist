from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    market_provider: str = "mock"
    demo_mode: bool = False

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120

    class Config:
        env_file = ".env"

settings = Settings()
