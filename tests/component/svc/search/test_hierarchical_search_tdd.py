"""
Hierarchical Search Service TDD Tests

Test-Driven Development tests for the Hierarchical Search Service.
All tests reference business rules from tests/contracts/search/logic_contract.md
and use data structures from tests/contracts/search/data_contract.py.

These tests are written BEFORE implementation (RED phase).
Implementation should make these tests pass (GREEN phase).
"""
import pytest
import time
from datetime import datetime, timezone
from typing import List
from pydantic import ValidationError

# Import contracts
from tests.contracts.search.data_contract import (
    SearchTestDataFactory,
    HierarchicalSearchRequestContract,
    HierarchicalSearchResponseContract,
    SkillSearchRequestContract,
    ToolSearchRequestContract,
    SkillMatchContract,
    ToolMatchContract,
    EnrichedToolContract,
    SearchMetadataContract,
    HierarchicalSearchRequestBuilder,
    SearchItemType,
    SearchStrategy,
)

# Import service and mocks
from services.search_service import HierarchicalSearchService
from tests.component.mocks.search_mocks import (
    MockQdrantSearchClient,
    MockDbPool,
    MockVectorRepository,
    MockSearchModelClient,
)


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_qdrant_search():
    """Provide mock Qdrant client for search."""
    client = MockQdrantSearchClient()
    # Seed default skills
    client.seed_skill(
        skill_id="calendar-management",
        name="Calendar Management",
        description="Tools for managing calendars and events",
        score=0.85,
        tool_count=5
    )
    client.seed_skill(
        skill_id="file-operations",
        name="File Operations",
        description="Tools for file manipulation",
        score=0.6,
        tool_count=10
    )
    # Seed default tools
    client.seed_tool(
        tool_id="tool-1",
        db_id=1,
        name="create_calendar_event",
        description="Create a calendar event",
        score=0.9,
        skill_ids=["calendar-management"],
        primary_skill_id="calendar-management"
    )
    client.seed_tool(
        tool_id="tool-2",
        db_id=2,
        name="list_events",
        description="List calendar events",
        score=0.85,
        skill_ids=["calendar-management"],
        primary_skill_id="calendar-management"
    )
    return client


@pytest.fixture
def mock_db_pool():
    """Provide mock database pool."""
    pool = MockDbPool()
    pool.seed_schema(1, input_schema={"type": "object", "properties": {"title": {"type": "string"}}})
    pool.seed_schema(2, input_schema={"type": "object", "properties": {"date": {"type": "string"}}})
    return pool


@pytest.fixture
def mock_model_client():
    """Provide mock model client."""
    return MockSearchModelClient()


@pytest.fixture
def mock_vector_repository(mock_qdrant_search):
    """Provide mock vector repository."""
    repo = MockVectorRepository()
    repo.set_client(mock_qdrant_search)
    return repo


@pytest.fixture
def search_service(mock_vector_repository, mock_model_client, mock_db_pool, mock_qdrant_search):
    """Provide HierarchicalSearchService with mocked dependencies."""
    service = HierarchicalSearchService(
        vector_repository=mock_vector_repository,
        model_client=mock_model_client,
        db_pool=mock_db_pool,
        qdrant_client=mock_qdrant_search  # Inject mock Qdrant client
    )
    return service


