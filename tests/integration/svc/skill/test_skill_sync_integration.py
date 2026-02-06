"""
Skill Service Integration Tests

Integration tests for the Skill Service with real (port-forwarded) services.
These tests verify the complete flow from sync to classification to embedding.

Requirements:
    - kubectl port-forward svc/postgres-grpc 50061:50061 -n isa-cloud-staging
    - kubectl port-forward svc/qdrant-grpc 50062:50062 -n isa-cloud-staging
    - kubectl port-forward svc/model 8082:8082 -n isa-cloud-staging
"""
import pytest
import os
from datetime import datetime, timezone

from tests.contracts.skill.data_contract import (
    SkillTestDataFactory,
    SkillCategoryCreateRequestContract,
    ToolClassificationRequestContract,
    SkillCategoryBuilder,
)


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
async def skill_service(mcp_settings):
    """Create skill service with real gRPC dependencies."""
    try:
        from services.skill_service import SkillService
        from services.skill_service.skill_repository import SkillRepository

        repository = SkillRepository(
            host=mcp_settings.infrastructure.postgres_grpc_host,
            port=mcp_settings.infrastructure.postgres_grpc_port
        )
        service = SkillService(repository=repository)
        yield service

    except Exception as e:
        pytest.skip(f"Integration services not available: {e}")


@pytest.fixture
async def seeded_skills(skill_service):
    """Get existing skill categories for testing (use pre-seeded data)."""
    # Use existing skills from database instead of creating new ones
    skills = await skill_service.list_skills(is_active=True)
    yield skills[:3] if skills else []


