#!/usr/bin/env python3
"""
Apply Refined Skill Categories Migration and Re-classify All Entities

This script:
1. Applies the 003_refined_skill_categories.sql migration
2. Syncs the new categories to Qdrant
3. Re-classifies all tools, prompts, and resources
4. Tests search precision

Usage:
    python scripts/apply_refined_categories.py

Prerequisites:
    - PostgreSQL accessible (via port-forward or direct)
    - Qdrant accessible
    - Model service accessible
"""

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


async def apply_migration():
    """Apply the migration via kubectl exec."""
    logger.info("=" * 70)
    logger.info("Step 1: Applying refined categories migration")
    logger.info("=" * 70)

    migration_file = (
        project_root / "services/skill_service/migrations/003_refined_skill_categories.sql"
    )

    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False

    # Read migration content
    migration_sql = migration_file.read_text()

    # Try kubectl first
    try:
        cmd = [
            "kubectl",
            "exec",
            "-i",
            "postgresql-0",
            "-n",
            "isa-cloud-staging",
            "--",
            "psql",
            "-U",
            "postgres",
            "-d",
            "isa_platform",
        ]

        result = subprocess.run(
            cmd, input=migration_sql, capture_output=True, text=True, timeout=60
        )

        if result.returncode == 0:
            logger.info("✅ Migration applied via kubectl")
            logger.info(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
            return True
        else:
            logger.warning(f"kubectl failed: {result.stderr}")
    except Exception as e:
        logger.warning(f"kubectl not available: {e}")

    # Try direct psql
    try:
        cmd = [
            "psql",
            "-h",
            "localhost",
            "-U",
            "postgres",
            "-d",
            "isa_platform",
            "-f",
            str(migration_file),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            logger.info("✅ Migration applied via direct psql")
            return True
    except Exception as e:
        logger.warning(f"Direct psql not available: {e}")

    logger.error("❌ Could not apply migration - please apply manually")
    logger.info(f"Migration file: {migration_file}")
    return False


async def sync_skill_categories():
    """Sync skill categories to Qdrant."""
    logger.info("=" * 70)
    logger.info("Step 2: Syncing skill categories to Qdrant")
    logger.info("=" * 70)

    from services.sync_service.sync_service import SyncService

    sync_service = SyncService(mcp_server=None)
    await sync_service.initialize()

    result = await sync_service.sync_skills()

    logger.info(f"✅ Skills sync: {result}")
    return result.get("synced", 0) >= 0


async def reclassify_tools():
    """Re-classify all tools with new categories."""
    logger.info("=" * 70)
    logger.info("Step 3: Re-classifying all tools")
    logger.info("=" * 70)

    from services.sync_service.sync_service import SyncService

    sync_service = SyncService(mcp_server=None)
    await sync_service.initialize()

    # Use classify_all_tools with force=True
    result = await sync_service.classify_all_tools(force_reclassify=True)

    logger.info(f"✅ Tools classification: {result}")
    return result.get("classified", 0) >= 0


async def reclassify_prompts():
    """Re-classify all prompts."""
    logger.info("=" * 70)
    logger.info("Step 4: Re-classifying all prompts")
    logger.info("=" * 70)

    from services.skill_service import SkillService
    from services.prompt_service.prompt_repository import PromptRepository

    skill_service = SkillService()
    prompt_repo = PromptRepository()

    # Get unclassified prompts
    prompts = await prompt_repo.get_unclassified_prompts(limit=500)

    if not prompts:
        # All prompts should be unclassified after migration reset
        prompts = await prompt_repo.list_prompts(is_active=True, limit=500)

    logger.info(f"Found {len(prompts)} prompts to classify")

    if prompts:
        entities = [
            {"id": p["id"], "name": p["name"], "description": p.get("description", "")}
            for p in prompts
        ]

        results = await skill_service.classify_entities_batch(entities, entity_type="prompt")
        classified = sum(1 for r in results if r.get("primary_skill_id"))
        logger.info(f"✅ Classified {classified}/{len(prompts)} prompts")

    return True


async def reclassify_resources():
    """Re-classify all resources."""
    logger.info("=" * 70)
    logger.info("Step 5: Re-classifying all resources")
    logger.info("=" * 70)

    from services.skill_service import SkillService
    from services.resource_service.resource_repository import ResourceRepository

    skill_service = SkillService()
    resource_repo = ResourceRepository()

    # Get unclassified resources
    resources = await resource_repo.get_unclassified_resources(limit=500)

    if not resources:
        resources = await resource_repo.list_resources(is_active=True, limit=500)

    logger.info(f"Found {len(resources)} resources to classify")

    if resources:
        entities = [
            {"id": r["id"], "name": r["name"], "description": r.get("description", "")}
            for r in resources
        ]

        results = await skill_service.classify_entities_batch(entities, entity_type="resource")
        classified = sum(1 for r in results if r.get("primary_skill_id"))
        logger.info(f"✅ Classified {classified}/{len(resources)} resources")

    return True


async def test_search_precision():
    """Test search precision with new categories."""
    logger.info("=" * 70)
    logger.info("Step 6: Testing search precision")
    logger.info("=" * 70)

    from isa_mcp.mcp_client import AsyncMCPClient

    async with AsyncMCPClient(base_url="http://localhost:8081") as client:
        test_cases = [
            ("schedule a meeting", "calendar-events"),
            ("send email notification", "email"),
            ("process payment", "payment-billing"),
            ("authenticate user", "authentication"),
            ("upload file", "file-system"),
            ("search documents", "text-search"),
            ("generate code", "code-generation"),
            ("deploy application", "deployment-devops"),
        ]

        passed = 0
        failed = 0

        for query, expected_skill in test_cases:
            result = await client.discover(query, limit=3)
            top_match = result.best_match()

            if top_match and top_match.skill == expected_skill:
                logger.info(f"  ✅ '{query}' → {top_match.name} (skill: {top_match.skill})")
                passed += 1
            else:
                actual_skill = top_match.skill if top_match else "none"
                logger.warning(f"  ❌ '{query}' → expected: {expected_skill}, got: {actual_skill}")
                failed += 1

        logger.info(f"\nPrecision: {passed}/{passed + failed} ({100*passed/(passed+failed):.0f}%)")

        # Show skill distribution
        skills = await client.list_skills()
        logger.info(f"\nNew skill categories: {len(skills)}")
        for skill in sorted(skills, key=lambda x: x.get("tool_count", 0), reverse=True)[:10]:
            logger.info(
                f"  {skill.get('name', skill.get('id')):30} {skill.get('tool_count', 0):>3} tools"
            )


async def main():
    logger.info("=" * 70)
    logger.info("REFINED SKILL CATEGORIES - MIGRATION & RE-CLASSIFICATION")
    logger.info("=" * 70)

    # Step 1: Apply migration
    migration_ok = await apply_migration()
    if not migration_ok:
        logger.warning("Migration may not have been applied - continuing anyway...")

    # Step 2: Sync skills to Qdrant
    try:
        await sync_skill_categories()
    except Exception as e:
        logger.error(f"Skills sync failed: {e}")

    # Step 3: Re-classify tools
    try:
        await reclassify_tools()
    except Exception as e:
        logger.error(f"Tools classification failed: {e}")

    # Step 4: Re-classify prompts
    try:
        await reclassify_prompts()
    except Exception as e:
        logger.error(f"Prompts classification failed: {e}")

    # Step 5: Re-classify resources
    try:
        await reclassify_resources()
    except Exception as e:
        logger.error(f"Resources classification failed: {e}")

    # Step 6: Test search
    try:
        await test_search_precision()
    except Exception as e:
        logger.error(f"Search test failed: {e}")

    logger.info("=" * 70)
    logger.info("DONE")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
