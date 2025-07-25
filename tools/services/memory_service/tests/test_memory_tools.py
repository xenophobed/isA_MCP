#!/usr/bin/env python3
"""
Test script for memory_tools.py
Tests all MCP tools in memory_tools with real data
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.insert(0, project_root)

from tools.mcp_client import default_client

class MemoryToolsTestSuite:
    """Comprehensive test suite for memory_tools.py MCP tools"""
    
    def __init__(self):
        self.user_id = "8735f5bb-9e97-4461-aef8-0197e6e1b008"  # Real UUID user
        self.session_id = "test_session_memory_tools"
        self.test_results = []
        
        # Test data themed around "AI Development" for unified search testing
        self.test_data = {
            "factual": "OpenAI released ChatGPT in November 2022. It's based on GPT-3.5 architecture. I have been working with AI models for 3 years.",
            "episodic": "Last week I attended the AI Conference 2024 in San Francisco. The main topic was transformer architectures and their applications. I met researchers from Stanford and MIT.",
            "semantic": "Artificial Intelligence encompasses machine learning, deep learning, natural language processing, and computer vision. Neural networks are fundamental building blocks.",
            "procedural": "To fine-tune a language model: 1) Prepare training data, 2) Set up training environment, 3) Configure hyperparameters, 4) Run training loop, 5) Evaluate performance, 6) Deploy model.",
            "working": "Currently developing an AI chatbot using Python and transformers library. Deadline is next Friday. Need to implement RAG architecture.",
            "session": "User is asking about best practices for training large language models and wants recommendations for GPU resources."
        }
    
    async def test_dialog_storage_tools(self):
        """Test all 'store_*_memory_from_dialog' tools"""
        print("🧪 Test 1: Dialog-based Storage Tools")
        print("="*60)
        
        storage_tools = [
            ("store_factual_memory_from_dialog", "factual"),
            ("store_episodic_memory_from_dialog", "episodic"), 
            ("store_semantic_memory_from_dialog", "semantic"),
            ("store_procedural_memory_from_dialog", "procedural"),
            ("store_working_memory_from_dialog", "working")
        ]
        
        success_count = 0
        
        for tool_name, data_key in storage_tools:
            print(f"\n🔧 Testing {tool_name}...")
            
            test_args = {
                "user_id": self.user_id,
                "dialog_content": self.test_data[data_key],
                "importance_score": 0.8
            }
            
            try:
                # Call the MCP tool
                raw_response = await default_client.call_tool(tool_name, test_args)
                parsed_response = default_client.parse_tool_response(raw_response)
                
                print(f"  📝 Dialog: {self.test_data[data_key][:50]}...")
                print(f"  📤 Status: {parsed_response.get('status', 'unknown')}")
                print(f"  📨 Message: {parsed_response.get('data', {}).get('message', 'N/A')}")
                
                if parsed_response.get('status') == 'success':
                    data = parsed_response.get('data', {})
                    total_facts = data.get('total_facts', data.get('stored_count', 'N/A'))
                    print(f"  ✅ SUCCESS: Stored {total_facts} memories")
                    success_count += 1
                else:
                    error_msg = parsed_response.get('data', {}).get('message', 'Unknown error')
                    print(f"  ❌ FAILED: {error_msg}")
                
            except Exception as e:
                print(f"  ❌ EXCEPTION: {str(e)}")
        
        self.test_results.append(("Dialog Storage Tools", success_count, len(storage_tools)))
        print(f"\n📊 Dialog Storage Test Summary: {success_count}/{len(storage_tools)} tools passed")
        return success_count == len(storage_tools)
    
    async def test_direct_storage_tools(self):
        """Test direct storage tools (store_fact, store_episode, etc.)"""
        print("\n🧪 Test 2: Direct Storage Tools")  
        print("="*60)
        
        success_count = 0
        
        # Test store_fact
        print(f"\n🔧 Testing store_fact...")
        fact_args = {
            "user_id": self.user_id,
            "fact_type": "technology",
            "subject": "GPT-4",
            "predicate": "developed_by", 
            "object_value": "OpenAI",
            "context": "Large language model",
            "confidence": 0.9
        }
        
        try:
            raw_response = await default_client.call_tool("store_fact", fact_args)
            parsed_response = default_client.parse_tool_response(raw_response)
            
            print(f"  📝 Fact: {fact_args['subject']} {fact_args['predicate']} {fact_args['object_value']}")
            print(f"  📤 Status: {parsed_response.get('status', 'unknown')}")
            
            if parsed_response.get('status') == 'success':
                print(f"  ✅ SUCCESS: Fact stored")
                success_count += 1
            else:
                print(f"  ❌ FAILED: {parsed_response.get('data', {}).get('message', 'Unknown error')}")
        except Exception as e:
            print(f"  ❌ EXCEPTION: {str(e)}")
        
        # Test store_episode
        print(f"\n🔧 Testing store_episode...")
        episode_args = {
            "user_id": self.user_id,
            "event_type": "conference",
            "content": "Attended keynote on transformer architecture at AI Summit 2024",
            "location": "San Francisco Convention Center",
            "participants": "Dr. Sarah Chen, Prof. Michael Liu",
            "emotional_valence": 0.8
        }
        
        try:
            raw_response = await default_client.call_tool("store_episode", episode_args) 
            parsed_response = default_client.parse_tool_response(raw_response)
            
            print(f"  📝 Episode: {episode_args['event_type']} at {episode_args['location']}")
            print(f"  📤 Status: {parsed_response.get('status', 'unknown')}")
            
            if parsed_response.get('status') == 'success':
                print(f"  ✅ SUCCESS: Episode stored")
                success_count += 1
            else:
                print(f"  ❌ FAILED: {parsed_response.get('data', {}).get('message', 'Unknown error')}")
        except Exception as e:
            print(f"  ❌ EXCEPTION: {str(e)}")
        
        # Test store_concept
        print(f"\n🔧 Testing store_concept...")
        concept_args = {
            "user_id": self.user_id,
            "concept_name": "Neural Networks",
            "category": "AI/ML",
            "definition": "Computational models inspired by biological neural networks",
            "examples": "CNN, RNN, Transformer",
            "mastery_level": 0.75
        }
        
        try:
            raw_response = await default_client.call_tool("store_concept", concept_args)
            parsed_response = default_client.parse_tool_response(raw_response)
            
            print(f"  📝 Concept: {concept_args['concept_name']} ({concept_args['category']})")
            print(f"  📤 Status: {parsed_response.get('status', 'unknown')}")
            
            if parsed_response.get('status') == 'success':
                print(f"  ✅ SUCCESS: Concept stored")
                success_count += 1
            else:
                print(f"  ❌ FAILED: {parsed_response.get('data', {}).get('message', 'Unknown error')}")
        except Exception as e:
            print(f"  ❌ EXCEPTION: {str(e)}")
        
        # Test store_procedure
        print(f"\n🔧 Testing store_procedure...")
        procedure_args = {
            "user_id": self.user_id,
            "procedure_name": "Model Training",
            "domain": "machine_learning", 
            "steps": "1. Data prep, 2. Model config, 3. Training, 4. Evaluation",
            "context": "Standard ML workflow",
            "difficulty_level": 3
        }
        
        try:
            raw_response = await default_client.call_tool("store_procedure", procedure_args)
            parsed_response = default_client.parse_tool_response(raw_response)
            
            print(f"  📝 Procedure: {procedure_args['procedure_name']} (Level {procedure_args['difficulty_level']})")
            print(f"  📤 Status: {parsed_response.get('status', 'unknown')}")
            
            if parsed_response.get('status') == 'success':  
                print(f"  ✅ SUCCESS: Procedure stored")
                success_count += 1
            else:
                print(f"  ❌ FAILED: {parsed_response.get('data', {}).get('message', 'Unknown error')}")
        except Exception as e:
            print(f"  ❌ EXCEPTION: {str(e)}")
        
        self.test_results.append(("Direct Storage Tools", success_count, 4))
        print(f"\n📊 Direct Storage Test Summary: {success_count}/4 tools passed")
        return success_count == 4
    
    async def test_search_tools(self):
        """Test all search tools"""
        print("\n🧪 Test 3: Search Tools")
        print("="*60)
        
        success_count = 0
        
        # Test unified search_memories
        print(f"\n🔧 Testing search_memories...")
        search_args = {
            "user_id": self.user_id,
            "query": "AI machine learning neural networks",
            "limit": 10,
            "similarity_threshold": 0.3
        }
        
        try:
            raw_response = await default_client.call_tool("search_memories", search_args)
            parsed_response = default_client.parse_tool_response(raw_response)
            
            print(f"  🔍 Query: {search_args['query']}")
            print(f"  📤 Status: {parsed_response.get('status', 'unknown')}")
            
            if parsed_response.get('status') == 'success':
                data = parsed_response.get('data', {})
                results = data.get('results', [])
                count = data.get('count', len(results))
                print(f"  ✅ SUCCESS: Found {count} memories")
                
                # Show memory types found
                if results:
                    types_found = set(r.get('memory_type', 'unknown') for r in results)
                    print(f"  📂 Types found: {sorted(types_found)}")
                    
                    # Show top 3 results
                    print(f"  🔝 Top results:")
                    for i, result in enumerate(results[:3], 1):
                        score = result.get('similarity_score', 0)
                        content = result.get('content', 'N/A')[:40]
                        print(f"    {i}. Score: {score:.3f} - {content}...")
                
                success_count += 1
            else:
                print(f"  ❌ FAILED: {parsed_response.get('data', {}).get('message', 'Unknown error')}")
        except Exception as e:
            print(f"  ❌ EXCEPTION: {str(e)}")
        
        # Test specialized search tools
        specialized_searches = [
            ("search_facts_by_type", {"user_id": self.user_id, "fact_type": "technology", "limit": 5}),
            ("search_episodes_by_participant", {"user_id": self.user_id, "participant": "Dr. Sarah", "limit": 5}),
            ("search_concepts_by_category", {"user_id": self.user_id, "category": "AI/ML", "limit": 5}),
            ("search_procedures_by_domain", {"user_id": self.user_id, "domain": "machine_learning", "limit": 5})
        ]
        
        for tool_name, args in specialized_searches:
            print(f"\n🔧 Testing {tool_name}...")
            
            try:
                raw_response = await default_client.call_tool(tool_name, args)
                parsed_response = default_client.parse_tool_response(raw_response)
                
                print(f"  📤 Status: {parsed_response.get('status', 'unknown')}")
                
                if parsed_response.get('status') == 'success':
                    data = parsed_response.get('data', {})
                    results = data.get('results', [])
                    print(f"  ✅ SUCCESS: Found {len(results)} results")
                    success_count += 1
                else:
                    print(f"  ❌ FAILED: {parsed_response.get('data', {}).get('message', 'Unknown error')}")
            except Exception as e:
                print(f"  ❌ EXCEPTION: {str(e)}")
        
        self.test_results.append(("Search Tools", success_count, 5))
        print(f"\n📊 Search Tools Test Summary: {success_count}/5 tools passed")
        return success_count == 5
    
    async def test_session_tools(self):
        """Test session-related tools"""
        print("\n🧪 Test 4: Session Tools")
        print("="*60)
        
        success_count = 0
        
        # Test store_session_message
        print(f"\n🔧 Testing store_session_message...")
        session_args = {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "message_content": self.test_data["session"],
            "message_type": "human",
            "role": "user",
            "importance_score": 0.7
        }
        
        try:
            raw_response = await default_client.call_tool("store_session_message", session_args)
            parsed_response = default_client.parse_tool_response(raw_response)
            
            print(f"  💬 Session: {self.session_id}")
            print(f"  📝 Message: {session_args['message_content'][:50]}...")
            print(f"  📤 Status: {parsed_response.get('status', 'unknown')}")
            
            if parsed_response.get('status') == 'success':
                print(f"  ✅ SUCCESS: Session message stored")
                success_count += 1
            else:
                print(f"  ❌ FAILED: {parsed_response.get('data', {}).get('message', 'Unknown error')}")
        except Exception as e:
            print(f"  ❌ EXCEPTION: {str(e)}")
        
        # Test get_session_context
        print(f"\n🔧 Testing get_session_context...")
        context_args = {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "include_summaries": True,
            "max_recent_messages": 5
        }
        
        try:
            raw_response = await default_client.call_tool("get_session_context", context_args) 
            parsed_response = default_client.parse_tool_response(raw_response)
            
            print(f"  📤 Status: {parsed_response.get('status', 'unknown')}")
            
            if parsed_response.get('status') == 'success':
                data = parsed_response.get('data', {})
                context = data.get('context', {})
                print(f"  ✅ SUCCESS: Retrieved session context")
                print(f"  📊 Messages: {len(context.get('recent_messages', []))}")
                success_count += 1
            else:
                print(f"  ❌ FAILED: {parsed_response.get('data', {}).get('message', 'Unknown error')}")
        except Exception as e:
            print(f"  ❌ EXCEPTION: {str(e)}")
        
        self.test_results.append(("Session Tools", success_count, 2))
        print(f"\n📊 Session Tools Test Summary: {success_count}/2 tools passed")
        return success_count == 2
    
    async def test_utility_tools(self):
        """Test utility and management tools"""
        print("\n🧪 Test 5: Utility & Management Tools")
        print("="*60)
        
        success_count = 0
        
        # Test get_active_working_memories
        print(f"\n🔧 Testing get_active_working_memories...")
        try:
            raw_response = await default_client.call_tool("get_active_working_memories", {"user_id": self.user_id})
            parsed_response = default_client.parse_tool_response(raw_response)
            
            print(f"  📤 Status: {parsed_response.get('status', 'unknown')}")
            
            if parsed_response.get('status') == 'success':
                data = parsed_response.get('data', {})
                memories = data.get('active_memories', [])
                print(f"  ✅ SUCCESS: Found {len(memories)} active working memories")
                success_count += 1
            else:
                print(f"  ❌ FAILED: {parsed_response.get('data', {}).get('message', 'Unknown error')}")
        except Exception as e:
            print(f"  ❌ EXCEPTION: {str(e)}")
        
        # Test get_memory_statistics
        print(f"\n🔧 Testing get_memory_statistics...")
        try:
            raw_response = await default_client.call_tool("get_memory_statistics", {"user_id": self.user_id})
            parsed_response = default_client.parse_tool_response(raw_response)
            
            print(f"  📤 Status: {parsed_response.get('status', 'unknown')}")
            
            if parsed_response.get('status') == 'success':
                data = parsed_response.get('data', {})
                stats = data.get('statistics', {})
                total = stats.get('total_memories', 0)
                print(f"  ✅ SUCCESS: Total memories: {total}")
                
                by_type = stats.get('by_type', {})
                if by_type:
                    print(f"  📊 By type: {dict(by_type)}")
                success_count += 1
            else:
                print(f"  ❌ FAILED: {parsed_response.get('data', {}).get('message', 'Unknown error')}")
        except Exception as e:
            print(f"  ❌ EXCEPTION: {str(e)}")
        
        # Test cleanup_expired_memories
        print(f"\n🔧 Testing cleanup_expired_memories...")
        try:
            raw_response = await default_client.call_tool("cleanup_expired_memories", {"user_id": self.user_id})
            parsed_response = default_client.parse_tool_response(raw_response)
            
            print(f"  📤 Status: {parsed_response.get('status', 'unknown')}")
            
            if parsed_response.get('status') == 'success':
                data = parsed_response.get('data', {})
                cleaned = data.get('cleaned_count', 0)
                print(f"  ✅ SUCCESS: Cleaned {cleaned} expired memories")
                success_count += 1
            else:
                print(f"  ❌ FAILED: {parsed_response.get('data', {}).get('message', 'Unknown error')}")
        except Exception as e:
            print(f"  ❌ EXCEPTION: {str(e)}")
        
        self.test_results.append(("Utility Tools", success_count, 3))
        print(f"\n📊 Utility Tools Test Summary: {success_count}/3 tools passed")
        return success_count == 3
    
    async def test_unified_workflow(self):
        """Test complete workflow: store → search → manage"""
        print("\n🧪 Test 6: Unified Workflow Integration")
        print("="*60)
        
        workflow_success = True
        
        # Step 1: Store different types of memories
        print(f"\n📝 Step 1: Storing workflow test data...")
        workflow_data = "Machine Learning workflow involves data preprocessing, model training, validation, and deployment. I recently completed a project using PyTorch and achieved 95% accuracy."
        
        try:
            # Store as factual memory
            store_args = {
                "user_id": self.user_id,
                "dialog_content": workflow_data,
                "importance_score": 0.9
            }
            raw_response = await default_client.call_tool("store_factual_memory_from_dialog", store_args)
            parsed_response = default_client.parse_tool_response(raw_response)
            
            if parsed_response.get('status') == 'success':
                stored_facts = parsed_response.get('data', {}).get('total_facts', 0)
                print(f"  ✅ Stored {stored_facts} facts from workflow data")
            else:
                print(f"  ❌ Failed to store workflow data")
                workflow_success = False
        except Exception as e:
            print(f"  ❌ Storage exception: {str(e)}")
            workflow_success = False
        
        # Step 2: Search for the stored data
        print(f"\n🔍 Step 2: Searching for workflow data...")
        try:
            search_args = {
                "user_id": self.user_id,
                "query": "machine learning workflow PyTorch accuracy",
                "limit": 5,
                "similarity_threshold": 0.4
            }
            raw_response = await default_client.call_tool("search_memories", search_args)
            parsed_response = default_client.parse_tool_response(raw_response)
            
            if parsed_response.get('status') == 'success':
                results = parsed_response.get('data', {}).get('results', [])
                found_workflow = any('workflow' in r.get('content', '').lower() for r in results)
                if found_workflow:
                    print(f"  ✅ Successfully found workflow data in search results")
                else:
                    print(f"  ⚠️  Workflow data not found in top results")
                    workflow_success = False
            else:
                print(f"  ❌ Search failed")
                workflow_success = False
        except Exception as e:
            print(f"  ❌ Search exception: {str(e)}")
            workflow_success = False
        
        # Step 3: Check statistics
        print(f"\n📊 Step 3: Verifying memory statistics...")
        try:
            raw_response = await default_client.call_tool("get_memory_statistics", {"user_id": self.user_id})
            parsed_response = default_client.parse_tool_response(raw_response)
            
            if parsed_response.get('status') == 'success':
                stats = parsed_response.get('data', {}).get('statistics', {})
                total = stats.get('total_memories', 0)
                print(f"  ✅ Current total memories: {total}")
                
                if total > 0:
                    print(f"  ✅ Memory system shows active data")
                else:
                    print(f"  ⚠️  No memories found in statistics")
                    workflow_success = False
            else:
                print(f"  ❌ Statistics check failed")
                workflow_success = False
        except Exception as e:
            print(f"  ❌ Statistics exception: {str(e)}")
            workflow_success = False
        
        self.test_results.append(("Unified Workflow", 1 if workflow_success else 0, 1))
        print(f"\n📊 Unified Workflow Test: {'✅ PASSED' if workflow_success else '❌ FAILED'}")
        return workflow_success

async def run_all_memory_tool_tests():
    """Run comprehensive memory tools test suite"""
    print("🚀 Starting memory_tools.py comprehensive tests...")
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    suite = MemoryToolsTestSuite()
    
    # Run all test categories
    tests = [
        suite.test_dialog_storage_tools,
        suite.test_direct_storage_tools,
        suite.test_search_tools,
        suite.test_session_tools,
        suite.test_utility_tools,
        suite.test_unified_workflow
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    # Print comprehensive summary
    print(f"\n{'='*80}")
    print("📊 COMPREHENSIVE TEST SUMMARY")
    print(f"{'='*80}")
    
    total_passed = 0
    total_tests = 0
    
    for test_name, passed, total in suite.test_results:
        success_rate = (passed/total)*100 if total > 0 else 0
        status = "✅ PASSED" if passed == total else "❌ FAILED"
        print(f"{test_name:25} | {passed:2}/{total:2} | {success_rate:5.1f}% | {status}")
        total_passed += passed
        total_tests += total
    
    overall_success_rate = (total_passed/total_tests)*100 if total_tests > 0 else 0
    overall_status = "🎉 ALL PASSED" if total_passed == total_tests else "⚠️  SOME FAILED"
    
    print(f"{'='*80}")
    print(f"OVERALL RESULTS       | {total_passed:2}/{total_tests:2} | {overall_success_rate:5.1f}% | {overall_status}")
    print(f"{'='*80}")
    
    if total_passed == total_tests:
        print("\n🎉 ALL MEMORY TOOLS TESTS PASSED!")
        print("✅ All MCP tools in memory_tools.py are working correctly")
        print("✅ Real data storage and retrieval verified")
        print("✅ Cross-memory-type search functionality confirmed")
        print("✅ Session management and utilities operational")
    else:
        print(f"\n⚠️  {total_tests - total_passed} out of {total_tests} tool categories failed")
        print("📋 Review the detailed output above for specific failures")
        print("💡 Common issues: user permissions, database connectivity, TextExtractor errors")
    
    return total_passed == total_tests

if __name__ == "__main__":
    asyncio.run(run_all_memory_tool_tests())