from typing import Optional, Union, List
import asyncio

import uuid
from datetime import datetime
from time import mktime

import httpx
import feedparser
from pydantic import BaseModel, Field

# Common globals
http_client = httpx.AsyncClient()

class Article(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    url: str
    title: str
    short_summary: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[Union[str, bytes]] = None
    mime_type: str

    def to_xml(self):

        content = f'<TITLE>{self.title}</TITLE>'
        if self.summary:
            content += f'\n<SUMMARY>{self.summary}</SUMMARY>'
        return f'<ARTICLE ID={self.id}\n' + content + '\n</ARTICLE>'

async def get_media_type(feed_url: str) -> Optional[str]:
    """
    Determine the media type of an RSS entry based on the feed URL and entry content.
    
    Args:
        feed_url: URL of the RSS feed
        entry: feedparser entry object
    
    Returns:
        Optional[str]: Media type if detected, None otherwise
    """
    # Check for youtube content
    if 'youtube.com' in feed_url:
        return 'video/vnd.youtube.yt'

    head = await http_client.head(feed_url).headers
    if 'Content-Type' in head:
        return head['Content-Type'].split(';')[0]

    return None

async def get_article(entry, starting_point) -> Article:
    # Get published date from the entry
    if hasattr(entry, 'published_parsed'):
        pub_date = datetime.fromtimestamp(mktime(entry.published_parsed))
    elif hasattr(entry, 'updated_parsed'):
        pub_date = datetime.fromtimestamp(mktime(entry.updated_parsed))
    else:
        return None

    # Check if article is newer than starting_point
    if pub_date > starting_point:
        if hasattr(entry, 'link'):
        # Determine media type based on feed URL and entry content
            # Check for youtube content
            media_type = None
            if 'youtube.com' in entry.link:
               media_type = 'video/vnd.youtube.yt'
            else:
                head = (await http_client.head(entry.link)).headers
                if 'Content-Type' in head:
                    media_type = head['Content-Type'].split(';')[0]
        else:
            # No link - no article
            return None

        # Extract description as summary, handling potential missing field
        summary = None
        if hasattr(entry, 'description'):
            summary = entry.description

        return Article(
            title=entry.title,
            url=entry.link,
            mime_type=media_type,
            summary=summary
        )
    else:
        return None


async def new_articles(feeds: List[str], starting_point: datetime) -> List[Article]:
    """
    Function will check RSS feeds in feeds and return all entries which are new from starting_point

    Args:
        feeds: List of RSS feed URLs to check
        starting_point: datetime object representing the cutoff point for new articles

    Returns:
        List of Article objects that were published after the starting_point
    """
    tasks = []
    for feed_url in feeds:
        feed = feedparser.parse(feed_url)

        # Check if feed parsing was successful
        if 'bozo_exception' in feed:
            print(f"Warning: Error parsing feed {feed_url}: {feed.bozo_exception}")
            continue
    
        tasks += [get_article(entry, starting_point) for entry in feed.entries]

    response = await asyncio.gather(*tasks)
    return [article for article in response if article]