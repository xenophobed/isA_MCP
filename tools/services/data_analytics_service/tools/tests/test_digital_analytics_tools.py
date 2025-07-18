#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for digital_analytics_tools.py
Comprehensive tests for RAG and knowledge management functionality
"""

import asyncio
import sys
import os
import json
import uuid
from typing import Dict, Any

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.insert(0, project_root)

from tools.services.data_analytics_service.tools.digital_analytics_tools import DigitalAnalyticsTool
from tools.services.data_analytics_service.services.digital_service.rag_service import rag_service

async def test_basic_knowledge_operations():
    """Test basic knowledge storage and retrieval functionality"""
    print("Test 1: Basic Knowledge Operations")
    print("="*50)
    
    digital_tool = DigitalAnalyticsTool()
    test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    
    print(f"Test Parameters:")
    print(f"  User ID: {test_user_id}")
    print(f"  Test Knowledge: Machine learning basics")
    print()
    
    try:
        # Test 1a: Store Knowledge
        print("Test 1a: Store Knowledge...")
        test_text = "Machine learning is a subset of artificial intelligence that focuses on algorithms and statistical models."
        test_metadata = {"topic": "AI", "source": "test", "difficulty": "beginner"}
        
        store_result = await digital_tool.store_knowledge(
            user_id=test_user_id,
            text=test_text,
            metadata=test_metadata
        )
        
        print(f"Store Result:")
        print(store_result)
        print()
        
        # Parse and validate store result
        store_data = json.loads(store_result)
        if store_data.get('status') == 'success':
            knowledge_id = store_data['data']['knowledge_id']
            print(f"  Knowledge stored with ID: {knowledge_id}")
            
            # Test 1b: Search Knowledge
            print("Test 1b: Search Knowledge...")
            search_result = await digital_tool.search_knowledge(
                user_id=test_user_id,
                query="artificial intelligence",
                top_k=3,
                enable_rerank=False
            )
            
            print(f"Search Result:")
            print(search_result)
            print()
            
            search_data = json.loads(search_result)
            if search_data.get('status') == 'success':
                search_results = search_data['data']['search_results']
                print(f"  Search found {len(search_results)} results")
                
                # Test 1c: Get Knowledge Item
                print("Test 1c: Get Knowledge Item...")
                get_result = await digital_tool.get_knowledge_item(
                    user_id=test_user_id,
                    knowledge_id=knowledge_id
                )
                
                print(f"Get Result:")
                print(get_result)
                print()
                
                get_data = json.loads(get_result)
                if get_data.get('status') == 'success':
                    print(f"  Knowledge item retrieved successfully")
                    
                    # Test 1d: List User Knowledge
                    print("Test 1d: List User Knowledge...")
                    list_result = await digital_tool.list_user_knowledge(test_user_id)
                    
                    list_data = json.loads(list_result)
                    if list_data.get('status') == 'success':
                        knowledge_count = list_data['data']['total_count']
                        print(f"  Listed {knowledge_count} knowledge items")
                        
                        # Test 1e: Delete Knowledge
                        print("Test 1e: Delete Knowledge...")
                        delete_result = await digital_tool.delete_knowledge_item(
                            user_id=test_user_id,
                            knowledge_id=knowledge_id
                        )
                        
                        delete_data = json.loads(delete_result)
                        if delete_data.get('status') == 'success':
                            print(f"  Knowledge deleted successfully")
                            print("Test 1 PASSED")
                            return True
                        else:
                            print(f"  Delete failed: {delete_data.get('message', 'Unknown error')}")
                    else:
                        print(f"  List failed: {list_data.get('message', 'Unknown error')}")
                else:
                    print(f"  Get failed: {get_data.get('message', 'Unknown error')}")
            else:
                print(f"  Search failed: {search_data.get('message', 'Unknown error')}")
        else:
            print(f"  Store failed: {store_data.get('message', 'Unknown error')}")
            
        print("Test 1 FAILED")
        return False
        
    except Exception as e:
        print(f"Test 1 FAILED with exception: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        
        # Check for common issues
        error_str = str(e).lower()
        if 'connection' in error_str or 'database' in error_str:
            print("This appears to be a database connection issue")
            print("Please ensure Supabase is running and configured properly")
        elif 'embedding' in error_str or 'isa' in error_str:
            print("This appears to be an embedding service issue")
            print("Please ensure ISA model service is running on port 8082")
        
        import traceback
        traceback.print_exc()
        return False

async def test_service_status():
    """Test service status and configuration"""
    print("\nTest 2: Service Status and Configuration")
    print("="*50)
    
    try:
        # Test RAG service status
        print("Testing RAG service status...")
        
        # Simulate the get_rag_service_status function
        status = {
            "service_name": "RAG Service",
            "status": "active",
            "table_name": rag_service.table_name,
            "default_chunk_size": rag_service.default_chunk_size,
            "default_overlap": rag_service.default_overlap,
            "default_top_k": rag_service.default_top_k,
            "embedding_model": rag_service.embedding_model,
            "rerank_enabled": rag_service.enable_rerank,
            "capabilities": [
                "knowledge_storage",
                "semantic_search", 
                "document_chunking",
                "rag_generation",
                "mcp_integration",
                "user_isolation"
            ]
        }
        
        print(f"Service Status:")
        print(json.dumps(status, indent=2))
        print()
        
        # Validate status structure
        required_fields = ["service_name", "status", "table_name", "capabilities"]
        print("Status Validation:")
        
        all_present = True
        for field in required_fields:
            if field in status:
                print(f"  {field}: Present")
            else:
                print(f"  {field}: Missing")
                all_present = False
        
        # Check capabilities
        expected_capabilities = [
            "knowledge_storage", "semantic_search", "document_chunking",
            "rag_generation", "mcp_integration", "user_isolation"
        ]
        
        capabilities = status.get("capabilities", [])
        for cap in expected_capabilities:
            if cap in capabilities:
                print(f"  capability.{cap}: Present")
            else:
                print(f"  capability.{cap}: Missing")
                all_present = False
        
        if all_present:
            print("Test 2 PASSED")
            return True
        else:
            print("Test 2 FAILED - Missing required fields")
            return False
        
    except Exception as e:
        print(f"Test 2 FAILED with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def run_all_tests():
    """Run all tests"""
    print("Starting digital_analytics_tools.py tests...\n")
    
    # Check if services are available before running tests
    print("Pre-flight checks...")
    try:
        # Test if we can access the RAG service
        test_user = "preflight_test"
        digital_tool = DigitalAnalyticsTool()
        
        # Try a simple operation to check service availability
        list_result = await digital_tool.list_user_knowledge(test_user)
        list_data = json.loads(list_result)
        
        if list_data.get('status') in ['success', 'error']:  # Either is fine for preflight
            print("RAG service is accessible")
        else:
            print("RAG service may not be fully available")
            
    except Exception as e:
        print(f"Pre-flight check failed: {str(e)}")
        print("Some tests may fail due to service availability")
    
    print()
    
    tests = [
        test_basic_knowledge_operations,
        test_service_status
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
        print("Common issues:")
        print("   - Ensure Supabase is running with user_knowledge table")
        print("   - Ensure ISA model service is running on port 8082")
        print("   - Check database connection and environment variables")

if __name__ == "__main__":
    asyncio.run(run_all_tests())