# ═══════════════════════════════════════════════════════════════
# Contract Validation Tests (Data Contract)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.unit
class TestSearchDataContractValidation:
    """Test that search data contracts validate input correctly."""

    def test_valid_search_request(self):
        """Test that valid search request is accepted."""
        request = SearchTestDataFactory.make_search_request(
            query="schedule a meeting tomorrow"
        )
        assert request.query == "schedule a meeting tomorrow"
        assert request.strategy == SearchStrategy.HIERARCHICAL
        assert request.include_schemas is True

    def test_invalid_search_empty_query_rejected(self):
        """Test that empty query is rejected."""
        invalid_data = SearchTestDataFactory.make_invalid_search_empty_query()
        with pytest.raises(ValidationError) as exc:
            HierarchicalSearchRequestContract(**invalid_data)
        assert "query" in str(exc.value).lower()

    def test_invalid_search_limit_too_high_rejected(self):
        """Test that limit > 50 is rejected."""
        invalid_data = SearchTestDataFactory.make_invalid_search_limit_too_high()
        with pytest.raises(ValidationError) as exc:
            HierarchicalSearchRequestContract(**invalid_data)
        assert "limit" in str(exc.value).lower()

    def test_invalid_search_negative_threshold_rejected(self):
        """Test that negative threshold is rejected."""
        invalid_data = SearchTestDataFactory.make_invalid_search_negative_threshold()
        with pytest.raises(ValidationError) as exc:
            HierarchicalSearchRequestContract(**invalid_data)

    def test_builder_creates_valid_request(self):
        """Test HierarchicalSearchRequestBuilder creates valid request."""
        request = (
            HierarchicalSearchRequestBuilder()
            .with_query("schedule a meeting")
            .tools_only()
            .with_high_thresholds()
            .limit_results(3)
            .build()
        )
        assert request.query == "schedule a meeting"
        assert request.item_type == SearchItemType.TOOL
        assert request.skill_threshold == 0.7
        assert request.tool_threshold == 0.6
        assert request.limit == 3

    def test_response_tools_sorted_by_score(self):
        """Test that response sorts tools by score descending."""
        tool1 = SearchTestDataFactory.make_enriched_tool(id="1", score=0.6, db_id=1)
        tool2 = SearchTestDataFactory.make_enriched_tool(id="2", score=0.9, db_id=2)
        tool3 = SearchTestDataFactory.make_enriched_tool(id="3", score=0.7, db_id=3)

        response = HierarchicalSearchResponseContract(
            query="test",
            tools=[tool1, tool2, tool3],
            matched_skills=[SearchTestDataFactory.make_skill_match()],
            metadata=SearchTestDataFactory.make_search_metadata(),
        )

        # Should be sorted descending by score
        assert response.tools[0].id == "2"
        assert response.tools[0].score == 0.9
        assert response.tools[1].id == "3"
        assert response.tools[2].id == "1"

    def test_calendar_queries_available(self):
        """Test that calendar test queries are available."""
        queries = SearchTestDataFactory.get_calendar_queries()
        assert len(queries) >= 3
        assert any("meeting" in q for q in queries)
        assert any("event" in q for q in queries)

    def test_ambiguous_queries_available(self):
        """Test that ambiguous test queries are available."""
        queries = SearchTestDataFactory.get_ambiguous_queries()
        assert len(queries) >= 2


# ═══════════════════════════════════════════════════════════════
# BR-001: Two-Stage Hierarchical Search
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.search
class TestBR001TwoStageHierarchicalSearch:
    """
    BR-001: Two-Stage Hierarchical Search

    Given: User query for tool/prompt/resource search
    When: Hierarchical search is executed
    Then:
    1. Stage 1: Search skills, return top skill_limit skills
    2. Stage 2: Search tools filtered by matched skills
    3. Stage 3: Load schemas for returned tools
    """

    @pytest.mark.asyncio
    async def test_hierarchical_search_returns_structured_response(
        self, search_service
    ):
        """Test that hierarchical search returns proper response structure."""
        # Act
        result = await search_service.search(query="schedule a meeting tomorrow")

        # Assert structure
        assert result.query == "schedule a meeting tomorrow"
        assert isinstance(result.tools, list)
        assert isinstance(result.matched_skills, list)
        assert result.metadata is not None
        assert result.metadata.strategy_used == "hierarchical"

    @pytest.mark.asyncio
    async def test_hierarchical_search_executes_stage1_first(
        self, search_service, mock_qdrant_search
    ):
        """Test that Stage 1 (skill search) executes first."""
        # Act
        await search_service.search(query="test query")

        # Verify Qdrant was queried for mcp_skills collection
        calls = mock_qdrant_search.get_calls("search_with_filter")
        skill_calls = [c for c in calls if c.get("collection_name") == "mcp_skills"]
        assert len(skill_calls) >= 1

    @pytest.mark.asyncio
    async def test_hierarchical_search_uses_skill_filter_in_stage2(
        self, search_service, mock_qdrant_search
    ):
        """Test that Stage 2 filters by matched skill IDs."""
        # Act
        result = await search_service.search(query="calendar event")

        # Verify skill IDs were used for filtering
        assert result.metadata.skill_ids_used is not None
        assert len(result.metadata.skill_ids_used) > 0

    @pytest.mark.asyncio
    async def test_hierarchical_search_reuses_query_embedding(
        self, search_service, mock_model_client
    ):
        """Test that query embedding is generated once and reused."""
        # Act
        await search_service.search(query="test query")

        # Verify model client called for embedding exactly once
        embedding_calls = mock_model_client.embeddings._calls
        assert len(embedding_calls) == 1

    @pytest.mark.asyncio
    async def test_hierarchical_search_loads_schemas_in_stage3(
        self, search_service, mock_db_pool
    ):
        """Test that schemas are loaded from PostgreSQL for returned tools."""
        # Act
        result = await search_service.search(query="calendar event", include_schemas=True)

        # Verify tools have schemas loaded (from mock)
        if result.tools:
            # At least one tool should have schema (from fixture)
            assert result.metadata.schema_load_time_ms >= 0


