from pydantic import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    PROJECT_NAME: str = "Online Cinema API"
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str  # Generated using: openssl rand -hex 32
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str  # postgresql+asyncpg://user:password@localhost:5432/dbname

    # Redis (for Celery)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Email
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str

    class Config:
        env_file = ".env"


settings = Settings()
