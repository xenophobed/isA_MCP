#!/usr/bin/env python3
"""
Test for Data Extraction Strategies (CSS, XPath, Regex)
"""
import asyncio
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def test_css_extraction_strategy():
    """Test CSS extraction strategy functionality"""
    print("🎯 Testing CSS Extraction Strategy")
    print("=" * 40)
    
    try:
        from tools.services.web_services.strategies.extraction import CSSExtractionStrategy, PredefinedSchemas
        from tools.services.web_services.core.browser_manager import BrowserManager
        
        # Create test HTML
        test_html = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <article class="news-article">
                <h1 class="title">Breaking News: AI Revolution</h1>
                <div class="author">By John Doe</div>
                <time class="date">2024-01-15</time>
                <div class="content">
                    <p>Artificial intelligence is transforming the world at an unprecedented pace.</p>
                    <p>Companies are investing billions in AI research and development.</p>
                </div>
                <div class="tags">
                    <span class="tag">AI</span>
                    <span class="tag">Technology</span>
                    <span class="tag">Innovation</span>
                </div>
                <a href="/full-article">Read More</a>
            </article>
            
            <article class="news-article">
                <h1 class="title">Climate Change Summit</h1>
                <div class="author">By Jane Smith</div>
                <time class="date">2024-01-14</time>
                <div class="content">
                    <p>World leaders gather to discuss climate action.</p>
                </div>
                <div class="tags">
                    <span class="tag">Climate</span>
                    <span class="tag">Environment</span>
                </div>
                <a href="/climate-article">Read More</a>
            </article>
        </body>
        </html>
        """
        
        # Initialize browser
        browser_manager = BrowserManager()
        page = await browser_manager.get_page("stealth")  # Use stealth profile (headless=True)
        
        # Set content
        await page.set_content(test_html)
        
        # Test predefined news schema
        news_schema = PredefinedSchemas.get_news_articles_schema()
        css_extractor = CSSExtractionStrategy(news_schema)
        
        print("✅ CSS extractor initialized with news schema")
        
        # Extract data
        results = await css_extractor.extract(page, test_html)
        
        print(f"✅ Extraction completed: {len(results)} articles found")
        
        # Validate results
        expected_articles = 2
        if len(results) == expected_articles:
            print(f"   ✓ Correct number of articles extracted: {len(results)}")
            
            # Check first article content
            first_article = results[0]
            expected_fields = ['title', 'content', 'author', 'date', 'tags', 'link']
            found_fields = sum(1 for field in expected_fields if field in first_article and first_article[field])
            
            print(f"   ✓ Fields extracted from first article: {found_fields}/{len(expected_fields)}")
            print(f"     - Title: {first_article.get('title', 'N/A')[:30]}...")
            print(f"     - Author: {first_article.get('author', 'N/A')}")
            print(f"     - Tags: {len(first_article.get('tags', []))} tags")
            
            success = found_fields >= 4  # At least 4 out of 6 fields should be extracted
        else:
            print(f"   ❌ Expected {expected_articles} articles, got {len(results)}")
            success = False
        
        await browser_manager.cleanup_all()
        return success
        
    except Exception as e:
        print(f"❌ CSS extraction test failed: {e}")
        return False

async def test_xpath_extraction_strategy():
    """Test XPath extraction strategy functionality"""
    print("\n🔍 Testing XPath Extraction Strategy")
    print("=" * 40)
    
    try:
        from tools.services.web_services.strategies.extraction import XPathExtractionStrategy, PredefinedXPathSchemas
        from tools.services.web_services.core.browser_manager import BrowserManager
        
        # Create test HTML with forms and meta data
        test_html = """
        <html>
        <head>
            <title>Contact Us - Example Company</title>
            <meta name="description" content="Get in touch with our team">
            <meta name="keywords" content="contact, support, help">
            <meta property="og:title" content="Contact Example Company">
            <link rel="canonical" href="https://example.com/contact">
        </head>
        <body>
            <form action="/submit-contact" method="post">
                <label for="name">Full Name:</label>
                <input type="text" name="name" id="name" required>
                
                <label for="email">Email Address:</label>
                <input type="email" name="email" id="email" required>
                
                <label for="phone">Phone Number:</label>
                <input type="tel" name="phone" id="phone">
                
                <label for="message">Message:</label>
                <textarea name="message" id="message" required></textarea>
                
                <button type="submit">Send Message</button>
                <input type="hidden" name="csrf_token" value="abc123">
            </form>
        </body>
        </html>
        """
        
        # Initialize browser
        browser_manager = BrowserManager()
        page = await browser_manager.get_page("stealth")  # Use stealth profile (headless=True)
        
        # Set content
        await page.set_content(test_html)
        
        # Test 1: Meta information extraction
        meta_schema = PredefinedXPathSchemas.get_meta_information_schema()
        xpath_extractor = XPathExtractionStrategy(meta_schema)
        
        print("✅ XPath extractor initialized with meta schema")
        
        meta_results = await xpath_extractor.extract(page, test_html)
        
        print(f"✅ Meta extraction completed: {len(meta_results)} items found")
        
        # Test 2: Form fields extraction
        form_schema = PredefinedXPathSchemas.get_form_fields_schema()
        form_extractor = XPathExtractionStrategy(form_schema)
        
        form_results = await form_extractor.extract(page, test_html)
        
        print(f"✅ Form extraction completed: {len(form_results)} forms found")
        
        # Validate results
        success = True
        
        # Check meta results
        if meta_results and len(meta_results) > 0:
            meta_data = meta_results[0]
            if 'title' in meta_data and meta_data['title']:
                print(f"   ✓ Page title extracted: {meta_data['title']}")
            if 'description' in meta_data and meta_data['description']:
                print(f"   ✓ Meta description extracted: {meta_data['description']}")
            if 'og_title' in meta_data and meta_data['og_title']:
                print(f"   ✓ OG title extracted: {meta_data['og_title']}")
        else:
            print("   ❌ No meta information extracted")
            success = False
        
        # Check form results
        if form_results and len(form_results) > 0:
            form_data = form_results[0]
            input_names = form_data.get('input_names', [])
            input_types = form_data.get('input_types', [])
            
            print(f"   ✓ Form inputs found: {len(input_names)} inputs")
            print(f"   ✓ Input types: {input_types}")
            
            if len(input_names) >= 4:  # name, email, phone, message, csrf_token
                print("   ✓ Expected form fields found")
            else:
                print("   ❌ Some form fields missing")
                success = False
        else:
            print("   ❌ No form data extracted")
            success = False
        
        await browser_manager.cleanup_all()
        return success
        
    except Exception as e:
        print(f"❌ XPath extraction test failed: {e}")
        return False

async def test_regex_extraction_strategy():
    """Test Regex extraction strategy functionality"""
    print("\n🔤 Testing Regex Extraction Strategy")
    print("=" * 40)
    
    try:
        from tools.services.web_services.strategies.extraction import RegexExtractionStrategy, PredefinedRegexSchemas
        from tools.services.web_services.core.browser_manager import BrowserManager
        
        # Create test content with various patterns
        test_html = """
        <html>
        <body>
            <div class="contact-info">
                <p>Contact us at: info@example.com or support@company.org</p>
                <p>Phone: (555) 123-4567 or +1-800-555-0199</p>
                <p>Visit our website: https://www.example.com</p>
                <p>Check our social: https://twitter.com/example</p>
            </div>
            
            <div class="pricing">
                <p>Premium Plan: $29.99/month</p>
                <p>Enterprise: $199.00/month</p>
                <p>Discount: 15% off for annual billing</p>
                <p>Processing fee: $2.50</p>
            </div>
            
            <div class="dates">
                <p>Event Date: 12/25/2024</p>
                <p>Registration: 2024-01-15</p>
                <p>Meeting at 2:30 PM EST</p>
                <p>Deadline: 01/31/2024 11:59 PM</p>
            </div>
        </body>
        </html>
        """
        
        # Initialize browser
        browser_manager = BrowserManager()
        page = await browser_manager.get_page("stealth")  # Use stealth profile (headless=True)
        
        # Set content
        await page.set_content(test_html)
        
        # Test 1: Contact information extraction
        contact_schema = PredefinedRegexSchemas.get_contact_extraction_schema()
        contact_extractor = RegexExtractionStrategy(contact_schema)
        
        print("✅ Regex extractor initialized with contact schema")
        
        contact_results = await contact_extractor.extract(page, test_html)
        
        print(f"✅ Contact extraction completed: {len(contact_results)} items found")
        
        # Test 2: Financial data extraction
        financial_schema = PredefinedRegexSchemas.get_financial_data_schema()
        financial_extractor = RegexExtractionStrategy(financial_schema)
        
        financial_results = await financial_extractor.extract(page, test_html)
        
        print(f"✅ Financial extraction completed: {len(financial_results)} items found")
        
        # Test 3: DateTime extraction
        datetime_schema = PredefinedRegexSchemas.get_datetime_schema()
        datetime_extractor = RegexExtractionStrategy(datetime_schema)
        
        datetime_results = await datetime_extractor.extract(page, test_html)
        
        print(f"✅ DateTime extraction completed: {len(datetime_results)} items found")
        
        # Validate results
        success = True
        
        # Check contact results
        if contact_results and len(contact_results) > 0:
            contact_data = contact_results[0]
            emails = contact_data.get('emails', [])
            phones = contact_data.get('phone_numbers', [])
            urls = contact_data.get('urls', [])
            
            print(f"   ✓ Emails found: {len(emails)} - {emails}")
            print(f"   ✓ Phone numbers found: {len(phones)} - {phones}")
            print(f"   ✓ URLs found: {len(urls)} - {urls}")
            
            if len(emails) >= 2 and len(phones) >= 2 and len(urls) >= 1:
                print("   ✓ Contact information extraction successful")
            else:
                print("   ⚠️ Some contact information may be missing")
        else:
            print("   ❌ No contact information extracted")
            success = False
        
        # Check financial results
        if financial_results and len(financial_results) > 0:
            financial_data = financial_results[0]
            prices = financial_data.get('prices', [])
            percentages = financial_data.get('percentages', [])
            
            print(f"   ✓ Prices found: {len(prices)} - {prices}")
            print(f"   ✓ Percentages found: {len(percentages)} - {percentages}")
            
            if len(prices) >= 3 and len(percentages) >= 1:
                print("   ✓ Financial data extraction successful")
            else:
                print("   ⚠️ Some financial data may be missing")
        
        # Check datetime results  
        if datetime_results and len(datetime_results) > 0:
            datetime_data = datetime_results[0]
            dates_mdy = datetime_data.get('dates_mdy', [])
            iso_dates = datetime_data.get('iso_dates', [])
            times = datetime_data.get('times', [])
            
            print(f"   ✓ MDY dates found: {len(dates_mdy)} - {dates_mdy}")
            print(f"   ✓ ISO dates found: {len(iso_dates)} - {iso_dates}")
            print(f"   ✓ Times found: {len(times)} - {times}")
            
            if len(dates_mdy) >= 1 or len(iso_dates) >= 1:
                print("   ✓ DateTime extraction successful")
        
        await browser_manager.cleanup_all()
        return success
        
    except Exception as e:
        print(f"❌ Regex extraction test failed: {e}")
        return False

async def test_extraction_strategy_integration():
    """Test combining multiple extraction strategies"""
    print("\n🔗 Testing Extraction Strategy Integration")
    print("=" * 40)
    
    try:
        from tools.services.web_services.strategies.extraction import (
            CSSExtractionStrategy, XPathExtractionStrategy, RegexExtractionStrategy,
            PredefinedSchemas, PredefinedXPathSchemas, PredefinedRegexSchemas
        )
        from tools.services.web_services.core.browser_manager import BrowserManager
        
        # Create comprehensive test content
        test_html = """
        <html>
        <head>
            <title>E-commerce Product Page</title>
            <meta name="description" content="Buy the best products online">
        </head>
        <body>
            <div class="product">
                <h1 class="name">Premium Wireless Headphones</h1>
                <div class="price">$89.99</div>
                <div class="description">High-quality wireless headphones with noise cancellation</div>
                <img src="/images/headphones.jpg" alt="Wireless Headphones">
                <div class="rating">4.5 stars</div>
                <a href="/buy-now">Buy Now</a>
            </div>
            
            <div class="contact-section">
                <p>Questions? Email us at: sales@store.com</p>
                <p>Call: (555) 987-6543</p>
                <p>Visit: https://store.com/support</p>
            </div>
            
            <form id="newsletter" action="/subscribe" method="post">
                <input type="email" name="email" placeholder="Enter your email">
                <button type="submit">Subscribe</button>
            </form>
        </body>
        </html>
        """
        
        # Initialize browser
        browser_manager = BrowserManager()
        page = await browser_manager.get_page("stealth")  # Use stealth profile (headless=True)
        await page.set_content(test_html)
        
        # Extract using different strategies
        print("🎯 Extracting with CSS strategy...")
        css_schema = PredefinedSchemas.get_product_listings_schema()
        css_extractor = CSSExtractionStrategy(css_schema)
        css_results = await css_extractor.extract(page, test_html)
        
        print("🔍 Extracting with XPath strategy...")
        xpath_schema = PredefinedXPathSchemas.get_form_fields_schema()
        xpath_extractor = XPathExtractionStrategy(xpath_schema)
        xpath_results = await xpath_extractor.extract(page, test_html)
        
        print("🔤 Extracting with Regex strategy...")
        regex_schema = PredefinedRegexSchemas.get_contact_extraction_schema()
        regex_extractor = RegexExtractionStrategy(regex_schema)
        regex_results = await regex_extractor.extract(page, test_html)
        
        # Combine results
        combined_data = {
            "products": css_results,
            "forms": xpath_results,
            "contacts": regex_results
        }
        
        print("✅ All extractions completed")
        print(f"   CSS (Products): {len(css_results)} items")
        print(f"   XPath (Forms): {len(xpath_results)} items")
        print(f"   Regex (Contacts): {len(regex_results)} items")
        
        # Validate combined results
        success = True
        
        # Check if we got product information
        if css_results and len(css_results) > 0:
            product = css_results[0]
            if 'name' in product and 'price' in product:
                print(f"   ✓ Product extracted: {product['name']} - {product['price']}")
            else:
                success = False
        
        # Check if we got contact information
        if regex_results and len(regex_results) > 0:
            contacts = regex_results[0]
            emails = contacts.get('emails', [])
            if len(emails) > 0:
                print(f"   ✓ Contact email extracted: {emails[0]}")
            else:
                success = False
        
        # Check if we got form information
        if xpath_results and len(xpath_results) > 0:
            form = xpath_results[0]
            if 'input_names' in form and form['input_names']:
                print(f"   ✓ Form fields extracted: {form['input_names']}")
            else:
                success = False
        
        await browser_manager.cleanup_all()
        
        if success:
            print("   ✅ Integration test successful - multiple strategies working together")
        else:
            print("   ❌ Integration test failed - some strategies not working properly")
        
        return success
        
    except Exception as e:
        print(f"❌ Extraction integration test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Starting Extraction Strategy Unit Tests...")
    
    async def run_tests():
        test1 = await test_css_extraction_strategy()
        test2 = await test_xpath_extraction_strategy() 
        test3 = await test_regex_extraction_strategy()
        test4 = await test_extraction_strategy_integration()
        
        return test1 and test2 and test3 and test4
    
    result = asyncio.run(run_tests())
    if result:
        print("\n🎉 All extraction strategy tests passed!")
    else:
        print("\n❌ Some extraction strategy tests failed!")
    
    sys.exit(0 if result else 1)