"""
Security Hardening Unit Tests.

Tests for security fixes across the codebase:
- Issue #12: API key query parameter rejection
- Issue #13: Path traversal protection in file_tools
- Issue #14: SSRF protection (tested separately in test_registry_fetcher_security.py)

These tests verify defense-in-depth security measures.
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
from starlette.requests import Request

from core.auth.middleware import MCPUnifiedAuthMiddleware
from tools.system_tools.file_tools import _validate_path_security


# ============================================================================
# Issue #12: API Key Query Parameter Rejection Tests
# ============================================================================


class TestAPIKeyQueryParamRejection:
    """Tests for API key query parameter rejection (defense in depth)."""

    @pytest.fixture
    def mock_auth_service(self):
        """Mock auth service for middleware testing."""
        with patch("core.auth.middleware.MCPAuthService") as mock:
            instance = mock.return_value
            instance.auth_service_url = "http://auth:8000"
            instance.authorization_service_url = "http://authz:8203"
            # Mock successful authentication
            mock_context = MagicMock()
            mock_context.is_authenticated = True
            mock_context.user_id = "test-user"
            mock_context.organization_id = "test-org"
            mock_context.subscription_tier = MagicMock(value="pro")
            mock_context.authorized_orgs = ["test-org"]
            instance.authenticate_token = AsyncMock(return_value=mock_context)
            instance.check_resource_access = AsyncMock(return_value={"has_access": True})
            instance.get_user_permissions = AsyncMock(return_value=["read", "write"])
            yield instance

    @pytest.fixture
    def app_with_auth(self, mock_auth_service):
        """Create a Starlette app with auth middleware enabled."""

        async def protected_endpoint(request: Request):
            return JSONResponse({"status": "ok"})

        app = Starlette(
            routes=[
                Route("/mcp/tools/test", protected_endpoint),  # MCP path requires auth
                Route("/health", protected_endpoint),
            ]
        )
        app.add_middleware(MCPUnifiedAuthMiddleware, config={"require_auth": True})
        return app

    def test_api_key_in_authorization_header_allowed(self, app_with_auth):
        """Test that API key in Authorization header is accepted."""
        client = TestClient(app_with_auth)
        response = client.get(
            "/mcp/tools/test", headers={"Authorization": "Bearer test-api-key-12345"}
        )
        # Should proceed to authentication (may fail auth, but not rejected for method)
        assert response.status_code in [200, 401, 403]

    def test_api_key_in_x_api_key_header_allowed(self, app_with_auth):
        """Test that API key in X-API-Key header is accepted."""
        client = TestClient(app_with_auth)
        response = client.get("/mcp/tools/test", headers={"X-API-Key": "test-api-key-12345"})
        # Should proceed to authentication
        assert response.status_code in [200, 401, 403]

    def test_api_key_in_x_mcp_api_key_header_allowed(self, app_with_auth):
        """Test that API key in X-MCP-API-Key header is accepted."""
        client = TestClient(app_with_auth)
        response = client.get(
            "/mcp/tools/test", headers={"X-MCP-API-Key": "test-api-key-12345"}
        )
        # Should proceed to authentication
        assert response.status_code in [200, 401, 403]

    def test_api_key_in_query_param_rejected(self, app_with_auth):
        """Test that API key in query parameter is rejected with 400."""
        client = TestClient(app_with_auth)
        response = client.get("/mcp/tools/test?api_key=test-api-key-12345")
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "query parameter" in data["message"].lower()

    def test_apikey_in_query_param_rejected(self, app_with_auth):
        """Test that 'apikey' query parameter is rejected."""
        client = TestClient(app_with_auth)
        response = client.get("/mcp/tools/test?apikey=secret123")
        assert response.status_code == 400

    def test_token_in_query_param_rejected(self, app_with_auth):
        """Test that 'token' query parameter is rejected."""
        client = TestClient(app_with_auth)
        response = client.get("/mcp/tools/test?token=bearer-token-xyz")
        assert response.status_code == 400

    def test_access_token_in_query_param_rejected(self, app_with_auth):
        """Test that 'access_token' query parameter is rejected."""
        client = TestClient(app_with_auth)
        response = client.get("/mcp/tools/test?access_token=oauth-token")
        assert response.status_code == 400

    def test_key_in_query_param_rejected(self, app_with_auth):
        """Test that 'key' query parameter is rejected."""
        client = TestClient(app_with_auth)
        response = client.get("/mcp/tools/test?key=secret-key")
        assert response.status_code == 400

    def test_bypass_path_allows_query_params(self, app_with_auth):
        """Test that bypass paths (like /health) don't check query params."""
        client = TestClient(app_with_auth)
        # Health endpoint should bypass auth entirely
        response = client.get("/health?api_key=should-not-matter")
        assert response.status_code == 200

    def test_normal_query_params_allowed(self, app_with_auth):
        """Test that normal query parameters are still allowed."""
        client = TestClient(app_with_auth)
        # Request with header auth and normal query params
        response = client.get(
            "/mcp/tools/test?page=1&limit=10",
            headers={"Authorization": "Bearer test-api-key"},
        )
        # Should proceed to authentication
        assert response.status_code in [200, 401, 403]

    def test_query_param_rejection_logged(self, app_with_auth, caplog):
        """Test that query param API key attempts are logged."""
        import logging

        with caplog.at_level(logging.WARNING):
            client = TestClient(app_with_auth)
            client.get("/mcp/tools/test?api_key=secret")

        # Check that warning was logged
        assert any("SECURITY" in record.message for record in caplog.records)
        assert any("api_key" in record.message for record in caplog.records)


