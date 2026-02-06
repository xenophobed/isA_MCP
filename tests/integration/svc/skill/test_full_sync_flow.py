"""
Full Sync Flow Test - Verify skills, prompts, resources, and tools all use hierarchical search

This script:
1. Syncs skills from SkillManager to database
2. Triggers full sync (tools, prompts, resources)
3. Tests unified meta search across all entity types

Run with:
    python -m tests.integration.svc.skill.test_full_sync_flow

Prerequisites:
    - kubectl port-forward svc/postgres-grpc 50061:50061 -n isa-cloud-staging
    - kubectl port-forward svc/qdrant-grpc 50062:50062 -n isa-cloud-staging
    - kubectl port-forward svc/model 8082:8082 -n isa-cloud-staging
"""
import asyncio
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)


async def test_skill_manager_sync():
    """Test 1: Sync skills from SkillManager to database."""
    logger.info("=" * 60)
    logger.info("TEST 1: Syncing skills from SkillManager to database")
    logger.info("=" * 60)

    from resources.skill_resources import get_skill_manager

    skill_manager = get_skill_manager()

    # Skills are auto-loaded on init, just get counts
    vibe_count = len(skill_manager._vibe_cache)
    external_count = len(skill_manager._external_cache)

    logger.info(f"Loaded {vibe_count} vibe skills, {external_count} external skills")

    if vibe_count + external_count == 0:
        logger.warning("No skills found to sync")
        return False

    # Sync to database
    result = await skill_manager.sync_to_database()

    logger.info(f"Sync result: {result}")

    return result.get("synced", 0) > 0 or result.get("total", 0) > 0


async def test_full_sync():
    """Test 2: Run full sync for tools, prompts, resources."""
    logger.info("=" * 60)
    logger.info("TEST 2: Running full sync (tools, prompts, resources)")
    logger.info("=" * 60)

    from services.sync_service.sync_service import SyncService

    # Create mock MCP server that returns empty lists (we just want to test the flow)
    class MockMCPServer:
        async def list_tools(self):
            return []
        async def list_prompts(self):
            return []
        async def list_resources(self):
            return []

    sync_service = SyncService(mcp_server=MockMCPServer())
    await sync_service.initialize()

    # Sync skills (which are now resources)
    logger.info("Syncing skills...")
    skills_result = await sync_service.sync_skills()
    logger.info(f"Skills sync result: {skills_result}")

    return True


async def test_unified_search():
    """Test 3: Test unified meta search across all entity types."""
    logger.info("=" * 60)
    logger.info("TEST 3: Testing unified meta search")
    logger.info("=" * 60)

    from services.search_service.unified_meta_search import UnifiedMetaSearch, EntityType

    search = UnifiedMetaSearch()

    # Test search for skills
    logger.info("Searching for 'calendar management'...")
    result = await search.search(
        query="calendar management",
        entity_types=[EntityType.TOOL, EntityType.PROMPT, EntityType.RESOURCE, EntityType.SKILL],
        limit=5,
    )

    logger.info(f"Found {result.metadata.get('total_results', 0)} total results")
    logger.info(f"Results by type: {result.metadata.get('results_by_type', {})}")

    if result.matched_skill_categories:
        logger.info(f"Matched {len(result.matched_skill_categories)} skill categories:")
        for cat in result.matched_skill_categories[:3]:
            logger.info(f"  - {cat.name} (score: {cat.score:.2f})")

    for entity in result.entities[:5]:
        logger.info(f"  [{entity.entity_type.value}] {entity.name} (score: {entity.score:.2f})")

    return True


async def test_hierarchical_search_direct():
    """Test 4: Test hierarchical search service directly."""
    logger.info("=" * 60)
    logger.info("TEST 4: Testing hierarchical search service")
    logger.info("=" * 60)

    from services.search_service.hierarchical_search_service import HierarchicalSearchService

    search = HierarchicalSearchService()

    # Test for tools
    logger.info("Searching tools with hierarchical strategy...")
    result = await search.search(
        query="calendar event scheduling",
        item_type="tool",
        limit=5,
        strategy="hierarchical",
    )

    logger.info(f"Found {len(result.tools)} tools")
    if result.matched_skills:
        logger.info(f"Matched {len(result.matched_skills)} skill categories")

    for tool in result.tools[:3]:
        logger.info(f"  - {tool.name} (score: {tool.score:.2f}, primary_skill: {tool.primary_skill_id})")

    # Test for resources (which includes skills)
    logger.info("\nSearching resources with hierarchical strategy...")
    result = await search.search(
        query="workflow automation",
        item_type="resource",
        limit=5,
        strategy="hierarchical",
    )

    logger.info(f"Found {len(result.tools)} resources")
    for res in result.tools[:3]:
        logger.info(f"  - {res.name} (score: {res.score:.2f})")

    return True


async def main():
    """Run all tests."""
    logger.info("Starting full sync flow tests...")
    logger.info("=" * 60)

    results = {}

    # Test 1: Skill manager sync
    try:
        results["skill_manager_sync"] = await test_skill_manager_sync()
    except Exception as e:
        logger.error(f"Test 1 failed: {e}")
        results["skill_manager_sync"] = False

    # Test 2: Full sync
    try:
        results["full_sync"] = await test_full_sync()
    except Exception as e:
        logger.error(f"Test 2 failed: {e}")
        results["full_sync"] = False

    # Test 3: Unified search
    try:
        results["unified_search"] = await test_unified_search()
    except Exception as e:
        logger.error(f"Test 3 failed: {e}")
        results["unified_search"] = False

    # Test 4: Hierarchical search
    try:
        results["hierarchical_search"] = await test_hierarchical_search_direct()
    except Exception as e:
        logger.error(f"Test 4 failed: {e}")
        results["hierarchical_search"] = False

    # Summary
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    all_passed = True
    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{name}: {status}")
        if not passed:
            all_passed = False

    logger.info("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
