#!/usr/bin/env python3
"""
Test for Intelligent Element Detection System
Validates multi-strategy element detection with precise coordinate positioning
"""
import asyncio
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

async def test_intelligent_login_detection():
    """Test intelligent login form detection with multi-strategy approach"""
    print("🧠 Testing Intelligent Login Detection")
    print("=" * 40)
    
    try:
        from tools.services.web_services.strategies.detection import IntelligentElementDetector, DetectionStrategy
        from tools.services.web_services.core.browser_manager import BrowserManager
        
        # Create test HTML content with login form
        test_html = """
        <html>
        <head><title>Login Test Page</title></head>
        <body>
            <div class="login-container">
                <h1>Welcome - Please Login</h1>
                
                <form class="login-form" action="/login" method="post">
                    <div class="form-group">
                        <label for="username">Email Address</label>
                        <input type="email" id="username" name="email" placeholder="Enter your email" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password" placeholder="Enter your password" required>
                    </div>
                    
                    <div class="form-group">
                        <button type="submit" class="login-btn">Login to Account</button>
                    </div>
                    
                    <div class="form-links">
                        <a href="/forgot">Forgot Password?</a>
                        <a href="/register">Create Account</a>
                    </div>
                </form>
            </div>
            
            <style>
                .login-container { max-width: 400px; margin: 50px auto; padding: 30px; border: 1px solid #ddd; }
                .form-group { margin: 15px 0; }
                input { width: 100%; padding: 10px; border: 1px solid #ccc; }
                .login-btn { width: 100%; padding: 12px; background: #007bff; color: white; border: none; cursor: pointer; }
                .form-links { margin-top: 20px; text-align: center; }
                .form-links a { margin: 0 10px; color: #007bff; text-decoration: none; }
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
        print("📄 Test page loaded with login form")
        
        # Test intelligent detection
        target_elements = ['username', 'password', 'submit']
        results = await detector.detect_login_elements(page, target_elements)
        
        print(f"✅ Detection completed: {len(results)} elements found")
        
        # Validate results
        success = True
        for element_name in target_elements:
            if element_name in results:
                result = results[element_name]
                print(f"📍 {element_name}:")
                print(f"   Strategy: {result.strategy.value}")
                print(f"   Coordinates: ({result.x:.1f}, {result.y:.1f})")
                print(f"   Size: {result.width:.1f} x {result.height:.1f}")
                print(f"   Confidence: {result.confidence:.2f}")
                print(f"   Description: {result.description}")
                
                # Validate coordinates are reasonable (not 0,0)
                if result.x > 0 and result.y > 0:
                    print(f"   ✓ Valid coordinates detected")
                else:
                    print(f"   ⚠️ Suspicious coordinates detected")
                    success = False
            else:
                print(f"❌ {element_name}: Not detected")
                success = False
        
        # Test strategy preferences
        print(f"\n🎯 Strategy Analysis:")
        strategies_used = [result.strategy.value for result in results.values()]
        strategy_counts = {strategy: strategies_used.count(strategy) for strategy in set(strategies_used)}
        
        for strategy, count in strategy_counts.items():
            print(f"   {strategy}: {count} elements")
        
        # Prefer higher accuracy strategies
        if any(result.strategy == DetectionStrategy.STACKED_AI for result in results.values()):
            print("   ✅ Stacked AI strategy successfully used")
        elif any(result.strategy == DetectionStrategy.TRADITIONAL for result in results.values()):
            print("   ✅ Traditional strategy successfully used as fallback")
        else:
            print("   ⚠️ Only lower-accuracy strategies used")
        
        # Clean up
        await detector.close()
        await browser_manager.cleanup_all()
        
        return success
        
    except Exception as e:
        print(f"❌ Intelligent login detection test failed: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

async def test_intelligent_search_detection():
    """Test intelligent search form detection"""
    print("\n🔍 Testing Intelligent Search Detection")
    print("=" * 35)
    
    try:
        from tools.services.web_services.strategies.detection import IntelligentElementDetector, ElementType
        from tools.services.web_services.core.browser_manager import BrowserManager
        
        # Create test HTML with search form
        test_html = """
        <html>
        <head><title>Search Test Page</title></head>
        <body>
            <header class="search-header">
                <div class="search-container">
                    <h1>Search Engine</h1>
                    
                    <form class="search-form" action="/search" method="get">
                        <div class="search-box">
                            <input type="search" name="q" placeholder="Search the web..." class="search-input" required>
                            <button type="submit" class="search-button">🔍 Search</button>
                        </div>
                    </form>
                    
                    <div class="search-suggestions">
                        <a href="/trending">Trending</a>
                        <a href="/news">News</a>
                        <a href="/images">Images</a>
                    </div>
                </div>
            </header>
            
            <style>
                .search-header { background: #f8f9fa; padding: 40px 0; text-align: center; }
                .search-container { max-width: 600px; margin: 0 auto; }
                .search-box { display: flex; margin: 20px 0; }
                .search-input { flex: 1; padding: 12px; font-size: 16px; border: 1px solid #ddd; }
                .search-button { padding: 12px 24px; background: #4285f4; color: white; border: none; cursor: pointer; }
                .search-suggestions a { margin: 0 15px; color: #1a73e8; text-decoration: none; }
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
        print("📄 Test page loaded with search form")
        
        # Test search detection
        target_elements = ['search_input', 'search_button']
        results = await detector.detect_search_elements(page, target_elements)
        
        print(f"✅ Search detection completed: {len(results)} elements found")
        
        # Validate results
        success = True
        for element_name in target_elements:
            if element_name in results:
                result = results[element_name]
                print(f"📍 {element_name}:")
                print(f"   Type: {result.element_type.value}")
                print(f"   Strategy: {result.strategy.value}")
                print(f"   Coordinates: ({result.x:.1f}, {result.y:.1f})")
                print(f"   Confidence: {result.confidence:.2f}")
                
                # Validate element types
                if element_name == 'search_input' and result.element_type == ElementType.INPUT_SEARCH:
                    print(f"   ✓ Correct element type detected")
                elif element_name == 'search_button' and result.element_type in [ElementType.BUTTON_SUBMIT, ElementType.BUTTON_GENERIC]:
                    print(f"   ✓ Correct element type detected")
                else:
                    print(f"   ⚠️ Unexpected element type: {result.element_type.value}")
                
                if result.x > 0 and result.y > 0:
                    print(f"   ✓ Valid coordinates detected")
                else:
                    print(f"   ⚠️ Suspicious coordinates detected")
                    success = False
            else:
                print(f"❌ {element_name}: Not detected")
                success = False
        
        # Clean up
        await detector.close()
        await browser_manager.cleanup_all()
        
        return success
        
    except Exception as e:
        print(f"❌ Intelligent search detection test failed: {e}")
        return False

async def test_generic_element_detection():
    """Test generic element detection with natural language descriptions"""
    print("\n🎯 Testing Generic Element Detection")
    print("=" * 35)
    
    try:
        from tools.services.web_services.strategies.detection import IntelligentElementDetector
        from tools.services.web_services.core.browser_manager import BrowserManager
        
        # Create test HTML with various elements
        test_html = """
        <html>
        <head><title>Generic Elements Test</title></head>
        <body>
            <header>
                <nav>
                    <a href="/" class="logo">Company Logo</a>
                    <a href="/about">About Us</a>
                    <a href="/contact">Contact</a>
                </nav>
            </header>
            
            <main>
                <section class="hero">
                    <h1>Welcome to Our Service</h1>
                    <p>Discover amazing features and capabilities</p>
                    <button class="cta-button red-button">Get Started Now</button>
                    <button class="secondary-button">Learn More</button>
                </section>
                
                <section class="features">
                    <div class="feature-card">
                        <h3>Feature 1</h3>
                        <p>Amazing capability</p>
                        <button class="feature-btn blue-button">Try It</button>
                    </div>
                    
                    <div class="feature-card">
                        <h3>Feature 2</h3>
                        <p>Another great feature</p>
                        <button class="feature-btn green-button">Explore</button>
                    </div>
                </section>
            </main>
            
            <style>
                .red-button { background: #dc3545; color: white; padding: 15px 30px; border: none; font-size: 18px; }
                .blue-button { background: #007bff; color: white; padding: 10px 20px; border: none; }
                .green-button { background: #28a745; color: white; padding: 10px 20px; border: none; }
                .secondary-button { background: #6c757d; color: white; padding: 15px 30px; border: none; }
                .feature-card { margin: 20px; padding: 20px; border: 1px solid #ddd; }
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
        print("📄 Test page loaded with various elements")
        
        # Test generic detection with natural language
        descriptions = [
            "red button that says Get Started",
            "blue button in the features section",
            "company logo link",
            "green button with Explore text"
        ]
        
        results = await detector.detect_generic_elements(page, descriptions)
        
        print(f"✅ Generic detection completed: {len(results)} elements found")
        
        # Validate results
        success = len(results) > 0
        
        for i, result in enumerate(results):
            description = descriptions[i] if i < len(descriptions) else "unknown"
            print(f"📍 Element {i+1} ('{description}'):")
            print(f"   Type: {result.element_type.value}")
            print(f"   Strategy: {result.strategy.value}")
            print(f"   Coordinates: ({result.x:.1f}, {result.y:.1f})")
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Description: {result.description}")
            
            if result.confidence > 0.5:
                print(f"   ✓ Good confidence level")
            else:
                print(f"   ⚠️ Low confidence level")
        
        if len(results) >= len(descriptions) // 2:
            print(f"   ✅ Found at least half of the target elements")
        else:
            print(f"   ⚠️ Found fewer elements than expected")
            success = False
        
        # Clean up
        await detector.close()
        await browser_manager.cleanup_all()
        
        return success
        
    except Exception as e:
        print(f"❌ Generic element detection test failed: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

async def test_detection_strategy_fallback():
    """Test that fallback strategies work when higher-level strategies fail"""
    print("\n🔄 Testing Detection Strategy Fallback")
    print("=" * 35)
    
    try:
        from tools.services.web_services.strategies.detection import IntelligentElementDetector, DetectionStrategy
        from tools.services.web_services.core.browser_manager import BrowserManager
        
        # Create simple HTML that should work with traditional selectors
        test_html = """
        <html>
        <body>
            <form>
                <input type="text" name="username" placeholder="Username">
                <input type="password" name="password" placeholder="Password">
                <button type="submit">Login</button>
            </form>
        </body>
        </html>
        """
        
        browser_manager = BrowserManager()
        page = await browser_manager.get_page("stealth")
        await page.set_content(test_html)
        
        detector = IntelligentElementDetector()
        
        print("✅ Simple form loaded for fallback testing")
        
        # Test detection (should fallback to traditional if AI fails)
        results = await detector.detect_login_elements(page)
        
        print(f"✅ Fallback detection completed: {len(results)} elements found")
        
        # Check that we got some results using any strategy
        success = len(results) >= 2  # At least username and password
        
        strategies_used = {result.strategy for result in results.values()}
        print(f"📊 Strategies used: {[s.value for s in strategies_used]}")
        
        # Verify traditional fallback works
        if DetectionStrategy.TRADITIONAL in strategies_used:
            print("   ✅ Traditional fallback strategy working")
        
        if DetectionStrategy.STACKED_AI in strategies_used:
            print("   ✅ Stacked AI strategy working")
        
        if success:
            print("   ✅ Fallback system functioning correctly")
        else:
            print("   ❌ Fallback system failed to detect elements")
        
        # Clean up
        await detector.close()
        await browser_manager.cleanup_all()
        
        return success
        
    except Exception as e:
        print(f"❌ Fallback strategy test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Starting Intelligent Element Detection Tests...")
    print("📝 Testing multi-strategy detection with coordinate precision")
    print("")
    
    async def run_tests():
        test1 = await test_intelligent_login_detection()
        test2 = await test_intelligent_search_detection()
        test3 = await test_generic_element_detection()
        test4 = await test_detection_strategy_fallback()
        
        return test1 and test2 and test3 and test4
    
    result = asyncio.run(run_tests())
    if result:
        print("\n🎉 All intelligent element detection tests passed!")
        print("✅ Multi-strategy detection system working correctly!")
        print("🎯 Precise coordinate positioning validated!")
        print("🚀 Ready for production use!")
    else:
        print("\n❌ Some intelligent element detection tests failed!")
        print("⚠️ Please check:")
        print("   - AI services configuration")
        print("   - Network connectivity")
        print("   - Browser automation setup")
    
    sys.exit(0 if result else 1)