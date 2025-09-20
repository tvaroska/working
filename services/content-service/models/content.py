"""
Content model for articles and posts
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Content(Base):
    """
    Content/Article database model.
    
    Represents individual content items (articles, blog posts) ingested
    from RSS feeds. Stores both original content and AI-processed metadata
    including summaries, sentiment analysis, and user interaction data.
    
    Attributes:
        id: Primary key identifier
        source_id: Foreign key to the RSS source
        title: Article title
        original_content: Full article content text
        url: Original article URL
        author: Article author name
        ai_summary: AI-generated summary and analysis (JSON)
        metadata: Additional content metadata (JSON)
        processing_status: Current processing state
        ai_processed: Flag indicating AI processing completion
        saved: User saved status (MVP single-user)
        dismissed: User dismissed status (MVP single-user)
        view_count: Number of times content was viewed
        content_hash: SHA-256 hash for deduplication
        published_at: Original publication timestamp
        created_at: Record creation timestamp
        updated_at: Record update timestamp
        processed_at: AI processing completion timestamp
        source: Relationship to Source model
    """
    
    __tablename__ = "content"
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    
    # Basic content fields
    title = Column(Text, nullable=False)
    original_content = Column(Text)  # Full article content
    url = Column(String(500), nullable=False, index=True)
    author = Column(String(255))
    
    # AI processing fields
    ai_summary = Column(JSON)  # AI-generated summary and metadata
    # Structure: {
    #   "text": "...",
    #   "keyPoints": [...],
    #   "sentiment": "...",
    #   "priority": 5,
    #   "readTime": 300,
    #   "tags": [...]
    # }
    
    # Content metadata
    metadata = Column(JSON)  # Additional content-specific data
    # Structure: {
    #   "publishedAt": "2024-01-01T00:00:00Z",
    #   "readTime": 300,
    #   "sourceUrl": "...",
    #   "guid": "...",
    #   "language": "en"
    # }
    
    # Processing status
    processing_status = Column(String(20), default="pending")  # pending, processing, completed, failed
    ai_processed = Column(Boolean, default=False)
    
    # User interaction fields (simplified for single-user MVP)
    saved = Column(Boolean, default=False)
    dismissed = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)
    
    # Content hash for deduplication
    content_hash = Column(String(64), index=True)
    
    # Timestamps
    published_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True))
    
    # Relationships
    source = relationship("Source", backref="content_items")
    
    def __repr__(self):
        """
        String representation of Content instance.
        
        Returns:
            str: Human-readable representation showing key identifiers
        """
        return f"<Content(id={self.id}, title='{self.title[:50]}...', source_id={self.source_id})>"