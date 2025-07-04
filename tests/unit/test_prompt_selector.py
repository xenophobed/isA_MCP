#!/usr/bin/env python3
"""
Test for prompt selector
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def test_prompt_selector():
    """Test prompt selector with ISA Model client"""
    print("🧪 TESTING PROMPT SELECTOR")
    print("=" * 50)
    
    try:
        from prompts.prompt_selector import PromptSelector
        
        print("📋 Test: Prompt selector initialization")
        
        # Create prompt selector
        selector = PromptSelector()
        
        # Add some mock prompt info
        selector.prompts_info = {
            "user_assistance_prompt": {
                "description": "Help users with general questions and tasks",
                "keywords": ["help", "assist", "user", "question", "task"]
            },
            "security_analysis_prompt": {
                "description": "Analyze security vulnerabilities and threats",
                "keywords": ["security", "vulnerability", "threat", "analysis", "safety"]
            },
            "memory_organization_prompt": {
                "description": "Organize and structure memory information",
                "keywords": ["memory", "organize", "structure", "information", "data"]
            }
        }
        
        print(f"   ✅ Prompt selector created with {len(selector.prompts_info)} prompts")
        
        # Initialize (this will create embeddings)
        print("   Initializing embeddings...")
        await selector.initialize()
        
        print(f"   ✅ Embeddings initialized: {len(selector.embeddings_cache)} prompts")
        
        # Test prompt selection
        test_queries = [
            "I need help with my task",
            "Check for security issues",
            "Organize my memories"
        ]
        
        for query in test_queries:
            print(f"\n   🔍 Query: '{query}'")
            selected_prompts = await selector.select_prompts(query, max_prompts=2)
            print(f"   📋 Selected prompts: {selected_prompts}")
        
        await selector.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {str(e)}")
        import traceback
        print(f"📋 Full traceback:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("🚀 Starting Prompt Selector Test...")
    success = asyncio.run(test_prompt_selector())
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n❌ Test failed!")