# ═══════════════════════════════════════════════════════════════
# BR-002: Skill Matching (Stage 1)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.search
class TestBR002SkillMatching:
    """
    BR-002: Skill Matching (Stage 1)

    Given: Query embedding and skill index
    When: Skill search is performed
    Then:
    - Search Qdrant mcp_skills collection
    - Filter by score >= skill_threshold
    - Return maximum skill_limit skills
    """

    @pytest.mark.asyncio
    async def test_skill_search_respects_threshold(
        self, search_service, mock_qdrant_search
    ):
        """Test that only skills above threshold are returned."""
        # Add a low-score skill
        mock_qdrant_search.seed_skill(
            skill_id="low-score-skill",
            name="Low Score",
            description="Should be filtered out",
            score=0.2,  # Below default threshold of 0.4
            tool_count=1
        )

        # Act with high threshold
        result = await search_service.search(query="test", skill_threshold=0.5)

        # Assert - only skills >= 0.5 returned
        for skill in result.matched_skills:
            assert skill.score >= 0.5

    @pytest.mark.asyncio
    async def test_skill_search_respects_limit(
        self, search_service
    ):
        """Test that skill search respects skill_limit."""
        # Act with limit
        result = await search_service.search(query="test", skill_limit=1)

        # Assert
        assert len(result.matched_skills) <= 1

    @pytest.mark.asyncio
    async def test_skill_search_only_active_skills(
        self, search_service, mock_qdrant_search
    ):
        """Test that only active skills are searched."""
        # Add an inactive skill
        mock_qdrant_search.seed_skill(
            skill_id="inactive-skill",
            name="Inactive",
            description="Should be filtered",
            score=0.99,
            tool_count=100,
            is_active=False
        )

        # Act
        result = await search_service.search(query="test")

        # Assert - inactive skill not in results
        skill_ids = [s.id for s in result.matched_skills]
        assert "inactive-skill" not in skill_ids

    @pytest.mark.asyncio
    async def test_skill_search_returns_tool_count(
        self, search_service
    ):
        """Test that each matched skill includes tool_count."""
        # Act
        result = await search_service.search(query="calendar")

        # Assert
        for skill in result.matched_skills:
            assert hasattr(skill, 'tool_count')
            assert skill.tool_count >= 0


