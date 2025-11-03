"""
Base Tool Class for ISA MCP Tools
统一处理ISA客户端调用、billing信息返回和工具注册

Enhanced with MCP SDK Features:
- Progress reporting via Context
- Human-in-loop via ctx.elicit()
- Streaming support
- Timeout and cancellation
- Rate limiting
- Resource cleanup
- Structured input/output validation

==============================================================================
AUTO-DISCOVERY REGISTRATION PATTERN
==============================================================================

To enable automatic tool discovery and registration, follow this pattern:
 
1. **Filename**: Must end with `_tools.py`
   Example: `weather_tools.py`, `data_analytics_tools.py`

2. **Register Function**: Must be named `register_{filename}(mcp)`
   Examples:
   - For `weather_tools.py` → `register_weather_tools(mcp)`
   - For `data_analytics_tools.py` → `register_data_analytics_tools(mcp)`

3. **Location**: Place your tool file in:
   - `tools/` directory (root level)
   - `tools/services/{service_name}/` (service-specific tools)
   - `tools/{any_subdirectory}/` (any subdirectory)

4. **Example Structure**:
   ```python
   from tools.base_tool import BaseTool

   class MyTool(BaseTool):
       def __init__(self):
           super().__init__()

       def register_tools(self, mcp):
           self.register_tool(
               mcp,
               self.my_tool_impl,
               name="my_tool",
               description="My tool description"
           )

       async def my_tool_impl(self, param1: str, ctx: Context = None):
           # Implementation
           pass

   # REQUIRED: Register function with correct naming pattern
   def register_weather_tools(mcp):
       '''Register my custom tools'''
       tool = MyTool()
       tool.register_tools(mcp)
       return tool
   ```

5. **Auto-Discovery Process** (see `core/auto_discovery.py:257-316`):
   - Scans all `*_tools.py` files recursively in `tools/` directory
   - Looks for `register_{module_name}(mcp)` function
   - Calls the register function to register tools with MCP server
   - Logs success/failure for each module

==============================================================================
"""
import json
import asyncio
import inspect
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional, List, Union, Callable, TypeVar, ParamSpec
from contextlib import asynccontextmanager
from functools import wraps
import logging

# MCP SDK imports
try:
    from mcp.server.fastmcp import Context
    from mcp.types import CallToolResult, TextContent, ImageContent, ToolAnnotations
    MCP_SDK_AVAILABLE = True
except ImportError:
    MCP_SDK_AVAILABLE = False
    Context = Any  # Type hint fallback
    ToolAnnotations = Any  # Type hint fallback

from isa_model.client import ISAModelClient
from core.security import SecurityLevel, get_security_manager

logger = logging.getLogger(__name__)

# Type variables for generic decorators
P = ParamSpec('P')
T = TypeVar('T')

def json_serializer(obj):
    """Custom JSON serializer for datetime and other objects"""
    # Skip Context objects (not serializable) - check multiple ways
    if obj.__class__.__name__ == 'Context':
        return "<Context>"
    if 'Context' in str(type(obj)):
        return "<Context>"
    # Skip any MCP types
    if 'mcp.' in str(type(obj)):
        return f"<{type(obj).__name__}>"

    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif hasattr(obj, 'dict') and callable(obj.dict):  # Pydantic models
        return obj.dict()
    elif hasattr(obj, '__dict__') and not callable(obj):
        # Filter out non-serializable objects from __dict__
        filtered_dict = {}
        for k, v in obj.__dict__.items():
            if 'Context' not in str(type(v)) and 'mcp.' not in str(type(v)):
                filtered_dict[k] = v
        return filtered_dict
    # Handle numpy types - be more aggressive
    try:
        import numpy as np
        # Handle any numpy type first
        if isinstance(obj, np.generic):
            return obj.item()
        # Handle numpy arrays
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        # Backup: check for any numpy module types
        elif hasattr(obj, 'dtype') and hasattr(obj, 'item'):
            return obj.item()
    except ImportError:
        pass
    except Exception:
        # If numpy conversion fails, try basic conversions
        try:
            if hasattr(obj, 'item'):
                return obj.item()
        except:
            pass
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

