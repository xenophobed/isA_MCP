"""
Shared test fixtures for isA_MCP tests.

This module provides:
- Factory Boy factories for generating test data
- Random data generators
- Mock API responses
- Sample request payloads
- Golden test data
"""

from .factories import (
    ToolFactory,
    PromptFactory,
    ResourceFactory,
    UserFactory,
    SearchResultFactory,
    EmbeddingFactory,
)
from .generators import (
    generate_random_tool,
    generate_random_prompt,
    generate_random_embedding,
    generate_random_user,
)
from .responses import (
    mock_tool_list_response,
    mock_prompt_list_response,
    mock_search_response,
    mock_error_response,
)
from .sample_requests import (
    sample_tool_call_request,
    sample_search_request,
    sample_auth_request,
)

__all__ = [
    # Factories
    "ToolFactory",
    "PromptFactory",
    "ResourceFactory",
    "UserFactory",
    "SearchResultFactory",
    "EmbeddingFactory",
    # Generators
    "generate_random_tool",
    "generate_random_prompt",
    "generate_random_embedding",
    "generate_random_user",
    # Mock responses
    "mock_tool_list_response",
    "mock_prompt_list_response",
    "mock_search_response",
    "mock_error_response",
    # Sample requests
    "sample_tool_call_request",
    "sample_search_request",
    "sample_auth_request",
]
