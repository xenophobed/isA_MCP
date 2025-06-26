#!/usr/bin/env python3
"""
Individual Step Tests for Web Automation
Test each automation step independently: Login -> Search -> Download
"""
import asyncio
import json
from pathlib import Path
import sys
sys.path.append('.')

from tools.services.web_services.core.browser_manager import BrowserManager
from tools.services.web_services.core.session_manager import SessionManager
from tools.services.web_services.core.vision_analyzer import VisionAnalyzer
from tools.services.web_services.utils.human_behavior import HumanBehavior
from tools.services.web_services.utils.rate_limiter import RateLimiter

class WebAutomationStepTester:
    """Test individual web automation steps"""
    
    def __init__(self):
        self.browser_manager = None
        self.session_manager = None
        self.vision_analyzer = None
        self.human_behavior = None
        self.rate_limiter = None
        
        # Test URLs
        self.test_sites = {
            "login": "https://httpbin.org/forms/post",  # Simple form for login testing
            "search": "https://duckduckgo.com",        # Search engine
            "download": "https://httpbin.org/uuid"      # Simple download test
        }
    
    async def initialize_services(self):
        """Initialize all required services"""
        print("🔧 Initializing web automation services...")
        
        try:
            self.browser_manager = BrowserManager()
            self.session_manager = SessionManager(self.browser_manager)
            self.vision_analyzer = VisionAnalyzer()
            self.human_behavior = HumanBehavior()
            self.rate_limiter = RateLimiter()
            
            # Initialize browser
            await self.browser_manager.initialize()
            
            print("✅ All services initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Service initialization failed: {e}")
            return False
    
    async def test_step_1_login(self):
        """Test Step 1: Login Functionality"""
        print("\n🔐 STEP 1: TESTING LOGIN FUNCTIONALITY")
        print("-" * 50)
        
        try:
            # Get a page for login testing
            page = await self.session_manager.get_or_create_session("login_test", "automation")
            
            # Navigate to login form
            print(f"📍 Navigating to: {self.test_sites['login']}")
            await page.goto(self.test_sites['login'], wait_until='networkidle')
            
            # Apply human-like behavior
            await self.human_behavior.apply_human_navigation(page)
            
            # Use vision analyzer to identify login form
            print("👁️ Identifying login form elements...")
            login_elements = await self.vision_analyzer.identify_login_form(page)
            
            if login_elements:
                print(f"✅ Login form detected: {list(login_elements.keys())}")
                
                # Test credentials
                test_credentials = {
                    "username": "test_user",
                    "password": "test_password"
                }
                
                # Simulate human typing
                print("⌨️ Testing human-like form filling...")
                if 'username' in login_elements:
                    await self.human_behavior.human_type(page, login_elements['username'], test_credentials['username'])
                    print("  ✅ Username field filled")
                
                if 'password' in login_elements:
                    await self.human_behavior.human_type(page, login_elements['password'], test_credentials['password'])
                    print("  ✅ Password field filled")
                
                # Test form submission (without actually submitting)
                if 'submit' in login_elements:
                    print("  🔍 Submit button detected (not clicking in test)")
                    print("  ✅ Login form interaction test complete")
                
                return {
                    "success": True,
                    "elements_found": list(login_elements.keys()),
                    "form_filled": True,
                    "submit_ready": 'submit' in login_elements
                }
            else:
                print("❌ No login form elements detected")
                return {"success": False, "error": "No login form detected"}
                
        except Exception as e:
            print(f"❌ Login test failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_step_2_search(self):
        """Test Step 2: Search Functionality"""
        print("\n🔍 STEP 2: TESTING SEARCH FUNCTIONALITY")
        print("-" * 50)
        
        try:
            # Get a page for search testing
            page = await self.session_manager.get_or_create_session("search_test", "stealth")
            
            # Navigate to search engine
            print(f"📍 Navigating to: {self.test_sites['search']}")
            await page.goto(self.test_sites['search'], wait_until='networkidle')
            
            # Apply human-like behavior
            await self.human_behavior.apply_human_navigation(page)
            
            # Use vision analyzer to identify search form
            print("👁️ Identifying search form elements...")
            search_elements = await self.vision_analyzer.identify_search_form(page)
            
            if search_elements:
                print(f"✅ Search form detected: {list(search_elements.keys())}")
                
                # Test search query
                test_query = "web automation testing"
                
                # Simulate human typing in search field
                print("⌨️ Testing search query input...")
                if 'input' in search_elements:
                    await self.human_behavior.human_type(page, search_elements['input'], test_query)
                    print(f"  ✅ Search query '{test_query}' entered")
                
                # Test search execution (without actually submitting)
                if 'submit' in search_elements:
                    print("  🔍 Search submit button detected (not clicking in test)")
                    print("  ✅ Search form interaction test complete")
                
                return {
                    "success": True,
                    "elements_found": list(search_elements.keys()),
                    "query_entered": True,
                    "search_ready": 'submit' in search_elements
                }
            else:
                print("❌ No search form elements detected")
                return {"success": False, "error": "No search form detected"}
                
        except Exception as e:
            print(f"❌ Search test failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_step_3_download(self):
        """Test Step 3: Download Functionality"""
        print("\n📥 STEP 3: TESTING DOWNLOAD FUNCTIONALITY")
        print("-" * 50)
        
        try:
            # Get a page for download testing
            page = await self.session_manager.get_or_create_session("download_test", "automation")
            
            # Set up download handling
            downloads = []
            page.on("download", lambda download: downloads.append(download))
            
            # Navigate to download test page
            print(f"📍 Navigating to: {self.test_sites['download']}")
            await page.goto(self.test_sites['download'], wait_until='networkidle')
            
            # Apply human-like behavior
            await self.human_behavior.apply_human_navigation(page)
            
            # Use vision analyzer to identify download links
            print("👁️ Identifying download links...")
            download_links = await self.vision_analyzer.identify_download_links(page)
            
            if download_links:
                print(f"✅ Download links detected: {len(download_links)} links")
                for i, link in enumerate(download_links):
                    print(f"  Link {i+1}: {link.get('text', 'No text')} -> {link.get('href', 'No href')}")
                
                # Test download interaction (without actually downloading)
                print("  🔍 Download links ready for interaction (not downloading in test)")
                print("  ✅ Download detection test complete")
                
                return {
                    "success": True,
                    "links_found": len(download_links),
                    "download_ready": True,
                    "link_details": download_links[:3]  # First 3 links
                }
            else:
                print("❌ No download links detected")
                return {"success": False, "error": "No download links detected"}
                
        except Exception as e:
            print(f"❌ Download test failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_vision_analyzer_only(self):
        """Test vision analyzer without browser (fallback methods)"""
        print("\n👁️ TESTING VISION ANALYZER (FALLBACK METHODS)")
        print("-" * 50)
        
        try:
            # Test basic instantiation
            vision = VisionAnalyzer()
            print("✅ Vision analyzer instantiated")
            
            # Test configuration methods
            screenshots_path = vision.screenshots_path
            monitoring_path = vision.monitoring_path
            print(f"✅ Paths configured: screenshots={screenshots_path}, monitoring={monitoring_path}")
            
            # Test helper methods
            exists = await vision.screenshot_exists("nonexistent.png")
            print(f"✅ Screenshot existence check: {exists}")
            
            return {
                "success": True,
                "vision_analyzer_ready": True,
                "paths_configured": True
            }
            
        except Exception as e:
            print(f"❌ Vision analyzer test failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def run_all_step_tests(self):
        """Run all step tests in sequence"""
        print("🧪 WEB AUTOMATION STEP-BY-STEP TESTING")
        print("=" * 60)
        
        results = {}
        
        # Initialize services first
        if not await self.initialize_services():
            print("❌ Cannot proceed - service initialization failed")
            return {"overall_success": False, "error": "Service initialization failed"}
        
        # Test each step
        test_steps = [
            ("vision_analyzer", self.test_vision_analyzer_only),
            ("login", self.test_step_1_login),
            ("search", self.test_step_2_search),
            ("download", self.test_step_3_download)
        ]
        
        for step_name, test_func in test_steps:
            try:
                print(f"\n{'='*20} {step_name.upper()} TEST {'='*20}")
                result = await test_func()
                results[step_name] = result
                
                if result.get("success"):
                    print(f"✅ {step_name.upper()} TEST: PASSED")
                else:
                    print(f"❌ {step_name.upper()} TEST: FAILED")
                    
            except Exception as e:
                print(f"❌ {step_name.upper()} TEST: ERROR - {e}")
                results[step_name] = {"success": False, "error": str(e)}
        
        # Generate summary
        self.generate_test_summary(results)
        
        # Cleanup
        await self.cleanup()
        
        return results
    
    def generate_test_summary(self, results):
        """Generate test summary"""
        print("\n📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(results)
        passed_tests = sum(1 for result in results.values() if result.get("success"))
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests / total_tests * 100):.1f}%")
        
        print(f"\nDetailed Results:")
        for step_name, result in results.items():
            status = "✅ PASS" if result.get("success") else "❌ FAIL"
            print(f"  {status} {step_name}")
            if not result.get("success") and "error" in result:
                print(f"         Error: {result['error']}")
        
        # Save results
        results_file = Path("test_results_web_automation_steps.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n📄 Detailed results saved to: {results_file}")
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.browser_manager:
                await self.browser_manager.cleanup_all()
            print("🧹 Cleanup completed")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")

# Individual test functions for manual testing
async def test_only_login():
    """Test only login step"""
    tester = WebAutomationStepTester()
    if await tester.initialize_services():
        result = await tester.test_step_1_login()
        await tester.cleanup()
        return result
    return {"success": False, "error": "Initialization failed"}

async def test_only_search():
    """Test only search step"""
    tester = WebAutomationStepTester()
    if await tester.initialize_services():
        result = await tester.test_step_2_search()
        await tester.cleanup()
        return result
    return {"success": False, "error": "Initialization failed"}

async def test_only_download():
    """Test only download step"""
    tester = WebAutomationStepTester()
    if await tester.initialize_services():
        result = await tester.test_step_3_download()
        await tester.cleanup()
        return result
    return {"success": False, "error": "Initialization failed"}

async def test_only_vision():
    """Test only vision analyzer"""
    tester = WebAutomationStepTester()
    result = await tester.test_vision_analyzer_only()
    return result

if __name__ == "__main__":
    print("🧪 Web Automation Step Testing")
    print("Choose test:")
    print("1. Vision analyzer only (no browser)")
    print("2. Login step only")
    print("3. Search step only") 
    print("4. Download step only")
    print("5. All steps")
    
    import sys
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("Enter choice (1-5): ").strip()
    
    if choice == "1":
        result = asyncio.run(test_only_vision())
        print(f"\nResult: {json.dumps(result, indent=2)}")
    elif choice == "2":
        result = asyncio.run(test_only_login())
        print(f"\nResult: {json.dumps(result, indent=2)}")
    elif choice == "3":
        result = asyncio.run(test_only_search())
        print(f"\nResult: {json.dumps(result, indent=2)}")
    elif choice == "4":
        result = asyncio.run(test_only_download())
        print(f"\nResult: {json.dumps(result, indent=2)}")
    elif choice == "5":
        tester = WebAutomationStepTester()
        results = asyncio.run(tester.run_all_step_tests())
    else:
        print("Invalid choice. Running vision analyzer test...")
        result = asyncio.run(test_only_vision())
        print(f"\nResult: {json.dumps(result, indent=2)}")