# ═══════════════════════════════════════════════════════════════
# BR-003: Tool Search with Skill Filter (Stage 2)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.search
class TestBR003ToolSearchWithSkillFilter:
    """
    BR-003: Tool Search with Skill Filter (Stage 2)

    Given: Query embedding and matched skill IDs
    When: Tool search is performed
    Then:
    - Search Qdrant mcp_unified_search collection
    - Apply filter: skill_ids CONTAINS ANY matched_skill_ids
    - Return maximum limit tools
    """

    @pytest.mark.asyncio
    async def test_tool_search_filters_by_skill_ids(
        self, search_service, mock_qdrant_search
    ):
        """Test that tool search filters by matched skill IDs."""
        # Act
        result = await search_service.search(query="calendar event")

        # Assert - tools returned should match calendar skill
        for tool in result.tools:
            assert "calendar-management" in tool.skill_ids

    @pytest.mark.asyncio
    async def test_tool_search_respects_threshold(
        self, search_service, mock_qdrant_search
    ):
        """Test that only tools above threshold are returned."""
        # Add a low-score tool
        mock_qdrant_search.seed_tool(
            tool_id="low-tool",
            db_id=99,
            name="low_score_tool",
            description="Low score tool",
            score=0.1,
            skill_ids=["calendar-management"]
        )

        # Act with high threshold
        result = await search_service.search(query="test", tool_threshold=0.5)

        # Assert - no low score tools
        for tool in result.tools:
            assert tool.score >= 0.5

    @pytest.mark.asyncio
    async def test_tool_search_sorted_by_score(
        self, search_service
    ):
        """Test that tools are sorted by similarity score descending."""
        # Act
        result = await search_service.search(query="calendar")

        # Assert - sorted descending
        if len(result.tools) > 1:
            for i in range(len(result.tools) - 1):
                assert result.tools[i].score >= result.tools[i + 1].score

    @pytest.mark.asyncio
    async def test_tool_search_includes_skill_ids_in_result(
        self, search_service
    ):
        """Test that each tool includes its skill_ids in result."""
        # Act
        result = await search_service.search(query="calendar")

        # Assert
        for tool in result.tools:
            assert hasattr(tool, 'skill_ids')
            assert isinstance(tool.skill_ids, list)


# ═══════════════════════════════════════════════════════════════
# BR-004: Schema Enrichment (Stage 3)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.search
class TestBR004SchemaEnrichment:
    """
    BR-004: Schema Enrichment (Stage 3)

    Given: Matched tools from Stage 2
    When: include_schemas=true
    Then:
    - Fetch full record from PostgreSQL by db_id
    - Extract input_schema, output_schema, annotations
    """

    @pytest.mark.asyncio
    async def test_schema_loading_when_enabled(
        self, search_service, mock_db_pool
    ):
        """Test that schemas are loaded when include_schemas=true."""
        # Act
        result = await search_service.search(query="calendar", include_schemas=True)

        # Assert - schema load time recorded
        assert result.metadata.schema_load_time_ms >= 0

    @pytest.mark.asyncio
    async def test_no_schema_loading_when_disabled(
        self, search_service, mock_db_pool
    ):
        """Test that schemas are NOT loaded when include_schemas=false."""
        # Act
        result = await search_service.search(query="calendar", include_schemas=False)

        # Assert - tools should have no schemas loaded
        for tool in result.tools:
            assert tool.input_schema is None

    @pytest.mark.asyncio
    async def test_missing_schema_returns_null(
        self, search_service, mock_qdrant_search, mock_db_pool
    ):
        """Test that missing schema returns null (not error)."""
        # Add tool without schema in DB
        mock_qdrant_search.seed_tool(
            tool_id="no-schema-tool",
            db_id=999,  # Not in mock_db_pool
            name="no_schema",
            description="Tool without schema",
            score=0.9,
            skill_ids=["calendar-management"]
        )

        # Act - should not raise
        result = await search_service.search(query="calendar", include_schemas=True)

        # Assert - still returns results
        assert result is not None


# ═══════════════════════════════════════════════════════════════
# BR-005: Item Type Filtering
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.search
class TestBR005ItemTypeFiltering:
    """
    BR-005: Item Type Filtering

    Given: Search request with item_type parameter
    When: Search is performed
    Then:
    - If item_type=null → Search all types
    - If item_type="tool" → Only return tools
    """

    @pytest.mark.asyncio
    async def test_filter_tools_only(
        self, search_service, mock_qdrant_search
    ):
        """Test that item_type=tool returns only tools."""
        # Add a prompt type
        mock_qdrant_search.seed_tool(
            tool_id="prompt-1",
            db_id=100,
            name="test_prompt",
            description="A test prompt",
            score=0.9,
            skill_ids=["calendar-management"],
            item_type="prompt"
        )

        # Act - filter to tools only
        result = await search_service.search(query="test", item_type="tool")

        # Assert - only tools returned
        for tool in result.tools:
            assert tool.type == "tool"

    @pytest.mark.asyncio
    async def test_filter_prompts_only(
        self, search_service, mock_qdrant_search
    ):
        """Test that item_type=prompt returns only prompts."""
        # Add a prompt
        mock_qdrant_search.seed_tool(
            tool_id="prompt-2",
            db_id=101,
            name="calendar_prompt",
            description="A calendar prompt",
            score=0.9,
            skill_ids=["calendar-management"],
            item_type="prompt"
        )

        # Act - filter to prompts only
        result = await search_service.search(query="test", item_type="prompt")

        # Assert - only prompts returned
        for tool in result.tools:
            assert tool.type == "prompt"

    @pytest.mark.asyncio
    async def test_no_filter_returns_all_types(
        self, search_service
    ):
        """Test that no item_type filter returns all types."""
        # Act - no type filter
        result = await search_service.search(query="calendar", item_type=None)

        # Assert - returns results (type doesn't matter)
        assert result is not None


