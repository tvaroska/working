"""
RSS source management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from ..database import get_db
from ..services.rss_service import RSSService
from ..services.content_service import ContentService

logger = logging.getLogger(__name__)

from ..models.source import Source
from ..models.content import Content
from ..schemas.source import (
    SourceResponse, 
    SourceCreate, 
    SourceUpdate,
    SourceStatsResponse
)
from ..models.source import Source

router = APIRouter()


@router.get("/", response_model=List[SourceResponse])
async def get_sources(
    active_only: bool = True,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all RSS sources with filtering options.
    
    Retrieves list of RSS sources configured in the system,
    with options to filter by active status and category.
    
    Args:
        active_only: Include only active sources if True (default)
        category: Filter by source category (optional)
        db: Database session dependency
        
    Returns:
        List[SourceResponse]: List of sources with full metadata
        
    TODO: Implement source retrieval with:
    - Active/inactive filtering using active column
    - Category filtering with case-insensitive matching
    - Sorting by priority desc, name asc
    - Statistics inclusion (success rates, item counts)
    """
    try:
        query = db.query(Source)
        
        if active_only:
            query = query.filter(Source.active == True)
        
        if category:
            query = query.filter(Source.category.ilike(f"%{category}%"))
        
        sources = query.order_by(
            Source.priority.desc(),
            Source.name.asc()
        ).all()
        
        return sources
    except Exception as e:
        logger.error(f"Error getting sources: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats", response_model=List[SourceStatsResponse])
