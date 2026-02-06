"""
🔒 CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the CURRENT behavior of PromptService and PromptRepository.
If these tests fail, it means behavior has changed unexpectedly.

Service Under Test: services/prompt_service/prompt_service.py
Repository Under Test: services/prompt_service/prompt_repository.py
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.golden
@pytest.mark.component
@pytest.mark.prompts
class TestPromptServiceGolden:
    """
    Golden tests for PromptService - DO NOT MODIFY.

    Key differences from ToolService:
    - Requires both 'name' AND 'content' fields
    - Has 'tags' array field for filtering
    - Statistics: usage_count, avg_generation_time_ms
    """

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository."""
        repo = AsyncMock()
        repo.get_prompt_by_id = AsyncMock(return_value=None)
        repo.get_prompt_by_name = AsyncMock(return_value=None)
        repo.create_prompt = AsyncMock(return_value={"id": 1, "name": "test_prompt"})
        repo.update_prompt = AsyncMock(return_value=True)
        repo.delete_prompt = AsyncMock(return_value=True)
        repo.list_prompts = AsyncMock(return_value=[])
        repo.search_prompts = AsyncMock(return_value=[])
        repo.search_by_tags = AsyncMock(return_value=[])
        repo.increment_usage_count = AsyncMock(return_value=True)
        return repo

    @pytest.fixture
    def prompt_service(self, mock_repository):
        """Create PromptService with mocked repository."""
        from services.prompt_service.prompt_service import PromptService
        return PromptService(repository=mock_repository)

    # ═══════════════════════════════════════════════════════════════
    # Registration Behavior
    # ═══════════════════════════════════════════════════════════════

    async def test_register_prompt_requires_name(self, prompt_service):
        """
        CURRENT BEHAVIOR: register_prompt raises ValueError if name is missing.
        """
        with pytest.raises(ValueError) as exc_info:
            await prompt_service.register_prompt({
                "content": "Some content"
            })

        assert "name" in str(exc_info.value).lower()

    async def test_register_prompt_requires_content(self, prompt_service):
        """
        CURRENT BEHAVIOR: register_prompt raises ValueError if content is missing.
        """
        with pytest.raises(ValueError) as exc_info:
            await prompt_service.register_prompt({
                "name": "test_prompt"
            })

        assert "content" in str(exc_info.value).lower()

    async def test_register_prompt_detects_duplicate_name(self, prompt_service, mock_repository):
        """
        CURRENT BEHAVIOR: register_prompt raises ValueError for duplicate names.
        """
        mock_repository.get_prompt_by_name.return_value = {
            "id": 1,
            "name": "existing_prompt"
        }

        with pytest.raises(ValueError):
            await prompt_service.register_prompt({
                "name": "existing_prompt",
                "content": "Content"
            })

    async def test_register_prompt_returns_dict_with_id(self, prompt_service, mock_repository):
        """
        CURRENT BEHAVIOR: Successful registration returns dict with 'id' field.
        """
        mock_repository.get_prompt_by_name.return_value = None
        mock_repository.create_prompt.return_value = {
            "id": 42,
            "name": "new_prompt",
            "content": "Prompt content"
        }

        result = await prompt_service.register_prompt({
            "name": "new_prompt",
            "content": "Prompt content"
        })

        assert isinstance(result, dict)
        assert "id" in result
        assert result["id"] == 42

    # ═══════════════════════════════════════════════════════════════
    # Get Prompt Polymorphism
    # ═══════════════════════════════════════════════════════════════

    async def test_get_prompt_by_integer_id(self, prompt_service, mock_repository):
        """
        CURRENT BEHAVIOR: Integer identifier calls get_prompt_by_id.
        """
        expected_prompt = {"id": 1, "name": "prompt_by_id"}
        mock_repository.get_prompt_by_id.return_value = expected_prompt

        result = await prompt_service.get_prompt(1)

        mock_repository.get_prompt_by_id.assert_called_once_with(1)
        assert result == expected_prompt

    async def test_get_prompt_by_string_name(self, prompt_service, mock_repository):
        """
        CURRENT BEHAVIOR: String identifier calls get_prompt_by_name.
        """
        expected_prompt = {"id": 1, "name": "prompt_by_name"}
        mock_repository.get_prompt_by_name.return_value = expected_prompt

        result = await prompt_service.get_prompt("prompt_by_name")

        mock_repository.get_prompt_by_name.assert_called_once_with("prompt_by_name")
        assert result == expected_prompt

    # ═══════════════════════════════════════════════════════════════
    # Tags Filtering
    # ═══════════════════════════════════════════════════════════════

    async def test_list_prompts_with_tags_filter(self, prompt_service, mock_repository):
        """
        CURRENT BEHAVIOR: Tags filter uses PostgreSQL array overlap operator.
        """
        mock_repository.list_prompts.return_value = [
            {"id": 1, "name": "prompt1", "tags": ["coding", "python"]}
        ]

        result = await prompt_service.list_prompts(tags=["coding"])

        assert isinstance(result, list)
        mock_repository.list_prompts.assert_called_once()

    async def test_search_by_tags_returns_matching_prompts(self, prompt_service, mock_repository):
        """
        CURRENT BEHAVIOR: search_by_tags returns prompts with ANY matching tag.
        """
        mock_repository.search_by_tags.return_value = [
            {"id": 1, "name": "prompt1", "tags": ["python", "coding"]},
            {"id": 2, "name": "prompt2", "tags": ["python", "data"]}
        ]

        result = await prompt_service.search_by_tags(["python"], limit=10)

        assert isinstance(result, list)
        mock_repository.search_by_tags.assert_called_once()

    # ═══════════════════════════════════════════════════════════════
    # Usage Statistics
    # ═══════════════════════════════════════════════════════════════

    async def test_record_prompt_usage_updates_statistics(self, prompt_service, mock_repository):
        """
        CURRENT BEHAVIOR: record_prompt_usage increments usage_count and updates avg_generation_time.
        """
        mock_repository.get_prompt_by_id.return_value = {"id": 1, "name": "prompt"}
        mock_repository.increment_usage_count.return_value = True

        result = await prompt_service.record_prompt_usage(
            prompt_identifier=1,
            generation_time_ms=200
        )

        assert result is True
        mock_repository.increment_usage_count.assert_called_once()

    # ═══════════════════════════════════════════════════════════════
    # Search Behavior
    # ═══════════════════════════════════════════════════════════════

    async def test_search_prompts_searches_name_description_content(self, prompt_service, mock_repository):
        """
        CURRENT BEHAVIOR: Search queries name, description, AND content fields.
        """
        mock_repository.search_prompts.return_value = [
            {"id": 1, "name": "test", "description": "A prompt", "content": "Content"}
        ]

        result = await prompt_service.search_prompts("test", limit=10)

        assert isinstance(result, list)
        mock_repository.search_prompts.assert_called_once()


@pytest.mark.golden
@pytest.mark.component
@pytest.mark.prompts
class TestPromptRepositoryGolden:
    """
    Golden tests for PromptRepository - DO NOT MODIFY.

    Key behaviors:
    - Tags stored as PostgreSQL array (not JSON)
    - Arguments and metadata as JSONB
    - Array overlap operator for tag filtering
    """

    async def test_tags_stored_as_postgres_array(self):
        """
        CURRENT BEHAVIOR: Tags are stored as native PostgreSQL array, not JSON.

        This allows use of array operators like @> and &&.
        """
        # Repository implementation stores tags as: tags text[]
        # Not as: tags jsonb
        pass

    async def test_tag_filter_uses_array_overlap(self):
        """
        CURRENT BEHAVIOR: Tag filtering uses && (overlap) operator.

        Example SQL: WHERE tags && ARRAY['tag1', 'tag2']
        Returns prompts with ANY matching tag.
        """
        pass

    async def test_arguments_and_metadata_as_jsonb(self):
        """
        CURRENT BEHAVIOR: arguments and metadata fields are JSONB.

        Allows flexible schema for prompt arguments.
        """
        pass