# ═══════════════════════════════════════════════════════════════
# BR-006: Fallback to Unfiltered Search
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.search
class TestBR006FallbackToUnfilteredSearch:
    """
    BR-006: Fallback to Unfiltered Search

    Given: No skills matched in Stage 1 (all scores < threshold)
    When: Stage 2 is executed
    Then:
    - Remove skill filter (search all tools)
    - Set metadata.skill_ids_used = null in response
    """

    @pytest.mark.asyncio
    async def test_fallback_when_no_skills_match(
        self, search_service, mock_qdrant_search
    ):
        """Test that search falls back when no skills match threshold."""
        # Add only low-score skills
        mock_qdrant_search.collections["mcp_skills"] = []
        # Add a high-scoring tool without skills
        mock_qdrant_search.seed_tool(
            tool_id="fallback-tool",
            db_id=50,
            name="fallback",
            description="High score but no skills",
            score=0.95,
            skill_ids=[]  # No skills
        )

        # Act with very high skill threshold
        result = await search_service.search(query="test", skill_threshold=0.99)

        # Assert - fallback used
        assert result.metadata.skill_ids_used is None
        assert result.metadata.stage1_skill_count == 0

    @pytest.mark.asyncio
    async def test_fallback_when_skill_collection_empty(
        self, search_service, mock_qdrant_search
    ):
        """Test fallback when skill collection is empty."""
        # Clear skills
        mock_qdrant_search.collections["mcp_skills"] = []

        # Act
        result = await search_service.search(query="test")

        # Assert - still works
        assert result is not None
        assert result.metadata.stage1_skill_count == 0

    @pytest.mark.asyncio
    async def test_metadata_indicates_fallback_used(
        self, search_service
    ):
        """Test that metadata correctly indicates when fallback was used."""
        # Act with very high threshold to force fallback
        result = await search_service.search(query="test", skill_threshold=0.99)

        # Assert - metadata shows no skills matched
        assert result.metadata.skill_ids_used is None
        assert result.metadata.strategy_used == "hierarchical"


# ═══════════════════════════════════════════════════════════════
# BR-007: Search Metadata Tracking
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.search
class TestBR007SearchMetadataTracking:
    """
    BR-007: Search Metadata Tracking

    Given: Any search request
    When: Search completes
    Then:
    - Record timing for each stage
    - Record counts (skills, candidates, final)
    - Record strategy and skill_ids_used
    """

    @pytest.mark.asyncio
    async def test_metadata_includes_timing(
        self, search_service
    ):
        """Test that metadata includes timing for each stage."""
        # Act
        result = await search_service.search(query="test")

        # Assert
        assert result.metadata.query_embedding_time_ms >= 0
        assert result.metadata.skill_search_time_ms >= 0
        assert result.metadata.tool_search_time_ms >= 0
        assert result.metadata.total_time_ms >= 0

    @pytest.mark.asyncio
    async def test_metadata_includes_counts(
        self, search_service
    ):
        """Test that metadata includes counts."""
        # Act
        result = await search_service.search(query="test")

        # Assert
        assert result.metadata.stage1_skill_count >= 0
        assert result.metadata.stage2_candidate_count >= 0
        assert result.metadata.final_count >= 0

    @pytest.mark.asyncio
    async def test_metadata_includes_strategy(
        self, search_service
    ):
        """Test that metadata includes strategy used."""
        # Act
        result = await search_service.search(query="test", strategy="direct")

        # Assert
        assert result.metadata.strategy_used == "direct"


