import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "MCP Server"
    POLL_INTERVAL_SECONDS: int = int(os.getenv("POLL_INTERVAL_SECONDS", "5"))
    CCXT_TIMEOUT: int = int(os.getenv("CCXT_TIMEOUT", "10"))
    COINMARKETCAP_API_KEY: str | None = os.getenv("COINMARKETCAP_API_KEY")
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "10"))
    MAX_CACHE_SIZE: int = int(os.getenv("MAX_CACHE_SIZE", "1024"))

settings = Settings()
