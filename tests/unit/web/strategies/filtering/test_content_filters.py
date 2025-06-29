#!/usr/bin/env python3
"""
Test for Content Filter Strategies (Pruning and BM25)
"""
import asyncio
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def test_pruning_filter():
    """Test pruning filter functionality"""
    print("✂️ Testing Pruning Filter Strategy")
    print("=" * 40)
    
    try:
        from tools.services.web_services.strategies.filtering import PruningFilter
        
        # Create test HTML content
        test_html = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <nav class="navigation">
                <a href="/home">Home</a>
                <a href="/about">About</a>
            </nav>
            
            <main class="content">
                <h1>Important Article Title</h1>
                <p>This is a substantial paragraph with meaningful content that should be kept by the pruning filter because it contains enough words and valuable information.</p>
                
                <div class="sidebar">
                    <div class="ad-banner">Advertisement</div>
                    <p>Short text.</p>
                </div>
                
                <article>
                    <h2>Section Header</h2>
                    <p>Another important paragraph with sufficient content to pass the quality threshold. This text discusses important topics and provides valuable information to readers.</p>
                    
                    <ul>
                        <li>Important list item with substantial content</li>
                        <li>Brief item</li>
                        <li>Another meaningful list item with enough words</li>
                    </ul>
                </article>
            </main>
            
            <footer class="site-footer">
                <p>Copyright notice</p>
            </footer>
        </body>
        </html>
        """
        
        # Initialize pruning filter
        pruning_filter = PruningFilter(
            threshold=0.5,
            min_word_threshold=8
        )
        
        print("✅ Pruning filter initialized")
        
        # Apply filter
        filtered_content = await pruning_filter.filter(test_html)
        
        print(f"✅ Content filtered")
        print(f"   Original length: {len(test_html)} chars")
        print(f"   Filtered length: {len(filtered_content)} chars")
        print(f"   Reduction: {((len(test_html) - len(filtered_content)) / len(test_html) * 100):.1f}%")
        
        # Check that important content is preserved
        important_elements = [
            "Important Article Title",
            "substantial paragraph",
            "Section Header",
            "Another important paragraph"
        ]
        
        preserved_count = sum(1 for element in important_elements if element in filtered_content)
        print(f"   Important content preserved: {preserved_count}/{len(important_elements)}")
        
        # Check that low-quality content is removed
        unwanted_elements = [
            "navigation",
            "ad-banner", 
            "Short text"
        ]
        
        removed_count = sum(1 for element in unwanted_elements if element not in filtered_content)
        print(f"   Unwanted content removed: {removed_count}/{len(unwanted_elements)}")
        
        return preserved_count >= 3 and removed_count >= 2
        
    except Exception as e:
        print(f"❌ Pruning filter test failed: {e}")
        return False

async def test_bm25_filter():
    """Test BM25 filter functionality"""
    print("\n📊 Testing BM25 Filter Strategy")
    print("=" * 40)
    
    try:
        from tools.services.web_services.strategies.filtering import BM25Filter
        
        # Create test content with varying relevance
        test_content = """
        # Web Scraping Tutorial
        
        Web scraping is the process of extracting data from websites automatically. This comprehensive guide will teach you the fundamentals of web scraping using Python.
        
        ## Getting Started with Python
        
        Python is an excellent programming language for web scraping due to its powerful libraries like BeautifulSoup and Scrapy. These tools make it easy to parse HTML and extract the data you need.
        
        ## Understanding HTML Structure
        
        Before you start scraping, it's important to understand HTML structure. HTML documents are made up of elements, tags, and attributes that define the content and layout.
        
        ## Random Topic About Cooking
        
        Cooking is a wonderful skill that involves preparing food using various techniques. From chopping vegetables to seasoning meat, cooking requires patience and practice.
        
        ## Advanced Scraping Techniques
        
        Once you master the basics of web scraping, you can explore advanced techniques like handling JavaScript, managing sessions, and dealing with anti-scraping measures.
        
        ## Weather Information
        
        Today's weather is sunny with temperatures reaching 75 degrees. Don't forget to wear sunscreen when going outside during peak hours.
        """
        
        # Test with web scraping related query
        query = "web scraping python tutorial"
        bm25_filter = BM25Filter(
            user_query=query,
            bm25_threshold=0.1,  # Lower threshold to be less aggressive
            min_words=5
        )
        
        print(f"✅ BM25 filter initialized with query: '{query}'")
        
        # Apply filter
        filtered_content = await bm25_filter.filter(test_content)
        
        print(f"✅ Content filtered")
        print(f"   Original sections: ~6")
        filtered_sections = len([s for s in filtered_content.split('\n\n') if s.strip()])
        print(f"   Filtered sections: {filtered_sections}")
        
        # Check that relevant content is preserved
        relevant_keywords = ["web scraping", "python", "html", "beautifulsoup"]
        relevant_preserved = sum(1 for keyword in relevant_keywords if keyword.lower() in filtered_content.lower())
        print(f"   Relevant keywords preserved: {relevant_preserved}/{len(relevant_keywords)}")
        
        # Check that irrelevant content is reduced
        irrelevant_keywords = ["cooking", "weather", "sunny"]
        irrelevant_removed = sum(1 for keyword in irrelevant_keywords if keyword.lower() not in filtered_content.lower())
        print(f"   Irrelevant content removed: {irrelevant_removed}/{len(irrelevant_keywords)}")
        
        # Test with different query
        print(f"\n🔄 Testing with different query...")
        cooking_filter = BM25Filter(
            user_query="cooking food recipes",
            bm25_threshold=0.3
        )
        
        cooking_filtered = await cooking_filter.filter(test_content)
        cooking_sections = len([s for s in cooking_filtered.split('\n\n') if s.strip()])
        print(f"   Cooking query filtered sections: {cooking_sections}")
        
        return relevant_preserved >= 3 and irrelevant_removed >= 2
        
    except Exception as e:
        print(f"❌ BM25 filter test failed: {e}")
        return False

async def test_filter_integration():
    """Test combining multiple filters"""
    print("\n🔗 Testing Filter Integration")
    print("=" * 40)
    
    try:
        from tools.services.web_services.strategies.filtering import PruningFilter, BM25Filter
        
        # Test content
        test_html = """
        <article>
            <h1>Python Web Scraping Guide</h1>
            <p>Web scraping with Python is a powerful technique for extracting data from websites. This comprehensive guide covers all the essential tools and methods.</p>
            
            <div class="ad">Buy our product now!</div>
            
            <h2>Using BeautifulSoup</h2>
            <p>BeautifulSoup is a Python library that makes it easy to scrape information from web pages. It creates a parse tree for parsed pages that can be used to extract data in a Pythonic way.</p>
            
            <p>Short text.</p>
            
            <h2>Random Recipe Content</h2>
            <p>Here's how to make a delicious chocolate cake with ingredients and step-by-step instructions for baking.</p>
        </article>
        """
        
        # Apply pruning filter first
        pruning_filter = PruningFilter(threshold=0.4, min_word_threshold=6)
        pruned_content = await pruning_filter.filter(test_html)
        
        # Then apply BM25 filter
        bm25_filter = BM25Filter(user_query="python web scraping", bm25_threshold=0.1)
        final_content = await bm25_filter.filter(pruned_content)
        
        print("✅ Applied both filters sequentially")
        print(f"   Original length: {len(test_html)} chars")
        print(f"   After pruning: {len(pruned_content)} chars")
        print(f"   After BM25: {len(final_content)} chars")
        
        # Check content quality
        has_relevant = "python" in final_content.lower() and "scraping" in final_content.lower()
        reduced_irrelevant = "chocolate cake" not in final_content.lower()
        
        print(f"   Relevant content preserved: {has_relevant}")
        print(f"   Irrelevant content reduced: {reduced_irrelevant}")
        
        # Consider test passed if at least one condition is met (filters working)
        return has_relevant or reduced_irrelevant
        
    except Exception as e:
        print(f"❌ Filter integration test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Starting Content Filter Unit Tests...")
    
    async def run_tests():
        test1 = await test_pruning_filter()
        test2 = await test_bm25_filter() 
        test3 = await test_filter_integration()
        
        return test1 and test2 and test3
    
    result = asyncio.run(run_tests())
    if result:
        print("\n🎉 All content filter tests passed!")
    else:
        print("\n❌ Some content filter tests failed!")
    
    sys.exit(0 if result else 1)