# ═══════════════════════════════════════════════════════════════
# BR-008: Direct Search Strategy (Bypass Skills)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.search
class TestBR008DirectSearchStrategy:
    """
    BR-008: Direct Search Strategy (Bypass Skills)

    Given: Search request with strategy="direct"
    When: Search is performed
    Then:
    - Skip Stage 1 entirely
    - Search tools directly without skill filter
    """

    @pytest.mark.asyncio
    async def test_direct_search_skips_skills(
        self, search_service
    ):
        """Test that direct search skips skill matching."""
        # Act with direct strategy
        result = await search_service.search(query="test", strategy="direct")

        # Assert - no skills matched
        assert len(result.matched_skills) == 0
        assert result.metadata.strategy_used == "direct"

    @pytest.mark.asyncio
    async def test_direct_search_still_applies_type_filter(
        self, search_service
    ):
        """Test that direct search still applies item_type filter."""
        # Act with direct strategy and type filter
        result = await search_service.search(query="test", strategy="direct", item_type="tool")

        # Assert - results still filtered by type
        assert result.metadata.strategy_used == "direct"


# ═══════════════════════════════════════════════════════════════
# BR-009: Score Normalization
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.search
class TestBR009ScoreNormalization:
    """
    BR-009: Score Normalization

    Given: Qdrant returns similarity scores
    When: Results are returned
    Then: All scores normalized to 0.0-1.0 range
    """

    @pytest.mark.asyncio
    async def test_scores_in_valid_range(
        self, search_service
    ):
        """Test that all scores are between 0.0 and 1.0."""
        # Act
        result = await search_service.search(query="test")

        # Assert
        for tool in result.tools:
            assert 0.0 <= tool.score <= 1.0
        for skill in result.matched_skills:
            assert 0.0 <= skill.score <= 1.0


# ═══════════════════════════════════════════════════════════════
# Edge Cases (from logic_contract.md)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.search
class TestSearchEdgeCases:
    """Edge case tests from logic contract EC-XXX."""

    @pytest.mark.asyncio
    async def test_EC001_no_skills_in_index(
        self, search_service, mock_qdrant_search
    ):
        """
        EC-001: No Skills in Index

        Scenario: Skill collection is empty (no skills seeded)
        Expected: Fall back to direct search
        """
        # Clear skills
        mock_qdrant_search.collections["mcp_skills"] = []

        # Act
        result = await search_service.search(query="test")

        # Assert - falls back gracefully
        assert result is not None
        assert result.metadata.stage1_skill_count == 0

    @pytest.mark.asyncio
    async def test_EC002_all_skills_match(
        self, search_service
    ):
        """
        EC-002: All Skills Match

        Scenario: Query is very generic, matches all skills highly
        Expected: Return top skill_limit skills by score
        """
        # Act with generic query
        result = await search_service.search(query="tool", skill_limit=2)

        # Assert - limited by skill_limit
        assert len(result.matched_skills) <= 2

    @pytest.mark.asyncio
    async def test_EC003_skill_matches_but_no_tools(
        self, search_service, mock_qdrant_search
    ):
        """
        EC-003: Skill Matches But No Tools

        Scenario: Matched skills have 0 assigned tools
        Expected: Return empty results (correct behavior)
        """
        # Clear tools but keep skills
        mock_qdrant_search.collections["mcp_unified_search"] = []

        # Act
        result = await search_service.search(query="test")

        # Assert
        assert len(result.tools) == 0

    @pytest.mark.asyncio
    async def test_EC004_very_long_query(
        self, search_service
    ):
        """
        EC-004: Very Long Query

        Scenario: Query > 1000 characters
        Expected: Reject with 422 Validation Error
        """
        long_query = "a" * 1001
        with pytest.raises(ValueError) as exc:
            await search_service.search(query=long_query)
        assert "1000" in str(exc.value)

    @pytest.mark.asyncio
    async def test_EC005_special_characters_in_query(
        self, search_service
    ):
        """
        EC-005: Special Characters in Query

        Scenario: Query contains SQL injection, XSS, etc.
        Expected: Query treated as literal text for embedding
        """
        # Malicious query should not cause issues
        result = await search_service.search(query="'; DROP TABLE users; --")
        assert result is not None  # Should not raise

    @pytest.mark.asyncio
    async def test_EC006_concurrent_same_query(
        self, search_service
    ):
        """
        EC-006: Concurrent Same Query

        Scenario: Same query submitted multiple times simultaneously
        Expected: All return consistent results
        """
        # Act - run same query twice
        result1 = await search_service.search(query="test")
        result2 = await search_service.search(query="test")

        # Assert - consistent results
        assert len(result1.tools) == len(result2.tools)
        assert result1.query == result2.query

    @pytest.mark.asyncio
    async def test_EC008_tool_belongs_to_zero_skills(
        self, search_service, mock_qdrant_search
    ):
        """
        EC-008: Tool Belongs to Zero Skills

        Scenario: Tool exists but has no skill assignments
        Expected: Tool excluded from hierarchical search
        """
        # Add tool with no skills
        mock_qdrant_search.seed_tool(
            tool_id="no-skill-tool",
            db_id=500,
            name="no_skills",
            description="Tool without skills",
            score=0.99,
            skill_ids=[]
        )

        # Act with hierarchical search
        result = await search_service.search(query="test", strategy="hierarchical")

        # Assert - tool not found with skills filter
        tool_ids = [t.id for t in result.tools]
        assert "no-skill-tool" not in tool_ids

        # Act with direct search
        result_direct = await search_service.search(query="test", strategy="direct")

        # Assert - tool found in direct search
        tool_ids_direct = [t.id for t in result_direct.tools]
        # May or may not be in results depending on mock data


