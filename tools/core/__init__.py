"""
Tools Core Module - MCP Tool Models and Utilities

Easy imports for tool development:

    from tools.core import (
        # Response models
        SuccessResponse,
        ErrorResponse,
        AskHumanResponse,
        RequestAuthorizationResponse,
        ManualInterventionResponse,

        # Helper functions
        create_success,
        create_error,
        create_ask_human,
        create_request_authorization,
        create_manual_intervention,

        # Enums
        ToolStatus,
        HILAction,
        InterventionType,
        SecurityLevel,

        # MCP types
        CallToolResult,
        TextContent,
        ImageContent
    )
"""

from .tool_models import (
    # Enums
    ToolStatus,
    HILAction,
    InterventionType,
    SecurityLevel,
    ContentType,
    # MCP Content
    TextContent,
    ImageContent,
    AudioContent,
    ResourceLink,
    MCPContent,
    # Base Models
    ToolMetadata,
    ErrorMetadata,
    HILMetadata,
    CallToolResult,
    # Standard Responses
    SuccessResponse,
    ErrorResponse,
    # HIL Responses
    AskHumanResponse,
    RequestAuthorizationResponse,
    RequestCredentialUsageResponse,
    ManualInterventionResponse,
    OAuthAuthorizationResponse,
    # Specialized Responses
    SearchResultsResponse,
    BatchOperationResponse,
    # Helper Functions
    create_success,
    create_error,
    create_ask_human,
    create_request_authorization,
    create_manual_intervention,
    # Type Aliases
    ToolResponse,
    HILResponse,
)

__all__ = [
    # Enums
    "ToolStatus",
    "HILAction",
    "InterventionType",
    "SecurityLevel",
    "ContentType",
    # MCP Content
    "TextContent",
    "ImageContent",
    "AudioContent",
    "ResourceLink",
    "MCPContent",
    # Base Models
    "ToolMetadata",
    "ErrorMetadata",
    "HILMetadata",
    "CallToolResult",
    # Standard Responses
    "SuccessResponse",
    "ErrorResponse",
    # HIL Responses
    "AskHumanResponse",
    "RequestAuthorizationResponse",
    "RequestCredentialUsageResponse",
    "ManualInterventionResponse",
    "OAuthAuthorizationResponse",
    # Specialized Responses
    "SearchResultsResponse",
    "BatchOperationResponse",
    # Helper Functions
    "create_success",
    "create_error",
    "create_ask_human",
    "create_request_authorization",
    "create_manual_intervention",
    # Type Aliases
    "ToolResponse",
    "HILResponse",
]
