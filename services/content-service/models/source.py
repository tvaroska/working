"""
Source model for RSS feeds and content sources
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from ..database import Base


class Source(Base):
    """
    RSS/Newsletter source database model.
    
    Represents content sources (RSS feeds, newsletters) that are monitored
    for new content. Tracks source configuration, fetch status, statistics,
    and metadata for content ingestion.
    
    Attributes:
        id: Primary key identifier
        name: Human-readable source name
        type: Source type ('rss', 'newsletter')
        url: Source URL for content fetching
        description: Source description
        category: Content category for organization
        active: Whether source is actively monitored
        priority: Source priority (1-10 scale)
        custom_source: Flag for user-added sources
        metadata_: Additional source-specific settings (JSON)
        last_fetched: Timestamp of last fetch attempt
        last_modified: ETag/Last-Modified header from last fetch
        etag: ETag header for conditional requests
        fetch_interval: Fetch interval in seconds
        total_items: Total content items from this source
        successful_fetches: Count of successful fetch attempts
        failed_fetches: Count of failed fetch attempts
        created_at: Record creation timestamp
        updated_at: Record update timestamp
    """
    
    __tablename__ = "sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    type = Column(String(20), nullable=False, default="rss")  # 'rss', 'newsletter'
    url = Column(String(500), nullable=False)
    description = Column(Text)
    category = Column(String(100), index=True)
    
    # Status and configuration
    active = Column(Boolean, default=True, index=True)
    priority = Column(Integer, default=5)  # 1-10 scale
    custom_source = Column(Boolean, default=False)
    
    # Metadata
    metadata_ = Column("metadata", JSON)  # Additional source-specific settings
    
    # RSS specific fields
    last_fetched = Column(DateTime(timezone=True))
    last_modified = Column(String(255))  # ETag/Last-Modified from RSS
    etag = Column(String(255))
    fetch_interval = Column(Integer, default=3600)  # seconds
    
    # Statistics
    total_items = Column(Integer, default=0)
    successful_fetches = Column(Integer, default=0)
    failed_fetches = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        """
        String representation of Source instance.
        
        Returns:
            str: Human-readable representation showing key identifiers
        """
        return f"<Source(id={self.id}, name='{self.name}', type='{self.type}'})>"