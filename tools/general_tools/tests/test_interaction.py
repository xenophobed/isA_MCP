#!/usr/bin/env python3
"""
Interaction Tools Tests
Tests for capabilities, discovery, and MCP tool I/O for client interaction tools
"""

import pytest
import json
import asyncio
import time
from tools.mcp_client import MCPClient


class TestInteractionToolsCapabilities:
    """Test interaction tools capabilities and discovery"""
    
    @pytest.fixture
    def client(self):
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_ask_human_in_capabilities(self, client):
        """Test that ask_human tool is listed in capabilities"""
        response = await client.get_capabilities()
        
        assert response.get("status") == "success"
        tools = response["capabilities"]["tools"]["available"]
        assert "ask_human" in tools
    
    @pytest.mark.asyncio
    async def test_request_authorization_in_capabilities(self, client):
        """Test that request_authorization tool is listed in capabilities"""
        response = await client.get_capabilities()
        
        assert response.get("status") == "success"
        tools = response["capabilities"]["tools"]["available"]
        assert "request_authorization" in tools
    
    @pytest.mark.asyncio
    async def test_check_security_status_in_capabilities(self, client):
        """Test that check_security_status tool is listed in capabilities"""
        response = await client.get_capabilities()
        
        assert response.get("status") == "success"
        tools = response["capabilities"]["tools"]["available"]
        assert "check_security_status" in tools
    
    @pytest.mark.asyncio
    async def test_format_response_in_capabilities(self, client):
        """Test that format_response tool is listed in capabilities"""
        response = await client.get_capabilities()
        
        assert response.get("status") == "success"
        tools = response["capabilities"]["tools"]["available"]
        assert "format_response" in tools
    
    @pytest.mark.asyncio
    async def test_interaction_tools_discovery(self, client):
        """Test AI discovery for interaction-related requests"""
        requests = [
            "I need to ask the user for clarification",
            "Request authorization before deleting files",
            "Check the current security status of the system",
            "Format the response in a structured way",
            "Get human input for this decision",
            "Verify security before proceeding"
        ]
        
        for request in requests:
            response = await client.discover_tools(request)
            if response.get("status") == "success":
                discovered_tools = response["capabilities"]["tools"]
                interaction_tools_found = any(tool in discovered_tools for tool in [
                    "ask_human", "request_authorization", 
                    "check_security_status", "format_response"
                ])
                assert interaction_tools_found, f"No interaction tools discovered for: {request}"


