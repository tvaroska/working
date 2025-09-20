"""
Configuration settings for the content service
"""

from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application configuration settings.
    
    Manages all configuration parameters for the content service including
    database connections, RSS processing settings, external service URLs,
    and operational parameters. Settings can be overridden via environment
    variables or .env file.
    
    Attributes:
        database_url: PostgreSQL connection string
        allowed_origins: CORS allowed origins list
        rss_fetch_timeout: RSS feed fetch timeout in seconds
        rss_user_agent: User agent string for RSS requests
        max_concurrent_feeds: Maximum number of concurrent RSS fetches
        content_batch_size: Batch size for content processing
        max_content_length: Maximum content length in bytes
        feed_refresh_interval: RSS feed refresh interval in seconds
        cleanup_interval: Content cleanup interval in seconds
        redis_url: Redis connection string for caching
        ai_service_url: AI summarization service URL
        search_service_url: Search service URL
    """
    
    # Database
    database_url: str = "postgresql://user:pass@localhost/newsletter_app"
    
    # CORS
    allowed_origins: List[str] = ["http://localhost:3000", "https://localhost:3000"]
    
    # RSS Processing
    rss_fetch_timeout: int = 30
    rss_user_agent: str = "Updater RSS Reader 1.0"
    max_concurrent_feeds: int = 10
    
    # Content Processing
    content_batch_size: int = 50
    max_content_length: int = 1000000  # 1MB
    
    # Background Tasks
    feed_refresh_interval: int = 3600  # 1 hour
    cleanup_interval: int = 86400  # 24 hours
    
    # Redis (for caching and queues)
    redis_url: str = "redis://localhost:6379"
    
    # External Services
    ai_service_url: str = "http://localhost:8002"
    search_service_url: str = "http://localhost:8003"
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings instance.
    
    Uses LRU cache to ensure settings are loaded only once and reused
    across the application lifecycle. This improves performance and
    ensures consistent configuration throughout the service.
    
    Returns:
        Settings: Cached settings instance with all configuration values
    """
    return Settings()