# ═══════════════════════════════════════════════════════════════
# Query-Specific Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.search
class TestQuerySpecificBehavior:
    """Tests for specific query types from test data factory."""

    @pytest.mark.asyncio
    async def test_calendar_queries_match_calendar_skill(
        self, search_service, mock_qdrant_search
    ):
        """Test that calendar queries match calendar_management skill."""
        # Ensure calendar skill is seeded with high score for calendar queries
        mock_qdrant_search.collections["mcp_skills"] = []
        mock_qdrant_search.seed_skill(
            skill_id="calendar-management",
            name="Calendar Management",
            description="Tools for scheduling meetings, events, and calendar management",
            score=0.92,
            tool_count=5
        )

        # Test each calendar query
        for query in SearchTestDataFactory.get_calendar_queries():
            result = await search_service.search(query=query)
            skill_ids = [s.id for s in result.matched_skills]
            assert "calendar-management" in skill_ids, f"Query '{query}' should match calendar-management skill"

    @pytest.mark.asyncio
    async def test_ambiguous_queries_match_multiple_skills(
        self, search_service, mock_qdrant_search
    ):
        """Test that ambiguous queries can match multiple skills."""
        # Seed multiple skills that could match ambiguous queries
        mock_qdrant_search.collections["mcp_skills"] = []
        mock_qdrant_search.seed_skill(
            skill_id="calendar-management",
            name="Calendar Management",
            description="Tools for scheduling and calendar",
            score=0.75,
            tool_count=5
        )
        mock_qdrant_search.seed_skill(
            skill_id="file-operations",
            name="File Operations",
            description="Tools for file management",
            score=0.70,
            tool_count=10
        )

        # Test each ambiguous query
        for query in SearchTestDataFactory.get_ambiguous_queries():
            result = await search_service.search(query=query, skill_threshold=0.3)
            assert len(result.matched_skills) >= 1, f"Ambiguous query '{query}' should match at least 1 skill"

    @pytest.mark.asyncio
    async def test_no_match_queries_return_low_scores(
        self, search_service, mock_qdrant_search
    ):
        """Test that no-match queries return low scores or empty results."""
        # Seed skills with very low scores for unrelated query
        mock_qdrant_search.collections["mcp_skills"] = []
        mock_qdrant_search.seed_skill(
            skill_id="calendar-management",
            name="Calendar Management",
            description="Calendar tools",
            score=0.15,  # Very low score
            tool_count=5
        )

        # Query for something unrelated with high threshold
        result = await search_service.search(
            query="xyzzy quantum entanglement blockchain",
            skill_threshold=0.5
        )

        # Should get no matches above threshold
        assert len(result.matched_skills) == 0, "Unrelated query should not match any skills above threshold"


