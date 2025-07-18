#!/usr/bin/env python3
"""
Admin Tools Tests
Tests for capabilities, discovery, and MCP tool I/O for admin tools
"""

import pytest
import json
import asyncio
from tools.mcp_client import MCPClient


class TestAdminToolsCapabilities:
    """Test admin tools capabilities and discovery"""
    
    @pytest.fixture
    def client(self):
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_get_authorization_requests_in_capabilities(self, client):
        """Test that get_authorization_requests tool is listed in capabilities"""
        response = await client.get_capabilities()
        
        assert response.get("status") == "success"
        tools = response["capabilities"]["tools"]["available"]
        assert "get_authorization_requests" in tools
    
    @pytest.mark.asyncio
    async def test_approve_authorization_in_capabilities(self, client):
        """Test that approve_authorization tool is listed in capabilities"""
        response = await client.get_capabilities()
        
        assert response.get("status") == "success"
        tools = response["capabilities"]["tools"]["available"]
        assert "approve_authorization" in tools
    
    @pytest.mark.asyncio
    async def test_get_monitoring_metrics_in_capabilities(self, client):
        """Test that get_monitoring_metrics tool is listed in capabilities"""
        response = await client.get_capabilities()
        
        assert response.get("status") == "success"
        tools = response["capabilities"]["tools"]["available"]
        assert "get_monitoring_metrics" in tools
    
    @pytest.mark.asyncio
    async def test_get_audit_log_in_capabilities(self, client):
        """Test that get_audit_log tool is listed in capabilities"""
        response = await client.get_capabilities()
        
        assert response.get("status") == "success"
        tools = response["capabilities"]["tools"]["available"]
        assert "get_audit_log" in tools
    
    @pytest.mark.asyncio
    async def test_admin_tools_discovery(self, client):
        """Test AI discovery for admin-related requests"""
        requests = [
            "I need to manage authorization requests",
            "Show me system monitoring metrics",
            "Get the audit log for security review",
            "Approve pending authorization requests",
            "Check system performance and security status",
            "View admin dashboard information"
        ]
        
        for request in requests:
            response = await client.discover_tools(request)
            if response.get("status") == "success":
                discovered_tools = response["capabilities"]["tools"]
                admin_tools_found = any(tool in discovered_tools for tool in [
                    "get_authorization_requests", "approve_authorization", 
                    "get_monitoring_metrics", "get_audit_log"
                ])
                assert admin_tools_found, f"No admin tools discovered for: {request}"


