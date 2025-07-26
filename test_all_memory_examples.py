#!/usr/bin/env python3
"""
Test All Memory Examples from Documentation
Tests all examples from HowTos/how_to_memory.md to verify services are working
"""

import asyncio
import sys
import os
import json

# Add the project root to the Python path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from tools.mcp_client import default_client

# Use the exact user_id from documentation examples
TEST_USER_ID = "8735f5bb-9e97-4461-aef8-0197e6e1b008"

class MemoryTestRunner:
    def __init__(self):
        self.results = []
        self.test_counter = 0
    
    async def run_test(self, test_name, tool_name, args, expected_keys=None):
        """Run a single test and track results"""
        self.test_counter += 1
        print(f"\n📝 Test {self.test_counter}: {test_name}")
        print(f"   Tool: {tool_name}")
        print(f"   Args: {json.dumps(args, indent=2)}")
        
        try:
            raw_response = await default_client.call_tool(tool_name, args)
            parsed_response = default_client.parse_tool_response(raw_response)
            
            success = parsed_response.get("status") == "success"
            status_emoji = "✅" if success else "❌"
            
            print(f"   {status_emoji} Status: {parsed_response.get('status')}")
            
            if success:
                data = parsed_response.get("data", {})
                print(f"   📋 Response data keys: {list(data.keys())}")
                
                # Check for expected keys if provided
                if expected_keys:
                    missing_keys = [key for key in expected_keys if key not in data]
                    if missing_keys:
                        print(f"   ⚠️  Missing expected keys: {missing_keys}")
                    else:
                        print(f"   ✅ All expected keys present: {expected_keys}")
                
                # Show some key data
                if "memory_id" in data:
                    print(f"   🆔 Memory ID: {data['memory_id']}")
                if "total_results" in data:
                    print(f"   📊 Total results: {data['total_results']}")
                if "message" in data:
                    print(f"   📝 Message: {data['message']}")
                if "total_memories" in data:
                    print(f"   📈 Total memories: {data['total_memories']}")
                    
            else:
                error_msg = parsed_response.get("error_message", "Unknown error")
                print(f"   💥 Error: {error_msg}")
            
            self.results.append({
                "test_name": test_name,
                "tool_name": tool_name,
                "success": success,
                "response": parsed_response
            })
            
            return success
            
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.results.append({
                "test_name": test_name,
                "tool_name": tool_name,
                "success": False,
                "error": str(e)
            })
            return False
    
    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*60}")
        print("📊 FINAL TEST SUMMARY")
        print(f"{'='*60}")
        
        passed = sum(1 for r in self.results if r["success"])
        total = len(self.results)
        
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total - passed}/{total}")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Memory services are fully operational!")
        else:
            print("\n⚠️  FAILED TESTS:")
            for result in self.results:
                if not result["success"]:
                    print(f"   ❌ {result['test_name']} ({result['tool_name']})")
                    if "error" in result:
                        print(f"      Error: {result['error']}")
                    elif "response" in result:
                        error_msg = result["response"].get("error_message", "Unknown")
                        print(f"      Error: {error_msg}")

