from pydantic_settings import BaseSettings
from urllib.parse import quote_plus

db_password = quote_plus("")

  


class Settings(BaseSettings):
    database_url: str =  f"postgresql+asyncpg://app_user:{db_password}@localhost:5432/saas_db"
    jwt_secret: str = "temp secret #1992"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    LOG_LEVEL: str = "INFO"
    EXEMPT_PATHS: set[str] = {"/health", "/auth/login", "/docs", "/openapi.json", "/redoc"}

    # Rate limit tiers: requests allowed per 60-second sliding window
    rate_limits: dict = {
        "free": 60,
        "pro": 600,
        "enterprise": 6000,
    }

    redis_url: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"


settings = Settings()
