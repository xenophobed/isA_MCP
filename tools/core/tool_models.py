"""
Tool Models - MCP-Compliant Pydantic Models for Tool I/O

Standards Compliance:
- MCP Protocol: Uses CallToolResult format (content + structuredContent + isError)
- OpenAI Compatible: Supports function calling patterns
- Type Safe: Full Pydantic validation
- HIL Support: Standardized human-in-loop responses

Architecture:
1. MCP SDK Types - Official types from mcp.types (imported)
2. Domain-Specific Models - Custom ISA response types
3. HIL Models - Human-in-loop interaction patterns
4. Specialized Models - Tool-specific responses
5. Helper Functions - Easy response creation

Migration Note:
- TextContent, ImageContent, AudioContent, CallToolResult now imported from mcp.types
- Removed duplicate implementations to use official MCP SDK types
- Kept domain-specific enums and models (ToolStatus, HIL responses, etc.)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import json

# ============================================================================
# MCP SDK Imports - Official Types
# ============================================================================

try:
    from mcp.types import (
        CallToolResult,
        TextContent,
        ImageContent,
        # AudioContent,  # Not available in mcp.types yet
        # ResourceLink,  # Not available in mcp.types yet
    )
    MCP_SDK_AVAILABLE = True
except ImportError:
    MCP_SDK_AVAILABLE = False
    # Fallback definitions if MCP SDK not available
    class TextContent(BaseModel):
        type: Literal["text"] = "text"
        text: str
        annotations: Optional[Dict[str, Any]] = None
        meta: Optional[Dict[str, Any]] = None

    class ImageContent(BaseModel):
        type: Literal["image"] = "image"
        data: str
        mimeType: str
        annotations: Optional[Dict[str, Any]] = None
        meta: Optional[Dict[str, Any]] = None

    class CallToolResult(BaseModel):
        content: List[Any]
        structuredContent: Optional[Dict[str, Any]] = None
        isError: bool = False


# ============================================================================
# Enums - Standard Values
# ============================================================================

class ToolStatus(str, Enum):
    """Standard tool execution status values"""
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    CREATED = "created"

    # HIL statuses
    HUMAN_INPUT_REQUESTED = "human_input_requested"
    AUTHORIZATION_REQUESTED = "authorization_requested"
    AUTHORIZATION_REQUIRED = "authorization_required"
    CREDENTIAL_REQUIRED = "credential_required"
    HUMAN_REQUIRED = "human_required"


class HILAction(str, Enum):
    """Human-in-loop action types"""
    ASK_HUMAN = "ask_human"
    REQUEST_AUTHORIZATION = "request_authorization"


class InterventionType(str, Enum):
    """Types of manual intervention needed"""
    CAPTCHA = "captcha"
    LOGIN = "login"
    PAYMENT = "payment"
    WALLET = "wallet"
    VERIFICATION = "verification"
    OAUTH = "oauth"


class SecurityLevel(str, Enum):
    """Security authorization levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ContentType(str, Enum):
    """MCP content types"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    RESOURCE = "resource_link"
    EMBEDDED = "embedded_resource"


# ============================================================================
# Additional MCP Content Models (Not in SDK yet)
# ============================================================================

# Keep AudioContent and ResourceLink until they're added to mcp.types
class AudioContent(BaseModel):
    """MCP audio content"""
    type: Literal["audio"] = "audio"
    data: str  # Base64 or URL
    mimeType: str
    annotations: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None


class ResourceLink(BaseModel):
    """MCP resource link"""
    type: Literal["resource_link"] = "resource_link"
    uri: str
    annotations: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None


# Union of all content types (TextContent and ImageContent from mcp.types)
MCPContent = Union[TextContent, ImageContent, AudioContent, ResourceLink]


# ============================================================================
# Base Metadata Models - Our Extended Metadata
# ============================================================================

class ToolMetadata(BaseModel):
    """Metadata for tool execution (stored in structuredContent)"""
    status: ToolStatus
    action: str
    timestamp: datetime = Field(default_factory=datetime.now)
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorMetadata(ToolMetadata):
    """Error-specific metadata"""
    error: str
    error_code: Optional[str] = None
    traceback: Optional[str] = None


class HILMetadata(ToolMetadata):
    """HIL-specific metadata"""
    hil_required: bool = True
    message: str
    instruction: Optional[str] = None


# ============================================================================
# MCP CallToolResult - From SDK (with helper methods)
# ============================================================================

# CallToolResult is imported from mcp.types
# Add helper methods via monkey-patching if needed, or use helper functions below


# ============================================================================
# Standard Response Models - Common Patterns
# ============================================================================

class SuccessResponse(BaseModel):
    """Standard success response structure"""
    status: Literal[ToolStatus.SUCCESS] = ToolStatus.SUCCESS
    action: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_mcp_result(self) -> CallToolResult:
        """Convert to MCP CallToolResult"""
        return CallToolResult(
            content=[TextContent(text=json.dumps(self.data))],
            structuredContent={
                "status": self.status,
                "action": self.action,
                "data": self.data,
                "timestamp": self.timestamp.isoformat()
            },
            isError=False
        )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ErrorResponse(BaseModel):
    """Standard error response structure"""
    status: Literal[ToolStatus.ERROR] = ToolStatus.ERROR
    action: str
    error: str
    error_code: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    traceback: Optional[str] = None

    def to_mcp_result(self) -> CallToolResult:
        """Convert to MCP CallToolResult"""
        error_text = f"Error: {self.error}"
        if self.error_code:
            error_text = f"[{self.error_code}] {error_text}"

        return CallToolResult(
            content=[TextContent(text=error_text)],
            structuredContent={
                "status": self.status,
                "action": self.action,
                "error": self.error,
                "error_code": self.error_code,
                "data": self.data,
                "timestamp": self.timestamp.isoformat(),
                "traceback": self.traceback
            },
            isError=True
        )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============================================================================
# HIL Response Models - Human-in-Loop Patterns
# ============================================================================

class AskHumanResponse(BaseModel):
    """
    HIL Response: Ask human for input

    Scenario 1: Agent needs user to provide information
    Used by: interaction_tools.ask_human
    """
    status: Literal[ToolStatus.HUMAN_INPUT_REQUESTED] = ToolStatus.HUMAN_INPUT_REQUESTED
    action: Literal[HILAction.ASK_HUMAN] = HILAction.ASK_HUMAN
    question: str
    context: Optional[str] = None
    user_id: str = "default"
    instruction: str = "This request requires human input. The client should handle the interaction."
    timestamp: datetime = Field(default_factory=datetime.now)

    # Optional validation rules for user input
    validation_rules: Optional[Dict[str, Any]] = None

    def to_mcp_result(self) -> CallToolResult:
        """Convert to MCP CallToolResult"""
        return CallToolResult(
            content=[
                TextContent(
                    text=self.question,
                    meta={"context": self.context} if self.context else None
                )
            ],
            structuredContent={
                "hil_required": True,
                "status": self.status,
                "action": self.action,
                "data": {
                    "question": self.question,
                    "context": self.context,
                    "user_id": self.user_id,
                    "instruction": self.instruction,
                    "validation_rules": self.validation_rules
                },
                "timestamp": self.timestamp.isoformat()
            },
            isError=False
        )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class RequestAuthorizationResponse(BaseModel):
    """
    HIL Response: Request authorization for tool execution

    Scenario 2: High-security tool needs user approval
    Used by: interaction_tools.request_authorization, security system
    """
    status: Literal[ToolStatus.AUTHORIZATION_REQUESTED] = ToolStatus.AUTHORIZATION_REQUESTED
    action: Literal[HILAction.REQUEST_AUTHORIZATION] = HILAction.REQUEST_AUTHORIZATION
    request_id: str
    tool_name: str
    tool_args: Dict[str, Any]
    reason: str
    security_level: SecurityLevel
    user_id: str = "default"
    expires_at: datetime
    instruction: str = "This request requires authorization. The client should handle the approval process."
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_mcp_result(self) -> CallToolResult:
        """Convert to MCP CallToolResult"""
        return CallToolResult(
            content=[
                TextContent(
                    text=f"Authorization required for '{self.tool_name}': {self.reason}"
                )
            ],
            structuredContent={
                "hil_required": True,
                "status": self.status,
                "action": self.action,
                "data": {
                    "request_id": self.request_id,
                    "tool_name": self.tool_name,
                    "tool_args": self.tool_args,
                    "reason": self.reason,
                    "security_level": self.security_level,
                    "user_id": self.user_id,
                    "expires_at": self.expires_at.isoformat(),
                    "instruction": self.instruction
                },
                "timestamp": self.timestamp.isoformat()
            },
            isError=False
        )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class RequestCredentialUsageResponse(BaseModel):
    """
    HIL Response: Request permission to use stored credentials

    Scenario 4a: Vault has credentials, ask permission to use
    Used by: web_automation_service (login pages)
    """
    status: Literal[ToolStatus.AUTHORIZATION_REQUIRED] = ToolStatus.AUTHORIZATION_REQUIRED
    action: Literal[HILAction.REQUEST_AUTHORIZATION] = HILAction.REQUEST_AUTHORIZATION
    message: str
    provider: str
    auth_type: str  # "social", "payment", "wallet"
    credential_preview: Dict[str, Any]
    url: Optional[str] = None
    screenshot: Optional[str] = None
    details: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_mcp_result(self) -> CallToolResult:
        """Convert to MCP CallToolResult"""
        return CallToolResult(
            content=[TextContent(text=self.message)],
            structuredContent={
                "hil_required": True,
                "status": self.status,
                "action": self.action,
                "message": self.message,
                "data": {
                    "provider": self.provider,
                    "auth_type": self.auth_type,
                    "credential_preview": self.credential_preview,
                    "url": self.url,
                    "screenshot": self.screenshot,
                    "details": self.details
                },
                "timestamp": self.timestamp.isoformat()
            },
            isError=False
        )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ManualInterventionResponse(BaseModel):
    """
    HIL Response: Request manual user intervention

    Scenario 4b: Vault has no credentials OR CAPTCHA detected
    Used by: web_automation_service (CAPTCHA, first-time login, etc.)
    """
    status: Union[
        Literal[ToolStatus.CREDENTIAL_REQUIRED],
        Literal[ToolStatus.HUMAN_REQUIRED]
    ]
    action: Literal[HILAction.ASK_HUMAN] = HILAction.ASK_HUMAN
    message: str
    intervention_type: InterventionType
    provider: str
    instructions: str
    url: Optional[str] = None
    screenshot: Optional[str] = None
    oauth_url: Optional[str] = None
    details: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_mcp_result(self) -> CallToolResult:
        """Convert to MCP CallToolResult"""
        return CallToolResult(
            content=[
                TextContent(
                    text=f"{self.message}\n\nInstructions: {self.instructions}"
                )
            ],
            structuredContent={
                "hil_required": True,
                "status": self.status,
                "action": self.action,
                "message": self.message,
                "data": {
                    "intervention_type": self.intervention_type,
                    "provider": self.provider,
                    "instructions": self.instructions,
                    "url": self.url,
                    "screenshot": self.screenshot,
                    "oauth_url": self.oauth_url,
                    "details": self.details
                },
                "timestamp": self.timestamp.isoformat()
            },
            isError=False
        )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class OAuthAuthorizationResponse(BaseModel):
    """
    HIL Response: Request OAuth authorization

    Scenario 3: Composio third-party app OAuth
    Used by: composio_service, HIL service
    """
    status: Literal[ToolStatus.AUTHORIZATION_REQUESTED] = ToolStatus.AUTHORIZATION_REQUESTED
    action: str = "oauth_authorization"
    provider: str
    oauth_url: str
    scopes: Optional[List[str]] = None
    context: Optional[str] = None
    user_id: str = "default"
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_mcp_result(self) -> CallToolResult:
        """Convert to MCP CallToolResult"""
        return CallToolResult(
            content=[
                TextContent(
                    text=f"OAuth authorization required for {self.provider}",
                    meta={"oauth_url": self.oauth_url}
                )
            ],
            structuredContent={
                "hil_required": True,
                "status": self.status,
                "action": self.action,
                "data": {
                    "provider": self.provider,
                    "oauth_url": self.oauth_url,
                    "scopes": self.scopes,
                    "context": self.context,
                    "user_id": self.user_id,
                    "auth_type": "oauth"
                },
                "timestamp": self.timestamp.isoformat()
            },
            isError=False
        )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============================================================================
# Progress & Streaming Models
# ============================================================================

# NOTE: Progress reporting now handled via Context.report_progress()
# from mcp.server.fastmcp import Context
# await ctx.report_progress(progress=1, total=10, message="Working...")
#
# This is the preferred MCP SDK way to report progress.
# Kept StreamChunk for custom streaming scenarios not covered by SDK.


# ============================================================================
# Specialized Response Models
# ============================================================================

class SearchResultsResponse(BaseModel):
    """Response for search operations (web_search, search_memories, etc.)"""
    status: Literal[ToolStatus.SUCCESS] = ToolStatus.SUCCESS
    action: str
    query: str
    total: int
    results: List[Dict[str, Any]]
    urls: Optional[List[str]] = None
    search_params: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_mcp_result(self) -> CallToolResult:
        """Convert to MCP CallToolResult"""
        summary = f"Found {self.total} results for: {self.query}"

        return CallToolResult(
            content=[TextContent(text=summary)],
            structuredContent={
                "status": self.status,
                "action": self.action,
                "data": {
                    "query": self.query,
                    "total": self.total,
                    "results": self.results,
                    "urls": self.urls,
                    "search_params": self.search_params
                },
                "timestamp": self.timestamp.isoformat()
            },
            isError=False
        )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class BatchOperationResponse(BaseModel):
    """Response for batch operations"""
    status: ToolStatus
    action: str
    total_processed: int
    successful: int
    failed: int
    results: List[Dict[str, Any]]
    errors: Optional[List[Dict[str, Any]]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_mcp_result(self) -> CallToolResult:
        """Convert to MCP CallToolResult"""
        summary = f"Processed {self.total_processed} items: {self.successful} succeeded, {self.failed} failed"

        return CallToolResult(
            content=[TextContent(text=summary)],
            structuredContent={
                "status": self.status,
                "action": self.action,
                "data": {
                    "total_processed": self.total_processed,
                    "successful": self.successful,
                    "failed": self.failed,
                    "results": self.results,
                    "errors": self.errors
                },
                "timestamp": self.timestamp.isoformat()
            },
            isError=self.failed > 0
        )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============================================================================
# Helper Functions - Easy Response Creation
# ============================================================================

def create_success(
    action: str,
    data: Dict[str, Any],
    user_id: Optional[str] = None  # Reserved for future use
) -> CallToolResult:
    """
    Create a standard success response

    Args:
        action: Tool/action name
        data: Response data
        user_id: Optional user ID

    Returns:
        MCP-compliant CallToolResult
    """
    response = SuccessResponse(action=action, data=data)
    return response.to_mcp_result()


def create_error(
    action: str,
    error: str,
    error_code: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    traceback: Optional[str] = None
) -> CallToolResult:
    """
    Create a standard error response

    Args:
        action: Tool/action name
        error: Error message
        error_code: Optional error code
        data: Optional additional data
        traceback: Optional stack trace

    Returns:
        MCP-compliant CallToolResult
    """
    response = ErrorResponse(
        action=action,
        error=error,
        error_code=error_code,
        data=data or {},
        traceback=traceback
    )
    return response.to_mcp_result()


def create_ask_human(
    question: str,
    context: Optional[str] = None,
    user_id: str = "default",
    validation_rules: Optional[Dict[str, Any]] = None
) -> CallToolResult:
    """
    Create an ask_human HIL response

    Args:
        question: Question to ask user
        context: Additional context
        user_id: User ID
        validation_rules: Optional input validation rules

    Returns:
        MCP-compliant CallToolResult
    """
    response = AskHumanResponse(
        question=question,
        context=context,
        user_id=user_id,
        validation_rules=validation_rules
    )
    return response.to_mcp_result()


def create_request_authorization(
    request_id: str,
    tool_name: str,
    tool_args: Dict[str, Any],
    reason: str,
    security_level: SecurityLevel,
    user_id: str = "default",
    expires_at: Optional[datetime] = None
) -> CallToolResult:
    """
    Create a request_authorization HIL response

    Args:
        request_id: Unique request ID
        tool_name: Tool requiring authorization
        tool_args: Tool arguments
        reason: Reason for authorization
        security_level: Security level
        user_id: User ID
        expires_at: Expiration datetime

    Returns:
        MCP-compliant CallToolResult
    """
    from datetime import timedelta

    if expires_at is None:
        expires_at = datetime.now() + timedelta(minutes=30)

    response = RequestAuthorizationResponse(
        request_id=request_id,
        tool_name=tool_name,
        tool_args=tool_args,
        reason=reason,
        security_level=security_level,
        user_id=user_id,
        expires_at=expires_at
    )
    return response.to_mcp_result()


def create_manual_intervention(
    intervention_type: InterventionType,
    provider: str,
    message: str,
    instructions: str,
    url: Optional[str] = None,
    screenshot: Optional[str] = None,
    oauth_url: Optional[str] = None,
    status: str = ToolStatus.HUMAN_REQUIRED
) -> CallToolResult:
    """
    Create a manual intervention HIL response

    Args:
        intervention_type: Type of intervention
        provider: Service provider
        message: User message
        instructions: What user should do
        url: Optional URL
        screenshot: Optional screenshot path
        oauth_url: Optional OAuth URL
        status: Status (HUMAN_REQUIRED or CREDENTIAL_REQUIRED)

    Returns:
        MCP-compliant CallToolResult
    """
    response = ManualInterventionResponse(
        status=status,
        intervention_type=intervention_type,
        provider=provider,
        message=message,
        instructions=instructions,
        url=url,
        screenshot=screenshot,
        oauth_url=oauth_url
    )
    return response.to_mcp_result()


# ============================================================================
# Type Aliases for Convenience
# ============================================================================

ToolResponse = Union[
    SuccessResponse,
    ErrorResponse,
    AskHumanResponse,
    RequestAuthorizationResponse,
    RequestCredentialUsageResponse,
    ManualInterventionResponse,
    OAuthAuthorizationResponse,
    SearchResultsResponse,
    BatchOperationResponse
]

HILResponse = Union[
    AskHumanResponse,
    RequestAuthorizationResponse,
    RequestCredentialUsageResponse,
    ManualInterventionResponse,
    OAuthAuthorizationResponse
]
