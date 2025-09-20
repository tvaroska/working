"""
Content management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from ..database import get_db
from ..services.content_service import ContentService

logger = logging.getLogger(__name__)

from ..models.content import Content
from ..schemas.content import (
    ContentResponse, 
    ContentCreate, 
    ContentUpdate, 
    ContentFeedResponse,
    ContentActionRequest
)
from ..models.content import Content

router = APIRouter()


@router.get("/feed", response_model=ContentFeedResponse)
async def get_content_feed(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    category: Optional[str] = None,
    saved_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get paginated content feed for the main interface.
    
    Retrieves a paginated list of content items with filtering options.
    Content is ordered by AI priority and recency for optimal user experience.
    
    Args:
        page: Page number (1-based, minimum 1)
        per_page: Items per page (1-100, default 50)
        category: Filter by content category (optional)
        saved_only: Show only saved content if True
        db: Database session dependency
        
    Returns:
        ContentFeedResponse: Paginated content with navigation metadata
        
    TODO: Implement content retrieval with:
    - Efficient pagination using database offset/limit
    - Category filtering with source table joins
    - Saved content filtering for single-user MVP
    - Sorting by AI priority score and published date
    - Processing status filtering (prefer processed content)
    """
    try:
        content_service = ContentService(db)
        result = await content_service.get_content_feed(
            page=page,
            per_page=per_page,
            category=category,
            saved_only=saved_only
        )
        
        return ContentFeedResponse(
            items=result["items"],
            total=result["total"],
            page=result["page"],
            per_page=result["per_page"],
            has_next=result["has_next"],
            has_prev=result["has_prev"]
        )
    except Exception as e:
        logger.error(f"Error getting content feed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/latest", response_model=List[ContentResponse])
