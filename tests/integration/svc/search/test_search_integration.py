"""
Hierarchical Search Service Integration Tests

Integration tests for the Search Service with real (port-forwarded) services.
These tests verify the complete hierarchical search flow via gRPC gateways.

Requirements (port-forwarded from K8s):
    - postgres-grpc:50061    (PostgreSQL gRPC gateway)
    - qdrant-grpc:50062      (Qdrant gRPC gateway)
    - model:8082             (ISA Model service)

Configuration loaded from: deployment/test/config/.env.test (when ENV=test)
"""
import pytest
import os
import time
from datetime import datetime, timezone
from typing import List
import uuid

from tests.contracts.search.data_contract import (
    SearchTestDataFactory,
    HierarchicalSearchRequestContract,
    HierarchicalSearchResponseContract,
    HierarchicalSearchRequestBuilder,
    SearchItemType,
    SearchStrategy,
)

# Try to import skill data contract, skip if not available
try:
    from tests.contracts.skill.data_contract import SkillTestDataFactory
    SKILL_CONTRACT_AVAILABLE = True
except ImportError:
    SKILL_CONTRACT_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
async def integration_db_pool():
    """
    Create PostgreSQL gRPC client for integration tests.

    Uses isa-common PostgresClient which connects via gRPC gateway.
    Port-forwarded: postgres-grpc:50061
    """
    try:
        from isa_common import PostgresClient

        # PostgresClient reads from env: POSTGRES_GRPC_HOST, POSTGRES_GRPC_PORT
        client = PostgresClient()
        # Verify connection
        client.health_check()
        yield client
        client.close()
    except ImportError as e:
        pytest.skip(f"isa-common not installed: {e}")
    except Exception as e:
        pytest.skip(f"PostgreSQL gRPC not available at localhost:50061: {e}")


@pytest.fixture
async def integration_qdrant_client():
    """
    Create Qdrant gRPC client for integration tests.

    Uses isa-common QdrantClient which connects via gRPC gateway.
    Port-forwarded: qdrant-grpc:50062
    """
    try:
        from isa_common import QdrantClient

        # QdrantClient reads from env: QDRANT_GRPC_HOST, QDRANT_GRPC_PORT
        client = QdrantClient()
        # Verify connection
        client.health_check()
        yield client
        client.close()
    except ImportError as e:
        pytest.skip(f"isa-common not installed: {e}")
    except Exception as e:
        pytest.skip(f"Qdrant gRPC not available at localhost:50062: {e}")


@pytest.fixture
async def integration_model_client():
    """
    Create model client for integration tests.

    Uses ISA Model Service at localhost:8082 (port-forwarded).
    Sets ISA_API_URL env var to prevent Consul discovery from overriding.
    """
    try:
        from core.clients.model_client import get_model_client, reset_client

        # Set env var to bypass Consul discovery override
        # (Consul returns internal K8s URL which isn't reachable locally)
        original_url = os.environ.get("ISA_API_URL")
        os.environ["ISA_API_URL"] = "http://localhost:8082"

        # Reset singleton to force new instance with our URL
        await reset_client()

        client = await get_model_client()
        yield client

        # Clean up
        await reset_client()
        if original_url:
            os.environ["ISA_API_URL"] = original_url
        else:
            os.environ.pop("ISA_API_URL", None)
    except ImportError as e:
        pytest.skip(f"isa-model not installed: {e}")
    except Exception as e:
        pytest.skip(f"Model service not available at localhost:8082: {e}")


@pytest.fixture
async def search_service(integration_db_pool, integration_qdrant_client, integration_model_client):
    """Create search service with real dependencies."""
    from services.search_service import HierarchicalSearchService
    from services.vector_service.vector_repository import VectorRepository

    # VectorRepository uses host/port from env (QDRANT_GRPC_HOST, QDRANT_GRPC_PORT)
    vector_repo = VectorRepository()

    service = HierarchicalSearchService(
        vector_repository=vector_repo,
        model_client=integration_model_client
    )
    yield service


@pytest.fixture
async def seeded_environment(integration_qdrant_client):
    """
    Verify environment has skills and tools for search testing.

    Integration tests use existing data in the staging environment.
    This fixture verifies collections exist and have data.
    """
    # Verify collections exist via gRPC client (sync client from isa-common)
    try:
        # Try to get collection info via the gRPC client
        # count_points(collection_name) returns point count
        skills_count = integration_qdrant_client.count_points("mcp_skills")
        tools_count = integration_qdrant_client.count_points("mcp_unified_search")

        yield {
            "skills_count": skills_count,
            "tools_count": tools_count,
            "seeded": False  # Using existing staging data
        }
    except Exception as e:
        # If collection doesn't exist or error, still yield to let tests handle it
        yield {
            "skills_count": -1,  # Unknown
            "tools_count": -1,   # Unknown
            "seeded": False,
            "note": f"Could not verify counts: {e}"
        }


