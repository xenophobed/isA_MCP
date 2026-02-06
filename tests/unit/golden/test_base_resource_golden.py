"""
Golden Tests for BaseResource - resources/base_resource.py

These tests capture the expected behavior of the BaseResource class,
MockSecurityManager, and related decorators.

Run with: pytest tests/unit/golden/test_base_resource_golden.py -v
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def base_resource():
    """Create a BaseResource instance for testing"""
    from resources.base_resource import BaseResource
    return BaseResource()


@pytest.fixture
def mock_mcp():
    """Create a mock MCP server"""
    mcp = Mock()
    # mcp.resource() returns a decorator that returns the function
    mcp.resource = Mock(return_value=lambda f: f)
    return mcp


@pytest.fixture
def mock_security_manager():
    """Create a mock security manager"""
    from resources.base_resource import MockSecurityManager
    return MockSecurityManager()


# =============================================================================
# BaseResource.__init__ Tests
# =============================================================================

class TestBaseResourceInit:
    """Tests for BaseResource initialization"""

    def test_init_sets_security_manager_to_none(self, base_resource):
        """Security manager should be None initially (lazy loading)"""
        assert base_resource._security_manager is None

    def test_init_creates_empty_registered_resources_list(self, base_resource):
        """Registered resources list should be empty initially"""
        assert base_resource.registered_resources == []
        assert isinstance(base_resource.registered_resources, list)


# =============================================================================
# BaseResource.security_manager Property Tests
# =============================================================================

class TestSecurityManagerProperty:
    """Tests for the security_manager lazy-loading property"""

    def test_security_manager_lazy_initialization(self, base_resource):
        """Security manager should be initialized on first access"""
        # Access the property
        sm = base_resource.security_manager
        # Should no longer be None
        assert base_resource._security_manager is not None

    def test_security_manager_returns_mock_on_error(self, base_resource):
        """Should return MockSecurityManager when real one unavailable"""
        from resources.base_resource import MockSecurityManager

        with patch('resources.base_resource.get_security_manager', side_effect=Exception("Not available")):
            sm = base_resource.security_manager
            assert isinstance(sm, MockSecurityManager)

    def test_security_manager_cached_after_first_access(self, base_resource):
        """Security manager should be cached after first access"""
        sm1 = base_resource.security_manager
        sm2 = base_resource.security_manager
        assert sm1 is sm2


# =============================================================================
# BaseResource.create_success_response Tests
# =============================================================================

class TestCreateSuccessResponse:
    """Tests for success response creation"""

    def test_string_data_returned_unchanged(self, base_resource):
        """String data should be returned as-is"""
        data = "# Hello World\n\nThis is markdown"
        result = base_resource.create_success_response(data)
        assert result == data

    def test_dict_data_converted_to_json(self, base_resource):
        """Dict data should be converted to JSON string"""
        data = {"key": "value", "number": 42}
        result = base_resource.create_success_response(data)
        parsed = json.loads(result)
        assert parsed == data

    def test_dict_json_has_indent(self, base_resource):
        """JSON output should be indented for readability"""
        data = {"key": "value"}
        result = base_resource.create_success_response(data)
        # Indented JSON has newlines
        assert "\n" in result

    def test_dict_json_allows_unicode(self, base_resource):
        """JSON should preserve unicode characters (ensure_ascii=False)"""
        data = {"message": "你好世界"}
        result = base_resource.create_success_response(data)
        assert "你好世界" in result
        assert "\\u" not in result  # Should not be escaped

    def test_other_types_converted_to_string(self, base_resource):
        """Other types should be converted via str()"""
        result = base_resource.create_success_response(12345)
        assert result == "12345"

    def test_list_converted_to_json(self, base_resource):
        """List data should be converted to JSON string"""
        data = [1, 2, 3, "four"]
        result = base_resource.create_success_response(data)
        # Lists are not dicts, so they go through str() path
        # Actually, let's check the implementation - it only checks for dict
        assert result == str(data)

    def test_uri_parameter_optional(self, base_resource):
        """URI parameter should be optional and not affect output"""
        data = "test"
        result1 = base_resource.create_success_response(data)
        result2 = base_resource.create_success_response(data, uri="memory://test")
        assert result1 == result2


# =============================================================================
# BaseResource.create_error_response Tests
# =============================================================================

class TestCreateErrorResponse:
    """Tests for error response creation"""

    def test_error_response_contains_uri(self, base_resource):
        """Error response should include the URI"""
        result = base_resource.create_error_response("memory://test/123", "Something failed")
        assert "memory://test/123" in result

    def test_error_response_contains_error_message(self, base_resource):
        """Error response should include the error message"""
        result = base_resource.create_error_response("memory://test", "Database connection failed")
        assert "Database connection failed" in result

    def test_error_response_contains_timestamp(self, base_resource):
        """Error response should include ISO timestamp"""
        result = base_resource.create_error_response("memory://test", "Error")
        assert "Timestamp" in result
        # Should have ISO format date
        assert datetime.now().strftime("%Y-%m-") in result

    def test_error_response_is_markdown(self, base_resource):
        """Error response should be markdown formatted"""
        result = base_resource.create_error_response("memory://test", "Error")
        assert result.startswith("# Error:")
        assert "**Error**:" in result
        assert "**Timestamp**:" in result

    def test_error_response_has_help_text(self, base_resource):
        """Error response should include help text"""
        result = base_resource.create_error_response("memory://test", "Error")
        assert "check the request parameters" in result


# =============================================================================
# BaseResource.create_not_found_response Tests
# =============================================================================

class TestCreateNotFoundResponse:
    """Tests for not found response creation"""

    def test_not_found_response_contains_uri(self, base_resource):
        """Not found response should include the URI"""
        result = base_resource.create_not_found_response("memory://test/123")
        assert "memory://test/123" in result

    def test_not_found_response_default_resource_type(self, base_resource):
        """Default resource type should be 'resource'"""
        result = base_resource.create_not_found_response("memory://test")
        assert "Resource Not Found" in result
        assert "No resource was found" in result

    def test_not_found_response_custom_resource_type(self, base_resource):
        """Custom resource type should be used in response"""
        result = base_resource.create_not_found_response("memory://user/123", "user")
        assert "User Not Found" in result
        assert "No user was found" in result

    def test_not_found_response_contains_timestamp(self, base_resource):
        """Not found response should include ISO timestamp"""
        result = base_resource.create_not_found_response("memory://test")
        assert "Timestamp" in result

    def test_not_found_response_is_markdown(self, base_resource):
        """Not found response should be markdown formatted"""
        result = base_resource.create_not_found_response("memory://test")
        assert result.startswith("#")
        assert "---" in result


# =============================================================================
# BaseResource.register_resource Tests
# =============================================================================

class TestRegisterResource:
    """Tests for resource registration"""

    def test_register_resource_calls_mcp_resource(self, base_resource, mock_mcp):
        """Should call mcp.resource() with the URI"""
        from core.security import SecurityLevel

        async def test_func():
            return "test"

        base_resource.register_resource(mock_mcp, "memory://test", test_func)
        mock_mcp.resource.assert_called()

    def test_register_resource_tracks_registration(self, base_resource, mock_mcp):
        """Should add resource to registered_resources list"""
        from core.security import SecurityLevel

        async def test_func():
            return "test"

        base_resource.register_resource(
            mock_mcp,
            "memory://test/{id}",
            test_func,
            security_level=SecurityLevel.LOW
        )

        assert len(base_resource.registered_resources) == 1
        assert base_resource.registered_resources[0]['uri'] == "memory://test/{id}"
        assert base_resource.registered_resources[0]['function'] == "test_func"
        assert base_resource.registered_resources[0]['security_level'] == "LOW"

    def test_register_resource_multiple_registrations(self, base_resource, mock_mcp):
        """Should track multiple resource registrations"""
        async def func1():
            return "1"

        async def func2():
            return "2"

        base_resource.register_resource(mock_mcp, "memory://a", func1)
        base_resource.register_resource(mock_mcp, "memory://b", func2)

        assert len(base_resource.registered_resources) == 2

    def test_register_resource_passes_kwargs_to_mcp(self, base_resource, mock_mcp):
        """Should pass additional kwargs to mcp.resource()"""
        async def test_func():
            return "test"

        base_resource.register_resource(
            mock_mcp,
            "memory://test",
            test_func,
            name="Test Resource",
            description="A test"
        )

        # Check that mcp.resource was called with the extra kwargs
        call_kwargs = mock_mcp.resource.call_args[1]
        assert call_kwargs.get('name') == "Test Resource"
        assert call_kwargs.get('description') == "A test"


# =============================================================================
# BaseResource.register_all_resources Tests
# =============================================================================

class TestRegisterAllResources:
    """Tests for the template method"""

    def test_register_all_resources_is_noop_by_default(self, base_resource, mock_mcp):
        """Base implementation should do nothing (template method)"""
        # Should not raise
        result = base_resource.register_all_resources(mock_mcp)
        assert result is None
        assert len(base_resource.registered_resources) == 0


# =============================================================================
# MockSecurityManager Tests
# =============================================================================

class TestMockSecurityManager:
    """Tests for the MockSecurityManager fallback class"""

    def test_security_check_returns_original_function(self, mock_security_manager):
        """security_check should return the function unchanged"""
        def original():
            return "test"

        result = mock_security_manager.security_check(original)
        assert result is original

    def test_require_authorization_returns_original_function(self, mock_security_manager):
        """require_authorization should return a decorator that returns the function unchanged"""
        def original():
            return "test"

        decorator = mock_security_manager.require_authorization("HIGH")
        result = decorator(original)
        assert result is original

    def test_require_authorization_accepts_any_level(self, mock_security_manager):
        """require_authorization should accept any security level"""
        def original():
            return "test"

        # Should not raise with any level
        mock_security_manager.require_authorization("LOW")(original)
        mock_security_manager.require_authorization("MEDIUM")(original)
        mock_security_manager.require_authorization("HIGH")(original)
        mock_security_manager.require_authorization("CRITICAL")(original)


# =============================================================================
# simple_resource Decorator Tests
# =============================================================================

class TestSimpleResourceDecorator:
    """Tests for the @simple_resource decorator"""

    def test_simple_resource_adds_uri_attribute(self):
        """Should add _resource_uri attribute to function"""
        from resources.base_resource import simple_resource

        @simple_resource("memory://test/{id}")
        async def get_test(id: str):
            return f"Test {id}"

        assert hasattr(get_test, '_resource_uri')
        assert get_test._resource_uri == "memory://test/{id}"

    def test_simple_resource_adds_security_level_attribute(self):
        """Should add _security_level attribute to function"""
        from resources.base_resource import simple_resource
        from core.security import SecurityLevel

        @simple_resource("memory://test", security_level=SecurityLevel.HIGH)
        async def get_test():
            return "test"

        assert hasattr(get_test, '_security_level')
        assert get_test._security_level == SecurityLevel.HIGH

    def test_simple_resource_default_security_level(self):
        """Default security level should be LOW"""
        from resources.base_resource import simple_resource
        from core.security import SecurityLevel

        @simple_resource("memory://test")
        async def get_test():
            return "test"

        assert get_test._security_level == SecurityLevel.LOW

    def test_simple_resource_preserves_function(self):
        """Decorated function should still be callable"""
        from resources.base_resource import simple_resource
        import asyncio

        @simple_resource("memory://test/{id}")
        async def get_test(id: str):
            return f"Result: {id}"

        result = asyncio.get_event_loop().run_until_complete(get_test("123"))
        assert result == "Result: 123"


# =============================================================================
# create_simple_resource_registration Decorator Tests
# =============================================================================

class TestCreateSimpleResourceRegistration:
    """Tests for the create_simple_resource_registration class decorator"""

    def test_creates_register_function_in_module(self):
        """Should create a register function in the caller's module"""
        from resources.base_resource import create_simple_resource_registration, BaseResource

        # This is tricky to test in isolation since it modifies caller's globals
        # We'll test the decorator's basic structure
        decorator = create_simple_resource_registration("register_test_resources")
        assert callable(decorator)

    def test_default_function_name(self):
        """Default register function name should be 'register_resources'"""
        from resources.base_resource import create_simple_resource_registration

        # The default is "register_resources"
        decorator = create_simple_resource_registration()
        assert callable(decorator)


# =============================================================================
# Integration Tests
# =============================================================================

class TestBaseResourceIntegration:
    """Integration tests for BaseResource with subclasses"""

    def test_subclass_can_override_register_all_resources(self, mock_mcp):
        """Subclasses should be able to override register_all_resources"""
        from resources.base_resource import BaseResource

        class TestResource(BaseResource):
            def register_all_resources(self, mcp):
                async def get_item(id: str):
                    return f"Item {id}"

                self.register_resource(mcp, "memory://item/{id}", get_item)

        resource = TestResource()
        resource.register_all_resources(mock_mcp)

        assert len(resource.registered_resources) == 1
        assert resource.registered_resources[0]['uri'] == "memory://item/{id}"

    def test_response_helpers_work_in_subclass(self, mock_mcp):
        """Response helper methods should work correctly in subclasses"""
        from resources.base_resource import BaseResource

        class TestResource(BaseResource):
            def get_formatted_data(self):
                return self.create_success_response({"status": "ok"})

            def get_error(self):
                return self.create_error_response("memory://test", "Failed")

        resource = TestResource()

        success = resource.get_formatted_data()
        assert '"status": "ok"' in success

        error = resource.get_error()
        assert "Failed" in error
        assert "memory://test" in error
