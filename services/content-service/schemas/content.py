"""
Content-related Pydantic schemas
"""

from pydantic import BaseModel, HttpUrl, validator
from typing import Optional, Dict, Any, List
from datetime import datetime


class ContentBase(BaseModel):
    """
    Base content schema with common fields.
    
    Contains the fundamental content fields shared across
    different content operations (create, update, response).
    
    Attributes:
        title: Content title
        url: Original content URL
        author: Content author name (optional)
        original_content: Full content text (optional)
    """
    title: str
    url: HttpUrl
    author: Optional[str] = None
    original_content: Optional[str] = None


class ContentCreate(ContentBase):
    """
    Schema for creating new content items.
    
    Extends ContentBase with additional fields required
    for content creation, including source association
    and metadata.
    
    Attributes:
        source_id: ID of the source this content belongs to
        metadata: Additional content metadata (optional)
        published_at: Original publication timestamp (optional)
    """
    source_id: int
    metadata: Optional[Dict[str, Any]] = None
    published_at: Optional[datetime] = None


class ContentUpdate(BaseModel):
    """
    Schema for updating existing content items.
    
    All fields are optional to allow partial updates.
    Used for updating content processing status, AI summaries,
    and user interaction states.
    
    Attributes:
        title: Updated content title (optional)
        original_content: Updated content text (optional)
        ai_summary: AI-generated summary data (optional)
        processing_status: Current processing state (optional)
        saved: User saved status (optional)
        dismissed: User dismissed status (optional)
    """
    title: Optional[str] = None
    original_content: Optional[str] = None
    ai_summary: Optional[Dict[str, Any]] = None
    processing_status: Optional[str] = None
    saved: Optional[bool] = None
    dismissed: Optional[bool] = None


class ContentSummary(BaseModel):
    """
    Schema for AI-generated content summary data.
    
    Represents the structured output from AI summarization
    including text summary, key points, sentiment analysis,
    and content metadata.
    
    Attributes:
        text: Main summary text
        key_points: List of key points extracted
        sentiment: Sentiment analysis result (optional)
        priority: Content priority score (1-10)
        read_time: Estimated reading time in seconds (optional)
        tags: List of content tags
    """
    text: str
    key_points: List[str]
    sentiment: Optional[str] = None
    priority: int = 5
    read_time: Optional[int] = None  # seconds
    tags: List[str] = []


class ContentResponse(BaseModel):
    """
    Schema for content API responses.
    
    Complete content representation returned by API endpoints.
    Includes all content fields, processing status, user interactions,
    and timestamps.
    
    Attributes:
        id: Content identifier
        source_id: Source identifier
        title: Content title
        url: Original content URL
        author: Content author (optional)
        ai_summary: AI-generated summary (optional)
        metadata: Additional content metadata (optional)
        processing_status: Current processing state
        ai_processed: AI processing completion flag
        saved: User saved status
        dismissed: User dismissed status
        view_count: Number of views
        published_at: Original publication timestamp (optional)
        created_at: Record creation timestamp
        updated_at: Record update timestamp (optional)
    """
    id: int
    source_id: int
    title: str
    url: str
    author: Optional[str] = None
    ai_summary: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    processing_status: str
    ai_processed: bool
    saved: bool
    dismissed: bool
    view_count: int
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ContentFeedResponse(BaseModel):
    """
    Schema for paginated content feed responses.
    
    Used for returning paginated lists of content items
    with pagination metadata for proper navigation.
    
    Attributes:
        items: List of content items for current page
        total: Total number of content items
        page: Current page number
        per_page: Items per page
        has_next: Whether next page exists
        has_prev: Whether previous page exists
    """
    items: List[ContentResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class ContentActionRequest(BaseModel):
    """
    Schema for content action requests.
    
    Used for user actions on content items such as saving,
    dismissing, or viewing content. Includes validation
    for allowed action types.
    
    Attributes:
        action: Action to perform (save, dismiss, view, unsave)
    """
    action: str  # save, dismiss, view
    
    @validator('action')
    def validate_action(cls, v):
        """
        Validate that the action is one of the allowed types.
        
        Args:
            v: Action value to validate
            
        Returns:
            str: Validated action value
            
        Raises:
            ValueError: If action is not in allowed list
        """
        allowed_actions = ['save', 'dismiss', 'view', 'unsave']
        if v not in allowed_actions:
            raise ValueError(f'Action must be one of {allowed_actions}')
        return v