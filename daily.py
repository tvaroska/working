import asyncio
import httpx
import feedparser
import argparse
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path

from google import genai

async def fetch_rss_feed(client: httpx.AsyncClient, url: str) -> Dict[str, Any]:
    """
    Fetch a single RSS feed asynchronously.
    
    Args:
        client: httpx AsyncClient for making requests
        url: RSS feed URL
        
    Returns:
        Dictionary containing feed data or error information
    """
    try:
        response = await client.get(url, timeout=30.0)
        response.raise_for_status()
        content = response.text
        feed = feedparser.parse(content)
        return {
            'url': url,
            'feed': feed,
            'error': None
        }
    except Exception as e:
        return {
            'url': url,
            'feed': None,
            'error': str(e)
        }


def sanitize_filename(title: str, max_length: int = 100) -> str:
    """
    Convert a title into a safe filename.

    Args:
        title: Article title
        max_length: Maximum length of filename

    Returns:
        Sanitized filename string
    """
    # Remove invalid characters
    safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
    # Replace spaces and special chars with underscores
    safe_title = re.sub(r'[\s]+', '_', safe_title)
    # Remove leading/trailing underscores and dots
    safe_title = safe_title.strip('._')
    # Limit length
    if len(safe_title) > max_length:
        safe_title = safe_title[:max_length].rstrip('._')
    return safe_title or 'untitled'


def filter_entries_by_day(feed: feedparser.FeedParserDict, target_day: str) -> List[Dict[str, Any]]:
    """
    Filter RSS feed entries by a specific day.

    Args:
        feed: Parsed RSS feed
        target_day: Target day in format 'YYYY-MM-DD'

    Returns:
        List of entries that match the target day
    """
    filtered_entries = []
    target_date = datetime.strptime(target_day, '%Y-%m-%d').date()
    
    for entry in feed.entries:
        # Try different date fields that might be present in RSS feeds
        entry_date = None
        
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            entry_date = datetime(*entry.published_parsed[:6]).date()
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            entry_date = datetime(*entry.updated_parsed[:6]).date()
        elif hasattr(entry, 'created_parsed') and entry.created_parsed:
            entry_date = datetime(*entry.created_parsed[:6]).date()
        
        if entry_date and entry_date == target_date:
            filtered_entries.append({
                'title': entry.get('title', 'No title'),
                'link': entry.get('link', ''),
                'published': entry.get('published', ''),
                'summary': entry.get('summary', ''),
                'author': entry.get('author', ''),
                'date': entry_date.isoformat()
            })
    
    return filtered_entries


async def collect_daily_updates(rss_feeds: List[str], day: str, data_dir: str = 'data') -> Dict[str, Any]:
    """
    Collect all updates for a specific day from multiple RSS feeds using maximum concurrency.

    Args:
        rss_feeds: List of RSS feed URLs
        day: Target day in format 'YYYY-MM-DD'
        data_dir: Base directory for storing data (default: 'data')

    Returns:
        Dictionary containing results from all feeds with entries filtered by day
    """
    results = {
        'day': day,
        'feeds': [],
        'total_entries': 0,
        'successful_feeds': 0,
        'failed_feeds': 0
    }

    # Create directory <data_dir>/<day>
    output_dir = Path(data_dir) / day
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create httpx async client with unlimited connections for maximum concurrency
    limits = httpx.Limits(max_connections=None, max_keepalive_connections=None)
    async with httpx.AsyncClient(limits=limits, follow_redirects=True) as client:
        # Create tasks for all feeds to fetch them concurrently
        tasks = [fetch_rss_feed(client, url) for url in rss_feeds]
        
        # Wait for all tasks to complete
        feed_results = await asyncio.gather(*tasks)

    # Initialize genai client for content generation
    genai_client = genai.Client(vertexai=True, location='global', project='conten001')

    # Process each feed result
    for feed_result in feed_results:
        if feed_result['error']:
            # Feed fetch failed
            feed_data = {
                'url': feed_result['url'],
                'status': 'error',
                'error': feed_result['error'],
                'feed_title': None,
                'entries': [],
                'entry_count': 0
            }
            print(f'Error: {feed_data}')
        else:
            # Feed fetch succeeded
            feed = feed_result['feed']
            feed_title = feed.feed.get('title', 'Unknown') if hasattr(feed, 'feed') else 'Unknown'
            
            # Filter entries by the target day
            filtered_entries = filter_entries_by_day(feed, day)
            
            # Generate AI summary for each feed's entries
            for entry in filtered_entries:
                title = entry['title']
                url = entry['link']
                url_schema = httpx.URL(url)
                summary = entry['summary']

                prompt = "Summarize content into three paragraphs"
                if 'youtube.com' in url_schema.host:
                    parts = [
                        genai.types.Part.from_text(text = prompt),
                        genai.types.Part.from_uri(
                            file_uri = url,
                            mime_type = 'video/vnd.youtube.yt'
                        )
                    ]
                response = genai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents = parts
                )

                # Get the generated summary text
                summary_text = response.candidates[0].content.parts[0].text

                # Save to markdown file
                safe_title = sanitize_filename(title)
                filename = output_dir / f"{safe_title}.md"

                # Create markdown content with title as hyperlink
                markdown_content = f"# [{title}]({url})\n\n{summary_text}\n"

                # Write to file
                filename.write_text(markdown_content, encoding='utf-8')

                print(60 * '-')
                print(f"Saved: {filename}")
                print(f"Title: {title}")
                print(f"URL: {url}")

