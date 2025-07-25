#!/usr/bin/env python3
"""
Unified Memory System Test
测试所有记忆类型的存储和统一搜索功能
"""

import asyncio
import json
import sys
import os

# Add the project root to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../..'))

from tools.services.memory_service.memory_service import MemoryService
from tools.services.memory_service.models import MemorySearchQuery
# 不需要外部配置，直接使用内置配置

async def test_unified_memory_system():
    """
    完整测试：
    1. 所有6种记忆类型都能存储
    2. 统一搜索能找到所有类型的记忆
    """
    print("🧪 Unified Memory System Test")
    print("=" * 60)
    
    memory_service = MemoryService()
    user_id = "8735f5bb-9e97-4461-aef8-0197e6e1b008"  # 使用真实用户ID
    
    # 测试数据 - 围绕"Python编程"主题，这样搜索时能找到所有类型
    test_data = {
        "factual": "Python is a programming language created by Guido van Rossum in 1991. I am proficient in Python with 5 years of experience.",
        "episodic": "Yesterday I attended a Python conference in San Francisco. The keynote speaker was talking about async programming. I met some interesting developers from Google.",
        "semantic": "Python programming involves object-oriented programming, functional programming, and dynamic typing. Key concepts include classes, functions, and modules.",
        "procedural": "To create a Python web application: 1) Install Flask or Django, 2) Set up virtual environment, 3) Create app structure, 4) Define routes, 5) Add templates, 6) Deploy to server.",
        "working": "Currently working on a Python data analysis project using pandas and numpy. Need to finish the visualization module by Friday.",
        "session": "User is discussing Python development best practices and asking about code optimization techniques."
    }
    
    print(f"👤 User ID: {user_id}")
    print(f"🎯 Testing all 6 memory types with Python programming theme")
    print()
    
    # === STEP 1: 存储所有类型的记忆 ===
    print("📝 STEP 1: Storing all memory types...")
    stored_memories = {}
    
    # 1. Factual Memory  
    print("  🔢 Storing factual memory...")
    result = await memory_service.store_factual_memory(
        user_id=user_id,
        dialog_content=test_data["factual"],
        importance_score=0.8
    )
    stored_memories["factual"] = {"success": result.success, "message": result.message, "data": result.data}
    print(f"    Result: {'✅' if result.success else '❌'} {result.message}")
    
    # 2. Episodic Memory
    print("  📅 Storing episodic memory...")
    result = await memory_service.store_episodic_memory(
        user_id=user_id,
        dialog_content=test_data["episodic"],
        importance_score=0.8
    )
    stored_memories["episodic"] = {"success": result.success, "message": result.message, "data": result.data}
    print(f"    Result: {'✅' if result.success else '❌'} {result.message}")
    
    # 3. Semantic Memory
    print("  🧠 Storing semantic memory...")
    result = await memory_service.store_semantic_memory(
        user_id=user_id,
        dialog_content=test_data["semantic"],
        importance_score=0.8
    )
    stored_memories["semantic"] = {"success": result.success, "message": result.message, "data": result.data}
    print(f"    Result: {'✅' if result.success else '❌'} {result.message}")
    
    # 4. Procedural Memory
    print("  ⚙️ Storing procedural memory...")
    result = await memory_service.store_procedural_memory(
        user_id=user_id,
        dialog_content=test_data["procedural"],
        importance_score=0.8
    )
    stored_memories["procedural"] = {"success": result.success, "message": result.message, "data": result.data}
    print(f"    Result: {'✅' if result.success else '❌'} {result.message}")
    
    # 5. Working Memory
    print("  💭 Storing working memory...")
    result = await memory_service.store_working_memory(
        user_id=user_id,
        dialog_content=test_data["working"],
        ttl_seconds=3600,  # 1 hour
        importance_score=0.8
    )
    stored_memories["working"] = {"success": result.success, "message": result.message, "data": result.data}
    print(f"    Result: {'✅' if result.success else '❌'} {result.message}")
    
    # 6. Session Memory
    print("  💬 Storing session message...")
    result = await memory_service.store_session_message(
        user_id=user_id,
        session_id="test_session_001",
        message_content=test_data["session"],
        importance_score=0.8
    )
    stored_memories["session"] = {"success": result.success, "message": result.message, "data": result.data}
    print(f"    Result: {'✅' if result.success else '❌'} {result.message}")
    
    # 统计存储结果
    successful_stores = sum(1 for mem_type, result in stored_memories.items() if result["success"])
    print(f"\n📊 Storage Summary: {successful_stores}/6 memory types stored successfully")
    
    if successful_stores < 6:
        print("❌ Not all memory types were stored successfully:")
        for mem_type, result in stored_memories.items():
            if not result["success"]:
                print(f"  - {mem_type}: {result['message']}")
        return False
    
    # === STEP 2: 统一搜索所有类型 ===
    print(f"\n🔍 STEP 2: Testing unified search across all memory types...")
    
    # 搜索"Python programming"应该能找到所有类型的记忆
    search_query = MemorySearchQuery(
        query="Python programming development",
        user_id=user_id,
        memory_types=None,  # 搜索所有类型
        top_k=20,
        similarity_threshold=0.3
    )
    
    search_results = await memory_service.search_memories(search_query)
    
    print(f"📥 Found {len(search_results)} memories across all types:")
    
    # 按类型分组统计结果
    results_by_type = {}
    for result in search_results:
        memory_type = result.memory.memory_type
        if hasattr(memory_type, 'value'):
            memory_type = memory_type.value
        else:
            memory_type = str(memory_type)
            
        if memory_type not in results_by_type:
            results_by_type[memory_type] = []
        results_by_type[memory_type].append(result)
    
    # 显示每种类型的搜索结果
    for memory_type, results in results_by_type.items():
        print(f"\n  📂 {memory_type.upper()} ({len(results)} results):")
        for i, result in enumerate(results[:3], 1):  # 只显示前3个
            print(f"    {i}. Score: {result.similarity_score:.3f} - {result.memory.content[:60]}...")
    
    # 验证是否找到了多种类型的记忆
    found_types = set(results_by_type.keys())
    print(f"\n📊 Search Summary:")
    print(f"  - Found memory types: {sorted(found_types)}")
    print(f"  - Total types found: {len(found_types)}")
    print(f"  - Total memories found: {len(search_results)}")
    
    # === STEP 3: 验证结果 ===
    print(f"\n✅ FINAL RESULTS:")
    print(f"  📝 Storage: {successful_stores}/6 memory types stored")
    print(f"  🔍 Search: {len(found_types)} different memory types found")
    print(f"  🎯 Total memories retrieved: {len(search_results)}")
    
    # 成功标准：存储了所有6种类型，搜索找到了至少3种不同类型
    success = successful_stores == 6 and len(found_types) >= 3
    
    if success:
        print(f"\n🎉 SUCCESS! Unified memory system is working correctly!")
        print(f"   ✅ All 6 memory types can be stored")
        print(f"   ✅ Unified search finds memories across multiple types")
        print(f"   ✅ Vector similarity search is working properly")
    else:
        print(f"\n❌ FAILURE! Issues detected in unified memory system:")
        if successful_stores < 6:
            print(f"   - Only {successful_stores}/6 memory types could be stored")
        if len(found_types) < 3:
            print(f"   - Unified search only found {len(found_types)} memory types")
    
    return success

if __name__ == "__main__":
    asyncio.run(test_unified_memory_system())