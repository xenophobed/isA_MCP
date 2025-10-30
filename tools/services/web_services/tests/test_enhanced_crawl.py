#!/usr/bin/env python3
"""
Test script for enhanced web crawl service
Tests robots.txt compliance, readability extraction, and transparent User-Agent
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from tools.services.web_services.services.web_crawl_service import WebCrawlService
from core.logging import get_logger

logger = get_logger(__name__)


async def test_basic_crawl():
    """Test basic crawling with enhancements"""
    print("\n" + "="*60)
    print("TEST 1: Basic Article Crawl (Should Work)")
    print("="*60)

    service = WebCrawlService()

    # Test with a blog article (should work with readability)
    test_url = "https://www.anthropic.com/research/claude-3-5-sonnet"

    try:
        result = await service.crawl_and_analyze(
            url=test_url,
            analysis_request="extract main content"
        )

        print(f"\n✅ Success: {result.get('success')}")
        print(f"📊 Extraction Method: {result.get('extraction_method', 'N/A')}")
        print(f"📝 Title: {result.get('result', {}).get('title', 'N/A')}")
        print(f"📏 Content Length: {len(result.get('result', {}).get('content', ''))} chars")
        print(f"🤖 User-Agent: {result.get('result', {}).get('user_agent', 'N/A')[:60]}...")
        print(f"🚦 Robots Checked: {result.get('result', {}).get('robots_checked', False)}")

        if result.get('result', {}).get('extraction_quality'):
            print(f"⭐ Extraction Quality: {result['result']['extraction_quality']}")

        # Show first 200 chars of content
        content = result.get('result', {}).get('content', '')
        if content:
            print(f"\n📄 Content Preview:\n{content[:200]}...")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await service.close()


async def test_robots_txt_blocked():
    """Test robots.txt blocking"""
    print("\n" + "="*60)
    print("TEST 2: Robots.txt Blocked Site (Should Block)")
    print("="*60)

    service = WebCrawlService()

    # Test with a site that blocks crawlers (Twitter/X)
    test_url = "https://twitter.com/elonmusk"

    try:
        result = await service.crawl_and_analyze(
            url=test_url,
            analysis_request=None
        )

        print(f"\n✅ Success: {result.get('success')}")
        print(f"📊 Method: {result.get('extraction_method', 'N/A')}")

        if not result.get('success'):
            print(f"🚫 Blocked Reason: {result.get('reason', 'N/A')}")
            print(f"   This is EXPECTED - robots.txt is working!")

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        await service.close()


async def test_content_quality():
    """Test content extraction quality comparison"""
    print("\n" + "="*60)
    print("TEST 3: Content Quality Test")
    print("="*60)

    service = WebCrawlService()

    # Test with a blog post
    test_url = "https://www.paulgraham.com/superlinear.html"

    try:
        result = await service.crawl_and_analyze(
            url=test_url,
            analysis_request=None
        )

        if result.get('success'):
            extraction_method = result.get('extraction_method', 'unknown')
            content = result.get('result', {}).get('content', '')

            print(f"\n📊 Extraction Method: {extraction_method}")
            print(f"📏 Content Length: {len(content)} chars")
            print(f"📝 Word Count: {result.get('result', {}).get('word_count', 0)} words")

            # Check for quality indicators
            has_markdown = '#' in content or '*' in content
            has_structure = '\n\n' in content
            noise_indicators = ['cookie', 'subscribe', 'advertisement']
            noise_count = sum(1 for indicator in noise_indicators if indicator.lower() in content.lower())

            print(f"\n🎨 Quality Indicators:")
            print(f"   - Markdown formatting: {'✅' if has_markdown else '❌'}")
            print(f"   - Structured paragraphs: {'✅' if has_structure else '❌'}")
            print(f"   - Noise level: {noise_count} indicators (lower is better)")

            if 'readability' in extraction_method:
                print(f"\n⭐ Using Readability extraction - Higher quality expected!")
            elif 'bs4' in extraction_method:
                print(f"\n⚠️ Using BS4 fallback - May contain noise")

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        await service.close()


async def run_all_tests():
    """Run all tests"""
    print("\n" + "🚀" + "="*58 + "🚀")
    print("   ENHANCED WEB CRAWL SERVICE - INTEGRATION TESTS")
    print("🚀" + "="*58 + "🚀")

    try:
        # Test 1: Basic crawl
        await test_basic_crawl()
        await asyncio.sleep(2)

        # Test 2: Robots.txt blocking
        await test_robots_txt_blocked()
        await asyncio.sleep(2)

        # Test 3: Content quality
        await test_content_quality()

    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print("✅ TEST SUITE COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    print("\n📋 Note: This test requires internet connection and may take a few minutes.")
    print("   Some tests intentionally fail to verify robots.txt compliance.\n")

    asyncio.run(run_all_tests())
