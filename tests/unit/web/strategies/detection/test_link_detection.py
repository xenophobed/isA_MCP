#!/usr/bin/env python3
"""
Test for Link Detection in Intelligent Element Detection System
Validates link detection capabilities for automation workflows
"""
import asyncio
import os
import sys

# Add parent directory to path  
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

async def test_product_link_detection():
    """Test detection of product links on e-commerce pages"""
    print("🛒 Testing Product Link Detection")
    print("=" * 40)
    
    try:
        from tools.services.web_services.strategies.detection import IntelligentElementDetector, ElementType
        from tools.services.web_services.core.browser_manager import BrowserManager
        
        # Create test HTML content with product links
        test_html = """
        <html>
        <head><title>E-commerce Product Page</title></head>
        <body>
            <header>
                <nav class="navbar">
                    <a href="/" class="nav-link">Home</a>
                    <a href="/categories" class="nav-link">Categories</a>
                    <a href="/cart" class="nav-link">Cart</a>
                </nav>
            </header>
            
            <main class="product-grid">
                <h1>Featured Products</h1>
                
                <div class="product-item">
                    <img src="/airpods.jpg" alt="AirPods Pro">
                    <h3>AirPods Pro</h3>
                    <p class="price">$249.99</p>
                    <a href="/product/airpods-pro" class="product-link btn-primary">View Details</a>
                    <button class="add-to-cart" data-product="airpods">Add to Cart</button>
                </div>
                
                <div class="product-item">
                    <img src="/macbook.jpg" alt="MacBook Air">
                    <h3>MacBook Air</h3>
                    <p class="price">$999.99</p>
                    <a href="/product/macbook-air-m2" class="product-link">Shop Now</a>
                    <button class="add-to-cart" data-product="macbook">Add to Cart</button>
                </div>
                
                <div class="product-item">
                    <img src="/iphone.jpg" alt="iPhone 15">
                    <h3>iPhone 15 Pro</h3>
                    <p class="price">$1099.99</p>
                    <a href="/p/iphone-15-pro" class="item-link">Learn More</a>
                    <button class="add-to-cart" data-product="iphone">Add to Cart</button>
                </div>
            </main>
            
            <footer>
                <div class="footer-links">
                    <a href="/about" class="footer-link">About Us</a>
                    <a href="/support" class="footer-link">Support</a>
                    <a href="/contact" class="footer-link">Contact</a>
                </div>
            </footer>
            
            <style>
                .navbar { display: flex; gap: 20px; background: #f8f9fa; padding: 15px; }
                .nav-link { color: #007bff; text-decoration: none; padding: 10px; }
                .product-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 30px; padding: 40px; }
                .product-item { border: 1px solid #ddd; padding: 20px; text-align: center; }
                .product-link { display: inline-block; background: #007bff; color: white; padding: 12px 24px; text-decoration: none; margin: 10px; }
                .item-link { color: #28a745; text-decoration: none; font-weight: bold; }
                .add-to-cart { background: #17a2b8; color: white; border: none; padding: 10px 20px; cursor: pointer; }
                .footer-links { display: flex; gap: 15px; justify-content: center; padding: 20px; background: #343a40; }
                .footer-link { color: #6c757d; text-decoration: none; }
            </style>
        </body>
        </html>
        """
        
        # Initialize browser and detector
        browser_manager = BrowserManager()
        page = await browser_manager.get_page("stealth")
        await page.set_content(test_html)
        
        detector = IntelligentElementDetector()
        
        print("✅ Intelligent detector initialized")
        print("📄 Test page loaded with product links")
        
        # Test product link detection
        target_links = ['product_links', 'navigation_links']
        results = await detector.detect_link_elements(page, target_links)
        
        print(f"✅ Link detection completed: {len(results)} link types found")
        
        # Validate results
        success = True
        for link_type in target_links:
            if link_type in results:
                result = results[link_type]
                print(f"🔗 {link_type}:")
                print(f"   Type: {result.element_type.value}")
                print(f"   Strategy: {result.strategy.value}")
                print(f"   Coordinates: ({result.x:.1f}, {result.y:.1f})")
                print(f"   Size: {result.width:.1f} x {result.height:.1f}")
                print(f"   Confidence: {result.confidence:.2f}")
                print(f"   Text: {result.metadata.get('text', 'N/A')[:50]}...")
                print(f"   URL: {result.metadata.get('href', 'N/A')}")
                
                # Validate element type
                if result.element_type == ElementType.LINK:
                    print(f"   ✓ Correct element type detected")
                else:
                    print(f"   ⚠️ Unexpected element type: {result.element_type.value}")
                
                # Validate coordinates are reasonable
                if result.x > 0 and result.y > 0:
                    print(f"   ✓ Valid coordinates detected")
                else:
                    print(f"   ⚠️ Suspicious coordinates detected")
                    success = False
            else:
                print(f"❌ {link_type}: Not detected")
                success = False
        
        # Additional test: detect specific product links
        print(f"\n🎯 Testing Specific Product Link Detection:")
        specific_links = await detector.detect_generic_elements(page, [
            "AirPods Pro product link",
            "MacBook Air shop link", 
            "iPhone 15 learn more link"
        ])
        
        print(f"   Found {len(specific_links)} specific product links")
        for i, link in enumerate(specific_links):
            print(f"   Link {i+1}: {link.metadata.get('text', 'N/A')[:30]}... -> {link.metadata.get('href', 'N/A')}")
        
        if len(specific_links) >= 2:
            print(f"   ✅ Successfully detected specific product links")
        else:
            print(f"   ⚠️ Could not detect enough specific product links")
        
        # Clean up
        await detector.close()
        await browser_manager.cleanup_all()
        
        return success
        
    except Exception as e:
        print(f"❌ Product link detection test failed: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

async def test_navigation_link_detection():
    """Test detection of navigation and menu links"""
    print("\n🧭 Testing Navigation Link Detection")
    print("=" * 40)
    
    try:
        from tools.services.web_services.strategies.detection import IntelligentElementDetector, ElementType
        from tools.services.web_services.core.browser_manager import BrowserManager
        
        # Create test HTML with complex navigation
        test_html = """
        <html>
        <head><title>Navigation Test Page</title></head>
        <body>
            <header class="site-header">
                <nav class="main-navigation" role="navigation">
                    <div class="navbar-brand">
                        <a href="/" class="logo-link">Company</a>
                    </div>
                    
                    <ul class="nav-menu">
                        <li><a href="/products" class="nav-link">Products</a></li>
                        <li><a href="/services" class="nav-link">Services</a></li>
                        <li><a href="/about" class="nav-link">About</a></li>
                        <li><a href="/contact" class="nav-link">Contact</a></li>
                    </ul>
                    
                    <div class="nav-actions">
                        <a href="/login" class="action-link btn-outline">Sign In</a>
                        <a href="/register" class="action-link btn-primary">Get Started</a>
                    </div>
                </nav>
            </header>
            
            <aside class="sidebar">
                <nav class="category-nav">
                    <h3>Categories</h3>
                    <ul>
                        <li><a href="/tech" class="category-link">Technology</a></li>
                        <li><a href="/business" class="category-link">Business</a></li>
                        <li><a href="/health" class="category-link">Health</a></li>
                    </ul>
                </nav>
            </aside>
            
            <main class="content">
                <div class="breadcrumb">
                    <a href="/" class="breadcrumb-link">Home</a> > 
                    <a href="/category" class="breadcrumb-link">Category</a> > 
                    <span>Current Page</span>
                </div>
                
                <section class="cta-section">
                    <h2>Take Action Now</h2>
                    <div class="action-buttons">
                        <a href="/demo" class="cta-link big-button">Request Demo</a>
                        <a href="/trial" class="cta-link secondary-button">Free Trial</a>
                    </div>
                </section>
            </main>
            
            <style>
                .site-header { background: #2c3e50; color: white; padding: 15px 0; }
                .main-navigation { display: flex; justify-content: space-between; align-items: center; max-width: 1200px; margin: 0 auto; }
                .nav-menu { display: flex; list-style: none; gap: 30px; margin: 0; padding: 0; }
                .nav-link { color: white; text-decoration: none; padding: 10px 15px; }
                .action-link { padding: 8px 16px; text-decoration: none; border-radius: 4px; margin-left: 10px; }
                .btn-outline { border: 1px solid white; color: white; }
                .btn-primary { background: #e74c3c; color: white; }
                .sidebar { width: 250px; float: left; padding: 20px; background: #ecf0f1; }
                .category-link { color: #34495e; text-decoration: none; display: block; padding: 8px 0; }
                .breadcrumb { margin: 20px 0; }
                .breadcrumb-link { color: #3498db; text-decoration: none; }
                .cta-section { text-align: center; padding: 60px 20px; }
                .big-button { background: #e67e22; color: white; padding: 15px 30px; text-decoration: none; font-size: 18px; margin: 10px; }
                .secondary-button { background: #95a5a6; color: white; padding: 15px 30px; text-decoration: none; margin: 10px; }
            </style>
        </body>
        </html>
        """
        
        # Initialize browser and detector
        browser_manager = BrowserManager()
        page = await browser_manager.get_page("stealth")
        await page.set_content(test_html)
        
        detector = IntelligentElementDetector()
        
        print("✅ Intelligent detector initialized")
        print("📄 Test page loaded with navigation links")
        
        # Test navigation link detection
        target_links = ['navigation_links', 'action_links']
        results = await detector.detect_link_elements(page, target_links)
        
        print(f"✅ Navigation detection completed: {len(results)} link types found")
        
        # Validate results
        success = True
        for link_type in target_links:
            if link_type in results:
                result = results[link_type]
                print(f"🧭 {link_type}:")
                print(f"   Type: {result.element_type.value}")
                print(f"   Strategy: {result.strategy.value}")
                print(f"   Coordinates: ({result.x:.1f}, {result.y:.1f})")
                print(f"   Confidence: {result.confidence:.2f}")
                print(f"   Text: {result.metadata.get('text', 'N/A')}")
                print(f"   URL: {result.metadata.get('href', 'N/A')}")
                
                if result.element_type == ElementType.LINK:
                    print(f"   ✓ Correct element type detected")
                else:
                    print(f"   ⚠️ Unexpected element type: {result.element_type.value}")
                
                if result.x > 0 and result.y > 0:
                    print(f"   ✓ Valid coordinates detected")
                else:
                    print(f"   ⚠️ Suspicious coordinates detected")
                    success = False
            else:
                print(f"❌ {link_type}: Not detected")
                success = False
        
        # Test specific navigation elements
        print(f"\n🎯 Testing Specific Navigation Elements:")
        navigation_descriptions = [
            "main navigation menu link",
            "call to action button link",
            "breadcrumb navigation link"
        ]
        
        nav_results = await detector.detect_generic_elements(page, navigation_descriptions)
        
        print(f"   Found {len(nav_results)} specific navigation elements")
        for i, nav_link in enumerate(nav_results):
            description = navigation_descriptions[i] if i < len(navigation_descriptions) else "unknown"
            print(f"   Nav {i+1} ('{description}'): {nav_link.metadata.get('text', 'N/A')[:30]}...")
        
        if len(nav_results) >= 2:
            print(f"   ✅ Successfully detected specific navigation elements")
        else:
            print(f"   ⚠️ Could not detect enough navigation elements")
        
        # Clean up
        await detector.close()
        await browser_manager.cleanup_all()
        
        return success
        
    except Exception as e:
        print(f"❌ Navigation link detection test failed: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

async def test_link_click_automation():
    """Test that detected links can be clicked for automation"""
    print("\n🖱️ Testing Link Click Automation")
    print("=" * 40)
    
    try:
        from tools.services.web_services.strategies.detection import IntelligentElementDetector
        from tools.services.web_services.core.browser_manager import BrowserManager
        
        # Create test HTML with clickable links
        test_html = """
        <html>
        <head><title>Click Test Page</title></head>
        <body>
            <div id="status">Ready</div>
            
            <nav class="test-nav">
                <a href="#" onclick="updateStatus('Home clicked')" class="nav-item">Home</a>
                <a href="#" onclick="updateStatus('Products clicked')" class="nav-item">Products</a>
                <a href="#" onclick="updateStatus('Contact clicked')" class="nav-item">Contact</a>
            </nav>
            
            <div class="action-area">
                <a href="#" onclick="updateStatus('Big button clicked')" class="big-action-btn">Click Me!</a>
                <button onclick="updateStatus('Regular button clicked')" class="regular-btn">Button</button>
            </div>
            
            <script>
                function updateStatus(message) {
                    document.getElementById('status').textContent = message;
                }
            </script>
            
            <style>
                .test-nav { margin: 20px 0; }
                .nav-item { margin: 0 15px; color: blue; text-decoration: none; padding: 10px; }
                .action-area { margin: 40px 0; text-align: center; }
                .big-action-btn { background: red; color: white; padding: 20px 40px; text-decoration: none; font-size: 18px; }
                .regular-btn { background: green; color: white; padding: 15px 30px; border: none; cursor: pointer; }
                #status { font-weight: bold; padding: 20px; background: #f0f0f0; }
            </style>
        </body>
        </html>
        """
        
        # Initialize browser and detector
        browser_manager = BrowserManager()
        page = await browser_manager.get_page("stealth")
        await page.set_content(test_html)
        
        detector = IntelligentElementDetector()
        
        print("✅ Detector initialized for click testing")
        print("📄 Interactive test page loaded")
        
        # Detect clickable elements
        clickable_descriptions = [
            "big red action button",
            "navigation link for Products",
            "green regular button"
        ]
        
        clickable_elements = await detector.detect_generic_elements(page, clickable_descriptions)
        
        print(f"✅ Found {len(clickable_elements)} clickable elements")
        
        success = True
        clicked_count = 0
        
        # Test clicking each detected element
        for i, element in enumerate(clickable_elements):
            try:
                description = clickable_descriptions[i] if i < len(clickable_descriptions) else f"Element {i+1}"
                print(f"🖱️ Testing click on: {description}")
                print(f"   Coordinates: ({element.x:.1f}, {element.y:.1f})")
                
                # Click at the detected coordinates
                await page.mouse.click(element.x, element.y)
                
                # Wait a bit for the action to take effect
                await page.wait_for_timeout(500)
                
                # Check if the status was updated (indicates successful click)
                status_text = await page.locator('#status').text_content()
                print(f"   Status after click: '{status_text}'")
                
                if status_text != "Ready":
                    print(f"   ✅ Click successful - page responded")
                    clicked_count += 1
                else:
                    print(f"   ⚠️ Click may not have registered")
                
            except Exception as e:
                print(f"   ❌ Click failed: {e}")
                success = False
        
        # Validate automation capability
        if clicked_count >= len(clickable_elements) // 2:
            print(f"\n✅ Link automation test successful!")
            print(f"   Successfully clicked {clicked_count}/{len(clickable_elements)} detected elements")
        else:
            print(f"\n⚠️ Link automation needs improvement")
            print(f"   Only {clicked_count}/{len(clickable_elements)} clicks succeeded")
            success = False
        
        # Clean up
        await detector.close()
        await browser_manager.cleanup_all()
        
        return success
        
    except Exception as e:
        print(f"❌ Link click automation test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Starting Link Detection Tests...")
    print("🔗 Testing intelligent link detection for web automation")
    print("")
    
    async def run_tests():
        test1 = await test_product_link_detection()
        test2 = await test_navigation_link_detection() 
        test3 = await test_link_click_automation()
        
        return test1 and test2 and test3
    
    result = asyncio.run(run_tests())
    if result:
        print("\n🎉 All link detection tests passed!")
        print("✅ Link detection system working correctly!")
        print("🔗 Ready for web automation workflows!")
        print("🚀 AirPods integration tests can proceed!")
    else:
        print("\n❌ Some link detection tests failed!")
        print("⚠️ Please check:")
        print("   - Element detection accuracy")
        print("   - Click coordinate precision")
        print("   - Automation integration")
    
    sys.exit(0 if result else 1)