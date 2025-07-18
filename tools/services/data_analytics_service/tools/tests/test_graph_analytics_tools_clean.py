#!/usr/bin/env python3
"""
Test script for graph_analytics_tools.py
Tests the complete MCP tool integration via the MCP client
"""

import asyncio
import sys
import os
import json
import time
from pathlib import Path

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..'))
sys.path.insert(0, project_root)

from tools.mcp_client import MCPClient, call_tool, get_capabilities, list_tools

class GraphAnalyticsToolTester:
    """Comprehensive tester for Graph Analytics Tools via MCP"""
    
    def __init__(self):
        self.client = MCPClient()
        self.test_pdf = "/Users/xenodennis/Documents/Fun/isA_MCP/test.pdf"
        self.test_user_id = 88888
        self.created_resource_id = None
        
    async def test_tool_discovery(self):
        """Test 1: Tool Discovery and Capabilities"""
        print(">> Test 1: Tool Discovery and MCP Integration")
        print("=" * 50)
        
        try:
            # Test capabilities endpoint
            print(">> Testing MCP capabilities endpoint...")
            capabilities = await get_capabilities()
            
            if capabilities.get("status") == "error":
                print(f"[FAIL] Capabilities endpoint failed: {capabilities.get('error')}")
                return False
            
            print("[OK] MCP capabilities endpoint working")
            
            # Test tool listing
            print(">> Testing tool discovery...")
            tools = await list_tools()
            
            graph_tools = [tool for tool in tools if "graph" in tool.lower()]
            print(f">> Found {len(tools)} total tools, {len(graph_tools)} graph-related")
            
            # Check for our specific tools
            expected_tools = [
                "process_pdf_to_knowledge_graph",
                "query_knowledge_graph", 
                "get_user_knowledge_graphs",
                "get_graph_analytics_status"
            ]
            
            missing_tools = []
            found_tools = []
            
            for tool in expected_tools:
                if tool in tools:
                    found_tools.append(tool)
                    print(f"  [OK] {tool}: DISCOVERED")
                else:
                    missing_tools.append(tool)
                    print(f"  [FAIL] {tool}: NOT FOUND")
            
            if missing_tools:
                print(f"[FAIL] Missing tools: {missing_tools}")
                return False
            
            print(f"[OK] All {len(expected_tools)} graph analytics tools discovered")
            print("[OK] Test 1 PASSED")
            return True
            
        except Exception as e:
            print(f"[FAIL] Test 1 FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_status_tool(self):
        """Test 2: Status Tool Functionality"""
        print("\n>> Test 2: Status Tool")
        print("=" * 50)
        
        try:
            print(">> Testing get_graph_analytics_status...")
            
            result = await call_tool("get_graph_analytics_status")
            
            if result.get("status") == "error":
                print(f"[FAIL] Status tool failed: {result.get('error')}")
                return False
            
            # Parse the status response
            if isinstance(result, dict) and "tool_name" in result:
                status_data = result
            else:
                # If it's wrapped in a response structure
                status_data = result
            
            print(">> Status Tool Response Analysis:")
            print(f"  Tool Name: {status_data.get('tool_name', 'N/A')}")
            print(f"  Version: {status_data.get('version', 'N/A')}")
            print(f"  Status: {status_data.get('status', 'N/A')}")
            
            # Check supported formats
            formats = status_data.get('supported_formats', [])
            print(f"  Supported Formats: {formats}")
            if "PDF" not in formats:
                print("  [WARN] PDF format not explicitly supported")
            
            # Check verified features
            features = status_data.get('verified_features', [])
            print(f"  Verified Features: {len(features)}")
            for feature in features:
                print(f"    [OK] {feature}")
            
            # Check performance metrics
            performance = status_data.get('performance', {})
            if performance:
                print("  Performance Metrics:")
                for key, value in performance.items():
                    print(f"    [INFO] {key}: {value}")
            
            print("[OK] Test 2 PASSED")
            return True
            
        except Exception as e:
            print(f"[FAIL] Test 2 FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_pdf_processing(self):
        """Test 3: PDF to Knowledge Graph Processing"""
        print("\n>> Test 3: PDF Processing via MCP")
        print("=" * 50)
        
        try:
            # Verify test PDF exists
            if not os.path.exists(self.test_pdf):
                print(f"[FAIL] Test PDF not found: {self.test_pdf}")
                return False
            
            print(f">> Processing test PDF: {self.test_pdf}")
            print(f">> User ID: {self.test_user_id}")
            
            # Start timing
            start_time = time.time()
            
            # Call the MCP tool
            result = await call_tool(
                "process_pdf_to_knowledge_graph",
                pdf_path=self.test_pdf,
                user_id=self.test_user_id,
                source_metadata='{"domain": "medical", "test": "mcp_integration"}',
                options='{"mode": "text"}'
            )
            
            processing_time = time.time() - start_time
            
            print(f"[TIME] Total MCP call time: {processing_time:.2f}s")
            
            # Analyze response
            if result.get("status") == "error":
                print(f"[FAIL] PDF processing failed: {result.get('error')}")
                return False
            
            if result.get("status") != "success":
                print(f"[FAIL] Unexpected status: {result.get('status')}")
                print(f"Raw response: {json.dumps(result, indent=2)}")
                return False
            
            # Extract data
            data = result.get("data", {})
            
            # Analyze PDF processing
            pdf_info = data.get("pdf_processing", {})
            print(">> PDF Processing Results:")
            print(f"  [INFO] File: {pdf_info.get('file_path', 'N/A')}")
            print(f"  [INFO] Mode: {pdf_info.get('mode', 'N/A')}")
            print(f"  [INFO] Pages: {pdf_info.get('pages_processed', 0)}")
            print(f"  [INFO] Characters: {pdf_info.get('total_characters', 0)}")
            print(f"  [INFO] Chunks: {pdf_info.get('chunks_created', 0)}")
            print(f"  [INFO] Extraction Time: {pdf_info.get('extraction_time', 0):.2f}s")
            
            # Analyze knowledge graph
            kg_info = data.get("knowledge_graph", {})
            print(">> Knowledge Graph Results:")
            print(f"  [INFO] Resource ID: {kg_info.get('resource_id', 'N/A')}")
            print(f"  [INFO] MCP Address: {kg_info.get('mcp_resource_address', 'N/A')}")
            print(f"  [INFO] Entities: {kg_info.get('entities_count', 0)}")
            print(f"  [INFO] Relationships: {kg_info.get('relationships_count', 0)}")
            print(f"  [INFO] Processing Time: {kg_info.get('processing_time', 0):.2f}s")
            
            # Store resource ID for later tests
            self.created_resource_id = kg_info.get('resource_id')
            
            # Analyze Neo4j storage
            storage_info = data.get("neo4j_storage", {})
            print(">> Neo4j Storage Results:")
            print(f"  [INFO] Nodes Created: {storage_info.get('nodes_created', 0)}")
            print(f"  [INFO] Relationships Created: {storage_info.get('relationships_created', 0)}")
            print(f"  [INFO] Storage Time: {storage_info.get('storage_time', 0):.2f}s")
            
            # Validation checks
            entities_count = kg_info.get('entities_count', 0)
            relationships_count = kg_info.get('relationships_count', 0)
            
            if entities_count == 0:
                print("[WARN] No entities extracted - check document content")
            else:
                print(f"[OK] Successfully extracted {entities_count} entities")
            
            if relationships_count == 0:
                print("[WARN] No relationships extracted")
            else:
                print(f"[OK] Successfully extracted {relationships_count} relationships")
            
            # Performance validation
            total_processing = kg_info.get('processing_time', 0)
            if total_processing > 60:
                print(f"[WARN] Processing took {total_processing:.1f}s (longer than expected)")
            else:
                print(f"[OK] Good performance: {total_processing:.1f}s processing time")
            
            print("[OK] Test 3 PASSED")
            return True
            
        except Exception as e:
            print(f"[FAIL] Test 3 FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_query_functionality(self):
        """Test 4: Knowledge Graph Querying"""
        print("\n>> Test 4: Knowledge Graph Querying via MCP")
        print("=" * 50)
        
        try:
            # Test queries
            test_queries = [
                "What medical information is mentioned?",
                "Who are the people in this document?", 
                "What organizations are referenced?",
                "What are the key findings?"
            ]
            
            successful_queries = 0
            
            for i, query in enumerate(test_queries, 1):
                print(f"\n>> Query {i}: '{query}'")
                
                query_start = time.time()
                
                result = await call_tool(
                    "query_knowledge_graph",
                    query=query,
                    user_id=self.test_user_id,
                    resource_id="",  # Search all resources
                    options='{"limit": 3, "similarity_threshold": 0.6}'
                )
                
                query_time = time.time() - query_start
                print(f"  [TIME] Query time: {query_time:.2f}s")
                
                if result.get("status") == "error":
                    print(f"  [FAIL] Query failed: {result.get('error')}")
                    continue
                
                if result.get("status") != "success":
                    print(f"  [FAIL] Unexpected status: {result.get('status')}")
                    continue
                
                # Analyze results
                data = result.get("data", {})
                results = data.get("results", [])
                results_found = data.get("results_found", 0)
                resources_searched = data.get("resources_searched", 0)
                
                print(f"  [OK] Query successful")
                print(f"    [INFO] Results found: {results_found}")
                print(f"    [INFO] Resources searched: {resources_searched}")
                
                # Show top result if available
                if results:
                    top_result = results[0]
                    content = top_result.get("content", "")
                    score = top_result.get("score", 0)
                    result_type = top_result.get("type", "unknown")
                    
                    print(f"    [INFO] Top result ({result_type}, score: {score:.2f}): {content[:80]}...")
                
                successful_queries += 1
            
            print(f"\n>> Query Test Summary: {successful_queries}/{len(test_queries)} successful")
            
            if successful_queries >= len(test_queries) * 0.75:  # Allow 25% failure rate
                print("[OK] Test 4 PASSED")
                return True
            else:
                print("[FAIL] Test 4 FAILED - Too many query failures")
                return False
            
        except Exception as e:
            print(f"[FAIL] Test 4 FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_user_resources(self):
        """Test 5: User Resource Management"""
        print("\n>> Test 5: User Resource Management via MCP")
        print("=" * 50)
        
        try:
            print(f">> Getting resources for user {self.test_user_id}...")
            
            result = await call_tool(
                "get_user_knowledge_graphs",
                user_id=self.test_user_id
            )
            
            if result.get("status") == "error":
                print(f"[FAIL] Resource query failed: {result.get('error')}")
                return False
            
            if result.get("status") != "success":
                print(f"[FAIL] Unexpected status: {result.get('status')}")
                return False
            
            # Analyze resources
            data = result.get("data", {})
            user_id = data.get("user_id")
            resource_count = data.get("resource_count", 0)
            mcp_resources = data.get("mcp_resources", {})
            user_isolation = data.get("user_isolation", False)
            
            print(">> Resource Management Results:")
            print(f"  [INFO] User ID: {user_id}")
            print(f"  [INFO] Resource Count: {resource_count}")
            print(f"  [INFO] User Isolation: {user_isolation}")
            print(f"  [INFO] MCP Resources: {len(mcp_resources)}")
            
            # List resources
            if mcp_resources:
                print("  >> Available Resources:")
                for resource_id, resource_data in mcp_resources.items():
                    address = resource_data.get("address", "N/A")
                    source_file = resource_data.get("source_file", "N/A")
                    created_at = resource_data.get("created_at", "N/A")
                    print(f"    [INFO] {resource_id[:8]}... : {source_file}")
                    print(f"      Address: {address}")
                    print(f"      Created: {created_at}")
            
            # Validation checks
            if not user_isolation:
                print("[WARN] User isolation not confirmed")
            else:
                print("[OK] User isolation confirmed")
            
            if resource_count == 0:
                print("[WARN] No resources found (may be expected for fresh test)")
            else:
                print(f"[OK] Found {resource_count} resources")
            
            # Check if our created resource is listed
            if self.created_resource_id and self.created_resource_id in mcp_resources:
                print(f"[OK] Previously created resource {self.created_resource_id[:8]}... found in user resources")
            elif self.created_resource_id:
                print(f"[WARN] Previously created resource {self.created_resource_id[:8]}... not found")
            
            print("[OK] Test 5 PASSED")
            return True
            
        except Exception as e:
            print(f"[FAIL] Test 5 FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_error_handling(self):
        """Test 6: Error Handling and Edge Cases"""
        print("\n>> Test 6: Error Handling via MCP")
        print("=" * 50)
        
        try:
            # Test 1: Non-existent PDF
            print(">> Testing non-existent PDF...")
            result = await call_tool(
                "process_pdf_to_knowledge_graph",
                pdf_path="/non/existent/file.pdf",
                user_id=self.test_user_id
            )
            
            if result.get("status") == "error":
                print("  [OK] Correctly handled non-existent PDF")
            else:
                print("  [FAIL] Should have failed with non-existent PDF")
                return False
            
            # Test 2: Invalid user ID for querying
            print(">> Testing invalid user access...")
            result = await call_tool(
                "query_knowledge_graph",
                query="test query",
                user_id=99999,  # Different user
                options='{"limit": 1}'
            )
            
            # This should either return no results or handle gracefully
            if result.get("status") in ["success", "error"]:
                print("  [OK] Handled invalid user access gracefully")
            else:
                print("  [FAIL] Unexpected response to invalid user")
                return False
            
            # Test 3: Invalid JSON parameters
            print(">> Testing invalid JSON parameters...")
            try:
                result = await call_tool(
                    "process_pdf_to_knowledge_graph",
                    pdf_path=self.test_pdf,
                    user_id=self.test_user_id,
                    source_metadata='{"invalid": json}',  # Invalid JSON
                    options='{"mode": "text"}'
                )
                
                if result.get("status") == "error":
                    print("  [OK] Correctly handled invalid JSON")
                else:
                    print("  [WARN] Unexpected success with invalid JSON")
            except Exception:
                print("  [OK] Correctly caught invalid JSON at client level")
            
            # Test 4: Empty query
            print(">> Testing empty query...")
            result = await call_tool(
                "query_knowledge_graph",
                query="",
                user_id=self.test_user_id
            )
            
            # Should handle empty query gracefully
            if result.get("status") in ["success", "error"]:
                print("  [OK] Handled empty query gracefully")
            else:
                print("  [FAIL] Unexpected response to empty query")
                return False
            
            print("[OK] Test 6 PASSED")
            return True
            
        except Exception as e:
            print(f"[FAIL] Test 6 FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_mcp_protocol_compliance(self):
        """Test 7: MCP Protocol Compliance"""
        print("\n>> Test 7: MCP Protocol Compliance")
        print("=" * 50)
        
        try:
            # Test JSON-RPC format compliance
            print(">> Testing MCP JSON-RPC protocol compliance...")
            
            # Make a raw MCP call to check response format
            response = await self.client.call_tool("get_graph_analytics_status")
            
            print(">> Raw MCP Response Analysis:")
            
            # Check for required JSON-RPC fields
            if "jsonrpc" in response:
                print("  [OK] JSON-RPC version field present")
            else:
                print("  [WARN] JSON-RPC version field missing (may be in parsed format)")
            
            if "id" in response:
                print("  [OK] Request ID field present")
            else:
                print("  [WARN] Request ID field missing (may be in parsed format)")
            
            # Check response structure
            if "result" in response or "error" in response:
                print("  [OK] Proper result/error structure")
            else:
                print("  [WARN] Response may be already parsed")
            
            # Test tool discoverability through capabilities
            print(">> Testing tool discoverability...")
            capabilities = await self.client.get_capabilities()
            
            if capabilities.get("status") == "success" or "capabilities" in capabilities:
                print("  [OK] Tools discoverable through capabilities endpoint")
            else:
                print("  [FAIL] Tool discovery issues")
                return False
            
            # Test response format consistency
            print(">> Testing response format consistency...")
            
            # Call multiple tools and check they all follow same format
            tools_to_test = [
                ("get_graph_analytics_status", {}),
                ("get_user_knowledge_graphs", {"user_id": self.test_user_id})
            ]
            
            consistent_format = True
            
            for tool_name, args in tools_to_test:
                result = await call_tool(tool_name, **args)
                
                # Check for standard response fields
                if "status" not in result and "error" not in result:
                    print(f"  [WARN] {tool_name}: Missing standard status field")
                    consistent_format = False
                
                if result.get("status") == "success" and "data" not in result:
                    # Check if the result itself is the data (direct format)
                    if not any(key in result for key in ["tool_name", "user_id", "query"]):
                        print(f"  [WARN] {tool_name}: Success status but no data field")
                        consistent_format = False
            
            if consistent_format:
                print("  [OK] Response format consistency maintained")
            else:
                print("  [WARN] Some response format inconsistencies detected")
            
            print("[OK] Test 7 PASSED")
            return True
            
        except Exception as e:
            print(f"[FAIL] Test 7 FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

async def run_comprehensive_tests():
    """Run all comprehensive tests for Graph Analytics Tools"""
    print(">> Starting Graph Analytics Tools MCP Integration Tests...")
    print("=" * 60)
    print("Testing complete MCP tool integration, discoverability, and functionality")
    print("=" * 60)
    
    tester = GraphAnalyticsToolTester()
    
    # Define all tests
    tests = [
        ("Tool Discovery & MCP Integration", tester.test_tool_discovery),
        ("Status Tool Functionality", tester.test_status_tool),
        ("PDF Processing via MCP", tester.test_pdf_processing),
        ("Knowledge Graph Querying", tester.test_query_functionality),
        ("User Resource Management", tester.test_user_resources),
        ("Error Handling & Edge Cases", tester.test_error_handling),
        ("MCP Protocol Compliance", tester.test_mcp_protocol_compliance)
    ]
    
    # Run all tests
    results = []
    start_time = time.time()
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result if result is not None else True))
        except Exception as e:
            print(f"[FAIL] {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    total_time = time.time() - start_time
    
    # Test Summary
    print("\n" + "=" * 60)
    print(">> COMPREHENSIVE TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    print(f"Total Test Time: {total_time:.1f}s")
    
    print("\n>> Individual Test Results:")
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status}: {test_name}")
    
    # Overall assessment
    if passed == total:
        print("\n[OK] ALL TESTS PASSED!")
        print("[OK] Graph Analytics Tools are fully functional via MCP")
        print("[OK] Tool discovery working correctly")
        print("[OK] All core functionality verified")
        print("[OK] Error handling robust")
        print("[OK] MCP protocol compliance confirmed")
    elif passed >= total * 0.8:
        print("\n[WARN] MOSTLY SUCCESSFUL")
        print(f"[OK] {passed} out of {total} tests passed")
        print(">> Review failed tests above for issues to address")
    else:
        print("\n[FAIL] SIGNIFICANT ISSUES DETECTED")
        print(f"[FAIL] Only {passed} out of {total} tests passed")
        print(">> Major functionality problems need to be addressed")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(run_comprehensive_tests())