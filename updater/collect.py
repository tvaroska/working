from typing import Optional, Union, List

import uuid
from datetime import datetime
from time import mktime

import httpx
import feedparser
from pydantic import BaseModel, Field

# Common globals
http_client = httpx.Client()

class Article(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    url: str
    title: str
    summary: Optional[str] = None
    content: Optional[Union[str, bytes]] = None
    mime_type: str

    def to_xml(self):

        content = f'<TITLE>{self.title}</TITLE>'
        if self.summary:
            content += f'\n<SUMMARY>{self.summary}</SUMMARY>'
        return f'<ARTICLE ID={self.id}\n' + content + '\n</ARTICLE>'

"""

Scraper
- get header
    - decide on media_type
    - get last_updated
- get the content (except youtube)

don't need to scrape the content 
prompt = [
    ("user", [{"type": "text", "text": "What is title and who is author of the paper?"}, 
              {"type": "media", "mime_type": "text/html", "file_uri": 'https://arxiv.org/html/2404.11553v1'}])
]

works only for robot allowed URLs (not for twitter for example)

"""

def get_media_type(feed_url: str) -> Optional[str]:
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

    with httpx.Client() as h:
        head = h.head(feed_url).headers
        if 'Content-Type' in head:
            return head['Content-Type'].split(';')[0]

    return None

def new_articles(feeds: List[str], starting_point: datetime) -> List[Article]:
    """
    Function will check RSS feeds in feeds and return all entries which are new from starting_point

    Args:
        feeds: List of RSS feed URLs to check
        starting_point: datetime object representing the cutoff point for new articles

    Returns:
        List of RSSEntry objects that were published after the starting_point
    """
    new_entries = []
    
    for feed_url in feeds:
        feed = feedparser.parse(feed_url)
            
        # Check if feed parsing was successful
        if 'bozo_exception' in feed:
            print(f"Warning: Error parsing feed {feed_url}: {feed.bozo_exception}")
            continue
    
        for entry in feed.entries:
            # Get published date from the entry
            if hasattr(entry, 'published_parsed'):
                pub_date = datetime.fromtimestamp(mktime(entry.published_parsed))
            elif hasattr(entry, 'updated_parsed'):
                pub_date = datetime.fromtimestamp(mktime(entry.updated_parsed))
            else:
                continue  # Skip if no date available
                    
            # Check if article is newer than starting_point
            if pub_date > starting_point:
                if hasattr(entry, 'link'):
                    # Determine media type based on feed URL and entry content
                    media_type = get_media_type(entry.link)
                    # Extract summary, handling potential missing field
                    summary = None
                    if hasattr(entry, 'summary'):
                        summary = entry.summary
                        
                    # Create RSSEntry object
                    rss_entry = Article(
                        title=entry.title,
                        url=entry.link,
                        mime_type=media_type,
                        summary=summary
                    )
                    new_entries.append(rss_entry)

    return new_entries
