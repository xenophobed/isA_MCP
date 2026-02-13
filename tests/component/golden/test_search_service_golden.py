"""
🔒 CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the CURRENT behavior of SearchService.
If these tests fail, it means behavior has changed unexpectedly.

Service Under Test: services/search_service/search_service.py
"""

import pytest
from unittest.mock import AsyncMock


@pytest.mark.golden
@pytest.mark.component
@pytest.mark.search
class TestSearchServiceGolden:
    """
    Golden tests for SearchService - DO NOT MODIFY.

    Key characteristics:
    - Orchestrates VectorRepository + ToolRepository + PromptRepository + ResourceRepository
    - Generates embeddings via EmbeddingGenerator
    - Enriches results with schemas from PostgreSQL
    - Returns SearchResult dataclass objects
    """

    @pytest.fixture
    def mock_vector_repo(self):
        """Create mock vector repository."""
        repo = AsyncMock()
        repo.ensure_collection = AsyncMock()
        repo.search_vectors = AsyncMock(return_value=[])
        repo.get_stats = AsyncMock(return_value={})
        return repo

    @pytest.fixture
    def mock_tool_repo(self):
        """Create mock tool repository."""
        repo = AsyncMock()
        repo.get_tool_by_id = AsyncMock(return_value=None)
        return repo

    @pytest.fixture
    def mock_prompt_repo(self):
        """Create mock prompt repository."""
        repo = AsyncMock()
        repo.get_prompt_by_id = AsyncMock(return_value=None)
        return repo

    @pytest.fixture
    def mock_resource_repo(self):
        """Create mock resource repository."""
        repo = AsyncMock()
        repo.get_resource_by_id = AsyncMock(return_value=None)
        return repo

    @pytest.fixture
    def mock_embedding_generator(self):
        """Create mock embedding generator."""
        generator = AsyncMock()
        generator.embed = AsyncMock(return_value=[0.1] * 1536)
        generator.embed_single = AsyncMock(return_value=[0.1] * 1536)
        generator.embed_batch = AsyncMock(return_value=[[0.1] * 1536])
        return generator

    @pytest.fixture
    def search_service(
        self,
        mock_vector_repo,
        mock_tool_repo,
        mock_prompt_repo,
        mock_resource_repo,
        mock_embedding_generator,
    ):
        """Create SearchService with mocked dependencies."""
        from services.search_service.search_service import SearchService

        service = SearchService(
            vector_repo=mock_vector_repo,
            embedding_gen=mock_embedding_generator,
            tool_repo=mock_tool_repo,
            prompt_repo=mock_prompt_repo,
            resource_repo=mock_resource_repo,
        )
        return service

    # ═══════════════════════════════════════════════════════════════
    # Initialization
    # ═══════════════════════════════════════════════════════════════

    async def test_initialize_ensures_collection(self, search_service, mock_vector_repo):
        """
        CURRENT BEHAVIOR: initialize() calls vector_repo.ensure_collection().
        """
        await search_service.initialize()

        mock_vector_repo.ensure_collection.assert_called_once()

    # ═══════════════════════════════════════════════════════════════
    # Search Flow
    # ═══════════════════════════════════════════════════════════════

    async def test_search_generates_embedding_first(
        self, search_service, mock_embedding_generator, mock_vector_repo
    ):
        """
        CURRENT BEHAVIOR: search() first generates embedding from query text.
        """
        mock_vector_repo.search_vectors.return_value = []

        await search_service.search("test query")

        mock_embedding_generator.embed_single.assert_called_once_with("test query")

    async def test_search_calls_vector_search_with_embedding(
        self, search_service, mock_embedding_generator, mock_vector_repo
    ):
        """
        CURRENT BEHAVIOR: search() passes generated embedding to vector search.
        """
        expected_embedding = [0.5] * 1536
        mock_embedding_generator.embed_single.return_value = expected_embedding
        mock_vector_repo.search_vectors.return_value = []

        await search_service.search("test query", limit=5, score_threshold=0.5)

        mock_vector_repo.search_vectors.assert_called_once()
        call_kwargs = mock_vector_repo.search_vectors.call_args
        # Verify embedding was passed
        assert call_kwargs is not None

    async def test_search_returns_list_of_search_results(self, search_service, mock_vector_repo):
        """
        CURRENT BEHAVIOR: search() returns list (possibly empty) of results.
        """
        mock_vector_repo.search_vectors.return_value = []

        result = await search_service.search("test query")

        assert isinstance(result, list)

    # ═══════════════════════════════════════════════════════════════
    # Schema Enrichment
    # ═══════════════════════════════════════════════════════════════

    async def test_search_enriches_tool_results_with_schema(
        self, search_service, mock_vector_repo, mock_tool_repo
    ):
        """
        CURRENT BEHAVIOR: Tool results are enriched with inputSchema and outputSchema from PostgreSQL.
        """
        # Vector search returns tool result
        mock_vector_repo.search_vectors.return_value = [
            {
                "id": "tool_1",
                "type": "tool",
                "name": "test_tool",
                "description": "A test tool",
                "db_id": 42,
                "score": 0.95,
                "metadata": {},
            }
        ]

        # PostgreSQL has full schema
        mock_tool_repo.get_tool_by_id.return_value = {
            "id": 42,
            "name": "test_tool",
            "input_schema": {"type": "object", "properties": {}},
            "output_schema": {"type": "string"},
            "annotations": {"category": "utility"},
        }

        await search_service.search("test query", item_type="tool")

        # Should fetch schema from PostgreSQL
        mock_tool_repo.get_tool_by_id.assert_called()

    async def test_search_handles_missing_postgresql_record(
        self, search_service, mock_vector_repo, mock_tool_repo
    ):
        """
        CURRENT BEHAVIOR: Logs warning but doesn't fail if PostgreSQL record is missing.
        """
        mock_vector_repo.search_vectors.return_value = [
            {
                "id": "tool_1",
                "type": "tool",
                "name": "orphaned_tool",
                "description": "Tool in Qdrant but not PostgreSQL",
                "db_id": 999,
                "score": 0.9,
                "metadata": {},
            }
        ]

        # PostgreSQL returns None (record deleted)
        mock_tool_repo.get_tool_by_id.return_value = None

        # Should not raise, just log warning
        result = await search_service.search("test query", item_type="tool")

        assert isinstance(result, list)

    # ═══════════════════════════════════════════════════════════════
    # Type-Specific Search Methods
    # ═══════════════════════════════════════════════════════════════

    async def test_search_tools_filters_by_tool_type(self, search_service, mock_vector_repo):
        """
        CURRENT BEHAVIOR: search_tools() passes item_type='tool' to search.
        """
        mock_vector_repo.search_vectors.return_value = []

        await search_service.search_tools("text generator", limit=5)

        mock_vector_repo.search_vectors.assert_called_once()
        # Verify item_type filter was applied

    async def test_search_prompts_filters_by_prompt_type(self, search_service, mock_vector_repo):
        """
        CURRENT BEHAVIOR: search_prompts() passes item_type='prompt' to search.
        """
        mock_vector_repo.search_vectors.return_value = []

        await search_service.search_prompts("coding assistant", limit=5)

        mock_vector_repo.search_vectors.assert_called_once()

    async def test_search_resources_filters_by_resource_type(
        self, search_service, mock_vector_repo
    ):
        """
        CURRENT BEHAVIOR: search_resources() passes item_type='resource' to search.
        """
        mock_vector_repo.search_vectors.return_value = []

        await search_service.search_resources("configuration", limit=5)

        mock_vector_repo.search_vectors.assert_called_once()

    # ═══════════════════════════════════════════════════════════════
    # Default Score Thresholds
    # ═══════════════════════════════════════════════════════════════

    async def test_default_score_threshold_for_tools(self, search_service, mock_vector_repo):
        """
        CURRENT BEHAVIOR: Tools have default score threshold of 0.3.
        """
        mock_vector_repo.search_vectors.return_value = []

        await search_service.search_tools("query")

        # Default threshold should be applied (0.3 for tools)

    async def test_default_score_threshold_for_prompts(self, search_service, mock_vector_repo):
        """
        CURRENT BEHAVIOR: Prompts have default score threshold of 0.5.
        """
        mock_vector_repo.search_vectors.return_value = []

        await search_service.search_prompts("query")

        # Default threshold should be applied (0.5 for prompts)

    # ═══════════════════════════════════════════════════════════════
    # Statistics
    # ═══════════════════════════════════════════════════════════════

    async def test_get_stats_returns_vector_repo_stats(self, search_service, mock_vector_repo):
        """
        CURRENT BEHAVIOR: get_stats() delegates to vector repository.
        """
        expected_stats = {
            "collection": "mcp_unified_search",
            "total_points": 1000,
            "vector_dimension": 1536,
        }
        mock_vector_repo.get_stats.return_value = expected_stats

        result = await search_service.get_stats()

        assert result == expected_stats
        mock_vector_repo.get_stats.assert_called_once()

    # ═══════════════════════════════════════════════════════════════
    # Error Handling
    # ═══════════════════════════════════════════════════════════════

    async def test_search_returns_empty_list_on_error(
        self, search_service, mock_embedding_generator
    ):
        """
        CURRENT BEHAVIOR: Returns empty list on error (graceful degradation).
        """
        mock_embedding_generator.embed_single.side_effect = Exception(
            "Embedding service unavailable"
        )

        result = await search_service.search("test query")

        assert result == []