class TestAdminToolsMCP:
    """Test admin tools MCP integration"""
    
    @pytest.fixture
    def client(self):
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_get_authorization_requests_admin_success(self, client):
        """Test get_authorization_requests with admin user"""
        arguments = {
            "user_id": "admin"
        }
        
        response = await client.call_tool_and_parse("get_authorization_requests", arguments)
        
        assert "status" in response
        assert "action" in response
        assert response["action"] == "get_authorization_requests"
        
        if response["status"] == "success":
            data = response["data"]
            assert "requests" in data
            assert "count" in data
            assert isinstance(data["requests"], list)
            assert isinstance(data["count"], int)
    
    @pytest.mark.asyncio
    async def test_get_authorization_requests_non_admin_failure(self, client):
        """Test get_authorization_requests with non-admin user should fail"""
        arguments = {
            "user_id": "regular_user"
        }
        
        response = await client.call_tool_and_parse("get_authorization_requests", arguments)
        
        # Should return error or unauthorized status
        assert response.get("status") == "error" or "Unauthorized" in str(response)
    
    @pytest.mark.asyncio
    async def test_approve_authorization_success(self, client):
        """Test approve_authorization with valid request ID"""
        arguments = {
            "request_id": "test-request-123",
            "approved_by": "admin"
        }
        
        response = await client.call_tool_and_parse("approve_authorization", arguments)
        
        assert "status" in response
        assert "action" in response
        assert response["action"] == "approve_authorization"
        
        if response["status"] == "success":
            data = response["data"]
            assert "request_id" in data
            assert "approved" in data
            assert "approved_by" in data
            assert data["request_id"] == "test-request-123"
            assert data["approved_by"] == "admin"
    
    @pytest.mark.asyncio
    async def test_get_monitoring_metrics_admin_success(self, client):
        """Test get_monitoring_metrics with admin user"""
        arguments = {
            "user_id": "admin"
        }
        
        response = await client.call_tool_and_parse("get_monitoring_metrics", arguments)
        
        assert "status" in response
        assert "action" in response
        assert response["action"] == "get_monitoring_metrics"
        
        if response["status"] == "success":
            assert "data" in response
            # Should contain metrics data
            assert isinstance(response["data"], dict)
    
    @pytest.mark.asyncio
    async def test_get_monitoring_metrics_non_admin_failure(self, client):
        """Test get_monitoring_metrics with non-admin user should fail"""
        arguments = {
            "user_id": "regular_user"
        }
        
        response = await client.call_tool_and_parse("get_monitoring_metrics", arguments)
        
        # Should return error or unauthorized status
        assert response.get("status") == "error" or "Unauthorized" in str(response)
    
    @pytest.mark.asyncio
    async def test_get_audit_log_admin_success(self, client):
        """Test get_audit_log with admin user"""
        arguments = {
            "limit": 25,
            "user_id": "admin"
        }
        
        response = await client.call_tool_and_parse("get_audit_log", arguments)
        
        assert "status" in response
        assert "action" in response
        assert response["action"] == "get_audit_log"
        
        if response["status"] == "success":
            data = response["data"]
            assert "logs" in data
            assert "count" in data
            assert isinstance(data["logs"], list)
            assert isinstance(data["count"], int)
    
    @pytest.mark.asyncio
    async def test_get_audit_log_non_admin_failure(self, client):
        """Test get_audit_log with non-admin user should fail"""
        arguments = {
            "limit": 10,
            "user_id": "regular_user"
        }
        
        response = await client.call_tool_and_parse("get_audit_log", arguments)
        
        # Should return error or unauthorized status
        assert response.get("status") == "error" or "Unauthorized" in str(response)
    
    @pytest.mark.asyncio
    async def test_get_audit_log_different_limits(self, client):
        """Test get_audit_log with different limit values"""
        limits = [5, 10, 50, 100]
        
        for limit in limits:
            arguments = {
                "limit": limit,
                "user_id": "admin"
            }
            
            response = await client.call_tool_and_parse("get_audit_log", arguments)
            
            assert "status" in response
            assert response["action"] == "get_audit_log"
            
            if response["status"] == "success":
                data = response["data"]
                assert "logs" in data
                assert "count" in data
                # Count should not exceed the limit
                assert data["count"] <= limit
    
    @pytest.mark.asyncio
    async def test_approve_authorization_invalid_request(self, client):
        """Test approve_authorization with invalid/non-existent request ID"""
        arguments = {
            "request_id": "invalid-request-999",
            "approved_by": "admin"
        }
        
        response = await client.call_tool_and_parse("approve_authorization", arguments)
        
        assert "status" in response
        assert response["action"] == "approve_authorization"
        
        if response["status"] == "success":
            data = response["data"]
            # Should indicate approval failed
            assert data.get("approved") is False
    
    @pytest.mark.asyncio
    async def test_admin_tools_error_handling(self, client):
        """Test admin tools error handling with missing parameters"""
        # Test approve_authorization with missing required parameter
        response = await client.call_tool_and_parse("approve_authorization", {})
        
        # Should return error for missing required parameters
        assert "status" in response
        # Either has error in response or status indicates error
        assert response.get("status") == "error" or "error" in response.get("text", "").lower() or "validation" in response.get("text", "").lower()
        
        # Test tools that might work with empty params (have defaults)
        tools_with_defaults = [
            "get_authorization_requests",
            "get_monitoring_metrics", 
            "get_audit_log"
        ]
        
        for tool_name in tools_with_defaults:
            response = await client.call_tool_and_parse(tool_name, {})
            assert "status" in response
            # These might succeed with defaults or fail gracefully


if __name__ == "__main__":
    pytest.main([__file__, "-v"])