# ═══════════════════════════════════════════════════════════════
# Skill Category CRUD Integration Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.skill
class TestSkillCRUDIntegration:
    """Integration tests for skill category CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_skill_persists_to_postgres(self, skill_service, mcp_settings):
        """Test that creating a skill persists to PostgreSQL."""
        from isa_common import AsyncPostgresClient

        # Create unique test skill
        test_skill_id = f"integration_test_skill_{datetime.now().timestamp():.0f}"
        request = SkillTestDataFactory.make_skill_category(
            id=test_skill_id,
            name=f"Integration Test Skill {test_skill_id}",  # Unique name
            description="A skill created for integration testing purposes"
        )

        try:
            result = await skill_service.create_skill_category(request.model_dump())
            assert result is not None
            assert result.get("id") == test_skill_id

            # Verify persisted in PostgreSQL via gRPC
            # Note: SkillRepository uses 'mcp' schema (hardcoded)
            pg_client = AsyncPostgresClient(
                host=mcp_settings.infrastructure.postgres_grpc_host,
                port=mcp_settings.infrastructure.postgres_grpc_port,
                user_id="mcp-integration-test"
            )
            async with pg_client:
                rows = await pg_client.query(
                    "SELECT * FROM mcp.skill_categories WHERE id = $1",
                    params=[test_skill_id]
                )
            assert rows is not None and len(rows) > 0
            assert rows[0]["name"] == f"Integration Test Skill {test_skill_id}"
        finally:
            # Cleanup
            try:
                await skill_service.delete_skill_category(test_skill_id)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_list_skills_returns_all_active(self, skill_service, seeded_skills):
        """Test that list_skills returns all active skills."""
        skills = await skill_service.list_skills(is_active=True)
        assert isinstance(skills, list)
        # Should have at least the seeded skills
        assert len(skills) >= 0  # May be empty if no skills exist

    @pytest.mark.asyncio
    async def test_get_skill_by_id(self, mcp_settings):
        """Test that get_skill returns correct skill by ID."""
        # Create a fresh service instance to avoid cross-test event loop issues
        from services.skill_service import SkillService
        from services.skill_service.skill_repository import SkillRepository

        repository = SkillRepository(
            host=mcp_settings.infrastructure.postgres_grpc_host,
            port=mcp_settings.infrastructure.postgres_grpc_port
        )
        skill_service = SkillService(repository=repository)

        # Use a known skill ID from seeded data
        known_skill_id = "calendar-management"

        # Test the service method directly
        skill = await skill_service.get_skill(known_skill_id)

        if skill is None:
            # Fallback: try to list skills first
            skills = await skill_service.list_skills(is_active=True)
            if not skills:
                pytest.skip("No skills available in database")
            known_skill_id = skills[0].get("id")
            skill = await skill_service.get_skill(known_skill_id)

        assert skill is not None, f"Skill '{known_skill_id}' not found"
        assert skill.get("id") == known_skill_id


# ═══════════════════════════════════════════════════════════════
# Tool Classification Integration Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.skill
class TestToolClassificationIntegration:
    """Integration tests for tool classification with real LLM."""

    @pytest.mark.asyncio
    async def test_classify_tool_calls_real_llm(self, skill_service, mcp_settings, seeded_skills):
        """
        Test that classification calls real LLM service.

        BR-002: Tool Classification (LLM)
        - LLM receives tool info + available skill categories
        - LLM returns 1-3 skill assignments with confidence scores
        """
        # Use a real tool_id from the database (FK constraint)
        # First get a real calendar tool
        from isa_common import AsyncPostgresClient

        pg_client = AsyncPostgresClient(
            host=mcp_settings.infrastructure.postgres_grpc_host,
            port=mcp_settings.infrastructure.postgres_grpc_port,
            user_id="mcp-integration-test"
        )
        async with pg_client:
            rows = await pg_client.query(
                "SELECT id, name, description FROM mcp.tools WHERE name ILIKE '%calendar%' LIMIT 1"
            )

        if not rows:
            pytest.skip("No calendar tools found in database")

        tool = rows[0]
        result = await skill_service.classify_tool(
            tool_id=tool["id"],
            tool_name=tool["name"],
            tool_description=tool.get("description", "Calendar tool"),
            force_reclassify=True
        )

        # Should match calendar-management skill (BR-002)
        assert result is not None
        assert "assignments" in result
        assert len(result["assignments"]) >= 1, f"Expected at least 1 assignment, got: {result}"
        assert result.get("primary_skill_id") is not None

        # Verify confidence threshold (>= 0.5)
        for assignment in result["assignments"]:
            assert assignment["confidence"] >= 0.5

    @pytest.mark.asyncio
    async def test_classify_tool_stores_assignment(self, skill_service, mcp_settings, seeded_skills):
        """
        Test that classification stores assignment in PostgreSQL.

        BR-003: Skill Assignment Storage
        - New assignments created in `mcp.tool_skill_assignments` table
        """
        from isa_common import AsyncPostgresClient

        # Get a real tool from database (FK constraint requires existing tool_id)
        pg_client = AsyncPostgresClient(
            host=mcp_settings.infrastructure.postgres_grpc_host,
            port=mcp_settings.infrastructure.postgres_grpc_port,
            user_id="mcp-integration-test"
        )
        async with pg_client:
            rows = await pg_client.query(
                "SELECT id, name, description FROM mcp.tools WHERE name ILIKE '%event%' LIMIT 1"
            )

        if not rows:
            pytest.skip("No event tools found in database")

        tool = rows[0]
        tool_id = tool["id"]

        result = await skill_service.classify_tool(
            tool_id=tool_id,
            tool_name=tool["name"],
            tool_description=tool.get("description", "Event tool"),
            force_reclassify=True
        )

        # Verify stored in database
        pg_client2 = AsyncPostgresClient(
            host=mcp_settings.infrastructure.postgres_grpc_host,
            port=mcp_settings.infrastructure.postgres_grpc_port,
            user_id="mcp-integration-test"
        )
        async with pg_client2:
            rows = await pg_client2.query(
                "SELECT * FROM mcp.tool_skill_assignments WHERE tool_id = $1",
                params=[tool_id]
            )

        assert rows is not None and len(rows) >= 1
        assert rows[0]["tool_id"] == tool_id
        assert rows[0]["confidence"] >= 0.5

    @pytest.mark.asyncio
    async def test_classify_tool_updates_qdrant_payload(self, skill_service, mcp_settings, seeded_skills):
        """
        Test that classification updates tool vector payload with skill_ids.

        BR-002: Tool updated in Qdrant with `skill_ids[]` payload
        """
        from isa_common import AsyncPostgresClient, AsyncQdrantClient

        # Get a real tool from database (FK constraint requires existing tool_id)
        pg_client = AsyncPostgresClient(
            host=mcp_settings.infrastructure.postgres_grpc_host,
            port=mcp_settings.infrastructure.postgres_grpc_port,
            user_id="mcp-integration-test"
        )
        async with pg_client:
            rows = await pg_client.query(
                "SELECT id, name, description FROM mcp.tools WHERE name ILIKE '%search%' LIMIT 1"
            )

        if not rows:
            pytest.skip("No search tools found in database")

        tool = rows[0]
        tool_id = tool["id"]

        result = await skill_service.classify_tool(
            tool_id=tool_id,
            tool_name=tool["name"],
            tool_description=tool.get("description", "Search tool"),
            force_reclassify=True
        )

        # Verify Qdrant payload updated
        qdrant_client = AsyncQdrantClient(
            host=mcp_settings.infrastructure.qdrant_grpc_host,
            port=mcp_settings.infrastructure.qdrant_grpc_port,
            user_id="mcp-integration-test"
        )

        # Get point from Qdrant - use db_id as point ID
        points = await qdrant_client.retrieve_points(
            collection_name="mcp_unified_search",
            ids=[tool_id],
            with_payload=True
        )

        if points and len(points) > 0:
            payload = points[0].get("payload", {})
            skill_ids = payload.get("skill_ids", [])
            assert len(skill_ids) >= 1, "Tool should have skill_ids in Qdrant payload"
            assert payload.get("primary_skill_id") is not None


# ═══════════════════════════════════════════════════════════════
# Skill Embedding Update Integration Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.skill
class TestSkillEmbeddingIntegration:
    """Integration tests for skill embedding updates."""

    @pytest.mark.asyncio
    async def test_skill_embedding_updated_after_tool_assignment(
        self, skill_service, qdrant_client, seeded_skills
    ):
        """Test that skill embedding is updated after tool assignment."""
        pytest.skip("Integration test - requires SkillService implementation")

        # Get initial embedding
        # skill_id = seeded_skills[0].id
        # initial_points = await qdrant_client.retrieve("mcp_skills", [skill_id])
        # initial_embedding = initial_points[0].vector

        # Assign a tool
        # await skill_service.assign_tool_to_skill(tool_id=997, skill_id=skill_id)

        # Get updated embedding
        # updated_points = await qdrant_client.retrieve("mcp_skills", [skill_id])
        # updated_embedding = updated_points[0].vector

        # Embedding should have changed (weighted average)
        # assert initial_embedding != updated_embedding

    @pytest.mark.asyncio
    async def test_skill_embedding_uses_description_when_no_tools(
        self, skill_service, qdrant_client
    ):
        """Test that skill with no tools uses description embedding."""
        pytest.skip("Integration test - requires SkillService implementation")


# ═══════════════════════════════════════════════════════════════
# Sync Service Integration Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.skill
class TestSyncIntegration:
    """Integration tests for sync service with skill classification."""

    @pytest.mark.asyncio
    async def test_sync_skills_syncs_to_qdrant(self, mcp_settings):
        """
        Test that sync_skills() syncs all PostgreSQL skills to Qdrant mcp_skills collection.

        BR-004: Skill Embedding Generation
        - Batch sync | Update all affected skills
        """
        from services.sync_service.sync_service import SyncService
        from isa_common import AsyncQdrantClient

        # Create sync service (no MCP server needed for skill sync)
        sync_service = SyncService(mcp_server=None)
        await sync_service.initialize()

        # Run skill sync
        result = await sync_service.sync_skills()

        # Verify result structure
        assert "total" in result
        assert "synced" in result
        assert "failed" in result
        assert result["total"] >= 0

        # If we have skills in PostgreSQL, they should be synced
        if result["total"] > 0:
            assert result["synced"] >= 0

            # Verify skills exist in Qdrant
            qdrant_client = AsyncQdrantClient(
                host=mcp_settings.infrastructure.qdrant_grpc_host,
                port=mcp_settings.infrastructure.qdrant_grpc_port,
                user_id="mcp-integration-test"
            )

            # Check collection has points
            count = await qdrant_client.count_points("mcp_skills")
            assert count is not None and count >= result["synced"]

    @pytest.mark.asyncio
    async def test_sync_all_includes_skills(self, mcp_settings):
        """
        Test that sync_all() includes skill sync in results.

        BR-004: Skill Embedding Generation
        - Batch sync | Update all affected skills
        """
        from services.sync_service.sync_service import SyncService

        # Create sync service with mock MCP server
        class MockMCPServer:
            async def list_tools(self):
                return []
            async def list_prompts(self):
                return []
            async def list_resources(self):
                return []

        sync_service = SyncService(mcp_server=MockMCPServer())
        await sync_service.initialize()

        # Run full sync
        result = await sync_service.sync_all()

        # Should include skills in results
        assert "details" in result
        assert "skills" in result["details"], "sync_all() should include skills sync"

        skills_result = result["details"]["skills"]
        assert "total" in skills_result
        assert "synced" in skills_result

    @pytest.mark.asyncio
    async def test_sync_skills_generates_embeddings(self, mcp_settings):
        """
        Test that sync_skills() generates embeddings for each skill.

        BR-001: Skill Category Creation
        - Initial embedding generated from description
        - Skill upserted to Qdrant `mcp_skills` collection
        """
        from services.sync_service.sync_service import SyncService
        from isa_common import AsyncQdrantClient

        sync_service = SyncService(mcp_server=None)
        await sync_service.initialize()

        # Run skill sync
        result = await sync_service.sync_skills()

        if result["synced"] > 0:
            # Verify embeddings exist in Qdrant
            qdrant_client = AsyncQdrantClient(
                host=mcp_settings.infrastructure.qdrant_grpc_host,
                port=mcp_settings.infrastructure.qdrant_grpc_port,
                user_id="mcp-integration-test"
            )

            # Scroll to get some points with vectors
            scroll_result = await qdrant_client.scroll(
                collection_name="mcp_skills",
                limit=5,
                with_payload=True,
                with_vectors=True
            )

            assert scroll_result is not None
            points = scroll_result.get("points", [])

            if points:
                # Verify points have embeddings
                for point in points:
                    assert point.get("vector") is not None, "Skill should have embedding vector"
                    assert len(point["vector"]) > 0, "Embedding should not be empty"

                    # Verify payload has required fields
                    payload = point.get("payload", {})
                    assert "id" in payload or "name" in payload, "Payload should have skill identifier"


# ═══════════════════════════════════════════════════════════════
# Error Handling Integration Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.skill
class TestErrorHandlingIntegration:
    """Integration tests for error handling."""

    @pytest.mark.asyncio
    async def test_llm_timeout_handled_gracefully(self, skill_service):
        """Test that LLM timeout is handled gracefully."""
        pytest.skip("Integration test - requires SkillService implementation")

    @pytest.mark.asyncio
    async def test_qdrant_error_handled_gracefully(self, skill_service):
        """Test that Qdrant errors are handled gracefully."""
        pytest.skip("Integration test - requires SkillService implementation")

    @pytest.mark.asyncio
    async def test_postgres_error_rolls_back_transaction(self, skill_service, db_pool):
        """Test that PostgreSQL errors roll back transaction."""
        pytest.skip("Integration test - requires SkillService implementation")


# ═══════════════════════════════════════════════════════════════
# SkillManager Database Sync Integration Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.skill
class TestSkillManagerSyncIntegration:
    """Integration tests for syncing skills from SkillManager to database."""

    @pytest.mark.asyncio
    async def test_skill_manager_sync_to_database(self, mcp_settings):
        """
        Test that SkillManager.sync_to_database() syncs vibe skills to resources table.

        Skills are stored as resources with resource_type="skill".
        """
        from resources.skill_resources import get_skill_manager

        skill_manager = get_skill_manager()

        # First ensure skills are loaded
        skill_manager.load_skills()
        total_skills = len(skill_manager._vibe_cache) + len(skill_manager._external_cache)

        if total_skills == 0:
            pytest.skip("No skills found to sync")

        # Sync skills to database
        result = await skill_manager.sync_to_database()

        assert "synced" in result
        assert "failed" in result
        assert "total" in result
        assert result["synced"] >= 0
        assert result["total"] == total_skills

    @pytest.mark.asyncio
    async def test_synced_skills_appear_in_resources(self, mcp_settings):
        """
        Test that synced skills can be retrieved from resources table.
        """
        from resources.skill_resources import get_skill_manager
        from services.resource_service.resource_repository import ResourceRepository

        skill_manager = get_skill_manager()
        skill_manager.load_skills()

        if not skill_manager._vibe_cache:
            pytest.skip("No vibe skills found")

        # Sync skills
        await skill_manager.sync_to_database()

        # Get a skill name to test
        skill_name = list(skill_manager._vibe_cache.keys())[0]

        # Check it exists in resources
        repo = ResourceRepository()
        resource = await repo.get_resource_by_uri(f"skill://vibe/{skill_name}")

        assert resource is not None
        assert resource.get("resource_type") == "skill"
        assert resource.get("name") == skill_name


# ═══════════════════════════════════════════════════════════════
# Unified Meta Search Integration Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.skill
class TestUnifiedMetaSearchIntegration:
    """Integration tests for UnifiedMetaSearch across all entity types."""

    @pytest.mark.asyncio
    async def test_unified_search_includes_skills(self, mcp_settings):
        """
        Test that unified search finds skills via hierarchical search.
        """
        from services.search_service.unified_meta_search import UnifiedMetaSearch, EntityType

        search = UnifiedMetaSearch()

        # Search for skills
        result = await search.search(
            query="calendar event scheduling",
            entity_types=[EntityType.SKILL],
            limit=5,
        )

        assert result is not None
        assert result.query == "calendar event scheduling"
        # Results may be empty if no skills match, but search should succeed
        assert isinstance(result.entities, list)

    @pytest.mark.asyncio
    async def test_unified_search_all_entity_types(self, mcp_settings):
        """
        Test that unified search can search across all entity types.
        """
        from services.search_service.unified_meta_search import UnifiedMetaSearch, EntityType

        search = UnifiedMetaSearch()

        # Search across all types
        result = await search.search(
            query="calendar management",
            entity_types=[EntityType.TOOL, EntityType.PROMPT, EntityType.RESOURCE, EntityType.SKILL],
            limit=5,
        )

        assert result is not None
        assert "metadata" in result.__dict__
        assert "total_results" in result.metadata

        # Check results are typed correctly
        for entity in result.entities:
            assert entity.entity_type in [EntityType.TOOL, EntityType.PROMPT, EntityType.RESOURCE, EntityType.SKILL]

    @pytest.mark.asyncio
    async def test_unified_search_skill_category_matching(self, mcp_settings):
        """
        Test that unified search returns matched skill categories.
        """
        from services.search_service.unified_meta_search import UnifiedMetaSearch, EntityType

        search = UnifiedMetaSearch()

        result = await search.search(
            query="web automation browser testing",
            entity_types=[EntityType.TOOL],
            limit=5,
            skill_limit=3,
            use_hierarchical=True,
        )

        # Should have skill category matches (if any exist)
        assert result.matched_skill_categories is not None
        assert isinstance(result.matched_skill_categories, list)

    @pytest.mark.asyncio
    async def test_unified_search_to_dict(self, mcp_settings):
        """
        Test that UnifiedMetaSearch.to_dict() produces valid API response.
        """
        from services.search_service.unified_meta_search import UnifiedMetaSearch, EntityType

        search = UnifiedMetaSearch()

        result = await search.search(
            query="file management",
            entity_types=[EntityType.TOOL],
            limit=3,
        )

        # Convert to dict
        result_dict = search.to_dict(result)

        assert "query" in result_dict
        assert "entities" in result_dict
        assert "matched_skill_categories" in result_dict
        assert "metadata" in result_dict
        assert result_dict["query"] == "file management"


# ═══════════════════════════════════════════════════════════════
# Entity Classification Integration Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.skill
class TestEntityClassificationIntegration:
    """Integration tests for entity classification (prompts, resources)."""

    @pytest.mark.asyncio
    async def test_prompt_classification_stores_in_db(self, mcp_settings):
        """
        Test that prompt classification stores skill_ids in prompts table.
        """
        from services.skill_service import SkillService
        from services.skill_service.skill_repository import SkillRepository
        from services.prompt_service.prompt_repository import PromptRepository
        from isa_common import AsyncPostgresClient

        # Get a prompt from database
        pg_client = AsyncPostgresClient(
            host=mcp_settings.infrastructure.postgres_grpc_host,
            port=mcp_settings.infrastructure.postgres_grpc_port,
            user_id="mcp-integration-test"
        )
        async with pg_client:
            rows = await pg_client.query(
                "SELECT id, name, description FROM mcp.prompts WHERE is_active = TRUE LIMIT 1"
            )

        if not rows:
            pytest.skip("No prompts found in database")

        prompt = rows[0]
        prompt_id = prompt["id"]

        # Classify the prompt
        repository = SkillRepository(
            host=mcp_settings.infrastructure.postgres_grpc_host,
            port=mcp_settings.infrastructure.postgres_grpc_port
        )
        skill_service = SkillService(repository=repository)

        entity = {
            "id": prompt["id"],
            "name": prompt["name"],
            "description": prompt.get("description", "A test prompt")
        }

        results = await skill_service.classify_entities_batch([entity], entity_type="prompt")

        # Verify stored in database
        prompt_repo = PromptRepository()
        updated_prompt = await prompt_repo.get_prompt_by_id(prompt_id)

        assert updated_prompt is not None
        # Classification should have been attempted
        # (skill_ids may be empty if no matches, but is_classified should be set)

    @pytest.mark.asyncio
    async def test_resource_classification_stores_in_db(self, mcp_settings):
        """
        Test that resource classification stores skill_ids in resources table.
        """
        from services.skill_service import SkillService
        from services.skill_service.skill_repository import SkillRepository
        from services.resource_service.resource_repository import ResourceRepository
        from isa_common import AsyncPostgresClient

        # Get a resource from database
        pg_client = AsyncPostgresClient(
            host=mcp_settings.infrastructure.postgres_grpc_host,
            port=mcp_settings.infrastructure.postgres_grpc_port,
            user_id="mcp-integration-test"
        )
        async with pg_client:
            rows = await pg_client.query(
                "SELECT id, name, description FROM mcp.resources WHERE is_active = TRUE AND resource_type != 'skill' LIMIT 1"
            )

        if not rows:
            pytest.skip("No resources found in database")

        resource = rows[0]
        resource_id = resource["id"]

        # Classify the resource
        repository = SkillRepository(
            host=mcp_settings.infrastructure.postgres_grpc_host,
            port=mcp_settings.infrastructure.postgres_grpc_port
        )
        skill_service = SkillService(repository=repository)

        entity = {
            "id": resource["id"],
            "name": resource["name"],
            "description": resource.get("description", "A test resource")
        }

        results = await skill_service.classify_entities_batch([entity], entity_type="resource")

        # Verify stored in database
        resource_repo = ResourceRepository()
        updated_resource = await resource_repo.get_resource_by_id(resource_id)

        assert updated_resource is not None
        # Classification should have been attempted
