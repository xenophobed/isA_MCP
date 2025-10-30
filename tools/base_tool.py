"""
Base Tool Class for ISA MCP Tools
Unified handling of ISA client calls, billing event publishing, and tool registration

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
    Base tool class for event-driven architecture with MCP SDK integration

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
            from core.clients.model_client import get_isa_client
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

    def extract_context_info(
        self,
        ctx: Optional[Context],
        user_id: Optional[str] = None,
        request_headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Extract serializable information from Context with centralized session service integration

        **Session Management Strategy** (Best Practice):
        Since MCP Context session_id/client_id may be None (known FastMCP limitation #956),
        we implement multi-source session tracking:

        Priority for session_id:
        1. MCP Context (if available from FastMCP)
        2. Request headers X-Session-Id (from isA_Agent SessionService)
        3. Generate correlation_id for fallback tracking

        Args:
            ctx: MCP Context (optional, auto-injected by FastMCP)
            user_id: Application-level user identifier (from tool parameters)
            request_headers: HTTP request headers (for X-Session-Id, X-Client-Id, X-User-Id)

        Returns:
            Dict[str, Any]: Enhanced serializable Context information

        Example:
            @mcp.tool()
            async def my_tool(user_id: str, data: str, ctx: Context) -> dict:
                # Extract Context with user_id and headers
                context_info = self.extract_context_info(ctx, user_id)

                # Return business data + Context metadata
                return {
                    "result": process(data),
                    "context": context_info
                }
        """
        import uuid

        timestamp = datetime.now().isoformat()
        request_headers = request_headers or {}

        if not ctx:
            # No MCP Context - use headers or generate fallback
            return {
                "request_id": None,
                "session_id": request_headers.get("X-Session-Id"),
                "client_id": request_headers.get("X-Client-Id") or "unknown",
                "user_id": user_id or request_headers.get("X-User-Id"),
                "correlation_id": request_headers.get("X-Session-Id") or str(uuid.uuid4()),
                "timestamp": timestamp,
                "tracking_source": "headers" if request_headers.get("X-Session-Id") else "generated"
            }

        # Extract MCP Context properties
        info = {
            "timestamp": timestamp,
            "user_id": user_id or request_headers.get("X-User-Id")
        }

        # Extract request_id (primary MCP tracking - always available)
        try:
            request_id = getattr(ctx, "request_id", None)
            info["request_id"] = request_id
        except Exception as e:
            logger.debug(f"Failed to extract request_id: {e}")
            info["request_id"] = None

        # Extract client_id (may be None - use headers as fallback)
        try:
            mcp_client_id = getattr(ctx, "client_id", None)
            info["client_id"] = mcp_client_id or request_headers.get("X-Client-Id") or "unknown"
        except Exception as e:
            logger.debug(f"Failed to extract client_id: {e}")
            info["client_id"] = request_headers.get("X-Client-Id") or "unknown"

        # Extract session_id (may be None - known FastMCP issue #956)
        # Fallback to headers from isA_Agent SessionService
        try:
            mcp_session_id = getattr(ctx, "session_id", None)
            header_session_id = request_headers.get("X-Session-Id")

            # Use best available session_id
            info["session_id"] = mcp_session_id or header_session_id
            info["tracking_source"] = "mcp" if mcp_session_id else ("headers" if header_session_id else "none")
        except Exception as e:
            logger.debug(f"Failed to extract session_id: {e}")
            info["session_id"] = request_headers.get("X-Session-Id")
            info["tracking_source"] = "headers" if info["session_id"] else "none"

        # Generate correlation_id for application-level session tracking
        if info.get("session_id"):
            info["correlation_id"] = info["session_id"]
        elif info.get("request_id") and user_id:
            info["correlation_id"] = f"{user_id}_{info['request_id']}"
        else:
            info["correlation_id"] = str(uuid.uuid4())

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
    # MCP SDK Enhanced Features
    # ============================================================================

    async def report_progress(
        self,
        ctx: Optional[Context],
        progress: int,
        total: int,
        message: str = ""
    ):
        """
        Report progress to client via MCP Context

        Args:
            ctx: MCP Context (if available)
            progress: Current progress value
            total: Total steps
            message: Optional progress message
        """
        if ctx and MCP_SDK_AVAILABLE:
            try:
                await ctx.report_progress(
                    progress=progress,
                    total=total,
                    message=message
                )
            except Exception as e:
                logger.warning(f"Failed to report progress: {e}")
        else:
            # Fallback: Log progress
            percentage = (progress / total * 100) if total > 0 else 0
            logger.info(f"Progress: {progress}/{total} ({percentage:.1f}%) - {message}")

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
        error_message: Optional[str] = None
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
            return {
                "status": "error",
                "action": action,
                "error": error_message or "Unknown error",
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
    
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
        # Build wrapper chain: timeout -> security -> error handling
        # Use @wraps to preserve function signature, but we'll clean Context type hints later
        @wraps(func)
        async def wrapped_func(*args, **kwargs):
            """
            Simplified wrapper that trusts the tool implementation

            Context is automatically injected by FastMCP and should ONLY be used
            for operations (logging, progress, resources, etc.), never returned.
            """
            try:
                # CRITICAL: Extract and remove ctx BEFORE calling function
                # This prevents FastMCP from trying to serialize it later
                ctx = kwargs.pop('ctx', None)

                # Re-add ctx only for function call
                func_kwargs = kwargs.copy()
                if ctx is not None:
                    func_kwargs['ctx'] = ctx

                # Apply timeout if specified
                if timeout:
                    result = await self.with_timeout(
                        func(*args, **func_kwargs),
                        timeout_seconds=timeout,
                        operation_name=func.__name__
                    )
                else:
                    result = await func(*args, **func_kwargs)

                # CRITICAL: Explicitly delete all Context references
                ctx = None
                func_kwargs = None

                # Convert Pydantic models to dict (FastMCP handles serialization)
                if hasattr(result, 'model_dump'):
                    # Pydantic v2
                    result = result.model_dump()
                elif hasattr(result, 'dict'):
                    # Pydantic v1
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

        # CRITICAL: Remove Context from type annotations to prevent serialization
        # FastMCP reads __annotations__ to generate schema, but Context type causes serialization issues
        if hasattr(wrapped_func, '__annotations__'):
            # Create a clean copy of annotations without Context types
            clean_annotations = {}
            for param_name, param_type in wrapped_func.__annotations__.items():
                # Skip Context types entirely
                if 'Context' not in str(param_type):
                    clean_annotations[param_name] = param_type
                # For ctx parameter, use Any instead of Context
                elif param_name == 'ctx':
                    from typing import Any
                    clean_annotations[param_name] = Any

            wrapped_func.__annotations__ = clean_annotations
            logger.debug(f"Cleaned Context from annotations for '{func.__name__}'")

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

        # IMPORTANT: Use structured_output=False to work around FastMCP Context serialization issue
        #
        # Issue: FastMCP with structured_output=True attempts to serialize the entire execution
        # context when handling tool responses, which includes the Context object that is not
        # JSON serializable.
        #
        # Workaround: structured_output=False tells FastMCP to treat the return value as plain
        # data without attempting to serialize the execution context. FastMCP will still:
        # - Inject Context automatically when ctx parameter exists in signature
        # - Handle all Context operations (logging, progress, etc.) correctly
        # - Serialize the tool's return value normally
        #
        # Tool implementation responsibility:
        # - Use self.extract_context_info(ctx) to extract serializable Context metadata
        # - Never return the Context object directly in tool responses
        # - Always return JSON-serializable data (dict, list, str, int, float, bool)
        #
        # This setting can be overridden by passing structured_output=True explicitly in kwargs
        if 'structured_output' not in kwargs:
            kwargs['structured_output'] = False
            logger.debug(
                f"Using structured_output=False for '{func.__name__}' "
                f"(workaround for FastMCP Context serialization)"
            )

        # Register with MCP
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