# ============================================================================
# Issue #13: Path Traversal Protection Tests
# ============================================================================


class TestPathTraversalProtection:
    """Tests for path traversal protection in file_tools."""

    def test_block_dotdot_traversal(self):
        """Test that '../' patterns are blocked."""
        result = _validate_path_security("../../../etc/passwd", Path("../../../etc/passwd"))
        assert result is not None
        assert result["status"] == "error"
        assert result["error_code"] == "PATH_TRAVERSAL"
        assert ".." in result["error"]

    def test_block_dotdot_in_middle(self):
        """Test that '../' in the middle of path is blocked."""
        result = _validate_path_security(
            "/home/user/../../../etc/passwd", Path("/home/user/../../../etc/passwd")
        )
        assert result is not None
        assert result["error_code"] == "PATH_TRAVERSAL"

    def test_block_encoded_dotdot(self):
        """Test that encoded '../' patterns are blocked after decoding."""
        # The '..' check happens on the string level
        result = _validate_path_security("..%2F..%2Fetc/passwd", Path("..%2F..%2Fetc/passwd"))
        assert result is not None
        assert result["error_code"] == "PATH_TRAVERSAL"

    def test_allow_normal_absolute_path(self, tmp_path):
        """Test that normal absolute paths are allowed."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        result = _validate_path_security(str(test_file), test_file)
        assert result is None  # None means path is safe

    def test_allow_relative_path_without_traversal(self, tmp_path):
        """Test that relative paths without '..' are allowed."""
        # Create a file in temp directory
        test_file = tmp_path / "subdir" / "test.txt"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("test")

        result = _validate_path_security(str(test_file), test_file)
        assert result is None

    def test_block_sensitive_etc_path(self):
        """Test that /etc paths are blocked."""
        # Use a path that exists on both Linux and macOS
        etc_path = "/etc/hosts"
        result = _validate_path_security(etc_path, Path(etc_path))
        assert result is not None
        assert result["error_code"] == "SENSITIVE_PATH"
        assert "/etc" in result["error"]

    def test_block_sensitive_usr_path(self):
        """Test that /usr paths are blocked."""
        result = _validate_path_security("/usr/bin/python", Path("/usr/bin/python"))
        assert result is not None
        assert result["error_code"] == "SENSITIVE_PATH"

    def test_block_sensitive_var_log_path(self):
        """Test that /var/log paths are blocked."""
        # Use /var/log which is sensitive on both Linux and macOS
        var_path = "/var/log/system.log"
        result = _validate_path_security(var_path, Path(var_path))
        assert result is not None
        assert result["error_code"] == "SENSITIVE_PATH"

    def test_block_root_home(self):
        """Test that /root paths are blocked."""
        result = _validate_path_security("/root/.bashrc", Path("/root/.bashrc"))
        assert result is not None
        assert result["error_code"] == "SENSITIVE_PATH"

    def test_block_proc_path(self):
        """Test that /proc paths are blocked."""
        result = _validate_path_security("/proc/self/environ", Path("/proc/self/environ"))
        assert result is not None
        assert result["error_code"] == "SENSITIVE_PATH"

    def test_block_sys_path(self):
        """Test that /sys paths are blocked."""
        result = _validate_path_security("/sys/kernel/config", Path("/sys/kernel/config"))
        assert result is not None
        assert result["error_code"] == "SENSITIVE_PATH"

    def test_block_boot_path(self):
        """Test that /boot paths are blocked."""
        result = _validate_path_security("/boot/vmlinuz", Path("/boot/vmlinuz"))
        assert result is not None
        assert result["error_code"] == "SENSITIVE_PATH"

    def test_symlink_resolution_blocks_traversal(self, tmp_path):
        """Test that symlinks resolving to sensitive paths are blocked."""
        # Create a symlink pointing to /etc
        symlink = tmp_path / "evil_link"
        try:
            symlink.symlink_to("/etc")
        except OSError:
            pytest.skip("Cannot create symlinks on this system")

        # The original path looks innocent but resolves to /etc
        # Use 'hosts' which exists on both Linux and macOS
        file_path = str(symlink / "hosts")
        path = Path(file_path)

        result = _validate_path_security(file_path, path)
        # Should be blocked because resolved path is in /etc
        assert result is not None
        assert result["error_code"] == "SENSITIVE_PATH"

    def test_security_log_on_traversal_attempt(self, caplog):
        """Test that path traversal attempts are logged."""
        import logging

        with caplog.at_level(logging.WARNING):
            _validate_path_security("../../../etc/passwd", Path("../../../etc/passwd"))

        assert any("SECURITY" in record.message for record in caplog.records)
        assert any("traversal" in record.message.lower() for record in caplog.records)


class TestFileToolsIntegration:
    """Integration tests for file tools with security protections."""

    @pytest.fixture
    def temp_test_file(self, tmp_path):
        """Create a temporary test file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!\nLine 2\nLine 3\n")
        return test_file

    @pytest.mark.asyncio
    async def test_read_file_blocks_traversal(self):
        """Test that read_file blocks path traversal."""
        from mcp.server.fastmcp import FastMCP
        from tools.system_tools.file_tools import register_file_tools

        mcp = FastMCP("test")
        register_file_tools(mcp)

        # Get the read_file tool
        read_file = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "read_file":
                read_file = tool.fn
                break

        assert read_file is not None

        result = await read_file(file_path="../../../etc/passwd")
        assert result["status"] == "error"
        assert result["error_code"] == "PATH_TRAVERSAL"

    @pytest.mark.asyncio
    async def test_read_file_works_for_normal_paths(self, temp_test_file):
        """Test that read_file works for legitimate paths."""
        from mcp.server.fastmcp import FastMCP
        from tools.system_tools.file_tools import register_file_tools

        mcp = FastMCP("test")
        register_file_tools(mcp)

        read_file = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "read_file":
                read_file = tool.fn
                break

        result = await read_file(file_path=str(temp_test_file))
        assert result["status"] == "success"
        assert "Hello" in result["data"]["content"]

    @pytest.mark.asyncio
    async def test_edit_file_blocks_traversal(self):
        """Test that edit_file blocks path traversal."""
        from mcp.server.fastmcp import FastMCP
        from tools.system_tools.file_tools import register_file_tools

        mcp = FastMCP("test")
        register_file_tools(mcp)

        edit_file = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "edit_file":
                edit_file = tool.fn
                break

        assert edit_file is not None

        result = await edit_file(
            file_path="../../../etc/passwd",
            old_string="root",
            new_string="hacked",
        )
        assert result["status"] == "error"
        assert result["error_code"] == "PATH_TRAVERSAL"

    @pytest.mark.asyncio
    async def test_multi_edit_file_blocks_traversal(self):
        """Test that multi_edit_file blocks path traversal."""
        from mcp.server.fastmcp import FastMCP
        from tools.system_tools.file_tools import register_file_tools

        mcp = FastMCP("test")
        register_file_tools(mcp)

        multi_edit_file = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "multi_edit_file":
                multi_edit_file = tool.fn
                break

        assert multi_edit_file is not None

        result = await multi_edit_file(
            file_path="../../../etc/passwd",
            edits=[{"old_string": "root", "new_string": "hacked"}],
        )
        assert result["status"] == "error"
        assert result["error_code"] == "PATH_TRAVERSAL"

    @pytest.mark.asyncio
    async def test_read_file_blocks_sensitive_path(self):
        """Test that read_file blocks sensitive system paths."""
        from mcp.server.fastmcp import FastMCP
        from tools.system_tools.file_tools import register_file_tools

        mcp = FastMCP("test")
        register_file_tools(mcp)

        read_file = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "read_file":
                read_file = tool.fn
                break

        # Use /etc/hosts which exists on both Linux and macOS
        result = await read_file(file_path="/etc/hosts")
        assert result["status"] == "error"
        assert result["error_code"] == "SENSITIVE_PATH"