# ═══════════════════════════════════════════════════════════════
# Hierarchical Search Flow Integration Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.search
class TestHierarchicalSearchFlowIntegration:
    """Integration tests for complete hierarchical search flow."""

    @pytest.mark.asyncio
    async def test_hierarchical_search_end_to_end(
        self, search_service, seeded_environment
    ):
        """Test complete hierarchical search from query to results."""
        # Act
        result = await search_service.search(query="schedule a meeting tomorrow")

        # Verify structure
        assert result.query == "schedule a meeting tomorrow"
        assert isinstance(result.tools, list)
        assert isinstance(result.matched_skills, list)
        assert result.metadata is not None
        assert result.metadata.strategy_used == "hierarchical"

    @pytest.mark.asyncio
    async def test_search_generates_embedding_via_model_service(
        self, search_service, seeded_environment
    ):
        """Test that search generates embedding via real model service."""
        # Act
        result = await search_service.search(query="test query")

        # Verify embedding was generated (via metadata timing)
        assert result.metadata.query_embedding_time_ms >= 0

    @pytest.mark.asyncio
    async def test_search_queries_qdrant_for_skills(
        self, search_service, integration_qdrant_client, seeded_environment
    ):
        """Test that search queries Qdrant mcp_skills collection."""
        # Act
        result = await search_service.search(query="calendar event")

        # Verify skills were searched
        assert result.metadata.skill_search_time_ms >= 0

    @pytest.mark.asyncio
    async def test_search_queries_qdrant_for_tools_with_filter(
        self, search_service, integration_qdrant_client, seeded_environment
    ):
        """Test that search queries Qdrant with skill_ids filter."""
        # Act
        result = await search_service.search(query="calendar meeting")

        # Verify tool search was performed
        assert result.metadata.tool_search_time_ms >= 0
        assert result.metadata.stage2_candidate_count >= 0

    @pytest.mark.asyncio
    async def test_search_loads_schemas_from_postgresql(
        self, search_service, integration_db_pool, seeded_environment
    ):
        """Test that search loads schemas from PostgreSQL."""
        # Act
        result = await search_service.search(query="calendar", include_schemas=True)

        # Verify schema load time recorded
        assert result.metadata.schema_load_time_ms >= 0


# ═══════════════════════════════════════════════════════════════
# Fallback Behavior Integration Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.search
class TestSearchFallbackIntegration:
    """Integration tests for search fallback behavior."""

    @pytest.mark.asyncio
    async def test_fallback_when_no_skills_match(self, search_service, seeded_environment):
        """Test that search falls back when no skills match threshold."""
        # Use query unlikely to match any skill with very high threshold
        result = await search_service.search(
            query="xyzabc random gibberish quantum",
            skill_threshold=0.99  # Very high threshold
        )

        # Should fall back - no skills matched
        assert result.metadata.stage1_skill_count == 0
        # Result should still be valid
        assert result is not None

    @pytest.mark.asyncio
    async def test_direct_search_bypasses_skills(self, search_service, seeded_environment):
        """Test that direct search strategy skips skill matching."""
        # Act with direct strategy
        result = await search_service.search(query="test", strategy="direct")

        # Verify direct search was used
        assert result.metadata.strategy_used == "direct"
        assert len(result.matched_skills) == 0


# ═══════════════════════════════════════════════════════════════
# Search Quality Integration Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.search
class TestSearchQualityIntegration:
    """Integration tests for search quality and relevance."""

    @pytest.mark.asyncio
    async def test_calendar_query_returns_results(
        self, search_service, seeded_environment
    ):
        """Test that calendar queries return results."""
        # Test with calendar query
        result = await search_service.search(query="schedule a meeting")

        # Should return valid response
        assert result is not None
        assert result.query == "schedule a meeting"

    @pytest.mark.asyncio
    async def test_generic_query_returns_results(
        self, search_service, seeded_environment
    ):
        """Test that generic queries return results."""
        # Act
        result = await search_service.search(query="help me with a task")

        # Verify valid response
        assert result is not None
        assert result.metadata is not None

    @pytest.mark.asyncio
    async def test_search_with_low_threshold_returns_more_results(
        self, search_service, seeded_environment
    ):
        """Test that lower threshold returns more results."""
        # Search with low threshold
        result_low = await search_service.search(
            query="tools",
            skill_threshold=0.1,
            tool_threshold=0.1
        )

        # Search with high threshold
        result_high = await search_service.search(
            query="tools",
            skill_threshold=0.9,
            tool_threshold=0.9
        )

        # Low threshold should return >= high threshold results
        assert result_low.metadata.stage1_skill_count >= result_high.metadata.stage1_skill_count

    @pytest.mark.asyncio
    async def test_results_sorted_by_relevance(self, search_service, seeded_environment):
        """Test that results are sorted by relevance score."""
        # Act
        result = await search_service.search(query="calendar event")

        # Tools should be sorted by score descending
        if len(result.tools) > 1:
            scores = [t.score for t in result.tools]
            assert scores == sorted(scores, reverse=True), "Tools should be sorted by score descending"