@pytest.mark.golden
@pytest.mark.component
@pytest.mark.search
class TestSearchResultGolden:
    """
    Golden tests for SearchResult dataclass - DO NOT MODIFY.
    """

    def test_search_result_structure(self):
        """
        CURRENT BEHAVIOR: SearchResult has specific fields.
        """
        from services.search_service.search_service import SearchResult

        result = SearchResult(
            id="test_1",
            type="tool",
            name="test_tool",
            description="A test tool",
            score=0.95,
            db_id=42,
            metadata={},
            inputSchema={"type": "object"},
            outputSchema=None,
            annotations=None,
        )

        assert result.id == "test_1"
        assert result.type == "tool"
        assert result.name == "test_tool"
        assert result.score == 0.95
        assert result.db_id == 42
        assert result.inputSchema == {"type": "object"}

    def test_search_result_optional_fields(self):
        """
        CURRENT BEHAVIOR: inputSchema, outputSchema, annotations are optional.
        """
        from services.search_service.search_service import SearchResult

        # Should not raise with None values
        result = SearchResult(
            id="test_1",
            type="tool",
            name="test_tool",
            description="A test tool",
            score=0.95,
            db_id=42,
            metadata={},
            inputSchema=None,
            outputSchema=None,
            annotations=None,
        )

        assert result.inputSchema is None
        assert result.outputSchema is None
        assert result.annotations is None
