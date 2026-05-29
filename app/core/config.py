from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional
import os

# Load .env for local development.
# IMPORTANT: do not override env vars already set by the runtime
# (e.g. docker-compose), otherwise DATABASE_URL/REDIS_URL meant
# for the container network gets overwritten by host-only values
# in .env (which causes "connection refused" inside containers).
load_dotenv(".env", override=False)


class Settings(BaseSettings):
    model_config = ConfigDict(case_sensitive=True, extra="ignore")

    APP_NAME: str = "Adata Price Monitor"
    APP_VERSION: str = "0.1.0"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/price_monitor")

    # Redis (for Celery)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    # Zyte
    ZYTE_API_KEY: Optional[str] = os.getenv("ZYTE_API_KEY")
    ZYTE_API_URL: str = "https://api.zyte.com/v1/extract"

    # Scraper settings
    SCRAPE_TIMEOUT: int = int(os.getenv("SCRAPE_TIMEOUT", "30"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

    # Price validation
    DEFAULT_PRICE_TOLERANCE: float = float(os.getenv("DEFAULT_PRICE_TOLERANCE", "0.3"))


settings = Settings()
