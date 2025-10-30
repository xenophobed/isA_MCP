#!/usr/bin/env python3
"""
Enhanced Plan Tools Example
Demonstrates new features from Sequential Thinking MCP pattern:
- Execution history tracking
- Plan branching and revision
- Dynamic plan adjustment
- Real-time status monitoring
"""

import asyncio
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from tools.general_tools.plan_tools_enhanced import EnhancedAutonomousPlanner
from tools.general_tools.plan_state_manager import create_state_manager


async def example_1_basic_plan_with_tracking():
    """Example 1: Create plan with automatic state tracking"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Plan Creation with State Tracking")
    print("="*80)

    planner = EnhancedAutonomousPlanner()

    # Create execution plan
    result = await planner.create_execution_plan(
        guidance="Build a web scraping pipeline with error handling",
        available_tools=["web_crawler", "html_parser", "data_validator", "storage_service"],
        request="Create a system to scrape product data from e-commerce sites"
    )

    result_data = json.loads(result)
    if result_data['status'] == 'success':
        plan = result_data['data']
        plan_id = plan['plan_id']
        print(f"\n✅ Plan created: {plan_id}")
        print(f"   Hypothesis: {plan.get('solution_hypothesis')}")
        print(f"   Tasks: {plan['total_tasks']}")

        return plan_id
    else:
        print(f"\n❌ Plan creation failed: {result_data.get('message')}")
        return None


async def example_2_update_task_status(plan_id: str):
    """Example 2: Update task status with visual feedback"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Update Task Status")
    print("="*80)

    if not plan_id:
        print("⚠️ No plan_id provided, skipping...")
        return

    planner = EnhancedAutonomousPlanner()

    # Simulate task execution
    print("\n🔄 Simulating task execution...")

    # Start task 1
    result = planner.update_task_status(plan_id, 1, "in_progress")
    print("  Task 1: Started")

    await asyncio.sleep(1)

    # Complete task 1
    result = planner.update_task_status(
        plan_id, 1, "completed",
        {"output": "Successfully crawled 100 products"}
    )
    print("  Task 1: Completed")

    # Start task 2
    result = planner.update_task_status(plan_id, 2, "in_progress")
    print("  Task 2: Started")

    await asyncio.sleep(1)

    # Task 2 encounters issue
    result = planner.update_task_status(
        plan_id, 2, "failed",
        {"error": "HTML parsing failed for 20% of products"}
    )
    print("  Task 2: Failed")


async def example_3_get_plan_status(plan_id: str):
    """Example 3: Get real-time plan status"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Real-Time Plan Status")
    print("="*80)

    if not plan_id:
        print("⚠️ No plan_id provided, skipping...")
        return

    planner = EnhancedAutonomousPlanner()

    # Get plan status
    result = planner.get_plan_status(plan_id)
    result_data = json.loads(result)

    if result_data['status'] == 'success':
        status = result_data['data']
        print("\nPlan Status Retrieved:")
        print(f"  Progress: {status['progress_percentage']}%")
        print(f"  Completed: {status['completed_tasks']}/{status['total_tasks']}")
        print(f"  Failed: {status['failed_tasks']}")
        print(f"  Current Task: {status.get('current_task', 'None')}")


async def example_4_adjust_plan_expand(plan_id: str):
    """Example 4: Dynamically expand plan with new tasks"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Dynamic Plan Expansion")
    print("="*80)

    if not plan_id:
        print("⚠️ No plan_id provided, skipping...")
        return

    planner = EnhancedAutonomousPlanner()

    # Add new tasks discovered during execution
    new_tasks = [
        {
            "title": "Implement Retry Logic",
            "description": "Add retry mechanism for failed parsing",
            "tools": ["retry_service", "error_handler"],
            "execution_type": "sequential",
            "dependencies": [2],
            "expected_output": "Retry logic implemented",
            "verification_criteria": "Failed items reduced to <5%",
            "priority": "high"
        },
        {
            "title": "Data Quality Check",
            "description": "Validate scraped data quality",
            "tools": ["data_validator", "quality_checker"],
            "execution_type": "sequential",
            "dependencies": [2],
            "expected_output": "Quality metrics report",
            "verification_criteria": "Data quality >95%",
            "priority": "medium"
        }
    ]

    result = await planner.adjust_execution_plan(
        plan_id=plan_id,
        adjustment_type="expand",
        new_tasks=new_tasks,
        reasoning="Task 2 failed - adding retry logic and quality checks"
    )

    result_data = json.loads(result)
    if result_data['status'] == 'success':
        print("\n✅ Plan expanded successfully")
        updated_plan = result_data['data']['updated_plan']
        print(f"   Total tasks: {updated_plan['total_tasks']}")
        print("   New tasks added:")
        for task in new_tasks:
            print(f"     - {task['title']}")


