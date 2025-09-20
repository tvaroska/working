"""
RSS feed processing service

This service handles fetching and parsing RSS feeds.
Will be implemented using a new RSS library to be selected.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
import feedparser
import httpx
import asyncio
from urllib.parse import urljoin, urlparse
import bleach
from dateutil import parser as date_parser
import logging

logger = logging.getLogger(__name__)


class RSSService:
    """
    Service for RSS feed processing and management.
    
    Handles RSS feed fetching, parsing, and content extraction.
    Provides functionality for feed validation, conditional requests,
    and content deduplication through hash generation.
    
    This service will integrate with a new RSS library to be selected.
    Current implementation contains placeholder methods with comprehensive
    TODO comments for future implementation.
    """
    
    def __init__(self):
        """
        Initialize RSS service with HTTP client and parsing configuration.
        
        Sets up the RSS parsing library, HTTP client with proper headers,
        timeout settings, and retry configuration for reliable feed fetching.
        """
        self.user_agent = "Updater RSS Reader 1.0"
        self.timeout = 30
        self.max_retries = 3
        
        # Configure feedparser
        feedparser.USER_AGENT = self.user_agent
        
        # HTTP client for conditional requests
        self.http_client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={"User-Agent": self.user_agent},
            follow_redirects=True
        )
    
    async def fetch_feed(self, url: str, etag: Optional[str] = None, 
                        last_modified: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch and parse RSS feed from URL with conditional requests.
        
        Performs HTTP request to fetch RSS feed content, supporting
        conditional requests to minimize bandwidth and processing.
        Handles various RSS/Atom formats and encoding issues.
        
        Args:
            url: RSS feed URL to fetch
            etag: ETag from previous fetch for conditional requests
            last_modified: Last-Modified header from previous fetch
            
        Returns:
            Dict containing:
                - status: 'success', 'not_modified', 'error'
                - items: List of parsed feed items
                - feed_info: Feed metadata (title, description, etc.)
                - etag: New ETag for next conditional request
                - last_modified: New Last-Modified for next request
                - error: Error message if status is 'error'
                
        TODO: Implement RSS fetching with:
        - Conditional requests using ETag and If-Modified-Since headers
        - Error handling for HTTP errors, timeouts, parsing errors
        - Support for RSS 2.0, RSS 1.0, and Atom feeds
        - Proper encoding detection and handling
        - Timeout and retry logic with exponential backoff
        - Rate limiting to respect server resources
        """
        try:
            # Prepare headers for conditional requests
            headers = {}
            if etag:
                headers["If-None-Match"] = etag
            if last_modified:
                headers["If-Modified-Since"] = last_modified
            
            # Fetch the feed with retries
            for attempt in range(self.max_retries):
                try:
                    response = await self.http_client.get(url, headers=headers)
                    
                    # Handle not modified response
                    if response.status_code == 304:
                        return {
                            "status": "not_modified",
                            "items": [],
                            "feed_info": {},
                            "etag": etag,
                            "last_modified": last_modified,
                            "error": None
                        }
                    
                    # Check for successful response
                    response.raise_for_status()
                    
                    # Parse the feed
                    feed = feedparser.parse(response.content)
                    
                    # Check for feed parsing errors
                    if feed.bozo and hasattr(feed, 'bozo_exception'):
                        logger.warning(f"Feed parsing warning for {url}: {feed.bozo_exception}")
                    
                    # Extract feed info
                    feed_info = {
                        "title": getattr(feed.feed, 'title', 'Unknown Feed'),
                        "description": getattr(feed.feed, 'description', ''),
                        "link": getattr(feed.feed, 'link', ''),
                        "language": getattr(feed.feed, 'language', 'en'),
                        "generator": getattr(feed.feed, 'generator', ''),
                        "last_build_date": getattr(feed.feed, 'updated', None)
                    }
                    
                    # Parse feed items
                    items = await self.parse_feed_items({"entries": feed.entries, "feed": feed.feed})\n                    
                    return {
                        "status": "success",
                        "items": items,
                        "feed_info": feed_info,
                        "etag": response.headers.get("etag"),
                        "last_modified": response.headers.get("last-modified"),
                        "error": None
                    }
                    
                except httpx.RequestError as e:
                    if attempt == self.max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    
        except Exception as e:
            logger.error(f"Error fetching feed {url}: {str(e)}")
            return {
                "status": "error",
                "items": [],
                "feed_info": {},
                "etag": None,
                "last_modified": None,
                "error": str(e)
            }
    
    async def parse_feed_items(self, feed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse individual items from raw feed data.
        
        Extracts and normalizes individual content items from parsed
        RSS/Atom feed data, handling various formats and field mappings.
        
        Args:
            feed_data: Raw feed data from RSS parser library
            
        Returns:
            List[Dict]: Parsed content items with normalized structure:
                - title: Cleaned article title
                - url: Canonical article URL
                - author: Author name (if available)
                - content: Full article content or summary
                - published_at: Publication datetime
                - guid: Unique identifier for deduplication
                - metadata: Additional item-specific data
                
        TODO: Implement item parsing with:
        - Title extraction and HTML tag cleaning
        - Content/summary extraction with preference order
        - Author information from various feed fields
        - Publication date parsing with timezone handling
        - URL extraction, validation, and canonicalization
        - GUID/ID extraction for reliable deduplication
        - Metadata extraction (categories, tags, etc.)
        """
        items = []
        entries = feed_data.get("entries", [])
        
        for entry in entries:
            try:
                # Extract title and clean HTML
                title = getattr(entry, 'title', 'Untitled')
                title = bleach.clean(title, tags=[], strip=True).strip()
                
                # Extract URL
                url = getattr(entry, 'link', '')
                if not url:
                    continue  # Skip entries without URLs
                
                # Extract author
                author = None
                if hasattr(entry, 'author'):
                    author = entry.author
                elif hasattr(entry, 'author_detail') and entry.author_detail:
                    author = entry.author_detail.get('name', '')
                
                # Extract content/summary
                content = ""
                if hasattr(entry, 'content') and entry.content:
                    # Use first content item
                    content = entry.content[0].value if entry.content else ""
                elif hasattr(entry, 'summary'):
                    content = entry.summary
                elif hasattr(entry, 'description'):
                    content = entry.description
                
                # Clean content HTML but preserve some structure
                if content:
                    content = bleach.clean(
                        content, 
                        tags=['p', 'br', 'strong', 'em', 'ul', 'ol', 'li'],
                        strip=True
                    ).strip()
                
                # Extract publication date
                published_at = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        published_at = datetime(*entry.published_parsed[:6])
                    except (TypeError, ValueError):
                        pass
                elif hasattr(entry, 'published'):
                    try:
                        published_at = date_parser.parse(entry.published)
                    except (ValueError, TypeError):
                        pass
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    try:
                        published_at = datetime(*entry.updated_parsed[:6])
                    except (TypeError, ValueError):
                        pass
                
                # Extract GUID for deduplication
                guid = getattr(entry, 'id', '') or getattr(entry, 'guid', '') or url
                
                # Extract categories/tags
                categories = []
                if hasattr(entry, 'tags') and entry.tags:
                    categories = [tag.term for tag in entry.tags if hasattr(tag, 'term')]
                
                # Build metadata
                metadata = {
                    "guid": guid,
                    "categories": categories,
                    "source_url": url,
                    "language": getattr(feed_data.get("feed", {}), 'language', 'en')
                }
                
                if published_at:
                    metadata["published_at"] = published_at.isoformat()
                
                item = {
                    "title": title,
                    "url": url,
                    "author": author,
                    "content": content,
                    "published_at": published_at,
                    "guid": guid,
                    "metadata": metadata
                }
                
                items.append(item)
                
            except Exception as e:
                logger.warning(f"Error parsing feed item: {str(e)}")
                continue
        
        return items
    
    async def validate_feed_url(self, url: str) -> Dict[str, Any]:
        """
        Validate RSS feed URL and extract metadata.
        
        Performs comprehensive validation of RSS feed URL including
        accessibility check, format validation, and metadata extraction.
        
        Args:
            url: RSS feed URL to validate
            
        Returns:
            Dict containing validation results:
                - valid: Boolean indicating if feed is valid
                - feed_title: Feed title if valid
                - feed_description: Feed description if available
                - feed_language: Feed language if specified
                - item_count: Number of items in feed
                - update_frequency: Estimated update frequency
                - error: Error message if validation failed
                
        TODO: Implement URL validation with:
        - HTTP accessibility check with proper error handling
        - RSS/Atom format validation using parser
        - Feed metadata extraction (title, description, language)
        - Update frequency estimation from item timestamps
        - Security validation (URL safety, redirect handling)
        - Feed health assessment (recent updates, content quality)
        """
        try:
            # Fetch and parse the feed
            result = await self.fetch_feed(url)
            
            if result["status"] == "error":
                return {
                    "valid": False,
                    "feed_title": None,
                    "feed_description": None,
                    "feed_language": None,
                    "item_count": 0,
                    "update_frequency": None,
                    "error": result["error"]
                }
            
            feed_info = result["feed_info"]
            items = result["items"]
            
            # Estimate update frequency from item timestamps
            update_frequency = None
            if len(items) >= 2:
                timestamps = []
                for item in items[:10]:  # Check first 10 items
                    if item.get("published_at"):
                        timestamps.append(item["published_at"])
                
                if len(timestamps) >= 2:
                    timestamps.sort(reverse=True)
                    # Calculate average time between posts
                    total_diff = (timestamps[0] - timestamps[-1]).total_seconds()
                    avg_interval = total_diff / (len(timestamps) - 1)
                    
                    if avg_interval < 3600:  # Less than 1 hour
                        update_frequency = "hourly"
                    elif avg_interval < 86400:  # Less than 1 day
                        update_frequency = "daily"
                    elif avg_interval < 604800:  # Less than 1 week
                        update_frequency = "weekly"
                    else:
                        update_frequency = "monthly"
            
            return {
                "valid": True,
                "feed_title": feed_info.get("title"),
                "feed_description": feed_info.get("description"),
                "feed_language": feed_info.get("language"),
                "item_count": len(items),
                "update_frequency": update_frequency,
                "error": None
            }
            
        except Exception as e:
            return {
                "valid": False,
                "feed_title": None,
                "feed_description": None,
                "feed_language": None,
                "item_count": 0,
                "update_frequency": None,
                "error": str(e)
            }
    
    def generate_content_hash(self, title: str, url: str, published_at: Optional[datetime] = None) -> str:
        """
        Generate SHA-256 hash for content deduplication.
        
        Creates a consistent hash value for content items to enable
        efficient deduplication across feeds and prevent duplicate
        content storage.
        
        Args:
            title: Content title (normalized and trimmed)
            url: Content URL (canonical form)
            published_at: Publication timestamp (optional for stability)
            
        Returns:
            str: SHA-256 hash string for deduplication indexing
            
        Note:
            Hash includes normalized title and URL for consistency.
            Publication timestamp is optional to handle feeds with
            missing or inconsistent date information.
        """
        # Create consistent hash for deduplication
        hash_input = f"{title.strip().lower()}|{url}"
        if published_at:
            hash_input += f"|{published_at.isoformat()}"
        
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
    
    async def get_feed_info(self, url: str) -> Dict[str, Any]:
        """
        Get RSS feed metadata without processing all items.
        
        Fetches and extracts basic feed information for preview
        and configuration purposes without the overhead of parsing
        all feed items.
        
        Args:
            url: RSS feed URL to inspect
            
        Returns:
            Dict containing feed metadata:
                - title: Feed title
                - description: Feed description
                - language: Feed language code
                - link: Feed website URL
                - last_build_date: Last build/update timestamp
                - update_frequency: Estimated update frequency
                - item_count: Approximate number of items
                - generator: Feed generator software
                
        TODO: Implement feed info extraction with:
        - Lightweight feed parsing for metadata only
        - Error handling for malformed feeds
        - Caching for frequently accessed feeds
        - Fallback values for missing metadata
        """
        try:
            # Use a lightweight approach - just fetch headers first
            response = await self.http_client.head(url)
            if response.status_code not in [200, 301, 302]:
                # If HEAD fails, try GET with small timeout
                response = await self.http_client.get(url, timeout=10)
                response.raise_for_status()
            
            # Parse just the feed metadata
            feed = feedparser.parse(url)
            
            feed_info = {
                "title": getattr(feed.feed, 'title', 'Unknown Feed'),
                "description": getattr(feed.feed, 'description', ''),
                "language": getattr(feed.feed, 'language', 'en'),
                "link": getattr(feed.feed, 'link', ''),
                "last_build_date": getattr(feed.feed, 'updated', None),
                "update_frequency": None,
                "item_count": len(feed.entries),
                "generator": getattr(feed.feed, 'generator', '')
            }
            
            return feed_info
            
        except Exception as e:
            logger.error(f"Error getting feed info for {url}: {str(e)}")
            return {
                "title": "Unknown Feed",
                "description": "",
                "language": "en",
                "link": "",
                "last_build_date": None,
                "update_frequency": None,
                "item_count": 0,
                "generator": "",
                "error": str(e)
            }