async def main():
    """Run all memory examples from documentation"""
    
    print("🧠 MEMORY SERVICE COMPREHENSIVE TEST")
    print("Testing all examples from HowTos/how_to_memory.md")
    print("=" * 60)
    print(f"👤 Test User ID: {TEST_USER_ID}")
    
    runner = MemoryTestRunner()
    
    # ========== CORE STORAGE TOOLS (Examples from docs) ==========
    
    # Test 1: store_factual_memory
    await runner.run_test(
        "Store Factual Memory (Documentation Example)",
        "store_factual_memory",
        {
            "user_id": TEST_USER_ID,
            "dialog_content": "Claude is an AI assistant created by Anthropic. It was trained using Constitutional AI techniques.",
            "importance_score": 0.8
        },
        expected_keys=["memory_id", "message", "operation"]
    )
    
    # Test 2: store_episodic_memory  
    await runner.run_test(
        "Store Episodic Memory (Documentation Example)",
        "store_episodic_memory",
        {
            "user_id": TEST_USER_ID,
            "dialog_content": "Yesterday we had our quarterly team meeting. Alice presented the new feature roadmap and we discussed the microservices migration plan.",
            "episode_date": "2025-01-24T14:00:00Z",
            "importance_score": 0.7
        },
        expected_keys=["memory_id", "message", "operation"]
    )
    
    # Test 3: store_semantic_memory
    await runner.run_test(
        "Store Semantic Memory (Documentation Example)",
        "store_semantic_memory",
        {
            "user_id": TEST_USER_ID,
            "dialog_content": "Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data without being explicitly programmed.",
            "importance_score": 0.9
        },
        expected_keys=["memory_id", "message", "operation"]
    )
    
    # Test 4: store_procedural_memory
    await runner.run_test(
        "Store Procedural Memory (Documentation Example)",
        "store_procedural_memory",
        {
            "user_id": TEST_USER_ID,
            "dialog_content": "To deploy our application: First, run tests with 'npm test'. Then build with 'npm run build'. Upload artifacts to staging. After approval, deploy to production using the CI/CD pipeline.",
            "importance_score": 0.8
        },
        expected_keys=["memory_id", "message", "operation"]
    )
    
    # Test 5: store_working_memory
    await runner.run_test(
        "Store Working Memory (Documentation Example)",
        "store_working_memory",
        {
            "user_id": TEST_USER_ID,
            "dialog_content": "Currently working on the authentication feature. Need to implement password reset and 2FA. Deadline is Friday.",
            "ttl_seconds": 604800,
            "importance_score": 0.7
        },
        expected_keys=["memory_id", "message", "operation"]
    )
    
    # Test 6: store_session_message
    await runner.run_test(
        "Store Session Message (Documentation Example)",
        "store_session_message",
        {
            "user_id": TEST_USER_ID,
            "session_id": "session_auth_discussion_001",
            "message_content": "How should we implement OAuth 2.0 for our API?",
            "message_type": "human",
            "role": "user",
            "importance_score": 0.6
        },
        expected_keys=["memory_id", "message", "operation"]
    )
    
    # ========== SEARCH AND RETRIEVAL TOOLS ==========
    
    # Test 7: search_memories
    await runner.run_test(
        "Search Memories (Documentation Example)",
        "search_memories",
        {
            "user_id": TEST_USER_ID,
            "query": "AI assistant",
            "top_k": 5
        },
        expected_keys=["query", "total_results", "results"]
    )
    
    # Test 8: search_facts_by_subject
    await runner.run_test(
        "Search Facts by Subject (Documentation Example)",
        "search_facts_by_subject",
        {
            "user_id": TEST_USER_ID,
            "subject": "Claude",
            "limit": 5
        },
        expected_keys=["subject", "total_results", "results"]
    )
    
    # Test 9: search_concepts_by_category
    await runner.run_test(
        "Search Concepts by Category (Documentation Example)",
        "search_concepts_by_category",
        {
            "user_id": TEST_USER_ID,
            "category": "AI/ML",
            "limit": 5
        },
        expected_keys=["category", "total_results", "results"]
    )
    
    # ========== SESSION AND WORKING MEMORY TOOLS ==========
    
    # Test 10: get_session_context
    await runner.run_test(
        "Get Session Context (Documentation Example)",
        "get_session_context",
        {
            "user_id": TEST_USER_ID,
            "session_id": "test_session_summarization_001",
            "include_summaries": True,
            "max_recent_messages": 5
        },
        expected_keys=["session_found", "user_id", "session_id"]
    )
    
    # Test 11: get_active_working_memories
    await runner.run_test(
        "Get Active Working Memories (Documentation Example)",
        "get_active_working_memories",
        {
            "user_id": TEST_USER_ID
        },
        expected_keys=["total_results", "results"]
    )
    
    # ========== UTILITY TOOLS ==========
    
    # Test 12: get_memory_statistics
    await runner.run_test(
        "Get Memory Statistics (Documentation Example)",
        "get_memory_statistics",
        {
            "user_id": TEST_USER_ID
        },
        expected_keys=["user_id", "total_memories", "by_type"]
    )
    
    # Print final summary
    runner.print_summary()

if __name__ == "__main__":
    asyncio.run(main())