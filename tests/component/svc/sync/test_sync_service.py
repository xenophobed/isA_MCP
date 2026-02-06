"""
TDD TESTS - SyncService batch embedding behavior

These tests define the expected behavior for batch embedding in SyncService.
Write tests BEFORE implementing the feature.

Feature: Use batch embedding instead of concurrent individual requests
Reason: ISA Model API has 100 req/min rate limit, batch avoids hitting it
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.component
@pytest.mark.sync
class TestSyncServiceBatchEmbedding:
    """TDD tests for SyncService batch embedding - RED first, then GREEN."""

    @pytest.fixture
    def sync_service_with_mocks(self):
        """Create SyncService with all dependencies mocked via instance attributes."""
        from services.sync_service.sync_service import SyncService

        # Create mocks
        mock_isa_model = MagicMock()
        mock_isa_model.embeddings = MagicMock()
        mock_isa_model.embeddings.create = AsyncMock()

        mock_tool_service = AsyncMock()
        mock_prompt_service = AsyncMock()
        mock_resource_service = AsyncMock()
        mock_vector_repo = AsyncMock()
        mock_mcp_server = AsyncMock()

        # Patch at the module level where imports happen
        with patch.object(SyncService, '__init__', lambda self, mcp_server=None: None):
            service = SyncService(mcp_server=mock_mcp_server)

        # Set attributes manually (since we bypassed __init__)
        service.mcp_server = mock_mcp_server
        service.tool_service = mock_tool_service
        service.prompt_service = mock_prompt_service
        service.resource_service = mock_resource_service
        service.vector_repo = mock_vector_repo
        service.isa_model = mock_isa_model
        service.embedding_model = "text-embedding-3-small"

        yield {
            "service": service,
            "mcp_server": mock_mcp_server,
            "isa_model": mock_isa_model,
            "tool_service": mock_tool_service,
            "prompt_service": mock_prompt_service,
            "resource_service": mock_resource_service,
            "vector_repo": mock_vector_repo,
        }

    @pytest.mark.asyncio
    async def test_sync_tools_uses_batch_embedding_single_call(self, sync_service_with_mocks):
        """
        RED: SyncService should call embeddings.create ONCE with a list of texts,
        not multiple times with individual texts.

        This is the key behavior change - batch vs concurrent individual calls.
        """
        mocks = sync_service_with_mocks
        service = mocks["service"]
        mock_isa_model = mocks["isa_model"]

        # Given: 5 tools to sync
        mock_tools = []
        for i in range(5):
            tool = MagicMock()
            tool.name = f"tool_{i}"
            tool.description = f"Description {i}"
            tool.inputSchema = {}
            mock_tools.append(tool)
        mocks["mcp_server"].list_tools.return_value = mock_tools

        # Mock embedding response - returns list of embeddings matching input order
        mock_embedding_data = [MagicMock(embedding=[0.1] * 1536) for _ in range(5)]
        mock_isa_model.embeddings.create.return_value = MagicMock(data=mock_embedding_data)

        # Mock services
        mocks["tool_service"].get_tool.return_value = None  # New tools
        mocks["tool_service"].register_tool.side_effect = [
            {"id": i, "name": f"tool_{i}"} for i in range(5)
        ]
        mocks["vector_repo"].get_all_by_type.return_value = []  # No existing
        mocks["vector_repo"].upsert_vector.return_value = True

        # When: Sync tools
        result = await service.sync_tools()

        # Then: embeddings.create should be called ONCE with a LIST of texts
        assert mock_isa_model.embeddings.create.call_count == 1, \
            f"Expected 1 batch call, got {mock_isa_model.embeddings.create.call_count} calls"

        # Verify it was called with a list (batch), not individual strings
        call_args = mock_isa_model.embeddings.create.call_args
        input_arg = call_args.kwargs.get("input")

        assert isinstance(input_arg, list), \
            f"Expected input to be a list (batch), got {type(input_arg)}"
        assert len(input_arg) == 5, \
            f"Expected 5 texts in batch, got {len(input_arg)}"

    @pytest.mark.asyncio
    async def test_sync_tools_batch_embedding_maintains_order(self, sync_service_with_mocks):
        """
        RED: Batch embedding response order must match input order.
        Each tool gets its corresponding embedding.
        """
        mocks = sync_service_with_mocks
        service = mocks["service"]
        mock_isa_model = mocks["isa_model"]

        # Given: 3 tools with distinct descriptions
        mock_tools = []
        for i in range(3):
            tool = MagicMock()
            tool.name = f"tool_{i}"
            tool.description = f"Unique description {i}"
            tool.inputSchema = {}
            mock_tools.append(tool)
        mocks["mcp_server"].list_tools.return_value = mock_tools

        # Mock embedding response - each embedding is distinct (first value = index)
        mock_embedding_data = [
            MagicMock(embedding=[float(i)] * 1536) for i in range(3)
        ]
        mock_isa_model.embeddings.create.return_value = MagicMock(data=mock_embedding_data)

        # Track which embedding is used for each tool
        upsert_calls = []
        async def track_upsert(**kwargs):
            upsert_calls.append(kwargs)
            return True

        mocks["tool_service"].get_tool.return_value = None
        mocks["tool_service"].register_tool.side_effect = [
            {"id": i, "name": f"tool_{i}"} for i in range(3)
        ]
        mocks["vector_repo"].get_all_by_type.return_value = []
        mocks["vector_repo"].upsert_vector.side_effect = track_upsert

        # When: Sync tools
        await service.sync_tools()

        # Then: Each tool should get its corresponding embedding (order preserved)
        assert len(upsert_calls) == 3, f"Expected 3 upsert calls, got {len(upsert_calls)}"

        for i, call in enumerate(upsert_calls):
            embedding = call.get("embedding")
            # The i-th tool should get embedding with value [i, i, i, ...]
            assert embedding[0] == float(i), \
                f"Tool {i} got wrong embedding: expected {float(i)}, got {embedding[0]}"

    @pytest.mark.asyncio
    async def test_sync_tools_handles_empty_tools_list(self, sync_service_with_mocks):
        """
        RED: When no tools to sync, should not call embedding API at all.
        """
        mocks = sync_service_with_mocks
        service = mocks["service"]
        mock_isa_model = mocks["isa_model"]

        # Given: No tools
        mocks["mcp_server"].list_tools.return_value = []
        mocks["vector_repo"].get_all_by_type.return_value = []

        # When: Sync tools
        result = await service.sync_tools()

        # Then: No embedding calls should be made
        assert mock_isa_model.embeddings.create.call_count == 0, \
            "Should not call embedding API when no tools to sync"
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_sync_prompts_uses_batch_embedding(self, sync_service_with_mocks):
        """
        RED: sync_prompts should also use batch embedding.
        """
        mocks = sync_service_with_mocks
        service = mocks["service"]
        mock_isa_model = mocks["isa_model"]

        # Given: 3 prompts to sync
        mock_prompts = []
        for i in range(3):
            prompt = MagicMock()
            prompt.name = f"prompt_{i}"
            prompt.description = f"Prompt description {i}"
            prompt.arguments = []
            mock_prompts.append(prompt)
        mocks["mcp_server"].list_prompts.return_value = mock_prompts

        mock_embedding_data = [MagicMock(embedding=[0.1] * 1536) for _ in range(3)]
        mock_isa_model.embeddings.create.return_value = MagicMock(data=mock_embedding_data)

        mocks["prompt_service"].get_prompt.return_value = None
        mocks["prompt_service"].register_prompt.side_effect = [
            {"id": i, "name": f"prompt_{i}"} for i in range(3)
        ]
        mocks["vector_repo"].get_all_by_type.return_value = []
        mocks["vector_repo"].upsert_vector.return_value = True

        # When: Sync prompts
        result = await service.sync_prompts()

        # Then: Should be ONE batch call
        assert mock_isa_model.embeddings.create.call_count == 1, \
            f"Expected 1 batch call for prompts, got {mock_isa_model.embeddings.create.call_count}"

        # Verify batch input
        call_args = mock_isa_model.embeddings.create.call_args
        input_arg = call_args.kwargs.get("input")
        assert isinstance(input_arg, list), "Expected batch input (list)"
        assert len(input_arg) == 3

    @pytest.mark.asyncio
    async def test_sync_resources_uses_batch_embedding(self, sync_service_with_mocks):
        """
        RED: sync_resources should also use batch embedding.
        """
        mocks = sync_service_with_mocks
        service = mocks["service"]
        mock_isa_model = mocks["isa_model"]

        # Given: 2 resources to sync
        mock_resources = []
        for i in range(2):
            resource = MagicMock()
            resource.name = f"resource_{i}"
            resource.uri = f"resource://test/{i}"
            resource.description = f"Resource description {i}"
            resource.mimeType = "text/plain"
            mock_resources.append(resource)
        mocks["mcp_server"].list_resources.return_value = mock_resources

        mock_embedding_data = [MagicMock(embedding=[0.1] * 1536) for _ in range(2)]
        mock_isa_model.embeddings.create.return_value = MagicMock(data=mock_embedding_data)

        mocks["resource_service"].get_resource.return_value = None
        mocks["resource_service"].register_resource.side_effect = [
            {"id": i, "name": f"resource_{i}"} for i in range(2)
        ]
        mocks["vector_repo"].get_all_by_type.return_value = []
        mocks["vector_repo"].upsert_vector.return_value = True

        # When: Sync resources
        result = await service.sync_resources()

        # Then: Should be ONE batch call
        assert mock_isa_model.embeddings.create.call_count == 1, \
            f"Expected 1 batch call for resources, got {mock_isa_model.embeddings.create.call_count}"

        # Verify batch input
        call_args = mock_isa_model.embeddings.create.call_args
        input_arg = call_args.kwargs.get("input")
        assert isinstance(input_arg, list), "Expected batch input (list)"
        assert len(input_arg) == 2