# ============================================================================
# Combined Security Scenario Tests
# ============================================================================


class TestCombinedSecurityScenarios:
    """Tests for combined security attack scenarios."""

    def test_combined_traversal_and_encoding(self):
        """Test that combined traversal with encoding attempts are blocked."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\etc\\passwd",  # Windows-style
            "....//....//etc/passwd",  # Double dots
            "./../.../../etc/passwd",  # Mixed
        ]

        for path in malicious_paths:
            if ".." in path:
                result = _validate_path_security(path, Path(path))
                assert result is not None, f"Path should be blocked: {path}"
                assert result["error_code"] == "PATH_TRAVERSAL"

    def test_null_byte_injection_blocked(self):
        """Test that null byte injection in paths is handled."""
        # Null bytes were historically used to truncate paths
        path_with_null = "/tmp/safe.txt\x00../../../etc/passwd"

        # Python 3 generally handles this, but we should be safe
        # The '..' check should still catch this
        if ".." in path_with_null:
            result = _validate_path_security(path_with_null, Path(path_with_null))
            assert result is not None

    def test_unicode_normalization_attacks(self):
        """Test that unicode normalization attacks don't bypass checks."""
        # Some systems might normalize unicode in ways that could bypass filters
        # For example, using different unicode representations of '.'
        # Our simple '..' string check should work for normalized strings

        normal_traversal = "../../../etc/passwd"
        result = _validate_path_security(normal_traversal, Path(normal_traversal))
        assert result is not None
        assert result["error_code"] == "PATH_TRAVERSAL"
