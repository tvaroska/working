"""
Content management service

This service handles content processing, storage, and retrieval.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from datetime import datetime, timedelta
import logging
from ..models.content import Content
from ..models.source import Source
from ..schemas.content import ContentCreate, ContentUpdate
from .rss_service import RSSService

logger = logging.getLogger(__name__)


class ContentService:
    """
    Service for content management and processing.
    
    Handles content creation, retrieval, updates, and user interactions.
    Provides business logic for content operations including feed generation,
    search functionality, and AI processing integration.
    
    Attributes:
        db: Database session for data operations
    """
    
    def __init__(self, db: Session):
        """
        Initialize content service with database session.
        
        Args:
            db: SQLAlchemy database session for data operations
        """
        self.db = db
    
    async def create_content(self, content_data: Dict[str, Any], source_id: int) -> Content:
        """
        Create new content item from RSS feed data.
        
        Processes raw content data from RSS feeds and creates a new Content
        record in the database. Handles data validation, hash generation
        for deduplication, and sets initial processing status.
        
        Args:
            content_data: Parsed content data from RSS feed including
                         title, url, author, content, published_at
            source_id: ID of the RSS source this content belongs to
            
        Returns:
            Content: Created content instance with generated ID
            
        TODO: Implement content creation with:
        - Data validation and sanitization
        - Content hash generation for deduplication
        - Duplicate detection and handling
        - Initial processing status setup
        - Metadata extraction and parsing
        """
        try:
            # Generate content hash for deduplication
            rss_service = RSSService()
            content_hash = rss_service.generate_content_hash(
                content_data.get("title", ""),
                content_data.get("url", ""),
                content_data.get("published_at")
            )
            
            # Check for existing content with same hash
            existing = self.db.query(Content).filter(
                Content.content_hash == content_hash
            ).first()
            
            if existing:
                logger.info(f"Duplicate content detected: {content_data.get('title', 'Unknown')}")
                return existing
            
            # Create new content
            content = Content(
                source_id=source_id,
                title=content_data.get("title", "Untitled"),
                url=content_data.get("url", ""),
                author=content_data.get("author"),
                original_content=content_data.get("content", ""),
                published_at=content_data.get("published_at"),
                content_hash=content_hash,
                metadata=content_data.get("metadata", {}),
                processing_status="pending",
                ai_processed=False
            )
            
            self.db.add(content)
            self.db.commit()
            self.db.refresh(content)
            
            logger.info(f"Created content: {content.title} (ID: {content.id})")
            return content
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating content: {str(e)}")
            raise
    
    async def get_content_feed(self, page: int = 1, per_page: int = 50, 
                              category: Optional[str] = None, 
                              saved_only: bool = False) -> Dict[str, Any]:
        """
        Get paginated content feed for the main interface.
        
        Retrieves a paginated list of content items based on filtering
        criteria. Supports category filtering, saved content filtering,
        and proper pagination with metadata.
        
        Args:
            page: Page number (1-based)
            per_page: Number of items per page (max 100)
            category: Filter by content category (optional)
            saved_only: Show only saved content if True
            
        Returns:
            Dict containing:
                - items: List of content items for the page
                - total: Total number of matching items
                - page: Current page number
                - per_page: Items per page
                - has_next: Whether next page exists
                - has_prev: Whether previous page exists
                
        TODO: Implement feed retrieval with:
        - Efficient pagination using offset/limit
        - Category filtering with source joins
        - Saved content filtering for single user
        - Sorting by AI priority and recency
        - Source information inclusion
        - Processing status filtering
        """
        try:
            # Build query
            query = self.db.query(Content).join(Source)
            
            # Apply filters
            if category:
                query = query.filter(Source.category.ilike(f"%{category}%"))
            
            if saved_only:
                query = query.filter(Content.saved == True)
            
            # Filter out dismissed content
            query = query.filter(Content.dismissed == False)
            
            # Order by AI priority (if processed) and recency
            query = query.order_by(
                desc(Content.ai_processed),
                desc(Content.published_at),
                desc(Content.created_at)
            )
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * per_page
            items = query.offset(offset).limit(per_page).all()
            
            # Calculate pagination metadata
            has_next = offset + per_page < total
            has_prev = page > 1
            
            return {
                "items": items,
                "total": total,
                "page": page,
                "per_page": per_page,
                "has_next": has_next,
                "has_prev": has_prev
            }
            
        except Exception as e:
            logger.error(f"Error getting content feed: {str(e)}")
            raise
    
    async def get_latest_content(self, limit: int = 20) -> List[Content]:
        """
        Get latest content items ordered by recency.
        
        Retrieves the most recently published or created content items,
        prioritizing AI-processed content for better user experience.
        
        Args:
            limit: Maximum number of items to return (max 100)
            
        Returns:
            List[Content]: Latest content items ordered by recency
            
        TODO: Implement with:
        - Ordering by published_at desc, created_at desc
        - Priority for AI-processed content
        - Filtering out dismissed content
        - Source information inclusion
        """
        try:
            content = self.db.query(Content).filter(
                Content.dismissed == False
            ).order_by(
                desc(Content.ai_processed),
                desc(Content.published_at),
                desc(Content.created_at)
            ).limit(limit).all()
            
            return content
            
        except Exception as e:
            logger.error(f"Error getting latest content: {str(e)}")
            raise
    
    async def search_content(self, query: str, limit: int = 20) -> List[Content]:
        """
        Search content by text query.
        
        Performs full-text search across content titles, summaries,
        and tags. Results are ranked by relevance and AI priority.
        
        Args:
            query: Search query string (minimum 1 character)
            limit: Maximum number of results to return (max 100)
            
        Returns:
            List[Content]: Matching content items ordered by relevance
            
        TODO: Implement search with:
        - Full-text search on title and AI summary text
        - Tag-based search within AI summary tags
        - Priority-based ranking using AI priority scores
        - Fuzzy matching for typos
        - Search result highlighting
        """
        try:
            # Build search query for title and AI summary
            search_term = f"%{query}%"
            
            content = self.db.query(Content).filter(
                and_(
                    Content.dismissed == False,
                    or_(
                        Content.title.ilike(search_term),
                        Content.original_content.ilike(search_term),
                        Content.ai_summary.op("->>")('text').ilike(search_term)
                    )
                )
            ).order_by(
                desc(Content.ai_processed),
                desc(Content.published_at)
            ).limit(limit).all()
            
            return content
            
        except Exception as e:
            logger.error(f"Error searching content: {str(e)}")
            raise
    
    async def update_content_action(self, content_id: int, action: str) -> bool:
        """
        Update content with user action.
        
        Handles user interactions with content including saving,
        dismissing, and view tracking. Updates appropriate fields
        and timestamps.
        
        Args:
            content_id: ID of the content item to update
            action: Action to perform (save, unsave, dismiss, view)
            
        Returns:
            bool: True if action was successful, False otherwise
            
        TODO: Implement actions:
        - save/unsave: Toggle saved status
        - dismiss: Mark as dismissed (hidden from feed)
        - view: Increment view counter and update timestamp
        - Validation of action types
        - Error handling for non-existent content
        """
        try:
            content = self.db.query(Content).filter(
                Content.id == content_id
            ).first()
            
            if not content:
                logger.warning(f"Content not found: {content_id}")
                return False
            
            if action == "save":
                content.saved = True
            elif action == "unsave":
                content.saved = False
            elif action == "dismiss":
                content.dismissed = True
            elif action == "view":
                content.view_count = (content.view_count or 0) + 1
            else:
                logger.warning(f"Unknown action: {action}")
                return False
            
            self.db.commit()
            self.db.refresh(content)
            
            logger.info(f"Action '{action}' performed on content {content_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error performing action {action} on content {content_id}: {str(e)}")
            raise
    
    async def get_saved_content(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """
        Get paginated saved content items.
        
        Retrieves content items that the user has marked as saved,
        with proper pagination and ordering by save date.
        
        Args:
            page: Page number (1-based)
            per_page: Number of items per page (max 100)
            
        Returns:
            Dict containing paginated saved content with same structure
            as get_content_feed
            
        TODO: Implement saved content retrieval with:
        - Filter for saved=True
        - Ordering by updated_at desc (save date)
        - Pagination with proper metadata
        - Source information inclusion
        """
        try:
            # Query saved content
            query = self.db.query(Content).filter(
                and_(
                    Content.saved == True,
                    Content.dismissed == False
                )
            ).order_by(desc(Content.updated_at))
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * per_page
            items = query.offset(offset).limit(per_page).all()
            
            # Calculate pagination metadata
            has_next = offset + per_page < total
            has_prev = page > 1
            
            return {
                "items": items,
                "total": total,
                "page": page,
                "per_page": per_page,
                "has_next": has_next,
                "has_prev": has_prev
            }
            
        except Exception as e:
            logger.error(f"Error getting saved content: {str(e)}")
            raise
    
    async def update_ai_summary(self, content_id: int, summary_data: Dict[str, Any]) -> bool:
        """
        Update content with AI-generated summary and analysis.
        
        Processes AI-generated summary data and updates the content
        record with structured summary information, tags, and metadata.
        
        Args:
            content_id: ID of the content item to update
            summary_data: AI summary data containing:
                - text: Summary text
                - keyPoints: List of key points
                - sentiment: Sentiment analysis
                - priority: Content priority (1-10)
                - readTime: Estimated reading time
                - tags: List of content tags
                
        Returns:
            bool: True if update was successful, False otherwise
            
        TODO: Implement AI summary updates with:
        - Validation of summary data structure
        - Update processing_status to 'completed'
        - Set ai_processed=True and processed_at timestamp
        - Error handling for invalid summary data
        - Logging for monitoring AI processing
        """
        try:
            content = self.db.query(Content).filter(
                Content.id == content_id
            ).first()
            
            if not content:
                logger.warning(f"Content not found for AI summary update: {content_id}")
                return False
            
            # Validate summary data structure
            required_fields = ['text', 'keyPoints', 'priority']
            if not all(field in summary_data for field in required_fields):
                logger.error(f"Invalid summary data structure: missing fields")
                return False
            
            # Update content with AI summary
            content.ai_summary = summary_data
            content.processing_status = "completed"
            content.ai_processed = True
            content.processed_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(content)
            
            logger.info(f"AI summary updated for content {content_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating AI summary for content {content_id}: {str(e)}")
            raise
    
    async def get_content_for_processing(self, limit: int = 10) -> List[Content]:
        """
        Get content items that need AI processing.
        
        Retrieves content items that are ready for AI summarization
        and analysis, prioritized by source priority and age.
        
        Args:
            limit: Maximum number of items to return for processing
            
        Returns:
            List[Content]: Content items ready for AI processing
            
        TODO: Implement with:
        - Filter by processing_status='pending'
        - Filter by ai_processed=False
        - Join with sources table for priority ordering
        - Order by source.priority desc, created_at asc
        - Exclude content without original_content
        """
        try:
            content = self.db.query(Content).join(Source).filter(
                and_(
                    Content.processing_status == "pending",
                    Content.ai_processed == False,
                    Content.original_content.isnot(None),
                    Content.original_content != ""
                )
            ).order_by(
                desc(Source.priority),
                asc(Content.created_at)
            ).limit(limit).all()
            
            return content
            
        except Exception as e:
            logger.error(f"Error getting content for processing: {str(e)}")
            raise
    
    async def cleanup_old_content(self, days: int = 30) -> int:
        """
        Clean up old content items to manage database size.
        
        Removes or archives old content items based on age threshold,
        while preserving saved content and important items.
        
        Args:
            days: Age threshold in days for content cleanup
            
        Returns:
            int: Number of content items cleaned up
            
        TODO: Implement cleanup with:
        - Delete content older than threshold days
        - Preserve saved content (saved=True)
        - Preserve high-priority content (AI priority > 7)
        - Update source statistics after cleanup
        - Log cleanup operations for monitoring
        - Consider archiving instead of deletion
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Query old content that can be cleaned up
            old_content = self.db.query(Content).filter(
                and_(
                    Content.created_at < cutoff_date,
                    Content.saved == False,  # Don't delete saved content
                    or_(
                        Content.ai_summary.is_(None),
                        True  # Simplified for now - can add priority filtering later
                    )  # Don't delete high priority content
                )
            ).all()
            
            count = len(old_content)
            
            if count > 0:
                for content in old_content:
                    self.db.delete(content)
                
                self.db.commit()
                logger.info(f"Cleaned up {count} old content items")
            
            return count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cleaning up old content: {str(e)}")
            raise