"""
🔒 CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the current behavior of the BaseTool class.
If these tests fail, it means behavior has changed unexpectedly.

CRITICAL: BaseTool is the foundation for ALL tools in the system.
Changes here affect every tool implementation.

Service Under Test: tools/base_tool.py
"""
import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.base_tool
class TestBaseToolResponseCreationGolden:
    """
    Golden tests for create_response() - DO NOT MODIFY.

    This is the standard response format returned by all tools.
    """

    @pytest.fixture
    def base_tool(self):
        """Create BaseTool instance."""
        from tools.base_tool import BaseTool
        return BaseTool()

    def test_success_response_structure(self, base_tool):
        """
        CURRENT BEHAVIOR: Success response has specific structure.
        """
        response = base_tool.create_response(
            status="success",
            action="test_action",
            data={"result": "ok"}
        )

        assert response["status"] == "success"
        assert response["action"] == "test_action"
        assert response["data"] == {"result": "ok"}
        assert "timestamp" in response

    def test_success_response_keys(self, base_tool):
        """
        CURRENT BEHAVIOR: Success response has exactly these keys.
        """
        response = base_tool.create_response(
            status="success",
            action="test",
            data={}
        )

        expected_keys = {"status", "action", "data", "timestamp"}
        assert set(response.keys()) == expected_keys

    def test_error_response_structure(self, base_tool):
        """
        CURRENT BEHAVIOR: Error response includes error message.
        """
        response = base_tool.create_response(
            status="error",
            action="test_action",
            data={"context": "info"},
            error_message="Something went wrong"
        )

        assert response["status"] == "error"
        assert response["action"] == "test_action"
        assert response["error"] == "Something went wrong"
        assert response["data"] == {"context": "info"}
        assert "timestamp" in response

    def test_error_response_with_error_code(self, base_tool):
        """
        CURRENT BEHAVIOR: Error response can include error_code.
        """
        response = base_tool.create_response(
            status="error",
            action="test_action",
            data={},
            error_message="Not found",
            error_code="NOT_FOUND"
        )

        assert response["error_code"] == "NOT_FOUND"

    def test_error_response_default_message(self, base_tool):
        """
        CURRENT BEHAVIOR: Error without message defaults to "Unknown error".
        """
        response = base_tool.create_response(
            status="error",
            action="test",
            data={}
        )

        assert response["error"] == "Unknown error"

    def test_timestamp_is_iso_format(self, base_tool):
        """
        CURRENT BEHAVIOR: Timestamp is ISO 8601 format.
        """
        response = base_tool.create_response(
            status="success",
            action="test",
            data={}
        )

        # Should be parseable as datetime
        timestamp = response["timestamp"]
        parsed = datetime.fromisoformat(timestamp)
        assert isinstance(parsed, datetime)


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.base_tool
class TestBaseToolHILAuthorizationGolden:
    """
    Golden tests for request_authorization() HIL method - DO NOT MODIFY.

    Human-in-Loop authorization requests for high-risk operations.
    """

    @pytest.fixture
    def base_tool(self):
        """Create BaseTool instance."""
        from tools.base_tool import BaseTool
        return BaseTool()

    def test_authorization_response_structure(self, base_tool):
        """
        CURRENT BEHAVIOR: Authorization request has specific structure.
        """
        response = base_tool.request_authorization(
            action="Delete database",
            reason="Remove deprecated data",
            risk_level="high"
        )

        assert response["status"] == "authorization_requested"
        assert response["hil_type"] == "authorization"
        assert response["hil_required"] is True
        assert response["action"] == "ask_human"
        assert "question" in response
        assert "message" in response
        assert "timeout" in response
        assert "timestamp" in response

    def test_authorization_options(self, base_tool):
        """
        CURRENT BEHAVIOR: Authorization has approve/reject options.
        """
        response = base_tool.request_authorization(
            action="Test action",
            reason="Test reason"
        )

        assert response["options"] == ["approve", "reject"]

    def test_authorization_includes_risk_level_in_context(self, base_tool):
        """
        CURRENT BEHAVIOR: Risk level is included in context.
        """
        response = base_tool.request_authorization(
            action="Test",
            reason="Test",
            risk_level="critical"
        )

        assert response["context"]["risk_level"] == "critical"

    def test_authorization_data_structure(self, base_tool):
        """
        CURRENT BEHAVIOR: Data field contains authorization details.
        """
        response = base_tool.request_authorization(
            action="Delete files",
            reason="Cleanup",
            risk_level="high"
        )

        data = response["data"]
        assert data["request_type"] == "authorization"
        assert data["action"] == "Delete files"
        assert data["reason"] == "Cleanup"
        assert data["risk_level"] == "high"

    def test_authorization_default_risk_level(self, base_tool):
        """
        CURRENT BEHAVIOR: Default risk level is "high".
        """
        response = base_tool.request_authorization(
            action="Test",
            reason="Test"
        )

        assert response["data"]["risk_level"] == "high"

    def test_authorization_default_timeout(self, base_tool):
        """
        CURRENT BEHAVIOR: Default timeout is 300 seconds (5 minutes).
        """
        response = base_tool.request_authorization(
            action="Test",
            reason="Test"
        )

        assert response["timeout"] == 300


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.base_tool
class TestBaseToolHILInputGolden:
    """
    Golden tests for request_input() HIL method - DO NOT MODIFY.

    Human-in-Loop input requests for data collection.
    """

    @pytest.fixture
    def base_tool(self):
        """Create BaseTool instance."""
        from tools.base_tool import BaseTool
        return BaseTool()

    def test_input_response_structure(self, base_tool):
        """
        CURRENT BEHAVIOR: Input request has specific structure.
        """
        response = base_tool.request_input(
            input_type="text",
            prompt="Enter API key",
            description="Provide your API key"
        )

        assert response["status"] == "human_input_requested"
        assert response["hil_type"] == "input"
        assert response["hil_required"] is True

    def test_input_options(self, base_tool):
        """
        CURRENT BEHAVIOR: Input has submit/skip/cancel options.
        """
        response = base_tool.request_input(
            input_type="text",
            prompt="Test",
            description="Test"
        )

        assert response["options"] == ["submit", "skip", "cancel"]

    def test_input_data_structure(self, base_tool):
        """
        CURRENT BEHAVIOR: Data field contains input details.
        """
        response = base_tool.request_input(
            input_type="credentials",
            prompt="Enter password",
            description="Provide database password",
            schema={"type": "string", "minLength": 8}
        )

        data = response["data"]
        assert data["request_type"] == "input"
        assert data["input_type"] == "credentials"
        assert data["prompt"] == "Enter password"
        assert data["schema"] == {"type": "string", "minLength": 8}

    def test_input_with_suggestions(self, base_tool):
        """
        CURRENT BEHAVIOR: Suggestions are included in data and context.
        """
        response = base_tool.request_input(
            input_type="selection",
            prompt="Choose env",
            description="Select environment",
            suggestions=["dev", "staging", "prod"]
        )

        assert response["data"]["suggestions"] == ["dev", "staging", "prod"]
        assert response["context"]["has_suggestions"] is True

    def test_input_with_current_data(self, base_tool):
        """
        CURRENT BEHAVIOR: Current data is included for augmentation.
        """
        current = {"existing": "data"}
        response = base_tool.request_input(
            input_type="augmentation",
            prompt="Add more",
            description="Augment data",
            current_data=current
        )

        assert response["data"]["current_data"] == current
        assert response["context"]["has_current_data"] is True


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.base_tool
class TestBaseToolHILReviewGolden:
    """
    Golden tests for request_review() HIL method - DO NOT MODIFY.

    Human-in-Loop review requests for content approval/editing.
    """

    @pytest.fixture
    def base_tool(self):
        """Create BaseTool instance."""
        from tools.base_tool import BaseTool
        return BaseTool()

    def test_review_response_structure(self, base_tool):
        """
        CURRENT BEHAVIOR: Review request has specific structure.
        """
        response = base_tool.request_review(
            content={"plan": ["step1", "step2"]},
            content_type="execution_plan",
            instructions="Review this plan"
        )

        assert response["status"] == "human_input_requested"
        assert response["hil_type"] == "review"
        assert response["hil_required"] is True

    def test_review_editable_options(self, base_tool):
        """
        CURRENT BEHAVIOR: Editable review has approve/edit/reject options.
        """
        response = base_tool.request_review(
            content="code here",
            content_type="code",
            instructions="Review",
            editable=True
        )

        assert response["options"] == ["approve", "edit", "reject"]

    def test_review_readonly_options(self, base_tool):
        """
        CURRENT BEHAVIOR: Read-only review has approve/reject options only.
        """
        response = base_tool.request_review(
            content="config",
            content_type="config",
            instructions="Review",
            editable=False
        )

        assert response["options"] == ["approve", "reject"]

    def test_review_data_structure(self, base_tool):
        """
        CURRENT BEHAVIOR: Data field contains review details.
        """
        content = {"steps": [1, 2, 3]}
        response = base_tool.request_review(
            content=content,
            content_type="plan",
            instructions="Check this"
        )

        data = response["data"]
        assert data["request_type"] == "review"
        assert data["content_type"] == "plan"
        assert data["content"] == content
        assert data["editable"] is True  # default

    def test_review_default_timeout(self, base_tool):
        """
        CURRENT BEHAVIOR: Default timeout is 600 seconds (10 minutes).
        """
        response = base_tool.request_review(
            content="test",
            content_type="code",
            instructions="Review"
        )

        assert response["timeout"] == 600


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.base_tool
class TestBaseToolContextExtractionGolden:
    """
    Golden tests for extract_context_info() - DO NOT MODIFY.

    Safe extraction of Context metadata for serialization.
    """

    @pytest.fixture
    def base_tool(self):
        """Create BaseTool instance."""
        from tools.base_tool import BaseTool
        return BaseTool()

    def test_extract_none_context(self, base_tool):
        """
        CURRENT BEHAVIOR: None context returns default structure.
        """
        result = base_tool.extract_context_info(None)

        assert result["request_id"] is None
        assert result["client_id"] is None
        assert result["session_id"] is None
        assert "timestamp" in result

    def test_extract_context_returns_timestamp(self, base_tool):
        """
        CURRENT BEHAVIOR: Always includes timestamp.
        """
        result = base_tool.extract_context_info(None)

        # Should be ISO format
        timestamp = result["timestamp"]
        parsed = datetime.fromisoformat(timestamp)
        assert isinstance(parsed, datetime)

    def test_extract_context_expected_keys(self, base_tool):
        """
        CURRENT BEHAVIOR: Returns specific keys for None context.
        """
        result = base_tool.extract_context_info(None)

        expected_keys = {"request_id", "client_id", "session_id", "timestamp"}
        assert set(result.keys()) == expected_keys


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.base_tool
class TestBaseToolProgressTrackingGolden:
    """
    Golden tests for progress tracking methods - DO NOT MODIFY.

    ProgressManager-based progress tracking (recommended approach).
    """

    @pytest.fixture
    def base_tool(self):
        """Create BaseTool instance."""
        from tools.base_tool import BaseTool
        return BaseTool()

    def test_create_progress_operation_method_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has create_progress_operation method.
        """
        import inspect
        assert hasattr(base_tool, 'create_progress_operation')
        assert inspect.iscoroutinefunction(base_tool.create_progress_operation)

    def test_update_progress_operation_method_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has update_progress_operation method.
        """
        import inspect
        assert hasattr(base_tool, 'update_progress_operation')
        assert inspect.iscoroutinefunction(base_tool.update_progress_operation)

    def test_complete_progress_operation_method_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has complete_progress_operation method.
        """
        import inspect
        assert hasattr(base_tool, 'complete_progress_operation')
        assert inspect.iscoroutinefunction(base_tool.complete_progress_operation)

    def test_fail_progress_operation_method_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has fail_progress_operation method.
        """
        import inspect
        assert hasattr(base_tool, 'fail_progress_operation')
        assert inspect.iscoroutinefunction(base_tool.fail_progress_operation)

    def test_report_progress_method_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has backward-compatible report_progress method.
        """
        import inspect
        assert hasattr(base_tool, 'report_progress')
        assert inspect.iscoroutinefunction(base_tool.report_progress)


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.base_tool
class TestBaseToolLoggingMethodsGolden:
    """
    Golden tests for logging methods - DO NOT MODIFY.
    """

    @pytest.fixture
    def base_tool(self):
        """Create BaseTool instance."""
        from tools.base_tool import BaseTool
        return BaseTool()

    def test_log_info_method_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has log_info method.
        """
        import inspect
        assert hasattr(base_tool, 'log_info')
        assert inspect.iscoroutinefunction(base_tool.log_info)

    def test_log_debug_method_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has log_debug method.
        """
        import inspect
        assert hasattr(base_tool, 'log_debug')
        assert inspect.iscoroutinefunction(base_tool.log_debug)

    def test_log_warning_method_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has log_warning method.
        """
        import inspect
        assert hasattr(base_tool, 'log_warning')
        assert inspect.iscoroutinefunction(base_tool.log_warning)

    def test_log_error_method_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has log_error method.
        """
        import inspect
        assert hasattr(base_tool, 'log_error')
        assert inspect.iscoroutinefunction(base_tool.log_error)


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.base_tool
class TestBaseToolInitializationGolden:
    """
    Golden tests for BaseTool initialization - DO NOT MODIFY.
    """

    def test_init_sets_isa_client_none(self):
        """
        CURRENT BEHAVIOR: ISA client is None initially (lazy loading).
        """
        from tools.base_tool import BaseTool
        tool = BaseTool()

        assert tool._isa_client is None

    def test_init_creates_empty_registered_tools(self):
        """
        CURRENT BEHAVIOR: registered_tools starts as empty list.
        """
        from tools.base_tool import BaseTool
        tool = BaseTool()

        assert tool.registered_tools == []

    def test_init_creates_empty_rate_limiters(self):
        """
        CURRENT BEHAVIOR: Rate limiters dict starts empty.
        """
        from tools.base_tool import BaseTool
        tool = BaseTool()

        assert tool._rate_limiters == {}

    def test_init_creates_empty_active_operations(self):
        """
        CURRENT BEHAVIOR: Active operations dict starts empty.
        """
        from tools.base_tool import BaseTool
        tool = BaseTool()

        assert tool._active_operations == {}


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.base_tool
class TestBaseToolRegistrationGolden:
    """
    Golden tests for tool registration - DO NOT MODIFY.
    """

    @pytest.fixture
    def base_tool(self):
        """Create BaseTool instance."""
        from tools.base_tool import BaseTool
        return BaseTool()

    def test_register_tool_method_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has register_tool method.
        """
        assert hasattr(base_tool, 'register_tool')
        assert callable(base_tool.register_tool)

    def test_register_all_tools_method_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has register_all_tools template method.
        """
        assert hasattr(base_tool, 'register_all_tools')
        assert callable(base_tool.register_all_tools)

    def test_register_tool_signature(self, base_tool):
        """
        CURRENT BEHAVIOR: register_tool accepts specific parameters.
        """
        import inspect
        sig = inspect.signature(base_tool.register_tool)
        params = list(sig.parameters.keys())

        assert 'mcp' in params
        assert 'func' in params
        assert 'security_level' in params
        assert 'timeout' in params
        assert 'rate_limit_calls' in params
        assert 'rate_limit_period' in params


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.base_tool
class TestJsonSerializerGolden:
    """
    Golden tests for json_serializer function - DO NOT MODIFY.

    Custom serializer for MCP tool responses.
    """

    def test_serializes_datetime(self):
        """
        CURRENT BEHAVIOR: Converts datetime to ISO format string.
        """
        from tools.base_tool import json_serializer

        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = json_serializer(dt)

        assert result == "2024-01-15T10:30:00"

    def test_serializes_decimal(self):
        """
        CURRENT BEHAVIOR: Converts Decimal to float.
        """
        from tools.base_tool import json_serializer

        dec = Decimal("123.45")
        result = json_serializer(dec)

        assert result == 123.45
        assert isinstance(result, float)

    def test_handles_context_by_name(self):
        """
        CURRENT BEHAVIOR: Context objects return placeholder string.
        """
        from tools.base_tool import json_serializer

        # Create mock with Context class name
        mock_ctx = MagicMock()
        mock_ctx.__class__.__name__ = 'Context'

        result = json_serializer(mock_ctx)

        assert result == "<Context>"

    def test_serializes_object_with_dict(self):
        """
        CURRENT BEHAVIOR: Objects with __dict__ are serialized to dict.
        """
        from tools.base_tool import json_serializer

        class CustomType:
            def __init__(self):
                self.x = 1
                self.y = "test"

        result = json_serializer(CustomType())

        assert isinstance(result, dict)
        assert result == {"x": 1, "y": "test"}


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.base_tool
class TestBaseToolISAClientGolden:
    """
    Golden tests for ISA client integration - DO NOT MODIFY.
    """

    @pytest.fixture
    def base_tool(self):
        """Create BaseTool instance."""
        from tools.base_tool import BaseTool
        return BaseTool()

    def test_get_isa_client_method_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has async get_isa_client method.
        """
        import inspect
        assert hasattr(base_tool, 'get_isa_client')
        assert inspect.iscoroutinefunction(base_tool.get_isa_client)

    def test_call_isa_with_events_method_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has async call_isa_with_events method.
        """
        import inspect
        assert hasattr(base_tool, 'call_isa_with_events')
        assert inspect.iscoroutinefunction(base_tool.call_isa_with_events)

    def test_invoke_isa_model_method_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has async _invoke_isa_model adapter method.
        """
        import inspect
        assert hasattr(base_tool, '_invoke_isa_model')
        assert inspect.iscoroutinefunction(base_tool._invoke_isa_model)


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.base_tool
class TestBaseToolTimeoutAndCancellationGolden:
    """
    Golden tests for timeout and cancellation - DO NOT MODIFY.
    """

    @pytest.fixture
    def base_tool(self):
        """Create BaseTool instance."""
        from tools.base_tool import BaseTool
        return BaseTool()

    def test_with_timeout_method_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has async with_timeout method.
        """
        import inspect
        assert hasattr(base_tool, 'with_timeout')
        assert inspect.iscoroutinefunction(base_tool.with_timeout)

    def test_track_operation_method_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has async context manager track_operation.
        """
        import inspect
        assert hasattr(base_tool, 'track_operation')
        # It's an async context manager
        assert inspect.isasyncgenfunction(base_tool.track_operation.__wrapped__) or \
               hasattr(base_tool.track_operation, '__aenter__')

    def test_cancel_operation_method_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has async cancel_operation method.
        """
        import inspect
        assert hasattr(base_tool, 'cancel_operation')
        assert inspect.iscoroutinefunction(base_tool.cancel_operation)

    def test_rate_limit_decorator_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has rate_limit decorator factory.
        """
        assert hasattr(base_tool, 'rate_limit')
        assert callable(base_tool.rate_limit)


@pytest.mark.golden
@pytest.mark.unit
@pytest.mark.base_tool
class TestBaseToolStreamingGolden:
    """
    Golden tests for streaming methods - DO NOT MODIFY.
    """

    @pytest.fixture
    def base_tool(self):
        """Create BaseTool instance."""
        from tools.base_tool import BaseTool
        return BaseTool()

    def test_stream_response_method_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has async stream_response method.
        """
        import inspect
        assert hasattr(base_tool, 'stream_response')
        assert inspect.iscoroutinefunction(base_tool.stream_response)

    def test_stream_generator_method_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has async stream_generator method.
        """
        import inspect
        assert hasattr(base_tool, 'stream_generator')
        assert inspect.isasyncgenfunction(base_tool.stream_generator)

    def test_resource_cleanup_method_exists(self, base_tool):
        """
        CURRENT BEHAVIOR: Has async context manager resource_cleanup.
        """
        assert hasattr(base_tool, 'resource_cleanup')
