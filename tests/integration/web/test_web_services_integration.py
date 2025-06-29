#!/usr/bin/env python3
"""
Comprehensive Web Services Integration Test
Tests the complete workflow of search -> crawl -> extract -> filter
"""
import asyncio
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def test_complete_web_services_workflow():
    """Test the complete web services workflow"""
    print("🌐 Testing Complete Web Services Workflow")
    print("=" * 50)
    
    try:
        # Import all components
        from tools.services.web_services.engines.search_engine import SearchEngine
        from tools.services.web_services.engines.extraction_engine import ExtractionEngine
        from tools.services.web_services.strategies.extraction import (
            CSSExtractionStrategy, RegexExtractionStrategy, PredefinedSchemas, PredefinedRegexSchemas
        )
        from tools.services.web_services.strategies.filtering import PruningFilter, BM25Filter
        from tools.services.web_services.strategies.generation.markdown_generator import MarkdownGenerator
        from tools.services.web_services.core.browser_manager import BrowserManager
        from tools.services.web_services.engines.detection_engine import DetectionEngine, DetectionMode
        
        workflow_success = True
        
        # Step 1: Initialize all engines and managers
        print("\n📋 Step 1: Initializing all components...")
        
        search_engine = SearchEngine()
        extraction_engine = ExtractionEngine()
        browser_manager = BrowserManager()
        selector_analyzer = SelectorAnalyzer()
        vision_analyzer = VisionAnalyzer()
        
        # Register search strategy (without actually using API)
        # brave_strategy = BraveSearchStrategy()
        # search_engine.register_strategy(SearchProvider.BRAVE, brave_strategy)
        
        print("   ✓ All engines initialized")
        
        # Step 2: Test browser automation
        print("\n🌐 Step 2: Testing browser automation...")
        
        page = await browser_manager.get_page("stealth")
        
        # Create a test HTML page that simulates a typical web page
        test_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Test E-commerce Site - Premium Products</title>
            <meta name="description" content="Best online store for premium products">
            <meta name="keywords" content="ecommerce, shopping, premium, products">
            <meta property="og:title" content="Premium Products Store">
            <link rel="canonical" href="https://example-store.com">
        </head>
        <body>
            <nav class="navigation">
                <a href="/home">Home</a>
                <a href="/products">Products</a>
                <a href="/contact">Contact</a>
            </nav>
            
            <main class="content">
                <section class="hero">
                    <h1>Welcome to Premium Products</h1>
                    <p>Discover our amazing collection of high-quality items at unbeatable prices!</p>
                </section>
                
                <section class="products">
                    <div class="product">
                        <h2 class="name">Wireless Bluetooth Headphones</h2>
                        <div class="price">$89.99</div>
                        <div class="description">High-quality wireless headphones with noise cancellation technology and 30-hour battery life.</div>
                        <img src="/images/headphones.jpg" alt="Wireless Headphones">
                        <div class="rating">4.8 stars (250 reviews)</div>
                        <a href="/product/headphones" class="buy-link">Buy Now</a>
                    </div>
                    
                    <div class="product">
                        <h2 class="name">Smart Fitness Watch</h2>
                        <div class="price">$199.00</div>
                        <div class="description">Track your fitness goals with this advanced smartwatch featuring GPS, heart rate monitoring, and 7-day battery.</div>
                        <img src="/images/watch.jpg" alt="Smart Watch">
                        <div class="rating">4.6 stars (180 reviews)</div>
                        <a href="/product/watch" class="buy-link">Buy Now</a>
                    </div>
                    
                    <div class="product">
                        <h2 class="name">Portable Power Bank</h2>
                        <div class="price">$39.99</div>
                        <div class="description">Keep your devices charged on the go with this compact 20,000mAh power bank with fast charging support.</div>
                        <img src="/images/powerbank.jpg" alt="Power Bank">
                        <div class="rating">4.4 stars (95 reviews)</div>
                        <a href="/product/powerbank" class="buy-link">Buy Now</a>
                    </div>
                </section>
                
                <section class="contact-info">
                    <h2>Contact Us</h2>
                    <p>Have questions? Reach out to us!</p>
                    <p>Email: support@premiumstore.com or sales@premiumstore.com</p>
                    <p>Phone: (555) 123-4567 or +1-800-PREMIUM</p>
                    <p>Visit us at: https://www.premiumstore.com/support</p>
                    <p>Follow us: https://twitter.com/premiumstore</p>
                    
                    <form id="contact-form" action="/contact" method="post">
                        <label for="name">Name:</label>
                        <input type="text" name="name" id="name" required>
                        
                        <label for="email">Email:</label>
                        <input type="email" name="email" id="email" required>
                        
                        <label for="subject">Subject:</label>
                        <input type="text" name="subject" id="subject">
                        
                        <label for="message">Message:</label>
                        <textarea name="message" id="message" required></textarea>
                        
                        <button type="submit">Send Message</button>
                    </form>
                </section>
                
                <section class="special-offers">
                    <h2>Special Offers</h2>
                    <p>Holiday Sale: Save 25% on all items!</p>
                    <p>Free shipping on orders over $75.00</p>
                    <p>Extended warranty available for $15.99</p>
                    <p>Today only: Buy 2 get 1 free on accessories</p>
                    
                    <div class="promo-dates">
                        <p>Sale starts: 12/01/2024</p>
                        <p>Sale ends: 12/31/2024</p>
                        <p>Last updated: 2024-12-15 at 10:30 AM EST</p>
                    </div>
                </section>
            </main>
            
            <footer class="site-footer">
                <p>&copy; 2024 Premium Store. All rights reserved.</p>
                <p>Privacy Policy | Terms of Service | Returns</p>
            </footer>
        </body>
        </html>
        """
        
        await page.set_content(test_html)
        page_url = "https://example-store.com"
        
        print("   ✓ Test page loaded successfully")
        
        # Step 3: Test data extraction strategies
        print("\n🎯 Step 3: Testing data extraction strategies...")
        
        # Test CSS extraction (product data)
        product_schema = PredefinedSchemas.get_product_listings_schema()
        css_extractor = CSSExtractionStrategy(product_schema)
        css_results = await css_extractor.extract(page, test_html)
        
        print(f"   ✓ CSS Extraction: {len(css_results)} products found")
        if len(css_results) >= 3:
            sample_product = css_results[0]
            print(f"     - Sample: {sample_product.get('name', 'N/A')} - {sample_product.get('price', 'N/A')}")
        
        # Test Regex extraction (contact data)
        contact_schema = PredefinedRegexSchemas.get_contact_extraction_schema()
        regex_extractor = RegexExtractionStrategy(contact_schema)
        regex_results = await regex_extractor.extract(page, test_html)
        
        print(f"   ✓ Regex Extraction: {len(regex_results)} contact sets found")
        if regex_results and len(regex_results) > 0:
            contacts = regex_results[0]
            emails = contacts.get('emails', [])
            phones = contacts.get('phone_numbers', [])
            print(f"     - Emails: {len(emails)}, Phones: {len(phones)}")
        
        # Step 4: Test content filtering
        print("\n🔄 Step 4: Testing content filtering...")
        
        # Generate markdown from page
        markdown_gen = MarkdownGenerator()
        markdown_content = await markdown_gen.generate(test_html, {"url": page_url})
        
        print(f"   ✓ Markdown generated: {len(markdown_content)} characters")
        
        # Apply pruning filter
        pruning_filter = PruningFilter(threshold=0.3, min_word_threshold=5)
        pruned_content = await pruning_filter.filter(markdown_content)
        
        print(f"   ✓ Pruning filter applied: {len(pruned_content)} characters remaining")
        
        # Apply BM25 filter for product-related content
        bm25_filter = BM25Filter(user_query="wireless headphones smartwatch products", bm25_threshold=0.1)
        filtered_content = await bm25_filter.filter(pruned_content)
        
        print(f"   ✓ BM25 filter applied: {len(filtered_content)} characters remaining")
        
        # Step 5: Test selector analysis
        print("\n🔍 Step 5: Testing selector analysis...")
        
        login_elements = await selector_analyzer.identify_login_elements(page)
        login_schema = selector_analyzer.get_login_schema()
        form_elements = await selector_analyzer.find_elements_by_schema(page, login_schema)
        
        print(f"   ✓ Login elements found: {len(login_elements)}")
        print(f"   ✓ Form elements found: {len(form_elements)}")
        
        # Step 6: Test complete extraction workflow
        print("\n⚙️ Step 6: Testing complete extraction workflow...")
        
        # Use the extraction engine for a complete crawl
        crawl_result = await extraction_engine.crawl_page(
            page,
            extraction_strategy="css",
            filter_strategy="pruning",
            generation_strategy="markdown"
        )
        
        print(f"   ✓ Complete crawl result:")
        print(f"     - Markdown length: {len(crawl_result.markdown or '')} chars")
        print(f"     - Extracted data items: {len(crawl_result.extracted_data or [])}")
        print(f"     - Metadata fields: {len(crawl_result.metadata or {})}")
        
        # Validate workflow success
        success_criteria = [
            len(css_results) >= 3,  # Found at least 3 products
            len(regex_results) > 0 and len(regex_results[0].get('emails', [])) >= 2,  # Found contact info
            len(filtered_content) > 100,  # Content filtering worked
            len(crawl_result.markdown or '') > 100,  # Complete workflow worked
            len(form_elements) > 0  # Found form elements
        ]
        
        workflow_success = all(success_criteria)
        
        print(f"\n📊 Workflow Summary:")
        print(f"   - Products extracted: {len(css_results)}")
        print(f"   - Contact info extracted: {'✓' if regex_results else '✗'}")
        print(f"   - Content filtered: {'✓' if len(filtered_content) > 0 else '✗'}")
        print(f"   - Forms analyzed: {len(form_elements)}")
        print(f"   - Complete workflow: {'✓' if len(crawl_result.markdown or '') > 0 else '✗'}")
        
        await browser_manager.cleanup_all()
        return workflow_success
        
    except Exception as e:
        print(f"❌ Complete workflow test failed: {e}")
        return False

async def test_error_handling():
    """Test error handling in web services"""
    print("\n🛡️ Testing Error Handling")
    print("=" * 30)
    
    try:
        from tools.services.web_services.engines.extraction_engine import ExtractionEngine
        from tools.services.web_services.core.browser_manager import BrowserManager
        
        extraction_engine = ExtractionEngine()
        browser_manager = BrowserManager()
        
        # Test with malformed HTML
        page = await browser_manager.get_page("stealth")
        malformed_html = "<html><head><title>Test</head><body><div>Unclosed div<p>Test</body></html>"
        
        await page.set_content(malformed_html)
        
        # Should handle malformed HTML gracefully
        crawl_result = await extraction_engine.crawl_page(page)
        
        print("   ✓ Malformed HTML handled gracefully")
        
        # Test with empty content
        await page.set_content("")
        crawl_result_empty = await extraction_engine.crawl_page(page)
        
        print("   ✓ Empty content handled gracefully")
        
        # Test with invalid strategies
        try:
            await extraction_engine.crawl_page(page, extraction_strategy="invalid_strategy")
            print("   ⚠️ Invalid strategy should have been handled")
        except Exception:
            print("   ✓ Invalid extraction strategy handled")
        
        await browser_manager.cleanup_all()
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

async def test_performance():
    """Test performance with multiple pages"""
    print("\n⚡ Testing Performance")
    print("=" * 25)
    
    try:
        import time
        from tools.services.web_services.engines.extraction_engine import ExtractionEngine
        from tools.services.web_services.core.browser_manager import BrowserManager
        
        extraction_engine = ExtractionEngine()
        browser_manager = BrowserManager()
        
        # Test processing multiple pages
        start_time = time.time()
        
        simple_html = """
        <html>
        <body>
            <div class="product">
                <h1>Test Product</h1>
                <div class="price">$10.00</div>
                <p>Simple test content for performance testing.</p>
            </div>
        </body>
        </html>
        """
        
        page = await browser_manager.get_page("stealth")
        results = []
        
        # Process 5 pages
        for i in range(5):
            await page.set_content(simple_html.replace("Test Product", f"Product {i+1}"))
            crawl_result = await extraction_engine.crawl_page(page)
            results.append(crawl_result)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"   ✓ Processed {len(results)} pages in {processing_time:.2f} seconds")
        print(f"   ✓ Average time per page: {processing_time/len(results):.2f} seconds")
        
        # All pages should have been processed successfully
        success = all(len(result.markdown or '') > 0 for result in results)
        
        await browser_manager.cleanup_all()
        return success
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Starting Web Services Integration Tests...")
    
    async def run_all_tests():
        test1 = await test_complete_web_services_workflow()
        test2 = await test_error_handling()
        test3 = await test_performance()
        
        return test1 and test2 and test3
    
    result = asyncio.run(run_all_tests())
    
    if result:
        print("\n🎉 All web services integration tests passed!")
        print("✅ Phase 1 basic modules are complete and working!")
    else:
        print("\n❌ Some web services integration tests failed!")
    
    sys.exit(0 if result else 1)