async def get_latest_content(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get latest content items ordered by recency.
    
    Retrieves the most recently published or added content items,
    prioritizing AI-processed content for better user experience.
    
    Args:
        limit: Maximum number of items to return (1-100, default 20)
        db: Database session dependency
        
    Returns:
        List[ContentResponse]: Latest content items with full metadata
        
    TODO: Implement latest content retrieval with:
    - Ordering by published_at desc, created_at desc
    - Priority for AI-processed content
    - Filtering out dismissed content
    - Source information inclusion
    """
    try:
        content_service = ContentService(db)
        content = await content_service.get_latest_content(limit=limit)
        return content
    except Exception as e:
        logger.error(f"Error getting latest content: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{content_id}", response_model=ContentResponse)
async def get_content(content_id: int, db: Session = Depends(get_db)):
    """
    Get specific content item by ID.
    
    Retrieves a single content item with all metadata including
    AI summary, user interaction status, and source information.
    
    Args:
        content_id: ID of the content item to retrieve
        db: Database session dependency
        
    Returns:
        ContentResponse: Complete content item data
        
    Raises:
        HTTPException: 404 if content item not found
        
    TODO: Implement content retrieval by ID with:
    - Database query with source table join
    - Error handling for non-existent content
    - View count increment on successful retrieval
    """
    try:
        content = db.query(Content).filter(Content.id == content_id).first()
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")
        
        # Increment view count
        content.view_count = (content.view_count or 0) + 1
        db.commit()
        db.refresh(content)
        
        return content
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting content {content_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{content_id}/actions")
async def content_action(
    content_id: int,
    action: ContentActionRequest,
    db: Session = Depends(get_db)
):
    """
    Perform user action on content item.
    
    Handles user interactions with content including saving,
    dismissing, and view tracking. Updates appropriate database
    fields and timestamps.
    
    Args:
        content_id: ID of the content item to act upon
        action: Action request containing action type
        db: Database session dependency
        
    Returns:
        Dict: Action result with success status and updated values
        
    Raises:
        HTTPException: 404 if content not found, 400 for invalid actions
        
    TODO: Implement content actions with:
    - save/unsave: Toggle saved status and update timestamp
    - dismiss: Mark as dismissed (hidden from feed)
    - view: Increment view counter
    - Validation of action types and content existence
    """
    try:
        content_service = ContentService(db)
        success = await content_service.update_content_action(
            content_id=content_id,
            action=action.action
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Content not found")
        
        return {"success": True, "action": action.action, "content_id": content_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing action on content {content_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/saved", response_model=List[ContentResponse])
async def get_saved_content(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get paginated saved content items.
    
    Retrieves content items that the user has marked as saved,
    ordered by save date (most recently saved first).
    
    Args:
        page: Page number (1-based, minimum 1)
        per_page: Items per page (1-100, default 50)
        db: Database session dependency
        
    Returns:
        List[ContentResponse]: Saved content items with full metadata
        
    TODO: Implement saved content retrieval with:
    - Filter for saved=True
    - Pagination with proper offset/limit
    - Ordering by updated_at desc (save date)
    - Source information inclusion
    """
    try:
        content_service = ContentService(db)
        result = await content_service.get_saved_content(
            page=page,
            per_page=per_page
        )
        return result["items"]
    except Exception as e:
        logger.error(f"Error getting saved content: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/search", response_model=List[ContentResponse])
async def search_content(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Search content by text query.
    
    Performs full-text search across content titles, AI summaries,
    and tags. Results are ranked by relevance and AI priority.
    
    Args:
        q: Search query string (minimum 1 character)
        limit: Maximum number of results (1-100, default 20)
        db: Database session dependency
        
    Returns:
        List[ContentResponse]: Matching content ordered by relevance
        
    TODO: Implement content search with:
    - Full-text search on title and AI summary text
    - Tag-based search within AI summary tags
    - Priority-based ranking using AI priority scores
    - Fuzzy matching for typos
    - Search result highlighting
    """
    try:
        content_service = ContentService(db)
        content = await content_service.search_content(query=q, limit=limit)
        return content
    except Exception as e:
        logger.error(f"Error searching content: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/", response_model=ContentResponse)
async def create_content(content: ContentCreate, db: Session = Depends(get_db)):
    """
    Create new content item (for testing/manual addition).
    
    Allows manual creation of content items for testing purposes
    or special content addition outside of RSS feeds.
    
    Args:
        content: Content creation data with title, URL, and metadata
        db: Database session dependency
        
    Returns:
        ContentResponse: Created content item with generated ID
        
    Raises:
        HTTPException: 400 for validation errors, 409 for duplicates
        
    TODO: Implement content creation with:
    - Data validation and sanitization
    - Content hash generation for deduplication
    - Duplicate detection and handling
    - Initial processing status setup
    """
    try:
        content_service = ContentService(db)
        
        # Convert Pydantic model to dict for service
        content_data = {
            "title": content.title,
            "url": str(content.url),
            "author": content.author,
            "content": content.original_content,
            "published_at": content.published_at,
            "metadata": content.metadata or {}
        }
        
        created_content = await content_service.create_content(
            content_data=content_data,
            source_id=content.source_id
        )
        
        return created_content
    except Exception as e:
        logger.error(f"Error creating content: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{content_id}", response_model=ContentResponse)
async def update_content(
    content_id: int,
    content_update: ContentUpdate,
    db: Session = Depends(get_db)
):
    """
    Update existing content item.
    
    Allows updating content fields including AI summary data,
    processing status, and user interaction states.
    
    Args:
        content_id: ID of the content item to update
        content_update: Partial update data for the content item
        db: Database session dependency
        
    Returns:
        ContentResponse: Updated content item with new values
        
    Raises:
        HTTPException: 404 if content not found, 400 for validation errors
        
    TODO: Implement content updates with:
    - Partial field updates using provided data only
    - Validation of update data
    - Timestamp updates for modified fields
    - Error handling for non-existent content
    """
    try:
        content = db.query(Content).filter(Content.id == content_id).first()
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")
        
        # Update fields that are provided
        update_data = content_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(content, field, value)
        
        db.commit()
        db.refresh(content)
        
        return content
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating content {content_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")