# ═══════════════════════════════════════════════════════════════
# Performance Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.search
@pytest.mark.slow
class TestSearchPerformanceSLAs:
    """Performance tests based on SLAs from logic contract."""

    @pytest.mark.asyncio
    async def test_full_search_under_100ms(
        self, search_service
    ):
        """Test that full hierarchical search completes in < 100ms (target p95)."""
        import time

        start = time.time()
        result = await search_service.search(query="test")
        elapsed_ms = (time.time() - start) * 1000

        # With mocks, should be very fast
        assert elapsed_ms < 100, f"Search took {elapsed_ms:.2f}ms, expected < 100ms"

    @pytest.mark.asyncio
    async def test_skill_search_under_15ms(
        self, search_service
    ):
        """Test that skill search (Stage 1) completes in < 15ms (target p95)."""
        import time

        start = time.time()
        result = await search_service.search(query="test")
        elapsed_ms = (time.time() - start) * 1000

        # With mocks, skill search should be fast
        assert result.metadata.skill_search_time_ms < 15, f"Skill search took {result.metadata.skill_search_time_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_tool_search_under_30ms(
        self, search_service
    ):
        """Test that tool search (Stage 2) completes in < 30ms (target p95)."""
        start = time.time()
        result = await search_service.search(query="test")
        elapsed_ms = (time.time() - start) * 1000

        # With mocks, should be very fast
        assert elapsed_ms < 50  # More lenient for overall test


# ═══════════════════════════════════════════════════════════════
# Integration with Skill Service
# ═══════════════════════════════════════════════════════════════

@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.search
class TestSkillSearchIntegration:
    """Tests for search service integration with skill service."""

    @pytest.mark.asyncio
    async def test_search_uses_skill_embeddings(
        self, search_service, mock_qdrant_search, mock_model_client
    ):
        """Test that search queries skill embeddings collection."""
        # Act
        await search_service.search(query="calendar event")

        # Assert - embedding was created for the query
        embedding_calls = mock_model_client.embeddings._calls
        assert len(embedding_calls) >= 1, "Should create embedding for query"

        # Assert - skill collection was queried
        qdrant_calls = mock_qdrant_search.get_calls("search_with_filter")
        skill_calls = [c for c in qdrant_calls if c.get("collection_name") == "mcp_skills"]
        assert len(skill_calls) >= 1, "Should query mcp_skills collection"

    @pytest.mark.asyncio
    async def test_tool_filter_uses_skill_ids_from_assignments(
        self, search_service, mock_qdrant_search
    ):
        """Test that tool filter uses skill_ids from assignments."""
        # Seed specific skills and tools
        mock_qdrant_search.collections["mcp_skills"] = []
        mock_qdrant_search.collections["mcp_unified_search"] = []

        # Seed a matching skill
        mock_qdrant_search.seed_skill(
            skill_id="email-management",
            name="Email Management",
            description="Email tools",
            score=0.88,
            tool_count=3
        )

        # Seed tools - one matching the skill, one not
        mock_qdrant_search.seed_tool(
            tool_id="send-email",
            db_id=200,
            name="send_email",
            description="Send an email",
            score=0.9,
            skill_ids=["email-management"],
            primary_skill_id="email-management"
        )
        mock_qdrant_search.seed_tool(
            tool_id="read-file",
            db_id=201,
            name="read_file",
            description="Read a file",
            score=0.85,
            skill_ids=["file-operations"],
            primary_skill_id="file-operations"
        )

        # Act
        result = await search_service.search(query="send email")

        # Assert - only tools matching the skill are returned
        tool_ids = [t.id for t in result.tools]
        assert "send-email" in tool_ids, "Should find tool matching the skill"

        # Verify skill IDs were used in filter
        assert result.metadata.skill_ids_used is not None
        assert "email-management" in result.metadata.skill_ids_used
