from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Adata Price Monitor"
    APP_VERSION: str = "0.1.0"
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/price_monitor"
    
    # Redis (for Celery)
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Zyte
    ZYTE_API_KEY: Optional[str] = None
    ZYTE_API_URL: str = "https://api.zyte.com/v1/extract"
    
    # Scraper settings
    SCRAPE_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    
    # Price validation
    DEFAULT_PRICE_TOLERANCE: float = 0.3  # 30%
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