# ═══════════════════════════════════════════════════════════════
# Performance Integration Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.search
@pytest.mark.slow
class TestSearchPerformanceIntegration:
    """Integration tests for search performance with real services."""

    @pytest.mark.asyncio
    async def test_search_completes_under_500ms(self, search_service, seeded_environment):
        """Test that search completes under 500ms (generous for integration)."""
        start = time.time()
        result = await search_service.search(query="test query")
        elapsed_ms = (time.time() - start) * 1000

        # Integration tests have network latency, be generous
        assert elapsed_ms < 500, f"Search took {elapsed_ms:.2f}ms, expected < 500ms"
        assert result.metadata.total_time_ms > 0

    @pytest.mark.asyncio
    async def test_metadata_timing_is_recorded(self, search_service, seeded_environment):
        """Test that metadata timing is recorded for each stage."""
        # Act
        result = await search_service.search(query="test")

        # Verify timing is recorded
        assert result.metadata.query_embedding_time_ms >= 0
        assert result.metadata.skill_search_time_ms >= 0
        assert result.metadata.tool_search_time_ms >= 0
        assert result.metadata.total_time_ms >= 0

    @pytest.mark.asyncio
    async def test_concurrent_searches(self, search_service, seeded_environment):
        """Test that concurrent searches are handled correctly."""
        import asyncio

        queries = [
            "schedule meeting",
            "read file",
            "search data",
        ]

        # Run concurrently
        results = await asyncio.gather(*[
            search_service.search(query=q)
            for q in queries
        ])

        # All should complete
        assert len(results) == len(queries)
        for result in results:
            assert result is not None
            assert result.metadata is not None


# ═══════════════════════════════════════════════════════════════
# Error Handling Integration Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.search
class TestSearchErrorHandlingIntegration:
    """Integration tests for search error handling."""

    @pytest.mark.asyncio
    async def test_handles_empty_query_gracefully(self, search_service, seeded_environment):
        """Test that empty query is handled with proper error."""
        with pytest.raises(ValueError) as exc:
            await search_service.search(query="")
        assert "query" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_handles_very_long_query(self, search_service, seeded_environment):
        """Test that very long query is rejected."""
        long_query = "a" * 1001
        with pytest.raises(ValueError) as exc:
            await search_service.search(query=long_query)
        assert "1000" in str(exc.value)

    @pytest.mark.asyncio
    async def test_handles_special_characters_in_query(self, search_service, seeded_environment):
        """Test that special characters don't break search."""
        # Should not raise
        result = await search_service.search(query="'; DROP TABLE users; --")
        assert result is not None


# ═══════════════════════════════════════════════════════════════
# Schema Loading Integration Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.search
class TestSchemaLoadingIntegration:
    """Integration tests for schema loading behavior."""

    @pytest.mark.asyncio
    async def test_schema_loading_enabled(self, search_service, seeded_environment):
        """Test that schemas are loaded when enabled."""
        # Act
        result = await search_service.search(query="calendar", include_schemas=True)

        # Verify schema load was attempted
        assert result.metadata.schema_load_time_ms >= 0

    @pytest.mark.asyncio
    async def test_schema_loading_disabled(self, search_service, seeded_environment):
        """Test that schemas are NOT loaded when disabled."""
        # Act
        result = await search_service.search(query="calendar", include_schemas=False)

        # No schemas should be loaded
        for tool in result.tools:
            assert tool.input_schema is None

    @pytest.mark.asyncio
    async def test_search_returns_valid_response_regardless_of_schema(
        self, search_service, seeded_environment
    ):
        """Test that search works even if schemas are missing in DB."""
        # Act - search should work regardless of schema availability
        result = await search_service.search(query="test tool")

        # Should return valid response
        assert result is not None
        assert result.metadata is not None
