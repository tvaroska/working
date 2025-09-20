#!/usr/bin/env python3
"""
Simple test script for the content service implementation
"""

import asyncio
import sys
import os

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rss_service import RSSService
from config import get_settings

async def test_rss_service():
    """Test RSS service functionality"""
    print("Testing RSS Service...")
    
    rss_service = RSSService()
    
    # Test with a known RSS feed
    test_url = "https://feeds.feedburner.com/oreilly/radar"
    
    try:
        print(f"Validating feed: {test_url}")
        validation = await rss_service.validate_feed_url(test_url)
        print(f"Validation result: {validation}")
        
        if validation["valid"]:
            print("Fetching feed...")
            result = await rss_service.fetch_feed(test_url)
            print(f"Fetch status: {result['status']}")
            print(f"Number of items: {len(result['items'])}")
            
            if result["items"]:
                first_item = result["items"][0]
                print(f"First item title: {first_item.get('title', 'N/A')}")
                print(f"First item URL: {first_item.get('url', 'N/A')}")
        
    except Exception as e:
        print(f"Error testing RSS service: {e}")

def test_config():
    """Test configuration loading"""
    print("Testing Configuration...")
    
    try:
        settings = get_settings()
        print(f"Database URL: {settings.database_url}")
        print(f"RSS fetch timeout: {settings.rss_fetch_timeout}")
        print(f"RSS user agent: {settings.rss_user_agent}")
        print("Configuration loaded successfully!")
        
    except Exception as e:
        print(f"Error testing configuration: {e}")

async def main():
    """Run all tests"""
    print("=== Content Service Test Suite ===\n")
    
    # Test configuration
    test_config()
    print()
    
    # Test RSS service
    await test_rss_service()
    print()
    
    print("=== Test Suite Complete ===")

if __name__ == "__main__":
    asyncio.run(main())