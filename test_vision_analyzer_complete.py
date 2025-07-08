#!/usr/bin/env python3
"""
Complete Vision Analyzer Testing Suite
Test the two-layer AI analysis: ISA Vision + OpenAI Vision
"""
import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.services.web_services.strategies.detection.vision_analyzer import VisionAnalyzer
from tools.services.web_services.core.browser_manager import BrowserManager
from core.logging import get_logger

logger = get_logger(__name__)

async def test_login_detection():
    """Test two-layer login form detection"""
    print("🔐 Testing Login Form Detection")
    print("=" * 40)
    
    try:
        # Initialize services
        vision_analyzer = VisionAnalyzer()
        browser_manager = BrowserManager()
        
        # Create a comprehensive login form test page
        login_html = """
        <html>
        <head>
            <title>Secure Login Portal</title>
            <style>
                body { font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 50px; }
                .login-container { max-width: 400px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .login-header { text-align: center; margin-bottom: 30px; }
                .form-group { margin-bottom: 20px; }
                label { display: block; margin-bottom: 5px; font-weight: bold; color: #333; }
                input[type="email"], input[type="password"] { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 16px; }
                .login-btn { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 4px; font-size: 16px; font-weight: bold; cursor: pointer; }
                .login-btn:hover { background: #0056b3; }
                .form-links { text-align: center; margin-top: 20px; }
                .form-links a { color: #007bff; text-decoration: none; margin: 0 10px; }
            </style>
        </head>
        <body>
            <div class="login-container">
                <div class="login-header">
                    <h1>Login to Your Account</h1>
                    <p>Please enter your credentials to continue</p>
                </div>
                
                <form action="/authenticate" method="post" class="login-form">
                    <div class="form-group">
                        <label for="email">Email Address</label>
                        <input type="email" id="email" name="email" placeholder="Enter your email address" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password" placeholder="Enter your password" required>
                    </div>
                    
                    <div class="form-group">
                        <button type="submit" class="login-btn">Sign In to Account</button>
                    </div>
                </form>
                
                <div class="form-links">
                    <a href="/forgot-password">Forgot Password?</a>
                    <a href="/register">Create New Account</a>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Load test page
        page = await browser_manager.get_page("stealth")
        await page.set_content(login_html)
        await page.wait_for_load_state('domcontentloaded')
        
        print("📄 Login test page loaded")
        print("🔍 Starting two-layer login form detection...")
        
        # Test login form identification
        login_elements = await vision_analyzer.identify_login_form(page)
        
        print(f"✅ Login detection completed: {len(login_elements)} elements found")
        
        # Validate results
        expected_elements = ['username', 'password', 'submit']
        success = True
        
        for element_name in expected_elements:
            if element_name in login_elements:
                element_data = login_elements[element_name]
                print(f"📍 {element_name}:")
                print(f"   Type: {element_data.get('type', 'unknown')}")
                print(f"   Coordinates: ({element_data.get('x', 0)}, {element_data.get('y', 0)})")
                print(f"   Action: {element_data.get('action', 'unknown')}")
                print(f"   Source: {element_data.get('source', 'unknown')}")
                print(f"   Description: {element_data.get('description', '')}")
                print(f"   Confidence: {element_data.get('confidence', 0):.2f}")
                print()
                
                # Validate coordinates
                if element_data.get('x', 0) > 0 and element_data.get('y', 0) > 0:
                    print(f"   ✓ Valid coordinates detected")
                else:
                    print(f"   ⚠️ Invalid coordinates")
                    success = False
            else:
                print(f"❌ {element_name}: Not detected")
                success = False
        
        # Check if two-layer analysis was used
        sources_used = [elem.get('source', '') for elem in login_elements.values()]
        if any('openai_semantic' in source for source in sources_used):
            print("🧠 ✅ OpenAI semantic analysis successfully used")
        elif any('isa_fallback' in source for source in sources_used):
            print("🔄 ✅ ISA fallback mapping successfully used")
        else:
            print("⚠️ Unknown detection source")
        
        # Clean up
        await browser_manager.cleanup_all()
        await vision_analyzer.close()
        
        return success
        
    except Exception as e:
        print(f"❌ Login detection test failed: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

async def test_search_detection():
    """Test two-layer search form detection"""
    print("\n🔍 Testing Search Form Detection")
    print("=" * 40)
    
    try:
        # Initialize services
        vision_analyzer = VisionAnalyzer()
        browser_manager = BrowserManager()
        
        # Create a comprehensive search page
        search_html = """
        <html>
        <head>
            <title>Search Engine</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: #fff; }
                .search-header { background: #f8f9fa; padding: 60px 20px; text-align: center; }
                .search-container { max-width: 600px; margin: 0 auto; }
                .logo { font-size: 48px; font-weight: bold; color: #4285f4; margin-bottom: 30px; }
                .search-form { margin: 30px 0; }
                .search-wrapper { position: relative; display: flex; max-width: 500px; margin: 0 auto; }
                .search-input { flex: 1; padding: 12px 16px; font-size: 16px; border: 1px solid #ddd; border-radius: 24px 0 0 24px; outline: none; }
                .search-input:focus { border-color: #4285f4; box-shadow: 0 2px 5px rgba(66,133,244,0.3); }
                .search-button { padding: 12px 20px; background: #4285f4; color: white; border: none; border-radius: 0 24px 24px 0; cursor: pointer; font-weight: bold; }
                .search-button:hover { background: #3367d6; }
                .search-suggestions { margin-top: 30px; }
                .suggestion-link { display: inline-block; margin: 0 15px; padding: 8px 16px; color: #1a73e8; text-decoration: none; border-radius: 16px; }
                .suggestion-link:hover { background: #f8f9fa; }
            </style>
        </head>
        <body>
            <div class="search-header">
                <div class="search-container">
                    <div class="logo">SearchEngine</div>
                    
                    <form class="search-form" action="/search" method="get">
                        <div class="search-wrapper">
                            <input type="search" name="q" class="search-input" placeholder="Search the web..." autocomplete="off" required>
                            <button type="submit" class="search-button">🔍 Search</button>
                        </div>
                    </form>
                    
                    <div class="search-suggestions">
                        <a href="/trending" class="suggestion-link">Trending</a>
                        <a href="/news" class="suggestion-link">News</a>
                        <a href="/images" class="suggestion-link">Images</a>
                        <a href="/videos" class="suggestion-link">Videos</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Load test page
        page = await browser_manager.get_page("stealth")
        await page.set_content(search_html)
        await page.wait_for_load_state('domcontentloaded')
        
        print("📄 Search test page loaded")
        print("🔍 Starting two-layer search form detection...")
        
        # Test search form identification
        search_elements = await vision_analyzer.identify_search_form(page)
        
        print(f"✅ Search detection completed: {len(search_elements)} elements found")
        print(f"🔍 Actual keys returned: {list(search_elements.keys())}")
        
        # Validate results
        expected_elements = ['input', 'submit']  # Vision analyzer uses 'input' and 'submit' for search
        success = True
        
        for element_name in expected_elements:
            if element_name in search_elements:
                element_data = search_elements[element_name]
                print(f"📍 {element_name}:")
                
                # Handle different return formats
                if isinstance(element_data, dict):
                    # Coordinate-based format (from two-layer AI)
                    print(f"   Type: {element_data.get('type', 'unknown')}")
                    print(f"   Coordinates: ({element_data.get('x', 0)}, {element_data.get('y', 0)})")
                    print(f"   Action: {element_data.get('action', 'unknown')}")
                    print(f"   Source: {element_data.get('source', 'unknown')}")
                    print(f"   Description: {element_data.get('description', '')}")
                    print(f"   Confidence: {element_data.get('confidence', 0):.2f}")
                    
                    # Validate coordinates
                    if element_data.get('x', 0) > 0 and element_data.get('y', 0) > 0:
                        print(f"   ✓ Valid coordinates detected")
                    else:
                        print(f"   ⚠️ Invalid coordinates")
                        success = False
                        
                elif isinstance(element_data, str):
                    # Selector-based format (from traditional fallback)
                    print(f"   Type: css_selector")
                    print(f"   Selector: {element_data}")
                    print(f"   Source: traditional_fallback")
                    print(f"   ✓ Valid selector detected")
                    
                else:
                    print(f"   ⚠️ Unknown format: {type(element_data)}")
                    success = False
                    
                print()
            else:
                print(f"❌ {element_name}: Not detected")
                success = False
        
        # Check analysis method used
        if 'input' in search_elements or 'submit' in search_elements:
            sources_used = [elem.get('source', '') for elem in search_elements.values()]
            if any('openai_semantic' in source for source in sources_used):
                print("🧠 ✅ OpenAI semantic search analysis successfully used")
            elif any('isa_fallback' in source for source in sources_used):
                print("🔄 ✅ ISA fallback search mapping successfully used")
            else:
                print("📋 ✅ Traditional search detection used")
        
        # Clean up
        await browser_manager.cleanup_all()
        await vision_analyzer.close()
        
        return success
        
    except Exception as e:
        print(f"❌ Search detection test failed: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

async def test_navigation_detection():
    """Test generic UI analysis for navigation elements"""
    print("\n🧭 Testing Navigation Detection")
    print("=" * 40)
    
    try:
        # Initialize services
        vision_analyzer = VisionAnalyzer()
        browser_manager = BrowserManager()
        
        # Create a page with navigation elements
        nav_html = """
        <html>
        <head>
            <title>Navigation Test</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; }
                .navbar { background: #343a40; padding: 15px 0; }
                .nav-container { max-width: 1200px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; }
                .logo { color: #fff; font-size: 24px; font-weight: bold; text-decoration: none; }
                .nav-menu { display: flex; list-style: none; margin: 0; padding: 0; }
                .nav-item { margin: 0 20px; }
                .nav-link { color: #fff; text-decoration: none; padding: 10px 15px; border-radius: 4px; transition: background 0.3s; }
                .nav-link:hover { background: #495057; }
                .nav-button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
                .main-content { padding: 40px 20px; text-align: center; }
                .breadcrumb { background: #f8f9fa; padding: 15px 0; }
                .breadcrumb-container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }
                .breadcrumb a { color: #007bff; text-decoration: none; margin-right: 10px; }
            </style>
        </head>
        <body>
            <nav class="navbar">
                <div class="nav-container">
                    <a href="/" class="logo">MyWebsite</a>
                    <ul class="nav-menu">
                        <li class="nav-item"><a href="/" class="nav-link">Home</a></li>
                        <li class="nav-item"><a href="/about" class="nav-link">About</a></li>
                        <li class="nav-item"><a href="/services" class="nav-link">Services</a></li>
                        <li class="nav-item"><a href="/portfolio" class="nav-link">Portfolio</a></li>
                        <li class="nav-item"><a href="/contact" class="nav-link">Contact</a></li>
                    </ul>
                    <button class="nav-button">Get Started</button>
                </div>
            </nav>
            
            <div class="breadcrumb">
                <div class="breadcrumb-container">
                    <a href="/">Home</a> > 
                    <a href="/services">Services</a> > 
                    <span>Web Development</span>
                </div>
            </div>
            
            <main class="main-content">
                <h1>Navigation Test Page</h1>
                <p>This page contains various navigation elements for testing.</p>
            </main>
        </body>
        </html>
        """
        
        # Load test page
        page = await browser_manager.get_page("stealth")
        await page.set_content(nav_html)
        await page.wait_for_load_state('domcontentloaded')
        
        print("📄 Navigation test page loaded")
        print("🔍 Starting generic UI analysis for navigation...")
        
        # Test generic UI analysis
        ui_analysis = await vision_analyzer.analyze_ui_elements(page, "navigation")
        
        print(f"✅ Navigation analysis completed")
        print(f"📊 Analysis result structure: {list(ui_analysis.keys()) if ui_analysis else 'Empty'}")
        
        success = len(ui_analysis) > 0
        
        if ui_analysis:
            print("📋 UI Analysis Results:")
            for key, value in ui_analysis.items():
                if isinstance(value, dict):
                    print(f"   {key}: {len(value)} items" if isinstance(value, (list, dict)) else f"   {key}: {value}")
                else:
                    print(f"   {key}: {value}")
        else:
            print("⚠️ No navigation analysis results")
            success = False
        
        # Clean up
        await browser_manager.cleanup_all()
        await vision_analyzer.close()
        
        return success
        
    except Exception as e:
        print(f"❌ Navigation detection test failed: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

async def test_link_detection():
    """Test download and link detection"""
    print("\n🔗 Testing Link Detection")
    print("=" * 40)
    
    try:
        # Initialize services
        vision_analyzer = VisionAnalyzer()
        browser_manager = BrowserManager()
        
        # Create a page with various links
        link_html = """
        <html>
        <head>
            <title>Link Detection Test</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 40px; line-height: 1.6; }
                .download-section { background: #f8f9fa; padding: 30px; margin: 20px 0; border-radius: 8px; }
                .download-btn { display: inline-block; background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; margin: 10px; }
                .download-btn:hover { background: #218838; }
                .file-link { display: block; margin: 10px 0; color: #007bff; text-decoration: none; }
                .file-link:hover { text-decoration: underline; }
                .link-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }
                .link-card { background: white; border: 1px solid #ddd; padding: 20px; border-radius: 8px; text-align: center; }
                .link-card a { color: #007bff; text-decoration: none; font-weight: bold; }
            </style>
        </head>
        <body>
            <h1>Link Detection Test Page</h1>
            
            <div class="download-section">
                <h2>Download Files</h2>
                <p>Various downloadable resources:</p>
                
                <a href="/files/document.pdf" class="download-btn" download>📄 Download PDF Report</a>
                <a href="/files/presentation.pptx" class="download-btn" download>📊 Download Presentation</a>
                <a href="/files/spreadsheet.xlsx" class="download-btn" download>📈 Download Spreadsheet</a>
                
                <h3>Direct File Links</h3>
                <a href="/manual.pdf" class="file-link">User Manual (PDF)</a>
                <a href="/setup.exe" class="file-link">Setup Program (EXE)</a>
                <a href="/data.zip" class="file-link">Data Archive (ZIP)</a>
                <a href="/template.docx" class="file-link">Template Document (DOCX)</a>
            </div>
            
            <div class="link-grid">
                <div class="link-card">
                    <h3>Products</h3>
                    <a href="/products">View All Products</a>
                </div>
                <div class="link-card">
                    <h3>Services</h3>
                    <a href="/services">Our Services</a>
                </div>
                <div class="link-card">
                    <h3>Support</h3>
                    <a href="/support">Get Help</a>
                </div>
                <div class="link-card">
                    <h3>About</h3>
                    <a href="/about">About Us</a>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Load test page
        page = await browser_manager.get_page("stealth")
        await page.set_content(link_html)
        await page.wait_for_load_state('domcontentloaded')
        
        print("📄 Link test page loaded")
        print("🔍 Starting download link detection...")
        
        # Test download link identification
        download_links = await vision_analyzer.identify_download_links(page)
        
        print(f"✅ Download link detection completed: {len(download_links)} links found")
        
        success = len(download_links) > 0
        
        if download_links:
            print("📥 Download Links Found:")
            for i, link in enumerate(download_links[:5]):  # Show first 5
                print(f"   {i+1}. Text: '{link.get('text', '')}' | Method: {link.get('detection_method', 'unknown')}")
                if link.get('href'):
                    print(f"      URL: {link.get('href')}")
                if link.get('file_type'):
                    print(f"      Type: {link.get('file_type')}")
        else:
            print("⚠️ No download links detected")
            success = False
        
        # Clean up
        await browser_manager.cleanup_all()
        await vision_analyzer.close()
        
        return success
        
    except Exception as e:
        print(f"❌ Link detection test failed: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

async def main():
    """Run all vision analyzer tests"""
    print("🧪 Complete Vision Analyzer Testing Suite")
    print("Testing two-layer AI analysis: ISA Vision + OpenAI Vision")
    print("=" * 60)
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run all tests
    results = {}
    
    results['login'] = await test_login_detection()
    results['search'] = await test_search_detection()
    results['navigation'] = await test_navigation_detection()
    results['links'] = await test_link_detection()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VISION ANALYZER TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name.title()} Detection: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All vision analyzer tests passed!")
        print("✅ Two-layer AI analysis system working correctly!")
        print("🚀 Ready for production use!")
    else:
        print("⚠️ Some tests failed. Check:")
        print("   - ISA client configuration")
        print("   - OpenAI Vision service availability")  
        print("   - Network connectivity")
        print("   - Model access permissions")
    
    return passed == total

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)