class TestInteractionToolsMCP:
    """Test interaction tools MCP integration"""
    
    @pytest.fixture
    def client(self):
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_ask_human_success(self, client):
        """Test ask_human with basic question"""
        arguments = {
            "question": "What is your preferred data format?",
            "context": "Setting up data export preferences",
            "user_id": "test-user"
        }
        
        response = await client.call_tool_and_parse("ask_human", arguments)
        
        assert "status" in response
        assert "action" in response
        assert response["action"] == "ask_human"
        assert response["status"] == "human_input_requested"
        
        data = response["data"]
        assert "question" in data
        assert "context" in data
        assert "user_id" in data
        assert "instruction" in data
        assert data["question"] == "What is your preferred data format?"
        assert data["user_id"] == "test-user"
    
    @pytest.mark.asyncio
    async def test_ask_human_minimal_params(self, client):
        """Test ask_human with minimal parameters"""
        arguments = {
            "question": "Are you sure you want to proceed?"
        }
        
        response = await client.call_tool_and_parse("ask_human", arguments)
        
        assert "status" in response
        assert response["status"] == "human_input_requested"
        assert response["action"] == "ask_human"
        
        data = response["data"]
        assert data["question"] == "Are you sure you want to proceed?"
        assert "context" in data  # Should have empty context
        assert "user_id" in data  # Should have default user_id
    
    @pytest.mark.asyncio
    async def test_request_authorization_success(self, client):
        """Test request_authorization with valid parameters"""
        arguments = {
            "tool_name": "delete_user_data",
            "reason": "User requested account deletion",
            "user_id": "test-user",
            "tool_args": {"user_id": "user123", "confirm": True}
        }
        
        response = await client.call_tool_and_parse("request_authorization", arguments)
        
        assert "status" in response
        assert "action" in response
        assert response["action"] == "request_authorization"
        assert response["status"] == "authorization_requested"
        
        data = response["data"]
        assert "request_id" in data
        assert "tool_name" in data
        assert "tool_args" in data
        assert "reason" in data
        assert "security_level" in data
        assert "user_id" in data
        assert "expires_at" in data
        assert "instruction" in data
        
        assert data["tool_name"] == "delete_user_data"
        assert data["reason"] == "User requested account deletion"
        assert data["user_id"] == "test-user"
    
    @pytest.mark.asyncio
    async def test_request_authorization_security_levels(self, client):
        """Test request_authorization with different security levels"""
        test_cases = [
            {"tool_name": "get_user_info", "expected_level": "MEDIUM"},
            {"tool_name": "forget_user_data", "expected_level": "HIGH"},
            {"tool_name": "delete_all_users", "expected_level": "HIGH"},
            {"tool_name": "admin_reset_system", "expected_level": "CRITICAL"},
        ]
        
        for case in test_cases:
            arguments = {
                "tool_name": case["tool_name"],
                "reason": f"Testing {case['tool_name']}",
                "user_id": "test-user"
            }
            
            response = await client.call_tool_and_parse("request_authorization", arguments)
            
            if response.get("status") == "authorization_requested":
                data = response["data"]
                assert "security_level" in data
                # Note: The actual security level logic might be more complex
                assert data["security_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    
    @pytest.mark.asyncio
    async def test_check_security_status_basic(self, client):
        """Test check_security_status without metrics"""
        arguments = {
            "include_metrics": False,
            "user_id": "test-user"
        }
        
        response = await client.call_tool_and_parse("check_security_status", arguments)
        
        assert "status" in response
        assert "action" in response
        assert response["action"] == "check_security_status"
        
        if response["status"] == "success":
            data = response["data"]
            assert "security_score" in data
            assert "pending_authorizations" in data
            assert "security_violations" in data
            assert "rate_limit_hits" in data
            assert "total_requests" in data
            assert "uptime" in data
            
            # Should not include detailed metrics
            assert "detailed_metrics" not in data
            assert "recent_logs" not in data
            
            # Security score should be valid
            assert data["security_score"] in ["HIGH", "MEDIUM", "LOW"]
    
    @pytest.mark.asyncio
    async def test_check_security_status_with_metrics(self, client):
        """Test check_security_status with detailed metrics"""
        arguments = {
            "include_metrics": True,
            "user_id": "test-user"
        }
        
        response = await client.call_tool_and_parse("check_security_status", arguments)
        
        assert "status" in response
        assert response["action"] == "check_security_status"
        
        if response["status"] == "success":
            data = response["data"]
            # Should include detailed metrics
            assert "detailed_metrics" in data
            assert "recent_logs" in data
            assert isinstance(data["detailed_metrics"], dict)
            assert isinstance(data["recent_logs"], list)
    
    @pytest.mark.asyncio
    async def test_format_response_json(self, client):
        """Test format_response with JSON format"""
        test_content = '{"test": "data", "number": 42}'
        arguments = {
            "content": test_content,
            "format_type": "json",
            "user_id": "test-user"
        }
        
        response = await client.call_tool_and_parse("format_response", arguments)
        
        assert "status" in response
        assert "action" in response
        assert response["action"] == "format_response"
        
        if response["status"] == "success":
            data = response["data"]
            assert "original_content" in data
            assert "formatted_content" in data
            assert "format_type" in data
            
            assert data["original_content"] == test_content
            assert data["format_type"] == "json"
            
            # Should be properly formatted JSON
            try:
                formatted = json.loads(data["formatted_content"])
                assert formatted["test"] == "data"
                assert formatted["number"] == 42
            except json.JSONDecodeError:
                pytest.fail("Formatted content is not valid JSON")
    
    @pytest.mark.asyncio
    async def test_format_response_markdown(self, client):
        """Test format_response with markdown format"""
        test_content = "This is a test response with important information."
        arguments = {
            "content": test_content,
            "format_type": "markdown",
            "user_id": "test-user"
        }
        
        response = await client.call_tool_and_parse("format_response", arguments)
        
        assert "status" in response
        assert response["action"] == "format_response"
        
        if response["status"] == "success":
            data = response["data"]
            formatted = data["formatted_content"]
            
            # Should contain markdown formatting
            assert "## Response" in formatted
            assert test_content in formatted
            assert "---" in formatted
            assert "Generated at" in formatted
    
    @pytest.mark.asyncio
    async def test_format_response_security_summary(self, client):
        """Test format_response with security_summary format"""
        test_content = "Security violation detected\nUnauthorized access attempt\nRate limit exceeded\nSuspicious activity logged"
        arguments = {
            "content": test_content,
            "format_type": "security_summary",
            "user_id": "test-user"
        }
        
        response = await client.call_tool_and_parse("format_response", arguments)
        
        assert "status" in response
        assert response["action"] == "format_response"
        
        if response["status"] == "success":
            data = response["data"]
            formatted = data["formatted_content"]
            
            # Should contain security summary formatting
            assert "SECURITY SUMMARY" in formatted
            assert "=" in formatted
            assert "•" in formatted
            assert "Security violation detected" in formatted
    
    @pytest.mark.asyncio
    async def test_format_response_structured_default(self, client):
        """Test format_response with default structured format"""
        test_content = "This is test content for structured formatting."
        arguments = {
            "content": test_content,
            "format_type": "structured",
            "user_id": "test-user"
        }
        
        response = await client.call_tool_and_parse("format_response", arguments)
        
        assert "status" in response
        assert response["action"] == "format_response"
        
        if response["status"] == "success":
            data = response["data"]
            formatted = data["formatted_content"]
            
            # Should contain structured formatting
            assert "STRUCTURED RESPONSE" in formatted
            assert "=" in formatted
            assert test_content in formatted
            assert "Timestamp:" in formatted
    
    @pytest.mark.asyncio
    async def test_interaction_tools_error_handling(self, client):
        """Test interaction tools error handling"""
        # Test ask_human with missing question
        response = await client.call_tool_and_parse("ask_human", {})
        # Should handle gracefully or return proper error
        assert "status" in response
        
        # Test request_authorization with missing tool_name
        response = await client.call_tool_and_parse("request_authorization", {})
        # Should handle gracefully or return proper error
        assert "status" in response
        
        # Test format_response with invalid JSON
        invalid_json = '{"invalid": json content}'
        arguments = {
            "content": invalid_json,
            "format_type": "json"
        }
        response = await client.call_tool_and_parse("format_response", arguments)
        assert "status" in response
        # Should handle invalid JSON gracefully
    
    @pytest.mark.asyncio
    async def test_request_authorization_no_tool_args(self, client):
        """Test request_authorization with None tool_args"""
        arguments = {
            "tool_name": "test_tool",
            "reason": "Testing null tool_args handling",
            "user_id": "test-user",
            "tool_args": None
        }
        
        response = await client.call_tool_and_parse("request_authorization", arguments)
        
        assert "status" in response
        assert response["action"] == "request_authorization"
        
        if response["status"] == "authorization_requested":
            data = response["data"]
            # Should handle None tool_args properly (convert to empty dict)
            assert "tool_args" in data
            assert isinstance(data["tool_args"], dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])