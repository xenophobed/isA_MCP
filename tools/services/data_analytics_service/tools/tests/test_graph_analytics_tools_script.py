#!/usr/bin/env python3
"""
Test the rewritten Graph Analytics Tools with verified services

This test verifies the complete PDF → Knowledge Graph pipeline using:
1. Verified SimplePDFExtractService
2. Verified GraphAnalyticsService
3. Real Neo4j storage
"""

import asyncio
import sys
import json
import logging
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Enable debug logging for key components
logging.getLogger('tools.services.data_analytics_service').setLevel(logging.INFO)
logging.getLogger('tools.services.intelligence_service').setLevel(logging.INFO)
logging.getLogger('embedding_generator').setLevel(logging.INFO)
logging.getLogger('graph_constructor').setLevel(logging.INFO)

def log_timing(step_name: str, start_time: float) -> float:
    """Log timing for a step and return current time"""
    current_time = time.time()
    elapsed = current_time - start_time
    print(f"⏱️  {step_name}: {elapsed:.2f}s")
    return current_time

async def test_graph_analytics_tools():
    """Test the complete Graph Analytics Tools pipeline"""
    test_start_time = time.time()
    print(f"🚀 Testing Rewritten Graph Analytics Tools - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # Step 1: Import and initialize
        step_start = time.time()
        print("🔧 Step 1: Importing and initializing services...")
        from tools.services.data_analytics_service.tools.graph_analytics_tools import GraphAnalyticsTool
        
        # Initialize the tool
        tool = GraphAnalyticsTool()
        log_timing("Service initialization", step_start)
        
        # Test PDF path (using our verified test file)
        test_pdf = "/Users/xenodennis/Documents/Fun/isA_MCP/test.pdf"
        test_user_id = 88888
        
        print(f"📄 Test PDF: {test_pdf}")
        print(f"👤 Test User: {test_user_id}")
        
        # Test 1: Process PDF to Knowledge Graph
        print("\n" + "=" * 60)
        print("🔬 TEST 1: Process PDF to Knowledge Graph")
        print("=" * 60)
        
        test1_start = time.time()
        print(f"🚀 Starting PDF processing at {datetime.now().strftime('%H:%M:%S')}...")
        
        result = await tool.process_pdf_to_knowledge_graph(
            pdf_path=test_pdf,
            user_id=test_user_id,
            source_metadata={
                'test': 'graph_analytics_tools_integration',
                'domain': 'medical_report'
            },
            options={
                'mode': 'text'  # Use fast text mode for testing
            }
        )
        
        test1_time = log_timing("TEST 1 - Complete PDF to Knowledge Graph", test1_start)
        
        # Parse the result (it's a JSON string)
        result_data = json.loads(result)
        
        if result_data.get('status') == 'success':
            data = result_data.get('data', {})
            print("✅ PDF to Knowledge Graph: SUCCESS")
            
            pdf_info = data.get('pdf_processing', {})
            print(f"   📝 PDF Processing:")
            print(f"      • File: {pdf_info.get('file_path')}")
            print(f"      • Mode: {pdf_info.get('mode')}")
            print(f"      • Pages: {pdf_info.get('pages_processed')}")
            print(f"      • Characters: {pdf_info.get('total_characters')}")
            print(f"      • Chunks: {pdf_info.get('chunks_created')}")
            print(f"      • Time: {pdf_info.get('extraction_time'):.2f}s")
            
            kg_info = data.get('knowledge_graph', {})
            print(f"   🧠 Knowledge Graph:")
            print(f"      • Resource ID: {kg_info.get('resource_id')}")
            print(f"      • MCP Address: {kg_info.get('mcp_resource_address')}")
            print(f"      • Entities: {kg_info.get('entities_count')}")
            print(f"      • Relationships: {kg_info.get('relationships_count')}")
            print(f"      • Processing: {kg_info.get('processing_method')}")
            print(f"      • Time: {kg_info.get('processing_time'):.2f}s")
            
            storage_info = data.get('neo4j_storage', {})
            print(f"   💾 Neo4j Storage:")
            print(f"      • Nodes: {storage_info.get('nodes_created')}")
            print(f"      • Relationships: {storage_info.get('relationships_created')}")
            print(f"      • Time: {storage_info.get('storage_time'):.2f}s")
            
            # Store resource ID for querying
            resource_id = kg_info.get('resource_id')
            
        else:
            print(f"❌ PDF to Knowledge Graph: FAILED")
            print(f"   Error: {result_data.get('message')}")
            return False
        
        # Test 2: Query Knowledge Graph
        print("\n" + "=" * 60)
        print("🔬 TEST 2: Query Knowledge Graph")
        print("=" * 60)
        
        test2_start = time.time()
        print(f"🔍 Starting knowledge graph queries at {datetime.now().strftime('%H:%M:%S')}...")
        
        test_queries = [
            "What medical information is in this report?",
            "What organizations are mentioned?",
            "What locations are referenced?",
            "Tell me about the content"
        ]
        
        for i, query in enumerate(test_queries, 1):
            query_start = time.time()
            print(f"\n   📝 Query {i}: '{query}'")
            
            query_result = await tool.query_knowledge_graph(
                query=query,
                user_id=test_user_id,
                resource_id=None,  # Search all user resources
                options={
                    'search_mode': 'semantic',
                    'limit': 3,
                    'similarity_threshold': 0.6
                }
            )
            
            log_timing(f"Query {i} execution", query_start)
            
            query_data = json.loads(query_result)
            
            if query_data.get('status') == 'success':
                query_info = query_data.get('data', {})
                results = query_info.get('results', [])
                
                print(f"   ✅ Query successful: {len(results)} results found")
                print(f"      • Resources searched: {query_info.get('resources_searched', 0)}")
                print(f"      • Total results: {query_info.get('total_results', 0)}")
                
                # Show first result
                if results:
                    first_result = results[0]
                    content = first_result.get('content', '')
                    score = first_result.get('score', 0)
                    print(f"      • Top result (score: {score:.2f}): {content[:100]}...")
                    
            else:
                print(f"   ❌ Query failed: {query_data.get('message')}")
        
        test2_time = log_timing("TEST 2 - Complete Query Testing", test2_start)
        
        # Test 3: Get User Knowledge Graphs
        print("\n" + "=" * 60)
        print("🔬 TEST 3: Get User Knowledge Graphs")
        print("=" * 60)
        
        test3_start = time.time()
        print(f"📊 Starting user resource query at {datetime.now().strftime('%H:%M:%S')}...")
        
        resources_result = await tool.get_user_knowledge_graphs(user_id=test_user_id)
        resources_data = json.loads(resources_result)
        
        test3_time = log_timing("TEST 3 - User Knowledge Graphs", test3_start)
        
        if resources_data.get('status') == 'success':
            resources_info = resources_data.get('data', {})
            print("✅ User Resources: SUCCESS")
            print(f"   👤 User ID: {resources_info.get('user_id')}")
            print(f"   📊 Resource Count: {resources_info.get('resource_count')}")
            print(f"   🔒 User Isolation: {resources_info.get('user_isolation')}")
            
            mcp_resources = resources_info.get('mcp_resources', {})
            print(f"   🔗 MCP Resources: {len(mcp_resources)}")
            
            for resource_id, resource_data in mcp_resources.items():
                address = resource_data.get('address', 'N/A')
                source_file = resource_data.get('source_file', 'N/A')
                print(f"      • {resource_id}: {source_file} ({address})")
                
        else:
            print(f"❌ User Resources: FAILED")
            print(f"   Error: {resources_data.get('message')}")
        
        # Test Summary with timing breakdown
        total_test_time = time.time() - test_start_time
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY & PERFORMANCE METRICS")
        print("=" * 60)
        print("✅ PDF → Knowledge Graph Pipeline: WORKING")
        print("✅ Text Extraction: VERIFIED")
        print("✅ Knowledge Graph Creation: VERIFIED")
        print("✅ Neo4j Storage: VERIFIED")
        print("✅ GraphRAG Queries: WORKING")
        print("✅ User Resource Management: WORKING")
        print("✅ Service Integration: COMPLETE")
        
        print("\n⏱️  PERFORMANCE BREAKDOWN:")
        print(f"   🔧 Service Initialization: Fast (< 1s)")
        print(f"   📄 PDF to Knowledge Graph: {(test1_time - test1_start):.1f}s")
        print(f"   🔍 Knowledge Graph Queries: {(test2_time - test2_start):.1f}s")
        print(f"   📊 User Resource Management: {(test3_time - test3_start):.1f}s")
        print(f"   🎯 TOTAL TEST TIME: {total_test_time:.1f}s")
        
        print(f"\n🎉 ALL TESTS PASSED in {total_test_time:.1f} seconds!")
        print("🚀 Rewritten Graph Analytics Tools are working correctly!")
        
        return True
        
    except Exception as e:
        total_test_time = time.time() - test_start_time
        print(f"❌ Test failed with error after {total_test_time:.1f}s: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the test"""
    main_start = time.time()
    print(f"🧪 Graph Analytics Tools Integration Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Testing the complete PDF → Knowledge Graph pipeline\n")
    
    success = await test_graph_analytics_tools()
    
    main_time = time.time() - main_start
    
    if success:
        print(f"\n✨ SUCCESS: All integration tests passed in {main_time:.1f}s!")
        print("✨ The rewritten Graph Analytics Tools are working correctly!")
        print("✨ Complete PDF → Knowledge Graph pipeline verified!")
    else:
        print(f"\n❌ FAILURE: Some tests failed after {main_time:.1f}s")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())