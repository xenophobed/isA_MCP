#!/usr/bin/env python3
"""
Test for automate_web_login function with detailed logging
"""
import json
import asyncio
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def test_login_automation_standalone():
    """Standalone test for login automation with detailed logging"""
    print("🚀 STANDALONE LOGIN AUTOMATION TEST")
    print("=" * 50)
    
    # Test URL - the-internet.herokuapp.com provides a reliable test login page
    test_url = "https://the-internet.herokuapp.com/login"
    test_credentials = "username=tomsmith password=SuperSecretPassword!"
    
    print(f"📍 Test URL: {test_url}")
    print(f"🔑 Test credentials: {test_credentials}")
    
    try:
        # Import the web tools module and initialize services
        import tools.web_tools as web_tools
        
        print("\n📋 Step 1: Initializing web services...")
        await web_tools._initialize_services()
        print("✅ Web services initialized successfully")
        
        print("\n📋 Step 2: Testing login automation manually...")
        start_time = datetime.now()
        
        # Manual implementation of login automation with detailed logging
        print("   🔍 Parsing credentials...")
        if isinstance(test_credentials, dict):
            creds = test_credentials
        else:
            try:
                creds = json.loads(test_credentials)
            except json.JSONDecodeError:
                creds = {}
                if '=' in test_credentials:
                    parts = test_credentials.split()
                    for part in parts:
                        if '=' in part:
                            key, value = part.split('=', 1)
                            creds[key.strip()] = value.strip()
                
                if not creds:
                    import re
                    username_match = re.search(r'username[=:\s]+([^\s,&]+)', test_credentials, re.IGNORECASE)
                    password_match = re.search(r'password[=:\s]+([^\s,&!]+[!]?)', test_credentials, re.IGNORECASE)
                    
                    if username_match and password_match:
                        creds = {
                            'username': username_match.group(1),
                            'password': password_match.group(1)
                        }
        
        print(f"   ✅ Parsed credentials: username={creds.get('username', 'N/A')}, password={'*' * len(creds.get('password', ''))}")
        
        print("\n   🔍 Creating browser session...")
        session_id = f"test_login_{hash(test_url)}"
        page = await web_tools._session_manager.get_or_create_session(session_id, "stealth")
        print(f"   ✅ Browser session created with ID: {session_id}")
        
        print("\n   🔍 Applying human-like behavior...")
        await web_tools._human_behavior.apply_human_navigation(page)
        print("   ✅ Human behavior patterns applied")
        
        print("\n   🔍 Navigating to login page...")
        await page.goto(test_url, wait_until='networkidle')
        current_title = await page.title()
        print(f"   ✅ Navigated to page. Title: {current_title}")
        
        print("\n   🔍 Identifying login form elements...")
        login_elements = await web_tools._vision_analyzer.identify_login_form(page)
        print(f"   ✅ Login elements identified: {login_elements}")
        
        print("\n   🔍 Filling username field...")
        username_ref = login_elements.get('username', '')
        print(f"      Username reference: {username_ref}")
        
        # Debug: Check what's actually at those coordinates before typing
        if isinstance(username_ref, dict) and username_ref.get('type') == 'coordinate':
            x, y = username_ref['x'], username_ref['y']
            element_info = await page.evaluate(f"""
                () => {{
                    const element = document.elementFromPoint({x}, {y});
                    if (element) {{
                        return {{
                            tagName: element.tagName,
                            type: element.type || 'N/A',
                            id: element.id || 'N/A',
                            name: element.name || 'N/A',
                            placeholder: element.placeholder || 'N/A',
                            value: element.value || 'N/A'
                        }};
                    }}
                    return null;
                }}
            """)
            print(f"      🔍 Element at ({x}, {y}): {element_info}")
        
        await web_tools._human_behavior.human_type(page, username_ref, creds.get('username', ''))
        print("   ✅ Username entered with human-like typing")
        
        # Debug: Check if username was actually entered
        if isinstance(username_ref, dict) and username_ref.get('type') == 'coordinate':
            x, y = username_ref['x'], username_ref['y']
            value_check = await page.evaluate(f"""
                () => {{
                    const element = document.elementFromPoint({x}, {y});
                    return element ? element.value : 'No element found';
                }}
            """)
            print(f"      🔍 Username field value after typing: '{value_check}'")
        
        print("\n   🔍 Adding random delay...")
        await web_tools._human_behavior.random_delay(500, 1500)
        print("   ✅ Random delay completed")
        
        print("\n   🔍 Filling password field...")
        password_ref = login_elements.get('password', '')
        print(f"      Password reference: {password_ref}")
        
        # Debug: Check what's actually at those coordinates before typing
        if isinstance(password_ref, dict) and password_ref.get('type') == 'coordinate':
            x, y = password_ref['x'], password_ref['y']
            element_info = await page.evaluate(f"""
                () => {{
                    const element = document.elementFromPoint({x}, {y});
                    if (element) {{
                        return {{
                            tagName: element.tagName,
                            type: element.type || 'N/A',
                            id: element.id || 'N/A',
                            name: element.name || 'N/A',
                            placeholder: element.placeholder || 'N/A',
                            value: element.value || 'N/A'
                        }};
                    }}
                    return null;
                }}
            """)
            print(f"      🔍 Element at ({x}, {y}): {element_info}")
        
        await web_tools._human_behavior.human_type(page, password_ref, creds.get('password', ''))
        print("   ✅ Password entered with human-like typing")
        
        # Debug: Check if password was actually entered (show length only for security)
        if isinstance(password_ref, dict) and password_ref.get('type') == 'coordinate':
            x, y = password_ref['x'], password_ref['y']
            value_check = await page.evaluate(f"""
                () => {{
                    const element = document.elementFromPoint({x}, {y});
                    return element ? element.value.length : 0;
                }}
            """)
            print(f"      🔍 Password field value length after typing: {value_check} characters")
        
        print("\n   🔍 Adding another random delay...")
        await web_tools._human_behavior.random_delay(500, 1500)
        print("   ✅ Random delay completed")
        
        print("\n   🔍 Clicking submit button...")
        submit_ref = login_elements.get('submit', '')
        print(f"      Submit reference: {submit_ref}")
        
        # Debug: Check what's actually at those coordinates before clicking
        if isinstance(submit_ref, dict) and submit_ref.get('type') == 'coordinate':
            x, y = submit_ref['x'], submit_ref['y']
            element_info = await page.evaluate(f"""
                () => {{
                    const element = document.elementFromPoint({x}, {y});
                    if (element) {{
                        return {{
                            tagName: element.tagName,
                            type: element.type || 'N/A',
                            id: element.id || 'N/A',
                            innerText: element.innerText || 'N/A',
                            disabled: element.disabled || false
                        }};
                    }}
                    return null;
                }}
            """)
            print(f"      🔍 Element at ({x}, {y}): {element_info}")
        
        await web_tools._human_behavior.human_click(page, submit_ref)
        print("   ✅ Submit button clicked with human-like behavior")
        
        print("\n   🔍 Waiting for login completion...")
        await page.wait_for_load_state('networkidle')
        print("   ✅ Page load completed")
        
        print("\n   🔍 Verifying login success...")
        final_url = page.url
        final_title = await page.title()
        login_successful = final_url != test_url
        
        print(f"      Original URL: {test_url}")
        print(f"      Final URL: {final_url}")
        print(f"      Final Title: {final_title}")
        print(f"      Login Successful: {login_successful}")
        
        # Take a screenshot for verification
        screenshot_path = f"test_login_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"   📸 Screenshot saved: {screenshot_path}")
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        print(f"\n✅ Function execution completed in {execution_time:.2f} seconds")
        
        # Build result
        result = {
            "status": "success" if login_successful else "partial_success",
            "data": {
                "original_url": test_url,
                "current_url": final_url,
                "title": final_title,
                "session_id": session_id,
                "login_successful": login_successful,
                "screenshot": screenshot_path
            },
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"\n📊 RESULT ANALYSIS:")
        print(f"   Status: {result.get('status', 'unknown')}")
        print(f"   Original URL: {result['data']['original_url']}")
        print(f"   Final URL: {result['data']['current_url']}")
        print(f"   Page Title: {result['data']['title']}")
        print(f"   Login Successful: {result['data']['login_successful']}")
        print(f"   Session ID: {result['data']['session_id']}")
        
        # Check if login was actually successful
        if result['data']['login_successful']:
            print("\n🎉 LOGIN TEST: PASSED")
            print("   ✅ Successfully logged into test website")
            print("   ✅ URL changed after login (indicating redirect)")
        else:
            print("\n⚠️ LOGIN TEST: PARTIAL SUCCESS")
            print("   ✅ Function executed without errors")
            print("   ❓ Login success could not be verified")
        
        print(f"\n📄 Full result JSON:")
        print(json.dumps(result, indent=2))
        
        return result.get('status') == 'success'
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {str(e)}")
        import traceback
        print(f"📋 Full traceback:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("🧪 Starting Login Automation Test...")
    result = asyncio.run(test_login_automation_standalone())
    if result:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n❌ Test failed!")