async def example_5_create_branch(plan_id: str):
    """Example 5: Create alternative execution branch"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Plan Branching")
    print("="*80)

    if not plan_id:
        print("⚠️ No plan_id provided, skipping...")
        return

    planner = EnhancedAutonomousPlanner()

    # Create alternative approach branch
    branch_tasks = [
        {
            "title": "Use Alternative Parser",
            "description": "Try BeautifulSoup instead of current parser",
            "tools": ["beautifulsoup_parser", "html_processor"],
            "execution_type": "sequential",
            "dependencies": [],
            "expected_output": "Parsed data with alternative parser",
            "verification_criteria": "Success rate >90%",
            "priority": "high"
        }
    ]

    result = await planner.adjust_execution_plan(
        plan_id=plan_id,
        adjustment_type="branch",
        task_id=2,
        new_tasks=branch_tasks,
        reasoning="Current parser failing - trying alternative approach"
    )

    result_data = json.loads(result)
    if result_data['status'] == 'success':
        print("\n✅ Branch created successfully")
        print("   Branch represents alternative execution path")


async def example_6_execution_history(plan_id: str):
    """Example 6: View complete execution history"""
    print("\n" + "="*80)
    print("EXAMPLE 6: Execution History")
    print("="*80)

    if not plan_id:
        print("⚠️ No plan_id provided, skipping...")
        return

    planner = EnhancedAutonomousPlanner()

    history = planner.state_manager.get_execution_history(plan_id)

    print(f"\n📜 Execution History ({len(history)} events):")
    for i, event in enumerate(history, 1):
        event_type = event.get('event_type', 'unknown')
        timestamp = event.get('timestamp', 'N/A')
        print(f"\n  Event {i}: {event_type}")
        print(f"    Timestamp: {timestamp}")
        if event.get('data'):
            print(f"    Data: {json.dumps(event['data'], indent=6)}")


async def example_7_list_active_plans():
    """Example 7: List all active plans"""
    print("\n" + "="*80)
    print("EXAMPLE 7: List Active Plans")
    print("="*80)

    planner = EnhancedAutonomousPlanner()

    plan_ids = planner.state_manager.list_active_plans()

    print(f"\n📋 Active Plans ({len(plan_ids)}):")
    for plan_id in plan_ids:
        print(f"  - {plan_id}")
        # Get status for each
        plan = planner.state_manager.get_plan(plan_id)
        if plan:
            print(f"    Status: {plan.get('status', 'unknown')}")
            print(f"    Tasks: {plan.get('total_tasks', 0)}")


async def example_8_storage_backends():
    """Example 8: Compare storage backends"""
    print("\n" + "="*80)
    print("EXAMPLE 8: Storage Backend Comparison")
    print("="*80)

    # In-Memory Backend
    print("\n1️⃣ In-Memory Backend:")
    from tools.general_tools.plan_state_manager import InMemoryStateStore
    memory_store = InMemoryStateStore()
    planner_mem = EnhancedAutonomousPlanner(state_manager=memory_store)
    print(f"   ✅ Created with {type(memory_store).__name__}")
    print("   ⚠️  Data will NOT persist on restart")

    # Redis Backend (if available)
    print("\n2️⃣ Redis Backend:")
    try:
        from tools.general_tools.plan_state_manager import RedisStateStore
        redis_store = RedisStateStore()
        planner_redis = EnhancedAutonomousPlanner(state_manager=redis_store)
        print(f"   ✅ Created with {type(redis_store).__name__}")
        print("   ✅ Data WILL persist on restart")
    except Exception as e:
        print(f"   ❌ Redis not available: {e}")
        print("   💡 Falling back to in-memory storage")

    # Auto-detection
    print("\n3️⃣ Auto-Detection (Recommended):")
    auto_store = create_state_manager(prefer_redis=True)
    planner_auto = EnhancedAutonomousPlanner(state_manager=auto_store)
    print(f"   ✅ Auto-selected: {type(auto_store).__name__}")


async def main():
    """Run all examples"""
    print("\n" + "🚀"*40)
    print("Enhanced Plan Tools Examples")
    print("Based on MCP Sequential Thinking Patterns")
    print("🚀"*40)

    # Run examples sequentially
    plan_id = await example_1_basic_plan_with_tracking()

    if plan_id:
        await example_2_update_task_status(plan_id)
        await example_3_get_plan_status(plan_id)
        await example_4_adjust_plan_expand(plan_id)
        await example_5_create_branch(plan_id)
        await example_6_execution_history(plan_id)

    await example_7_list_active_plans()
    await example_8_storage_backends()

    print("\n" + "✅"*40)
    print("Examples completed!")
    print("✅"*40 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
