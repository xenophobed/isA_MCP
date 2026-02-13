"""
Mock API responses for testing.

Provides pre-built responses that match the MCP protocol and API contracts.
"""

from typing import Any, Dict, List, Optional

# ═══════════════════════════════════════════════════════════════
# MCP Protocol Responses
# ═══════════════════════════════════════════════════════════════


def mock_mcp_response(
    result: Any = None, error: Dict = None, request_id: int = 1
) -> Dict[str, Any]:
    """Create a mock MCP JSON-RPC 2.0 response."""
    response = {"jsonrpc": "2.0", "id": request_id}

    if error:
        response["error"] = error
    else:
        response["result"] = result

    return response


def mock_initialize_response(
    protocol_version: str = "2024-11-05",
    server_name: str = "isA_MCP",
    server_version: str = "0.1.0",
) -> Dict[str, Any]:
    """Create mock initialize response."""
    return mock_mcp_response(
        result={
            "protocolVersion": protocol_version,
            "capabilities": {
                "tools": {"listChanged": True},
                "prompts": {"listChanged": True},
                "resources": {"subscribe": True, "listChanged": True},
            },
            "serverInfo": {"name": server_name, "version": server_version},
        }
    )


# ═══════════════════════════════════════════════════════════════
# Tool Responses
# ═══════════════════════════════════════════════════════════════


def mock_tool_list_response(tools: List[Dict] = None, count: int = 3) -> Dict[str, Any]:
    """Create mock tools/list response."""
    if tools is None:
        tools = [
            {
                "name": f"tool_{i}",
                "description": f"Test tool {i}",
                "inputSchema": {
                    "type": "object",
                    "properties": {"input": {"type": "string"}},
                    "required": ["input"],
                },
            }
            for i in range(count)
        ]

    return mock_mcp_response(result={"tools": tools})


def mock_tool_call_response(content: Any = None, is_error: bool = False) -> Dict[str, Any]:
    """Create mock tools/call response."""
    if content is None:
        content = [{"type": "text", "text": "Tool execution result"}]

    return mock_mcp_response(result={"content": content, "isError": is_error})


def mock_tool_execution_result(result: Any = "Success", metadata: Dict = None) -> Dict[str, Any]:
    """Create mock tool execution result."""
    return {
        "content": [{"type": "text", "text": str(result)}],
        "metadata": metadata or {},
        "isError": False,
    }


# ═══════════════════════════════════════════════════════════════
# Prompt Responses
# ═══════════════════════════════════════════════════════════════


def mock_prompt_list_response(prompts: List[Dict] = None, count: int = 3) -> Dict[str, Any]:
    """Create mock prompts/list response."""
    if prompts is None:
        prompts = [
            {
                "name": f"prompt_{i}",
                "description": f"Test prompt {i}",
                "arguments": [{"name": "input", "description": "Input text", "required": True}],
            }
            for i in range(count)
        ]

    return mock_mcp_response(result={"prompts": prompts})


def mock_prompt_get_response(
    messages: List[Dict] = None, description: str = "Test prompt"
) -> Dict[str, Any]:
    """Create mock prompts/get response."""
    if messages is None:
        messages = [{"role": "user", "content": {"type": "text", "text": "Test prompt content"}}]

    return mock_mcp_response(result={"description": description, "messages": messages})


# ═══════════════════════════════════════════════════════════════
# Resource Responses
# ═══════════════════════════════════════════════════════════════


def mock_resource_list_response(resources: List[Dict] = None, count: int = 3) -> Dict[str, Any]:
    """Create mock resources/list response."""
    if resources is None:
        resources = [
            {
                "uri": f"resource://test/{i}",
                "name": f"resource_{i}",
                "description": f"Test resource {i}",
                "mimeType": "application/json",
            }
            for i in range(count)
        ]

    return mock_mcp_response(result={"resources": resources})


def mock_resource_read_response(
    content: Any = None, mime_type: str = "application/json"
) -> Dict[str, Any]:
    """Create mock resources/read response."""
    if content is None:
        content = {"data": "test content"}

    return mock_mcp_response(
        result={
            "contents": [
                {
                    "uri": "resource://test/1",
                    "mimeType": mime_type,
                    "text": str(content) if isinstance(content, str) else None,
                    "blob": None,
                }
            ]
        }
    )


# ═══════════════════════════════════════════════════════════════
# Search Responses
# ═══════════════════════════════════════════════════════════════


def mock_search_response(
    results: List[Dict] = None, query: str = "test query", total: int = None
) -> Dict[str, Any]:
    """Create mock search response."""
    if results is None:
        results = [
            {
                "id": f"result_{i}",
                "name": f"item_{i}",
                "description": f"Search result {i}",
                "score": round(1.0 - (i * 0.1), 2),
                "category": "tool",
            }
            for i in range(5)
        ]

    return {"query": query, "results": results, "total": total or len(results), "took_ms": 42}


# ═══════════════════════════════════════════════════════════════
# Error Responses
# ═══════════════════════════════════════════════════════════════


def mock_error_response(
    code: int, message: str, data: Dict = None, request_id: int = 1
) -> Dict[str, Any]:
    """Create mock error response."""
    error = {"code": code, "message": message}
    if data:
        error["data"] = data

    return mock_mcp_response(error=error, request_id=request_id)


def mock_validation_error(field: str, message: str = "Validation failed") -> Dict[str, Any]:
    """Create mock validation error response."""
    return mock_error_response(
        code=-32602, message="Invalid params", data={"field": field, "message": message}
    )


def mock_not_found_error(resource_type: str, identifier: str) -> Dict[str, Any]:
    """Create mock not found error response."""
    return mock_error_response(code=-32602, message=f"{resource_type} not found: {identifier}")


def mock_auth_error(message: str = "Authentication required") -> Dict[str, Any]:
    """Create mock authentication error response."""
    return mock_error_response(code=-32001, message=message)


def mock_rate_limit_error(retry_after: int = 60) -> Dict[str, Any]:
    """Create mock rate limit error response."""
    return mock_error_response(
        code=-32003, message="Rate limit exceeded", data={"retry_after": retry_after}
    )


# ═══════════════════════════════════════════════════════════════
# HTTP API Responses
# ═══════════════════════════════════════════════════════════════


def mock_http_success(data: Any = None, message: str = "Success") -> Dict[str, Any]:
    """Create mock HTTP success response."""
    return {"success": True, "message": message, "data": data}


def mock_http_error(status_code: int, message: str, details: Dict = None) -> Dict[str, Any]:
    """Create mock HTTP error response."""
    return {
        "success": False,
        "error": {"code": status_code, "message": message, "details": details or {}},
    }


def mock_paginated_response(
    items: List[Any], page: int = 1, page_size: int = 20, total: int = None
) -> Dict[str, Any]:
    """Create mock paginated response."""
    total = total or len(items)
    total_pages = (total + page_size - 1) // page_size

    return {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    }
