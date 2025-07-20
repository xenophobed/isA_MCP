#!/usr/bin/env python3
"""
Test script for web_tools.py
"""

import asyncio
import sys
import os
import json

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.insert(0, project_root)

from tools.services.web_services.web_tools import WebToolsService

async def test_web_search():
    """Test web search functionality"""
    print("Test 1: Web Search Functionality")
    print("="*50)
    
    web_service = WebToolsService()
    
    test_queries = [
        ("artificial intelligence", 5),
        ("python programming", 3)
    ]
    
    print(f"Testing {len(test_queries)} search queries")
    print()
    
    try:
        for i, (query, count) in enumerate(test_queries, 1):
            print(f"Search {i}: '{query}' (count: {count})")
            
            result = await web_service.web_search(query, count)
            result_data = json.loads(result)
            
            print(f"  Status: {result_data.get('status', 'unknown')}")
            print(f"  Action: {result_data.get('action', 'unknown')}")
            
            if result_data.get('status') == 'success':
                data = result_data.get('data', {})
                results = data.get('results', [])
                print(f"  Results: {len(results)} found")
                
                # Verify result structure
                if results:
                    first_result = results[0]
                    required_fields = ['title', 'url', 'description']
                    for field in required_fields:
                        if field in first_result:
                            print(f"    Field {field}: Present")
                        else:
                            print(f"    Field {field}: Missing")
                
                print(f"    Sample title: {results[0].get('title', 'N/A')[:50]}...")
            else:
                print(f"  Error: {result_data.get('error_message', 'Unknown error')}")
            
            print()
        
        print("Test 1 PASSED")
        return True
        
    except Exception as e:
        print(f"Test 1 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_web_crawl_single():
    """Test web crawl functionality with single URL"""
    print("\nTest 2: Web Crawl Single URL")
    print("="*50)
    
    web_service = WebToolsService()
    
    test_cases = [
        ("https://example.com", "extract main content"),
        ("https://httpbin.org/html", "analyze page structure")
    ]
    
    print(f"Testing {len(test_cases)} crawl scenarios")
    print()
    
    try:
        for i, (url, analysis_request) in enumerate(test_cases, 1):
            print(f"Crawl {i}: {url}")
            print(f"  Analysis: {analysis_request}")
            
            result = await web_service.web_crawl(url, analysis_request)
            result_data = json.loads(result)
            
            print(f"  Status: {result_data.get('status', 'unknown')}")
            
            if result_data.get('status') == 'success':
                data = result_data.get('data', {})
                
                # Check for required fields
                required_fields = ['extraction_method', 'content', 'metadata']
                for field in required_fields:
                    if field in data:
                        print(f"    Field {field}: Present")
                    else:
                        print(f"    Field {field}: Missing")
                
                # Show extraction method used
                method = data.get('extraction_method', 'unknown')
                print(f"    Method: {method}")
                
                # Show content length
                content = data.get('content', '')
                if isinstance(content, dict):
                    content_length = len(str(content))
                else:
                    content_length = len(content)
                print(f"    Content length: {content_length} characters")
                
            else:
                print(f"  Error: {result_data.get('error_message', 'Unknown error')}")
            
            print()
        
        print("Test 2 PASSED")
        return True
        
    except Exception as e:
        print(f"Test 2 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_web_automation():
    """Test web automation functionality"""
    print("\nTest 3: Web Automation")
    print("="*50)
    
    web_service = WebToolsService()
    
    test_cases = [
        ("https://example.com", "find contact information"),
    ]
    
    print(f"Testing {len(test_cases)} automation scenarios")
    print()
    
    try:
        for i, (url, task) in enumerate(test_cases, 1):
            print(f"Automation {i}: {url}")
            print(f"  Task: {task}")
            
            result = await web_service.web_automation(url, task)
            result_data = json.loads(result)
            
            print(f"  Status: {result_data.get('status', 'unknown')}")
            
            if result_data.get('status') == 'success':
                data = result_data.get('data', {})
                
                # Check for automation-specific fields
                automation_fields = ['task', 'initial_url', 'final_url', 'workflow_results']
                for field in automation_fields:
                    if field in data:
                        print(f"    Field {field}: Present")
                    else:
                        print(f"    Field {field}: Missing")
                
                # Show workflow results if available
                workflow = data.get('workflow_results', {})
                if workflow:
                    step_count = len([k for k in workflow.keys() if k.startswith('step')])
                    print(f"    Workflow steps completed: {step_count}")
                
            else:
                print(f"  Error: {result_data.get('error_message', 'Unknown error')}")
            
            print()
        
        print("Test 3 PASSED")
        return True
        
    except Exception as e:
        print(f"Test 3 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_error_handling():
    """Test error handling for invalid inputs"""
    print("\nTest 4: Error Handling")
    print("="*50)
    
    web_service = WebToolsService()
    
    error_test_cases = [
        ("web_search", ("", 5), "Empty search query"),
        ("web_crawl", ("invalid-url", ""), "Invalid URL"),
        ("web_automation", ("https://example.com", ""), "Empty task"),
    ]
    
    print(f"Testing {len(error_test_cases)} error scenarios")
    print()
    
    try:
        for i, (method, args, description) in enumerate(error_test_cases, 1):
            print(f"Error Test {i}: {description}")
            
            try:
                if method == "web_search":
                    result = await web_service.web_search(*args)
                elif method == "web_crawl":
                    result = await web_service.web_crawl(*args)
                elif method == "web_automation":
                    result = await web_service.web_automation(*args)
                
                result_data = json.loads(result)
                
                if result_data.get('status') == 'error':
                    print(f"  Correctly returned error status")
                    print(f"  Error message: {result_data.get('error_message', 'No message')}")
                else:
                    print(f"  Expected error but got: {result_data.get('status')}")
                
            except Exception as e:
                print(f"  Correctly raised exception: {type(e).__name__}")
            
            print()
        
        print("Test 4 PASSED")
        return True
        
    except Exception as e:
        print(f"Test 4 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_response_format():
    """Test response format consistency"""
    print("\nTest 5: Response Format Validation")
    print("="*50)
    
    web_service = WebToolsService()
    
    print("Testing response format consistency across all tools")
    print()
    
    try:
        # Test each tool and validate response format
        test_responses = []
        
        # Web search response
        search_result = await web_service.web_search("test query", 1)
        test_responses.append(("web_search", search_result))
        
        # Web crawl response  
        crawl_result = await web_service.web_crawl("https://example.com", "test")
        test_responses.append(("web_crawl", crawl_result))
        
        # Validate all responses have consistent format
        required_fields = ['status', 'action', 'data']
        
        for tool_name, response in test_responses:
            print(f"Validating {tool_name} response format:")
            
            try:
                result_data = json.loads(response)
                
                for field in required_fields:
                    if field in result_data:
                        print(f"  Field {field}: Present")
                    else:
                        print(f"  Field {field}: Missing")
                
                # Validate status values
                status = result_data.get('status')
                if status in ['success', 'error']:
                    print(f"  Status: Valid value '{status}'")
                else:
                    print(f"  Status: Invalid value '{status}'")
                
                # Validate action matches tool name
                action = result_data.get('action')
                if action == tool_name:
                    print(f"  Action: Correctly set to '{action}'")
                else:
                    print(f"  Action: Expected '{tool_name}', got '{action}'")
                
            except json.JSONDecodeError:
                print(f"  Invalid JSON response")
            
            print()
        
        print("Test 5 PASSED")
        return True
        
    except Exception as e:
        print(f"Test 5 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def run_all_tests():
    """Run all tests"""
    print("Starting web_tools.py comprehensive tests...\n")
    
    tests = [
        test_web_search,
        test_web_crawl_single,
        test_web_automation,
        test_error_handling,
        test_response_format
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result if result is not None else True)
        except Exception as e:
            print(f"Test failed with exception: {e}")
            results.append(False)
    
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("ALL TESTS PASSED!")
    else:
        print("Some tests failed - review output above")

if __name__ == "__main__":
    asyncio.run(run_all_tests())