#             if filtered_entries:
#                 try:
#                     # Create a summary prompt from all entries
#                     entries_text = "\n\n".join([
#                         f"Title: {entry['title']}\nLink: {entry['link']}\nSummary: {entry['summary']}"
#                         for entry in filtered_entries
#                     ])
                    
#                     prompt = f"""Analyze the following news articles from {feed_title} published on {day}:

# {entries_text}

# Please provide:
# 1. A concise summary of the main topics covered
# 2. Key themes and trends
# 3. Most significant stories
# """
                    
#                     # Generate content using genai
#                     response = genai_client.models.generate_content(
#                         model='gemini-2.5-flash',
#                         contents=prompt
#                     )
                    
#                     ai_summary = response.text
#                     feed_data['ai_summary'] = ai_summary
                    
#                     # Save AI summary to file
#                     feed_name = feed_title.replace('/', '_').replace(' ', '_')
#                     summary_file = data_dir / f"{feed_name}_summary.txt"
#                     summary_file.write_text(ai_summary, encoding='utf-8')
                    
#                 except Exception as e:
#                     feed_data['ai_summary_error'] = str(e)
    
#     # Save complete results to JSON file
#     results_file = data_dir / 'results.json'
#     with results_file.open('w', encoding='utf-8') as f:
#         json.dump(results, f, indent=2, ensure_ascii=False)
    
#     return results


# Example usage
async def main(day: str = None, data_dir: str = 'data'):
    """
    Example usage of the collect_daily_updates function

    Args:
        day: Target day in format 'YYYY-MM-DD'. If None, uses yesterday.
        data_dir: Base directory for storing data (default: 'data')
    """
    rss_feeds = [
        'https://www.youtube.com/feeds/videos.xml?channel_id=UCRAu2aXcH-B5h9SREfyhXuA',
        'https://www.youtube.com/feeds/videos.xml?channel_id=UC1yNl2E66ZzKApQdRuTQ4tw'
    ]

    # Use provided day or default to yesterday
    if day is None:
        day = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    # Collect updates for the specified day
    results = await collect_daily_updates(rss_feeds, day, data_dir)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Fetch and summarize RSS feed entries for a specific day'
    )
    parser.add_argument(
        '--day',
        type=str,
        default=None,
        help='Target day in YYYY-MM-DD format (default: yesterday)'
    )
    parser.add_argument(
        '--data-dir',
        type=str,
        default='data',
        help='Base directory for storing data (default: data)'
    )
    args = parser.parse_args()

    # Validate date format if provided
    if args.day:
        try:
            datetime.strptime(args.day, '%Y-%m-%d')
        except ValueError:
            print(f"Error: Invalid date format '{args.day}'. Use YYYY-MM-DD format.")
            exit(1)

    asyncio.run(main(args.day, args.data_dir))
