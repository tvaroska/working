import asyncio
import json
import uuid
import structlog
import logging
import argparse
from datetime import datetime, timedelta
from time import mktime
from typing import List, Optional, Union

import feedparser
import httpx
from google import genai
from google.genai.errors import ClientError, ServerError
from google.genai.types import GenerateContentConfig, Part
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.EventRenamer("event"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.KeyValueRenderer(key_order=["level", "event", "num"])
#        structlog.processors.JSONRenderer(key_order=["level", "event", "num"]),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)
logger = structlog.get_logger()

class Article(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    url: str
    title: str
    short_summary: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[Union[str, bytes]] = None
    mime_type: str


class Summary(BaseModel):
    short: str = Field(description="Tweet like summary of the article")
    long: str = Field(
        description="Summary of the article in form of independent text. Length of the text should be 250 words. Audience of this new version will consume it on the mobile phone during their commute. Respond in Markdown, each point as header3 and short support text for point."
    )


class ResourceExaused(ClientError):
    pass


gemini = genai.Client(vertexai=True, location="us-central1")


async def get_article(http_client: httpx.AsyncClient, entry, starting_point) -> Article:
    # Get published date from the entry
    if hasattr(entry, "published_parsed"):
        pub_date = datetime.fromtimestamp(mktime(entry.published_parsed))
    elif hasattr(entry, "updated_parsed"):
        pub_date = datetime.fromtimestamp(mktime(entry.updated_parsed))
    else:
        return None

    # Check if article is newer than starting_point
    if pub_date > starting_point:
        if hasattr(entry, "link"):
            # Determine media type based on feed URL and entry content
            # Check for youtube content
            media_type = None
            if "youtube.com" in entry.link:
                media_type = "video/vnd.youtube.yt"
            else:
                try:
                    head = (await http_client.head(entry.link)).headers
                    if "Content-Type" in head:
                        media_type = head["Content-Type"].split(";")[0]
                except httpx.ConnectTimeout:
                    return None
        else:
            # No link - no article
            return None

        # Extract description as summary, handling potential missing field
        summary = None
        if hasattr(entry, "description"):
            summary = entry.description

        return Article(
            title=entry.title, url=entry.link, mime_type=media_type, summary=summary
        )
    else:
        return None


async def new_articles(http_client: httpx.AsyncClient, feeds: List[str], starting_point: datetime) -> List[Article]:
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
        if "bozo_exception" in feed:
            print(f"Warning: Error parsing feed {feed_url}: {feed.bozo_exception}")
            continue

        tasks += [get_article(http_client, entry, starting_point) for entry in feed.entries]

    response = await asyncio.gather(*tasks)
    return [article for article in response if article]


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential_jitter(initial=10, jitter=5),
    retry=retry_if_exception_type(ResourceExaused),
)
async def get_summary(semaphore: asyncio.Semaphore, article: Article, model: str) -> Article:
    bound_logger = logger.bind(location="get_summary", url=article.url)
    bound_logger.info("Processing article")
    async with semaphore:
        try:
            response = await gemini.aio.models.generate_content(
                model=model,
                contents=[
                    Part.from_text("Analyze the article"),
                    Part.from_uri(article.url, mime_type=article.mime_type),
                ],
                config=GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=Summary,
                ),
            )
        except ClientError as e:
            if e.code == 429:
                raise ResourceExaused(code=e.code, response=e.response) from e
            elif e.code == 400:
                bound_logger.info("Block", code=400)
                # cannot load, page blocked for robots
                return None
            else:
                raise ClientError(code=e.code, response=e.response) from e
        except ServerError:
            bound_logger.info("Internal error", code=400)
            return None
        summary = Summary.model_validate_json(response.text)

        article.short_summary = summary.short
        article.summary = summary.long

        bound_logger.info("Success")
        return article


async def main(model: str, input_file: str, output_file: str):
    bound_logger = logger.bind(location="main")
    bound_logger.info("Starting process")
    
    # Create resources within the async context
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        semaphore = asyncio.Semaphore(10)
        
        with open(input_file) as f:
            data = json.load(f)

        bound_logger.info("Read source feeds", num=len(data["feeds"]))

        starting_point = datetime.now() - timedelta(weeks=52)
        articles = await new_articles(http_client, data["feeds"], starting_point=starting_point)

        bound_logger.info("List of articles", num=len(articles), starting_point=starting_point)

        tasks = [get_summary(semaphore, article, model) for article in articles if article]

        updated_articles = await asyncio.gather(*tasks)

        with open(output_file, "w+") as f:
            json.dump(
                {
                    "date": datetime.now().strftime("%b %d %Y"),
                    "updates": [
                        {
                            "title": item.title,
                            "short": item.short_summary,
                            "long": item.summary,
                            "url": item.url,
                        }
                        for item in updated_articles
                        if item
                    ],
                },
                f,
            )


def parse_arguments():
    parser = argparse.ArgumentParser(description="Process RSS feeds and generate article summaries using Gemini API")
    parser.add_argument("--model", type=str, default="gemini-2.0-flash-001", 
                        help="Gemini model to use for summarization (default: gemini-2.0-flash-001)")
    parser.add_argument("--input", type=str, default="settings.json", 
                        help="Input JSON file containing RSS feed URLs (default: settings.json)")
    parser.add_argument("--output", type=str, default="articles.json", 
                        help="Output JSON file to store processed articles (default: articles.json)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    asyncio.run(main(args.model, args.input, args.output))