class BaseTool:
    """
    基础工具类 - Event-driven architecture with MCP SDK integration

    Features:
    - ISA client integration with billing events
    - MCP SDK Context support (progress, logging, HIL)
    - Security integration with authorization levels
    - Rate limiting and timeout control
    - Resource cleanup and lifecycle management
    - Streaming and cancellation support
    - Tool registration with structured I/O
    """

    def __init__(self):
        self._isa_client = None
        self._security_manager = None
        self.registered_tools = []
        self._current_user_id: Optional[str] = None
        self._rate_limiters: Dict[str, 'AsyncLimiter'] = {}
        self._active_operations: Dict[str, asyncio.Task] = {}

        # Check MCP SDK availability
        if not MCP_SDK_AVAILABLE:
            logger.warning(
                "MCP SDK not available. Advanced features "
                "(progress, HIL, streaming) will be limited."
            )
    
    @property
    def isa_client(self):
        """延迟初始化ISA客户端"""
        if self._isa_client is None:
            from core.isa_client_factory import get_isa_client
            self._isa_client = get_isa_client()
        return self._isa_client
    
    @property
    def security_manager(self):
        """Get the global security manager instance"""
        if self._security_manager is None:
            try:
                self._security_manager = get_security_manager()
            except RuntimeError:
                # Fallback to simple security manager if not initialized
                logger.warning("Security manager not initialized, using fallback")
                class SimpleSecurityManager:
                    def security_check(self, func):
                        return func
                    def require_authorization(self, security_level):
                        def decorator(func):
                            func._security_level = security_level.name
                            return func
                        return decorator
                self._security_manager = SimpleSecurityManager()
        return self._security_manager

    def extract_context_info(self, ctx: Optional[Context]) -> Dict[str, Any]:
        """
        从 Context 中提取可序列化的信息

        这是安全提取 Context 元数据的官方方式。
        Context 本身不可序列化，但其基本属性可以安全提取。

        Args:
            ctx: MCP Context（可选）

        Returns:
            Dict[str, Any]: 包含可序列化的 Context 信息

        Example:
            @mcp.tool()
            async def my_tool(data: str, ctx: Context) -> dict:
                # 提取 Context 信息
                context_info = self.extract_context_info(ctx)

                # 返回业务数据 + Context 元数据
                return {
                    "result": process(data),
                    "context": context_info
                }
        """
        if not ctx:
            return {
                "request_id": None,
                "client_id": None,
                "session_id": None,
                "timestamp": datetime.now().isoformat()
            }

        # 只提取可序列化的基本属性
        info = {
            "timestamp": datetime.now().isoformat()
        }

        # 安全提取 request_id
        try:
            info["request_id"] = getattr(ctx, "request_id", None)
        except Exception as e:
            logger.debug(f"Failed to extract request_id: {e}")
            info["request_id"] = None

        # 安全提取 client_id
        try:
            info["client_id"] = getattr(ctx, "client_id", None)
        except Exception as e:
            logger.debug(f"Failed to extract client_id: {e}")
            info["client_id"] = None

        # 安全提取 session_id
        try:
            info["session_id"] = getattr(ctx, "session_id", None)
        except Exception as e:
            logger.debug(f"Failed to extract session_id: {e}")
            info["session_id"] = None

        return info
    
    async def call_isa_with_events(
        self,
        input_data: Union[str, List[Dict], Dict],
        task: str,
        service_type: str,
        user_id: str,
        parameters: Optional[Dict] = None
    ) -> Any:
        """
        调用ISA客户端并发布billing事件 (Event-driven architecture)

        Args:
            input_data: 输入数据
            task: 任务类型 ("chat", "embed", "generate_image", "image_to_image")
            service_type: 服务类型 ("text", "embedding", "image")
            user_id: 用户ID (用于billing事件)
            parameters: 额外参数

        Returns:
            result_data: 仅返回结果数据，billing通过事件发布
        """
        try:
            # 调用ISA客户端
            isa_response = await self.isa_client.invoke(
                input_data=input_data,
                task=task,
                service_type=service_type,
                parameters=parameters or {}
            )

            # 提取结果
            result_data = isa_response.get('result', {})

            if not isa_response.get('success'):
                raise Exception(f"ISA API call failed: {isa_response.get('error', 'Unknown error')}")

            # 发布billing事件 (异步，不阻塞主流程)
            billing_info = isa_response.get('billing', {})
            if billing_info:
                await self._publish_billing_event(
                    user_id=user_id,
                    service_type=service_type,
                    operation=task,
                    metadata={
                        'model': billing_info.get('model', 'unknown'),
                        'provider': billing_info.get('provider', 'unknown'),
                        'cost_usd': billing_info.get('cost_usd', 0.0),
                        'input_tokens': billing_info.get('input_tokens'),
                        'output_tokens': billing_info.get('output_tokens'),
                    }
                )

            return result_data

        except Exception as e:
            logger.error(f"ISA API call failed: {e}")
            raise

    async def _publish_billing_event(
        self,
        user_id: str,
        service_type: str,
        operation: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        input_units: Optional[float] = None,
        output_units: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        发布billing事件到NATS (异步事件驱动架构)

        Event will be consumed by billing_service for cost calculation and wallet deduction.

        Args:
            user_id: 用户ID
            service_type: 服务类型
            operation: 操作类型
            input_tokens: 输入token数
            output_tokens: 输出token数
            input_units: 输入单位 (非token服务)
            output_units: 输出单位 (非token服务)
            metadata: 额外元数据
        """
        try:
            from decimal import Decimal

            # Calculate usage
            if input_tokens is not None and output_tokens is not None:
                usage_amount = Decimal(input_tokens + output_tokens)
                unit_type = "token"
            elif input_units is not None:
                usage_amount = Decimal(input_units)
                unit_type = "request"
            else:
                # Extract from metadata if available
                if metadata and 'cost_usd' in metadata:
                    usage_amount = Decimal(1)  # Count as 1 request
                    unit_type = "request"
                else:
                    logger.warning(f"No usage metrics for user {user_id}")
                    return

            # Prepare usage details
            usage_details = {
                "service_type": service_type,
                "operation": operation,
            }

            if input_tokens:
                usage_details["input_tokens"] = input_tokens
            if output_tokens:
                usage_details["output_tokens"] = output_tokens
            if metadata:
                usage_details.update(metadata)

            # Publish event via isa_common
            try:
                from isa_common.events import publish_usage_event

                success = await publish_usage_event(
                    user_id=user_id,
                    product_id=metadata.get('model', 'unknown') if metadata else 'unknown',
                    usage_amount=usage_amount,
                    unit_type=unit_type,
                    usage_details=usage_details,
                    nats_host='localhost',  # TODO: from config
                    nats_port=50056
                )

                if success:
                    logger.info(
                        f"📊 Published billing event: user={user_id}, "
                        f"operation={operation}, usage={usage_amount} {unit_type}"
                    )
                else:
                    logger.warning(f"Failed to publish billing event for {user_id}")

            except ImportError:
                logger.warning(
                    "isa_common.events not available. "
                    "Billing events will not be published. "
                    "Install isa_common package for event-driven billing."
                )
            except Exception as e:
                logger.error(f"Error publishing billing event: {e}", exc_info=True)

        except Exception as e:
            # Don't let billing errors break the service
            logger.warning(f"Failed to publish billing event: {e}", exc_info=False)

    # ============================================================================
    # Progress Tracking - ProgressManager (Recommended)
    # ============================================================================
    # ⚠️ DEPRECATED: ctx.report_progress() - Use ProgressManager instead!
    #
    # New Architecture:
    # - ProgressManager: Redis-based, stateless, works with any HTTP client
    # - SSE Streaming: Real-time server push (recommended)
    # - HTTP Polling: Simple polling fallback
    #
    # Example Usage:
    #   from services.progress_service import ProgressManager
    #
    #   async def my_tool(data: str):
    #       operation_id = str(uuid.uuid4())
    #       manager = ProgressManager()
    #
    #       await manager.start_operation(operation_id)
    #       # ... do work ...
    #       await manager.update_progress(operation_id, 50)
    #       # ... more work ...
    #       await manager.complete_operation(operation_id, result)
    #
    #       return {"operation_id": operation_id}
    #
    #   # Client monitors via SSE: GET /progress/{operation_id}/stream
    # ============================================================================

    async def create_progress_operation(
        self,
        operation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new progress operation (NEW RECOMMENDED WAY)

        Returns operation_id that clients can use to monitor progress via:
        - SSE: GET /progress/{operation_id}/stream (recommended)
        - Polling: call get_task_progress MCP tool

        Args:
            operation_id: Optional custom ID (auto-generated if not provided)
            metadata: Optional metadata to attach

        Returns:
            operation_id string

        Example:
            async def my_long_task(self, data: str):
                # Start progress tracking
                op_id = await self.create_progress_operation(
                    metadata={"task": "processing", "data_size": len(data)}
                )

                # Update progress as you work
                await self.update_progress_operation(op_id, 25, message="Step 1 done")
                # ... work ...
                await self.update_progress_operation(op_id, 50, message="Step 2 done")
                # ... work ...
                await self.complete_progress_operation(op_id, {"result": "success"})

                # Return operation_id so client can monitor
                return self.create_response("success", "my_long_task", {
                    "operation_id": op_id,
                    "message": "Task started. Monitor via SSE: GET /progress/{op_id}/stream"
                })
        """
        import uuid
        from services.progress_service import ProgressManager

        if operation_id is None:
            operation_id = str(uuid.uuid4())

        manager = ProgressManager()
        await manager.start_operation(operation_id, metadata=metadata)

        logger.info(f"Created progress operation: {operation_id}")
        return operation_id

    async def update_progress_operation(
        self,
        operation_id: str,
        progress: float,
        current: Optional[int] = None,
        total: Optional[int] = None,
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Update progress for an operation (NEW RECOMMENDED WAY)

        Progress is automatically pushed to clients via SSE.

        Args:
            operation_id: Operation ID from create_progress_operation()
            progress: Progress percentage (0-100)
            current: Current step number (optional)
            total: Total steps (optional)
            message: Progress message
            metadata: Additional metadata to merge
        """
        from services.progress_service import ProgressManager

        manager = ProgressManager()
        await manager.update_progress(
            operation_id,
            progress=progress,
            current=current,
            total=total,
            message=message,
            metadata=metadata
        )

        logger.debug(f"Updated progress {operation_id}: {progress}% - {message}")

    async def complete_progress_operation(
        self,
        operation_id: str,
        result: Optional[Dict[str, Any]] = None,
        message: str = "Completed"
    ):
        """
        Mark operation as completed (NEW RECOMMENDED WAY)

        Args:
            operation_id: Operation ID
            result: Final result data
            message: Completion message
        """
        from services.progress_service import ProgressManager

        manager = ProgressManager()
        await manager.complete_operation(operation_id, result=result, message=message)

        logger.info(f"Completed progress operation: {operation_id}")

    async def fail_progress_operation(
        self,
        operation_id: str,
        error: str,
        message: str = "Failed"
    ):
        """
        Mark operation as failed (NEW RECOMMENDED WAY)

        Args:
            operation_id: Operation ID
            error: Error message
            message: Failure message
        """
        from services.progress_service import ProgressManager

        manager = ProgressManager()
        await manager.fail_operation(operation_id, error=error, message=message)

        logger.error(f"Failed progress operation {operation_id}: {error}")

    # ============================================================================
    # REMOVED: Old Context-based Progress (use ProgressManager instead)
    # ============================================================================
    # All progress tracking now uses:
    #   1. create_progress_operation() -> returns operation_id
    #   2. update_progress_operation(operation_id, progress, message)
    #   3. complete_progress_operation(operation_id, result)
    # ============================================================================

    async def log_info(self, ctx: Optional[Context], message: str, **extra):
        """Log info message via Context or standard logging"""
        if ctx and MCP_SDK_AVAILABLE:
            try:
                await ctx.info(message, **extra)
            except Exception as e:
                logger.warning(f"Context logging failed: {e}")
        logger.info(message, extra=extra)

    async def log_debug(self, ctx: Optional[Context], message: str, **extra):
        """Log debug message via Context or standard logging"""
        if ctx and MCP_SDK_AVAILABLE:
            try:
                await ctx.debug(message, **extra)
            except Exception as e:
                logger.warning(f"Context logging failed: {e}")
        logger.debug(message, extra=extra)

    async def log_warning(self, ctx: Optional[Context], message: str, **extra):
        """Log warning message via Context or standard logging"""
        if ctx and MCP_SDK_AVAILABLE:
            try:
                await ctx.warning(message, **extra)
            except Exception as e:
                logger.warning(f"Context logging failed: {e}")
        logger.warning(message, extra=extra)

    async def log_error(self, ctx: Optional[Context], message: str, **extra):
        """Log error message via Context or standard logging"""
        if ctx and MCP_SDK_AVAILABLE:
            try:
                await ctx.error(message, **extra)
            except Exception as e:
                logger.error(f"Context logging failed: {e}")
        logger.error(message, extra=extra)

    async def elicit_user_input(
        self,
        ctx: Optional[Context],
        message: str,
        schema: Any,
        fallback_response: Optional[Any] = None
    ) -> Optional[Any]:
        """
        Request user input via MCP elicitation protocol

        Args:
            ctx: MCP Context
            message: Message to display to user
            schema: Pydantic model for expected input
            fallback_response: Response if elicitation not available

        Returns:
            User input data or fallback_response
        """
        if ctx and MCP_SDK_AVAILABLE:
            try:
                result = await ctx.elicit(message=message, schema=schema)

                if result.action == "accept":
                    return result.data
                elif result.action == "decline":
                    logger.info(f"User declined: {message}")
                    return None
                else:  # cancel
                    logger.info(f"User cancelled: {message}")
                    return None

            except Exception as e:
                logger.error(f"Elicitation failed: {e}")
                return fallback_response
        else:
            # Fallback: Use custom HIL response
            logger.warning(
                "MCP elicitation not available. "
                "Use custom HIL responses for this scenario."
            )
            return fallback_response

    # ============================================================================
    # Standard HIL (Human-in-Loop) Methods - Return Data Field Approach
    # ============================================================================

    def _create_hil_response(
        self,
        status: str,
        hil_type: str,
        question: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        options: Optional[List[str]] = None,
        timeout: int = 300,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Internal method to create standardized HIL response

        This ensures consistency across all HIL methods and alignment with Agent detection.

        Args:
            status: Agent-compatible status value
            hil_type: HIL interaction type for routing
            question: Short question for UI header
            message: Detailed message/instructions
            context: Additional context data
            options: User selection options
            timeout: Timeout in seconds
            data: Tool-specific data

        Returns:
            Standardized HIL response dict
        """
        response = {
            "status": status,
            "hil_type": hil_type,
            "hil_required": True,  # For Agent detection
            "action": "ask_human",
            "question": question,
            "message": message,
            "timeout": timeout,
            "timestamp": datetime.now().isoformat()
        }

        if context is not None:
            response["context"] = context

        if options is not None:
            response["options"] = options

        if data is not None:
            response["data"] = data

        return response

    def request_authorization(
        self,
        action: str,
        reason: str,
        risk_level: str = "high",
        context: Optional[Dict[str, Any]] = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Request user authorization to execute an operation

        Use this when a tool needs explicit approval before proceeding
        with an operation, especially for high-risk actions.

        Args:
            action: The action requiring authorization (e.g., "delete database", "process payment", "deploy to production")
            reason: Clear explanation of why this action is needed
            risk_level: Risk level of the operation ("low", "medium", "high", "critical")
            context: Additional context (amounts, targets, affected resources, etc.)
            timeout: Timeout in seconds (default: 300 = 5 minutes)

        Returns:
            Dict[str, Any]: HIL response to be returned by the tool

        Examples:
            ```python
            # High-risk: Payment
            return self.request_authorization(
                action="Process $5000 payment",
                reason="Complete vendor payment for invoice INV-123",
                risk_level="high",
                context={
                    "amount": 5000,
                    "currency": "USD",
                    "vendor": "Acme Corp",
                    "invoice_id": "INV-123"
                }
            )

            # Critical: Data deletion
            return self.request_authorization(
                action="Delete production database",
                reason="Remove deprecated customer data table",
                risk_level="critical",
                context={
                    "database": "prod_db",
                    "table": "old_customers",
                    "row_count": 50000,
                    "irreversible": True
                }
            )

            # Low-risk: Configuration change
            return self.request_authorization(
                action="Update cache TTL",
                reason="Improve performance by increasing cache duration",
                risk_level="low",
                context={"old_ttl": 300, "new_ttl": 600}
            )
            ```

        Response includes:
            - Options: ["approve", "reject"]
            - risk_level in context for UI highlighting
        """
        ctx = context or {}
        ctx["risk_level"] = risk_level

        return self._create_hil_response(
            status="authorization_requested",
            hil_type="authorization",
            question=f"Authorize: {action}",
            message=f"**Authorization Required ({risk_level.upper()} risk)**\n\n{reason}",
            context=ctx,
            options=["approve", "reject"],
            timeout=timeout,
            data={
                "request_type": "authorization",
                "action": action,
                "reason": reason,
                "risk_level": risk_level
            }
        )

    def request_input(
        self,
        input_type: str,
        prompt: str,
        description: str,
        schema: Optional[Dict[str, Any]] = None,
        current_data: Optional[Any] = None,
        suggestions: Optional[List[str]] = None,
        default_value: Optional[Any] = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Request user to provide information or augment existing data

        Use this when a tool needs information from the user, including:
        - Missing data (API keys, credentials, configuration)
        - Additional data to augment existing content
        - User preferences or selections

        Args:
            input_type: Type of input ("text", "credentials", "file", "selection", "augmentation")
            prompt: Short prompt for the input field
            description: Detailed description of what is needed
            schema: JSON schema for expected input format (optional)
            current_data: Existing data to augment (for augmentation type)
            suggestions: Suggested values or actions (optional)
            default_value: Default value to pre-fill (optional)
            timeout: Timeout in seconds (default: 300 = 5 minutes)

        Returns:
            Dict[str, Any]: HIL response to be returned by the tool

        Examples:
            ```python
            # Request API key
            return self.request_input(
                input_type="credentials",
                prompt="Enter OpenAI API Key",
                description="Provide your OpenAI API key to enable AI features",
                schema={
                    "type": "string",
                    "pattern": "^sk-[A-Za-z0-9]{48}$"
                }
            )

            # Request selection
            return self.request_input(
                input_type="selection",
                prompt="Choose deployment environment",
                description="Select the target environment for deployment",
                suggestions=["development", "staging", "production"]
            )

            # Request augmentation of existing data
            return self.request_input(
                input_type="augmentation",
                prompt="Add more requirements",
                description="The AI generated initial requirements. Please add any missing details or additional requirements.",
                current_data={"requirements": ["Feature A", "Feature B"]},
                suggestions=[
                    "Add error handling requirements",
                    "Specify performance requirements",
                    "Define security requirements"
                ]
            )
            ```

        Response includes:
            - Options: ["submit", "skip", "cancel"]
        """
        data = {
            "request_type": "input",
            "input_type": input_type,
            "prompt": prompt
        }

        if schema is not None:
            data["schema"] = schema

        if current_data is not None:
            data["current_data"] = current_data

        if suggestions is not None:
            data["suggestions"] = suggestions

        if default_value is not None:
            data["default_value"] = default_value

        context = {}
        if suggestions:
            context["has_suggestions"] = True
            context["suggestions"] = suggestions
        if current_data is not None:
            context["has_current_data"] = True

        return self._create_hil_response(
            status="human_input_requested",
            hil_type="input",
            question=prompt,
            message=description,
            context=context,
            options=["submit", "skip", "cancel"],
            timeout=timeout,
            data=data
        )

    def request_review(
        self,
        content: Any,
        content_type: str,
        instructions: str,
        editable: bool = True,
        timeout: int = 600
    ) -> Dict[str, Any]:
        """
        Request user to review and optionally edit content before approval

        Use this when a tool generates content that needs human review and
        possible editing before proceeding (e.g., execution plans, code, configurations).

        This is fundamentally an approval request with editing capability.

        Args:
            content: The content to review (can be string, dict, list)
            content_type: Type of content ("plan", "code", "config", "document", "query")
            instructions: Instructions for the reviewer
            editable: Whether user can edit the content (default: True)
            timeout: Timeout in seconds (default: 600 = 10 minutes)

        Returns:
            Dict[str, Any]: HIL response to be returned by the tool

        Examples:
            ```python
            # Review execution plan
            return self.request_review(
                content=execution_plan,
                content_type="execution_plan",
                instructions=(
                    "Review this execution plan before autonomous execution begins.\n"
                    "You can approve, edit tasks, or reject the plan."
                ),
                editable=True
            )

            # Review generated code
            return self.request_review(
                content=generated_code,
                content_type="code",
                instructions="Review the API endpoint code for security and best practices.",
                editable=True
            )

            # Review config (read-only)
            return self.request_review(
                content=current_config,
                content_type="config",
                instructions="Review current system configuration before applying changes.",
                editable=False
            )
            ```

        Response includes:
            - Options: ["approve", "edit", "reject"]
            - editable flag controls if editing is allowed
        """
        return self._create_hil_response(
            status="human_input_requested",
            hil_type="review",
            question=f"Review {content_type}",
            message=instructions,
            context={
                "content_type": content_type,
                "editable": editable,
                "content_length": len(str(content))
            },
            options=["approve", "edit", "reject"] if editable else ["approve", "reject"],
            timeout=timeout,
            data={
                "request_type": "review",
                "content_type": content_type,
                "content": content,
                "editable": editable
            }
        )

    def request_input_with_authorization(
        self,
        input_prompt: str,
        input_description: str,
        authorization_reason: str,
        input_type: str = "text",
        risk_level: str = "high",
        schema: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Request user to provide information AND authorize the action

        Use this for operations that need both user input and explicit authorization,
        such as configuring and deploying, or entering payment details and confirming.

        This combines input collection with authorization in a single step.

        Args:
            input_prompt: What input is needed
            input_description: Detailed description of the input
            authorization_reason: Why authorization is needed after input
            input_type: Type of input ("text", "credentials", "file", "number")
            risk_level: Risk level of the authorized action ("low", "medium", "high", "critical")
            schema: JSON schema for input validation (optional)
            context: Additional context (optional)
            timeout: Timeout in seconds (default: 300 = 5 minutes)

        Returns:
            Dict[str, Any]: HIL response to be returned by the tool

        Examples:
            ```python
            # Enter payment amount and authorize
            return self.request_input_with_authorization(
                input_prompt="Enter payment amount",
                input_description="Specify the amount to pay vendor Acme Corp",
                authorization_reason="Authorize payment transaction after entering amount",
                input_type="number",
                risk_level="high",
                schema={"type": "number", "minimum": 0, "maximum": 10000},
                context={"vendor": "Acme Corp", "invoice": "INV-123"}
            )

            # Configure deployment and authorize
            return self.request_input_with_authorization(
                input_prompt="Enter deployment configuration",
                input_description="Provide environment variables and settings for production deployment",
                authorization_reason="Authorize production deployment with provided configuration",
                input_type="text",
                risk_level="critical",
                context={"environment": "production", "service": "api-gateway"}
            )
            ```

        Response includes:
            - Options: ["approve_with_input", "cancel"]
            - Combined input + authorization flow
        """
        ctx = context or {}
        ctx["risk_level"] = risk_level
        ctx["requires_input"] = True

        return self._create_hil_response(
            status="authorization_requested",
            hil_type="input_with_authorization",
            question=f"{input_prompt} (requires authorization)",
            message=f"**Input Required with Authorization ({risk_level.upper()} risk)**\n\n{input_description}\n\n{authorization_reason}",
            context=ctx,
            options=["approve_with_input", "cancel"],
            timeout=timeout,
            data={
                "request_type": "input_with_authorization",
                "input_prompt": input_prompt,
                "input_type": input_type,
                "input_schema": schema,
                "authorization_reason": authorization_reason,
                "risk_level": risk_level
            }
        )

    async def with_timeout(
        self,
        coro: Callable,
        timeout_seconds: float,
        operation_name: str = "operation"
    ) -> Any:
        """
        Execute operation with timeout

        Args:
            coro: Coroutine to execute
            timeout_seconds: Timeout in seconds
            operation_name: Name for logging

        Returns:
            Result of coroutine

        Raises:
            asyncio.TimeoutError: If operation times out
        """
        try:
            async with asyncio.timeout(timeout_seconds):
                return await coro
        except asyncio.TimeoutError:
            logger.error(f"{operation_name} timed out after {timeout_seconds}s")
            raise

    @asynccontextmanager
    async def track_operation(self, operation_id: str):
        """
        Track and allow cancellation of long-running operations

        Usage:
            async with self.track_operation("my-op-123"):
                result = await long_operation()
        """
        task = asyncio.current_task()
        self._active_operations[operation_id] = task

        try:
            yield
        finally:
            self._active_operations.pop(operation_id, None)

    async def cancel_operation(self, operation_id: str) -> bool:
        """
        Cancel a tracked operation

        Args:
            operation_id: ID of operation to cancel

        Returns:
            True if operation was cancelled, False if not found
        """
        task = self._active_operations.get(operation_id)
        if task and not task.done():
            task.cancel()
            logger.info(f"Cancelled operation: {operation_id}")
            return True
        return False

    def rate_limit(
        self,
        calls: int,
        period: float,
        per_user: bool = False
    ):
        """
        Rate limiting decorator

        Args:
            calls: Number of calls allowed
            period: Time period in seconds
            per_user: Whether to apply limit per user_id

        Usage:
            @self.rate_limit(calls=100, period=3600)
            async def my_tool(self, user_id: str):
                ...
        """
        def decorator(func: Callable[P, T]) -> Callable[P, T]:
            @wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                # Try to import rate limiter
                try:
                    from aiolimiter import AsyncLimiter
                except ImportError:
                    logger.warning(
                        "aiolimiter not installed. Rate limiting disabled. "
                        "Install with: pip install aiolimiter"
                    )
                    return await func(*args, **kwargs)

                # Determine rate limit key
                if per_user:
                    user_id = kwargs.get('user_id', 'default')
                    limit_key = f"{func.__name__}:{user_id}"
                else:
                    limit_key = func.__name__

                # Get or create rate limiter
                if limit_key not in self._rate_limiters:
                    self._rate_limiters[limit_key] = AsyncLimiter(calls, period)

                limiter = self._rate_limiters[limit_key]

                # Apply rate limit
                async with limiter:
                    return await func(*args, **kwargs)

            return wrapper
        return decorator

    @asynccontextmanager
    async def resource_cleanup(self, *resources):
        """
        Ensure proper cleanup of resources

        Usage:
            async with self.resource_cleanup(conn, file_handle):
                # Use resources
                await process(conn, file_handle)
            # Resources automatically closed
        """
        try:
            yield
        finally:
            for resource in resources:
                try:
                    if hasattr(resource, 'close'):
                        if asyncio.iscoroutinefunction(resource.close):
                            await resource.close()
                        else:
                            resource.close()
                    elif hasattr(resource, '__aexit__'):
                        await resource.__aexit__(None, None, None)
                except Exception as e:
                    logger.error(f"Error closing resource: {e}")

    async def stream_response(
        self,
        ctx: Optional[Context],
        chunks: List[str],
        delay: float = 0.1
    ):
        """
        Stream response chunks to client (for LLM streaming)

        Args:
            ctx: MCP Context
            chunks: List of text chunks to stream
            delay: Delay between chunks (seconds)

        Usage:
            chunks = ["Hello", " ", "World", "!"]
            await self.stream_response(ctx, chunks, delay=0.05)
        """
        for i, chunk in enumerate(chunks):
            if ctx and MCP_SDK_AVAILABLE:
                # Use Context logging to simulate streaming
                await ctx.info(chunk, extra_data={"chunk": i + 1, "total": len(chunks)})
            else:
                logger.info(f"Stream chunk {i+1}/{len(chunks)}: {chunk}")

            if delay > 0:
                await asyncio.sleep(delay)

    async def stream_generator(
        self,
        ctx: Optional[Context],
        generator,
        report_interval: int = 10
    ):
        """
        Stream results from an async generator with progress reporting

        Args:
            ctx: MCP Context
            generator: Async generator yielding items
            report_interval: Report progress every N items

        Usage:
            async def data_generator():
                for i in range(100):
                    yield f"Item {i}"

            async for item in self.stream_generator(ctx, data_generator()):
                process(item)
        """
        count = 0
        async for item in generator:
            count += 1

            # Report progress periodically
            if count % report_interval == 0:
                await self.report_progress(
                    ctx,
                    progress=count,
                    total=count,  # Unknown total for generators
                    message=f"Processed {count} items"
                )

            yield item

    def create_response(
        self,
        status: str,
        action: str,
        data: Dict[str, Any],
        error_message: Optional[str] = None,
        error_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建统一格式的响应（返回可序列化的字典）

        注意：确保 data 中不包含 Context 或其他不可序列化对象。
        如果需要返回 Context 信息，使用 self.extract_context_info(ctx)。

        Args:
            status: 状态 ("success" or "error")
            action: 操作名称
            data: 响应数据（必须是可JSON序列化的）
            error_message: 错误消息（可选）
            error_code: 错误代码，用于客户端精确错误处理（可选）

        Returns:
            Dict[str, Any]: 可序列化的字典响应

        Example:
            # ✅ 正确用法
            return self.create_response(
                status="success",
                action="process_data",
                data={
                    "result": "processed",
                    "count": 42,
                    "context": self.extract_context_info(ctx)  # 提取 Context 信息
                }
            )

            # ✅ 错误处理（带错误代码）
            return self.create_response(
                status="error",
                action="get_task_progress",
                data={"operation_id": op_id},
                error_message="Operation not found",
                error_code="NOT_FOUND"
            )

            # ❌ 错误用法
            return self.create_response(
                status="success",
                action="bad_example",
                data={"ctx": ctx}  # 不要这样做！Context 不可序列化
            )
        """
        # Create simple response dict
        if status == "success":
            return {
                "status": "success",
                "action": action,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
        else:
            response = {
                "status": "error",
                "action": action,
                "error": error_message or "Unknown error",
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
            # Add error_code if provided
            if error_code:
                response["error_code"] = error_code
            return response
    
    def register_tool(
        self,
        mcp,
        func: Callable,
        security_level: Optional[SecurityLevel] = None,
        timeout: Optional[float] = None,
        rate_limit_calls: Optional[int] = None,
        rate_limit_period: Optional[float] = None,
        **kwargs
    ):
        """
        注册工具到MCP服务器 - Enhanced with MCP SDK features

        Args:
            mcp: MCP服务器实例
            func: 工具函数
            security_level: 安全级别 (LOW, MEDIUM, HIGH, CRITICAL)
            timeout: Optional timeout in seconds
            rate_limit_calls: Number of calls allowed per period
            rate_limit_period: Rate limit period in seconds
            **kwargs: 传递给@mcp.tool()的额外参数 (name, description, annotations, etc.)

        Example:
            # Register with security and rate limiting
            self.register_tool(
                mcp,
                my_tool,
                security_level=SecurityLevel.MEDIUM,
                timeout=30.0,
                rate_limit_calls=100,
                rate_limit_period=3600,
                structured_output=True
            )

            # Register with MCP ToolAnnotations
            from mcp.types import ToolAnnotations
            self.register_tool(
                mcp,
                read_only_tool,
                security_level=SecurityLevel.LOW,
                annotations=ToolAnnotations(
                    readOnlyHint=True,
                    idempotentHint=True
                )
            )
        """
        # CRITICAL FIX: Check if function needs Context injection
        # If it has a Context parameter, we MUST preserve the exact signature
        # so FastMCP can inject it properly
        import inspect
        sig = inspect.signature(func)

        # Check for Context parameter (handle Optional[Context] and Context)
        has_context_param = False
        for param_name, param in sig.parameters.items():
            param_type_str = str(param.annotation)
            if 'Context' in param_type_str:
                has_context_param = True
                logger.info(f"🎯 Tool '{func.__name__}' has Context parameter: {param_name}: {param_type_str}")
                break

        if not has_context_param:
            logger.debug(f"Tool '{func.__name__}' has NO Context parameter")

        if has_context_param:
            # For Context-aware tools, minimal wrapper that preserves signature
            # Don't use *args/**kwargs as it hides parameters from FastMCP
            async def execute_with_error_handling(**kwargs_only):
                try:
                    if timeout:
                        result = await self.with_timeout(
                            func(**kwargs_only),
                            timeout_seconds=timeout,
                            operation_name=func.__name__
                        )
                    else:
                        result = await func(**kwargs_only)

                    # Convert Pydantic models
                    if hasattr(result, 'model_dump'):
                        result = result.model_dump()
                    elif hasattr(result, 'dict'):
                        result = result.dict()

                    return result

                except asyncio.TimeoutError:
                    logger.error(f"{func.__name__} timed out after {timeout}s")
                    return {
                        "status": "error",
                        "action": func.__name__,
                        "error": f"Operation timed out after {timeout}s",
                        "error_code": "TIMEOUT",
                        "timestamp": datetime.now().isoformat()
                    }
                except Exception as e:
                    logger.error(f"{func.__name__} failed: {e}", exc_info=True)
                    return {
                        "status": "error",
                        "action": func.__name__,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }

            # Preserve original signature for FastMCP Context injection
            execute_with_error_handling.__signature__ = sig
            execute_with_error_handling.__annotations__ = func.__annotations__
            execute_with_error_handling.__name__ = func.__name__
            execute_with_error_handling.__doc__ = func.__doc__
            wrapped_func = execute_with_error_handling

        else:
            # For non-Context tools, use standard wrapper with *args/**kwargs
            @wraps(func)
            async def wrapped_func(*args, **kwargs):
                """Standard wrapper for non-Context tools"""
                try:
                    if timeout:
                        result = await self.with_timeout(
                            func(*args, **kwargs),
                            timeout_seconds=timeout,
                            operation_name=func.__name__
                        )
                    else:
                        result = await func(*args, **kwargs)

                    # Convert Pydantic models
                    if hasattr(result, 'model_dump'):
                        result = result.model_dump()
                    elif hasattr(result, 'dict'):
                        result = result.dict()

                    return result

                except asyncio.TimeoutError:
                    logger.error(f"{func.__name__} timed out after {timeout}s")
                    return {
                        "status": "error",
                        "action": func.__name__,
                        "error": f"Operation timed out after {timeout}s",
                        "error_code": "TIMEOUT",
                        "timestamp": datetime.now().isoformat()
                    }
                except Exception as e:
                    logger.error(f"{func.__name__} failed: {e}", exc_info=True)
                    return {
                        "status": "error",
                        "action": func.__name__,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }

        # Apply rate limiting if specified
        if rate_limit_calls and rate_limit_period:
            wrapped_func = self.rate_limit(
                calls=rate_limit_calls,
                period=rate_limit_period,
                per_user=True
            )(wrapped_func)
            logger.info(
                f"Applied rate limit to '{func.__name__}': "
                f"{rate_limit_calls} calls per {rate_limit_period}s"
            )

        # Apply security level if specified
        if security_level is not None:
            wrapped_func = self.security_manager.require_authorization(security_level)(wrapped_func)
            logger.info(f"Registered tool '{func.__name__}' with security level: {security_level.name}")
        else:
            wrapped_func = self.security_manager.security_check(wrapped_func)

        # CRITICAL FIX: Remove Context from type annotations to prevent serialization issues
        # FastMCP reads __annotations__ to generate schema, but Context type causes problems
        # This allows FastMCP to properly inject Context while avoiding serialization errors
        if hasattr(wrapped_func, '__annotations__'):
            from typing import Any
            clean_annotations = {}
            for param_name, param_type in wrapped_func.__annotations__.items():
                # Skip Context types entirely or replace with Any
                if 'Context' not in str(param_type):
                    clean_annotations[param_name] = param_type
                else:
                    # For Context parameters, use Any to avoid serialization but allow injection
                    clean_annotations[param_name] = Any

            wrapped_func.__annotations__ = clean_annotations
            if has_context_param:
                logger.info(f"🎯 Cleaned Context annotations for '{func.__name__}' to enable injection")

        # Register with MCP (use FastMCP defaults: structured_output=True)
        # FastMCP will automatically inject Context when ctx parameter is in signature
        # and handle serialization correctly as long as tools don't return Context
        tool_func = mcp.tool(**kwargs)(wrapped_func)

        # 记录注册的工具
        self.registered_tools.append(func.__name__)

        return tool_func
    
    def register_all_tools(self, mcp):
        """
        注册所有工具的模板方法
        子类应该重写这个方法来注册具体的工具
        """
        pass