async def get_source_stats(db: Session = Depends(get_db)):
    """
    Get performance statistics for all sources.
    
    Provides detailed statistics about source performance including
    fetch success rates, content volume, and reliability metrics.
    
    Args:
        db: Database session dependency
        
    Returns:
        List[SourceStatsResponse]: Statistics for each source including
        success rates, item counts, and performance metrics
        
    TODO: Implement source statistics with:
    - Calculated success rates from fetch attempts
    - Content volume metrics (total items, items per fetch)
    - Last fetch times and frequency analysis
    - Performance trends and reliability indicators
    """
    try:
        sources = db.query(Source).all()
        stats = []
        
        for source in sources:
            total_fetches = source.successful_fetches + source.failed_fetches
            success_rate = (
                source.successful_fetches / total_fetches 
                if total_fetches > 0 else 0.0
            )
            avg_items_per_fetch = (
                source.total_items / source.successful_fetches 
                if source.successful_fetches > 0 else 0.0
            )
            
            stats.append({
                "id": source.id,
                "name": source.name,
                "total_items": source.total_items,
                "successful_fetches": source.successful_fetches,
                "failed_fetches": source.failed_fetches,
                "success_rate": success_rate,
                "last_fetched": source.last_fetched,
                "avg_items_per_fetch": avg_items_per_fetch
            })
        
        return stats
    except Exception as e:
        logger.error(f"Error getting source stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(source_id: int, db: Session = Depends(get_db)):
    """
    Get specific RSS source by ID.
    
    Retrieves detailed information about a single RSS source
    including configuration, statistics, and status.
    
    Args:
        source_id: ID of the source to retrieve
        db: Database session dependency
        
    Returns:
        SourceResponse: Complete source data with metadata
        
    Raises:
        HTTPException: 404 if source not found
        
    TODO: Implement source retrieval by ID with:
    - Database query with error handling
    - Statistics calculation and inclusion
    - Recent fetch status information
    """
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        return source
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/", response_model=SourceResponse)
async def create_source(source: SourceCreate, db: Session = Depends(get_db)):
    """
    Create new RSS source.
    
    Adds a new RSS source to the system with validation and
    initial configuration setup.
    
    Args:
        source: Source creation data with URL, name, and settings
        db: Database session dependency
        
    Returns:
        SourceResponse: Created source with generated ID and metadata
        
    Raises:
        HTTPException: 400 for validation errors, 409 for duplicate URLs
        
    TODO: Implement source creation with:
    - RSS URL validation and accessibility testing
    - Feed format validation (RSS/Atom)
    - Duplicate URL detection
    - Initial fetch and metadata extraction
    - Monitoring setup and scheduling
    """
    try:
        # Validate RSS URL first
        rss_service = RSSService()
        validation = await rss_service.validate_feed_url(str(source.url))
        
        if not validation["valid"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid RSS feed: {validation['error']}"
            )
        
        # Check for duplicate URLs
        existing = db.query(Source).filter(Source.url == str(source.url)).first()
        if existing:
            raise HTTPException(status_code=409, detail="Source URL already exists")
        
        # Create source with feed metadata
        new_source = Source(
            name=source.name,
            url=str(source.url),
            description=source.description,
            category=source.category,
            type=source.type,
            priority=source.priority,
            fetch_interval=source.fetch_interval,
            metadata_=source.metadata_ or {},
            active=True,
            custom_source=True
        )
        
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        
        return new_source
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating source: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: int,
    source_update: SourceUpdate,
    db: Session = Depends(get_db)
):
    """
    Update existing RSS source.
    
    Updates source configuration including URL, settings,
    and monitoring parameters.
    
    Args:
        source_id: ID of the source to update
        source_update: Partial update data for the source
        db: Database session dependency
        
    Returns:
        SourceResponse: Updated source with new values
        
    Raises:
        HTTPException: 404 if source not found, 400 for validation errors
        
    TODO: Implement source updates with:
    - Partial field updates using provided data only
    - URL change validation and testing
    - Monitoring schedule updates
    - Configuration validation
    """
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # If URL is being changed, validate it
        if source_update.url and str(source_update.url) != source.url:
            rss_service = RSSService()
            validation = await rss_service.validate_feed_url(str(source_update.url))
            
            if not validation["valid"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid RSS feed: {validation['error']}"
                )
        
        # Update fields that are provided
        update_data = source_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == "url":
                value = str(value)
            setattr(source, field, value)
        
        db.commit()
        db.refresh(source)
        
        return source
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating source {source_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{source_id}")
async def delete_source(source_id: int, db: Session = Depends(get_db)):
    """
    Delete RSS source.
    
    Removes source from the system with options for content
    handling and cleanup.
    
    Args:
        source_id: ID of the source to delete
        db: Database session dependency
        
    Returns:
        Dict: Deletion confirmation with cleanup details
        
    Raises:
        HTTPException: 404 if source not found
        
    TODO: Implement source deletion with:
    - Soft delete option (mark as inactive)
    - Hard delete with content cleanup
    - Archive related content items
    - Stop monitoring and background tasks
    """
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Get content count for reporting
        content_count = db.query(Content).filter(
            Content.source_id == source_id
        ).count()
        
        # Soft delete - mark as inactive instead of hard delete
        source.active = False
        db.commit()
        
        return {
            "message": "Source deactivated successfully",
            "source_id": source_id,
            "content_items_affected": content_count
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting source {source_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{source_id}/fetch")
async def trigger_source_fetch(source_id: int, db: Session = Depends(get_db)):
    """
    Manually trigger RSS fetch for specific source.
    
    Initiates an immediate fetch operation for the specified source,
    bypassing the normal scheduled fetch cycle.
    
    Args:
        source_id: ID of the source to fetch
        db: Database session dependency
        
    Returns:
        Dict: Fetch trigger confirmation with job status
        
    Raises:
        HTTPException: 404 if source not found, 400 if source inactive
        
    TODO: Implement manual fetch trigger with:
    - Background job queuing for fetch operation
    - Job status tracking and reporting
    - Rate limiting to prevent abuse
    - Source status validation (must be active)
    """
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        if not source.active:
            raise HTTPException(status_code=400, detail="Source is not active")
        
        # TODO: Queue background job for RSS fetch
        # For now, return success message
        return {
            "message": "Fetch triggered successfully",
            "source_id": source_id,
            "source_name": source.name,
            "status": "queued"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering fetch for source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{source_id}/content", response_model=List[dict])
async def get_source_content(
    source_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get recent content from specific source.
    
    Retrieves content items associated with a particular RSS source,
    ordered by recency for source monitoring and management.
    
    Args:
        source_id: ID of the source to get content from
        limit: Maximum number of items to return (1-100, default 20)
        db: Database session dependency
        
    Returns:
        List[dict]: Recent content items from the source
        
    Raises:
        HTTPException: 404 if source not found
        
    TODO: Implement source-specific content retrieval with:
    - Filter content by source_id
    - Ordering by published_at desc, created_at desc
    - Include processing status and AI summary data
    - Source validation and error handling
    """
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        content = db.query(Content).filter(
            Content.source_id == source_id
        ).order_by(
            Content.published_at.desc(),
            Content.created_at.desc()
        ).limit(limit).all()
        
        return content
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting content for source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")