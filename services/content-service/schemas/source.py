"""
Source-related Pydantic schemas
"""

from pydantic import BaseModel, HttpUrl, validator
from typing import Optional, Dict, Any
from datetime import datetime


class SourceBase(BaseModel):
    """
    Base source schema with common fields.
    
    Contains fundamental source fields shared across
    different source operations (create, update, response).
    
    Attributes:
        name: Human-readable source name
        url: Source URL for content fetching
        description: Source description (optional)
        category: Content category (optional)
    """
    name: str
    url: HttpUrl
    description: Optional[str] = None
    category: Optional[str] = None


class SourceCreate(SourceBase):
    """
    Schema for creating new content sources.
    
    Extends SourceBase with additional fields required
    for source creation including type validation and
    fetch configuration.
    
    Attributes:
        type: Source type (rss, newsletter, api)
        priority: Source priority (1-10 scale)
        fetch_interval: Fetch interval in seconds
        metadata_: Additional source-specific settings (optional)
    """
    type: str = "rss"
    priority: int = 5
    fetch_interval: int = 3600
    metadata_: Optional[Dict[str, Any]] = None
    
    @validator('type')
    def validate_type(cls, v):
        """
        Validate that the source type is allowed.
        
        Args:
            v: Source type value to validate
            
        Returns:
            str: Validated source type
            
        Raises:
            ValueError: If type is not in allowed list
        """
        allowed_types = ['rss', 'newsletter', 'api']
        if v not in allowed_types:
            raise ValueError(f'Type must be one of {allowed_types}')
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        """
        Validate that priority is within allowed range.
        
        Args:
            v: Priority value to validate
            
        Returns:
            int: Validated priority value
            
        Raises:
            ValueError: If priority is not between 1 and 10
        """
        if not 1 <= v <= 10:
            raise ValueError('Priority must be between 1 and 10')
        return v


class SourceUpdate(BaseModel):
    """
    Schema for updating existing sources.
    
    All fields are optional to allow partial updates.
    Used for modifying source configuration, status,
    and fetch settings.
    
    Attributes:
        name: Updated source name (optional)
        url: Updated source URL (optional)
        description: Updated description (optional)
        category: Updated category (optional)
        active: Updated active status (optional)
        priority: Updated priority (optional)
        fetch_interval: Updated fetch interval (optional)
        metadata_: Updated metadata (optional)
    """
    name: Optional[str] = None
    url: Optional[HttpUrl] = None
    description: Optional[str] = None
    category: Optional[str] = None
    active: Optional[bool] = None
    priority: Optional[int] = None
    fetch_interval: Optional[int] = None
    metadata_: Optional[Dict[str, Any]] = None


class SourceResponse(BaseModel):
    """
    Schema for source API responses.
    
    Complete source representation returned by API endpoints.
    Includes all source fields, statistics, and timestamps.
    
    Attributes:
        id: Source identifier
        name: Source name
        type: Source type
        url: Source URL
        description: Source description (optional)
        category: Content category (optional)
        active: Whether source is active
        priority: Source priority (1-10)
        custom_source: Whether source is user-added
        metadata_: Additional source settings (optional)
        last_fetched: Last fetch timestamp (optional)
        fetch_interval: Fetch interval in seconds
        total_items: Total content items from source
        successful_fetches: Count of successful fetches
        failed_fetches: Count of failed fetches
        created_at: Record creation timestamp
        updated_at: Record update timestamp (optional)
    """
    id: int
    name: str
    type: str
    url: str
    description: Optional[str] = None
    category: Optional[str] = None
    active: bool
    priority: int
    custom_source: bool
    metadata_: Optional[Dict[str, Any]] = None
    last_fetched: Optional[datetime] = None
    fetch_interval: int
    total_items: int
    successful_fetches: int
    failed_fetches: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SourceStatsResponse(BaseModel):
    """
    Schema for source statistics responses.
    
    Provides statistical information about source performance
    including fetch success rates and content volume metrics.
    
    Attributes:
        id: Source identifier
        name: Source name
        total_items: Total content items fetched
        successful_fetches: Count of successful fetch attempts
        failed_fetches: Count of failed fetch attempts
        success_rate: Fetch success rate (0.0-1.0)
        last_fetched: Last fetch timestamp (optional)
        avg_items_per_fetch: Average items per successful fetch
    """
    id: int
    name: str
    total_items: int
    successful_fetches: int
    failed_fetches: int
    success_rate: float
    last_fetched: Optional[datetime] = None
    avg_items_per_fetch: float
    
    class Config:
        from_attributes = True