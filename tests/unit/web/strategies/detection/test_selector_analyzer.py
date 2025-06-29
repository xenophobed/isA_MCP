#!/usr/bin/env python3
"""
Test for Selector Analyzer (Traditional CSS/XPath strategies)
"""
import asyncio
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def test_selector_analyzer_basic():
    """Test basic selector analyzer functionality"""
    print("📋 Testing Selector Analyzer - Traditional CSS/XPath Detection")
    print("=" * 60)
    
    try:
        # Import required modules
        from tools.services.web_services.core.browser_manager import BrowserManager
        from tools.services.web_services.strategies.detection.selector_analyzer import SelectorAnalyzer
        
        # Initialize services
        browser_manager = BrowserManager()
        await browser_manager.initialize()
        
        selector_analyzer = SelectorAnalyzer()
        
        print("✅ Selector analyzer initialized")
        
        # Get browser page
        browser = await browser_manager.get_browser("stealth")
        context = await browser.new_context()
        page = await context.new_page()
        
        # Test with a known login page
        test_url = "https://the-internet.herokuapp.com/login"
        print(f"\n🌐 Testing with login page: {test_url}")
        
        await page.goto(test_url, wait_until='networkidle')
        page_title = await page.title()
        print(f"✅ Navigated to page: {page_title}")
        
        # Test login element identification
        print("\n🔍 Testing login element identification...")
        login_elements = await selector_analyzer.identify_login_elements(page)
        
        print(f"✅ Found {len(login_elements)} login elements:")
        for element_type, element_data in login_elements.items():
            print(f"   {element_type}:")
            print(f"     Type: {element_data.get('type', 'unknown')}")
            print(f"     Selector: {element_data.get('selector', 'N/A')}")
            if 'x' in element_data and 'y' in element_data:
                print(f"     Coordinates: ({element_data['x']:.1f}, {element_data['y']:.1f})")
        
        # Verify elements are actually present
        print("\n🔍 Verifying element presence...")
        for element_type, element_data in login_elements.items():
            if element_data.get('type') == 'css_selector':
                selector = element_data.get('selector')
                try:
                    element = page.locator(selector).first
                    count = await element.count()
                    is_visible = await element.is_visible() if count > 0 else False
                    print(f"   ✅ {element_type}: {count} found, visible: {is_visible}")
                except Exception as e:
                    print(f"   ❌ {element_type}: Error - {e}")
        
        # Test schema-based extraction
        print("\n🔍 Testing schema-based extraction...")
        schema = selector_analyzer.get_login_schema()
        schema_results = await selector_analyzer.find_elements_by_schema(page, schema)
        
        print(f"✅ Schema extraction found {len(schema_results)} elements:")
        for field_name, field_data in schema_results.items():
            print(f"   {field_name}: {field_data.get('type', 'unknown')}")
        
        # Test with a different page (form with different structure)
        print(f"\n🌐 Testing with different form structure...")
        await page.goto("https://httpbin.org/forms/post", wait_until='networkidle')
        
        form_elements = await selector_analyzer.identify_login_elements(page)
        print(f"✅ Different form: Found {len(form_elements)} elements")
        
        # Clean up
        await page.close()
        await context.close()
        
        print("\n✅ Selector analyzer test completed successfully")
        return True
        
    except Exception as e:
        print(f"\n❌ Selector analyzer test failed: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        return False

async def test_selector_patterns():
    """Test selector pattern matching"""
    print("\n📋 Testing Selector Pattern Matching")
    print("-" * 40)
    
    try:
        from tools.services.web_services.core.browser_manager import BrowserManager
        from tools.services.web_services.strategies.detection.selector_analyzer import SelectorAnalyzer
        
        browser_manager = BrowserManager()
        await browser_manager.initialize()
        selector_analyzer = SelectorAnalyzer()
        
        browser = await browser_manager.get_browser("stealth")
        context = await browser.new_context()
        page = await context.new_page()
        
        # Create a test HTML page with various form elements
        test_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Test Form</title></head>
        <body>
            <form id="test-form">
                <input type="text" name="username" placeholder="Enter username" />
                <input type="email" id="email-field" placeholder="Email address" />
                <input type="password" name="password" />
                <button type="submit">Sign In</button>
                <input type="submit" value="Login" />
            </form>
        </body>
        </html>
        """
        
        await page.set_content(test_html)
        print("✅ Test HTML page created")
        
        # Test pattern detection
        elements = await selector_analyzer.identify_login_elements(page)
        
        print(f"✅ Pattern detection found {len(elements)} elements:")
        for element_type, element_data in elements.items():
            print(f"   {element_type}: {element_data.get('selector', 'N/A')}")
        
        # Verify we found the expected elements
        expected_elements = ['username', 'password', 'submit']
        found_elements = list(elements.keys())
        
        success = all(elem in found_elements for elem in expected_elements)
        print(f"✅ Expected elements check: {success}")
        
        await page.close()
        await context.close()
        
        return success
        
    except Exception as e:
        print(f"❌ Pattern test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Starting Selector Analyzer Unit Tests...")
    
    async def run_tests():
        test1 = await test_selector_analyzer_basic()
        test2 = await test_selector_patterns()
        
        return test1 and test2
    
    result = asyncio.run(run_tests())
    if result:
        print("\n🎉 All selector analyzer tests passed!")
    else:
        print("\n❌ Some selector analyzer tests failed!")
    
    sys.exit(0 if result else 1)