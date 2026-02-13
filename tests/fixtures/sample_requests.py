"""
Sample request payloads for testing.

Provides pre-built request payloads that match the MCP protocol and API contracts.
"""

from typing import Any, Dict, List

# ═══════════════════════════════════════════════════════════════
# MCP Protocol Requests
# ═══════════════════════════════════════════════════════════════


def mcp_request(method: str, params: Dict = None, request_id: int = 1) -> Dict[str, Any]:
    """Create a MCP JSON-RPC 2.0 request."""
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}


def sample_initialize_request(
    protocol_version: str = "2024-11-05",
    client_name: str = "test_client",
    client_version: str = "1.0.0",
) -> Dict[str, Any]:
    """Create sample initialize request."""
    return mcp_request(
        "initialize",
        {
            "protocolVersion": protocol_version,
            "capabilities": {},
            "clientInfo": {"name": client_name, "version": client_version},
        },
    )


# ═══════════════════════════════════════════════════════════════
# Tool Requests
# ═══════════════════════════════════════════════════════════════


def sample_tool_list_request(cursor: str = None) -> Dict[str, Any]:
    """Create sample tools/list request."""
    params = {}
    if cursor:
        params["cursor"] = cursor
    return mcp_request("tools/list", params)


def sample_tool_call_request(
    tool_name: str = "text_generator", arguments: Dict = None
) -> Dict[str, Any]:
    """Create sample tools/call request."""
    if arguments is None:
        arguments = {"input": "test input"}

    return mcp_request("tools/call", {"name": tool_name, "arguments": arguments})


def sample_text_generator_request(
    prompt: str = "Hello, world!", max_tokens: int = 100, temperature: float = 0.7
) -> Dict[str, Any]:
    """Create sample text generator tool request."""
    return sample_tool_call_request(
        tool_name="text_generator",
        arguments={"prompt": prompt, "max_tokens": max_tokens, "temperature": temperature},
    )


def sample_vision_analyzer_request(
    image_url: str = "https://example.com/image.jpg", prompt: str = "Describe this image"
) -> Dict[str, Any]:
    """Create sample vision analyzer tool request."""
    return sample_tool_call_request(
        tool_name="vision_analyzer", arguments={"image_url": image_url, "prompt": prompt}
    )


def sample_embedding_request(
    text: str = "Sample text for embedding", model: str = "text-embedding-3-small"
) -> Dict[str, Any]:
    """Create sample embedding generator tool request."""
    return sample_tool_call_request(
        tool_name="embedding_generator", arguments={"text": text, "model": model}
    )


# ═══════════════════════════════════════════════════════════════
# Prompt Requests
# ═══════════════════════════════════════════════════════════════


def sample_prompt_list_request(cursor: str = None) -> Dict[str, Any]:
    """Create sample prompts/list request."""
    params = {}
    if cursor:
        params["cursor"] = cursor
    return mcp_request("prompts/list", params)


def sample_prompt_get_request(
    prompt_name: str = "assistant_prompt", arguments: Dict = None
) -> Dict[str, Any]:
    """Create sample prompts/get request."""
    if arguments is None:
        arguments = {"task": "Help me with a task"}

    return mcp_request("prompts/get", {"name": prompt_name, "arguments": arguments})


# ═══════════════════════════════════════════════════════════════
# Resource Requests
# ═══════════════════════════════════════════════════════════════


def sample_resource_list_request(cursor: str = None) -> Dict[str, Any]:
    """Create sample resources/list request."""
    params = {}
    if cursor:
        params["cursor"] = cursor
    return mcp_request("resources/list", params)


def sample_resource_read_request(uri: str = "resource://data/sample") -> Dict[str, Any]:
    """Create sample resources/read request."""
    return mcp_request("resources/read", {"uri": uri})


def sample_resource_subscribe_request(uri: str = "resource://data/sample") -> Dict[str, Any]:
    """Create sample resources/subscribe request."""
    return mcp_request("resources/subscribe", {"uri": uri})


# ═══════════════════════════════════════════════════════════════
# Search Requests
# ═══════════════════════════════════════════════════════════════


def sample_search_request(
    query: str = "search query", limit: int = 10, category: str = None, filters: Dict = None
) -> Dict[str, Any]:
    """Create sample search request."""
    request = {"query": query, "limit": limit}

    if category:
        request["category"] = category

    if filters:
        request["filters"] = filters

    return request


def sample_tool_search_request(query: str = "analyze data", limit: int = 5) -> Dict[str, Any]:
    """Create sample tool search request."""
    return sample_search_request(query=query, limit=limit, category="tool")


def sample_semantic_search_request(
    query: str = "I need to process images", limit: int = 10, min_score: float = 0.5
) -> Dict[str, Any]:
    """Create sample semantic search request."""
    return {"query": query, "limit": limit, "filters": {"min_score": min_score}}


# ═══════════════════════════════════════════════════════════════
# Auth Requests
# ═══════════════════════════════════════════════════════════════


def sample_auth_request(api_key: str = "mcp_test_api_key_12345") -> Dict[str, str]:
    """Create sample auth headers."""
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def sample_jwt_auth_request(
    token: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
) -> Dict[str, str]:
    """Create sample JWT auth headers."""
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def sample_basic_auth_request(
    username: str = "test_user", password: str = "test_password"
) -> Dict[str, str]:
    """Create sample basic auth headers."""
    import base64

    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {credentials}", "Content-Type": "application/json"}


# ═══════════════════════════════════════════════════════════════
# Sync Requests
# ═══════════════════════════════════════════════════════════════


def sample_sync_request(force: bool = False, collections: List[str] = None) -> Dict[str, Any]:
    """Create sample sync request."""
    return {"force": force, "collections": collections or ["tools", "prompts", "resources"]}


def sample_incremental_sync_request(
    since_timestamp: str = None, db_id: int = None
) -> Dict[str, Any]:
    """Create sample incremental sync request."""
    request = {}

    if since_timestamp:
        request["since"] = since_timestamp

    if db_id is not None:
        request["db_id"] = db_id

    return request


# ═══════════════════════════════════════════════════════════════
# Progress Requests
# ═══════════════════════════════════════════════════════════════


def sample_progress_subscribe_request(operation_id: str = "op_12345") -> Dict[str, Any]:
    """Create sample progress subscribe request."""
    return {"operation_id": operation_id}


def sample_progress_status_request(operation_id: str = "op_12345") -> Dict[str, Any]:
    """Create sample progress status request."""
    return {"operation_id": operation_id}


# ═══════════════════════════════════════════════════════════════
# Batch Request Helpers
# ═══════════════════════════════════════════════════════════════


def create_batch_tool_calls(tool_name: str, arguments_list: List[Dict]) -> List[Dict[str, Any]]:
    """Create multiple tool call requests."""
    return [sample_tool_call_request(tool_name, args) for args in arguments_list]


def create_request_batch(requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Assign incremental IDs to a batch of requests."""
    for i, req in enumerate(requests):
        req["id"] = i + 1
    return requests
