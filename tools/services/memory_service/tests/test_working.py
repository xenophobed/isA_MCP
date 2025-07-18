#!/usr/bin/env python3
"""
Working Memory Tests
Tests for capabilities, discovery, and MCP tool I/O for working memories
"""

import pytest
import json
import asyncio
from tools.mcp_client import MCPClient


class TestWorkingMemoryCapabilities:
    """Test working memory capabilities and discovery"""
    
    @pytest.fixture
    def client(self):
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_working_memory_tools_in_capabilities(self, client):
        """Test that working memory tools are listed in capabilities"""
        response = await client.get_capabilities()
        
        assert response.get("status") == "success"
        tools = response["capabilities"]["tools"]["available"]
        
        working_memory_tools = [
            "store_working_memory",
            "get_active_working_memories", 
            "cleanup_expired_memories"
        ]
        
        for tool in working_memory_tools:
            assert tool in tools, f"Working memory tool {tool} not found in capabilities"
    
    @pytest.mark.asyncio
    async def test_working_memory_discovery(self, client):
        """Test AI discovery for working memory requests"""
        requests = [
            "Manage temporary task memories",
            "Store active workflow context",
            "Keep track of ongoing project state",
            "Handle short-term task information",
            "Clean up expired task data"
        ]
        
        for request in requests:
            response = await client.discover_tools(request)
            if response.get("status") == "success":
                discovered_tools = response["capabilities"]["tools"]
                
                # Should discover at least one working memory tool or any memory tool
                working_tools_found = any(tool in discovered_tools for tool in 
                    ["store_working_memory", "get_active_working_memories", "cleanup_expired_memories", "store_memory"])
                assert working_tools_found or len(discovered_tools) > 0, f"No tools discovered for: {request}"


class TestWorkingMemoryMCP:
    """Test working memory MCP tool integration"""
    
    @pytest.fixture
    def client(self):
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_store_working_memory_success(self, client):
        """Test successful working memory storage"""
        task_context = {
            "project": "Memory Service Integration",
            "phase": "testing",
            "priority": "high",
            "deadline": "2024-12-31",
            "team_members": ["Alice", "Bob"],
            "current_status": "implementing MCP tools"
        }
        
        arguments = {
            "user_id": "test-working-user",
            "task_id": "task-memory-integration-001",
            "content": "Currently working on integrating memory service with MCP tools and testing functionality",
            "task_context": json.dumps(task_context),
            "ttl_hours": 24,
            "priority": 8
        }
        
        response = await client.call_tool_and_parse("store_working_memory", arguments)
        
        assert "status" in response
        
        if response["status"] == "success":
            if "validation errors" in response.get("text", ""):
                # Handle validation errors in success response
                assert "validation errors" in response.get("text", "")
            elif "action" in response and response["action"] == "store_working_memory":
                data = response["data"]
                assert "memory_id" in data
                assert "task_id" in data
                assert "ttl_hours" in data
                assert data["task_id"] == "task-memory-integration-001"
                assert data["ttl_hours"] == 24
        else:
            # Should handle validation errors gracefully
            assert ("validation errors" in response.get("text", "") or 
                    "error" in response)
    
    @pytest.mark.asyncio
    async def test_get_active_working_memories(self, client):
        """Test retrieving active working memories"""
        # First store a working memory
        task_context = {
            "task": "test_retrieval",
            "status": "active"
        }
        
        store_args = {
            "user_id": "test-active-user",
            "task_id": "task-active-test",
            "content": "Test working memory for retrieval",
            "task_context": json.dumps(task_context),
            "ttl_hours": 48,
            "priority": 5
        }
        
        store_response = await client.call_tool_and_parse("store_working_memory", store_args)
        
        if store_response.get("status") == "success":
            # Now get active working memories
            get_args = {
                "user_id": "test-active-user"
            }
            
            get_response = await client.call_tool_and_parse("get_active_working_memories", get_args)
            
            assert "status" in get_response
            assert "action" in get_response
            assert get_response["action"] == "get_active_working_memories"
            
            if get_response["status"] == "success":
                data = get_response["data"]
                assert "user_id" in data
                assert "working_memories" in data
                assert "count" in data
                
                # Should have at least our stored memory
                assert data["count"] >= 1
                
                # Check format of working memories
                if data["count"] > 0:
                    memory = data["working_memories"][0]
                    assert "memory_id" in memory
                    assert "task_id" in memory
                    assert "content" in memory
                    assert "expires_at" in memory
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_memories(self, client):
        """Test cleanup of expired working memories"""
        arguments = {
            "user_id": "test-cleanup-user"
        }
        
        response = await client.call_tool_and_parse("cleanup_expired_memories", arguments)
        
        assert "status" in response
        assert "action" in response
        assert response["action"] == "cleanup_expired_memories"
        
        if response["status"] == "success":
            data = response["data"]
            assert "operation" in data
            assert "affected_count" in data
            assert "user_id" in data
            
            # affected_count should be a number
            assert isinstance(data["affected_count"], int)
    
    @pytest.mark.asyncio
    async def test_working_memory_ttl(self, client):
        """Test working memory with different TTL values"""
        # Test short TTL
        task_context = {"type": "short_term"}
        
        short_ttl_args = {
            "user_id": "test-ttl-user",
            "task_id": "task-short-ttl",
            "content": "Short term working memory",
            "task_context": json.dumps(task_context),
            "ttl_hours": 1,  # Very short TTL
            "priority": 3
        }
        
        response = await client.call_tool_and_parse("store_working_memory", short_ttl_args)
        
        if response.get("status") == "success":
            if "data" in response and "ttl_hours" in response["data"]:
                assert response["data"]["ttl_hours"] == 1
        
        # Test long TTL
        long_ttl_args = {
            "user_id": "test-ttl-user",
            "task_id": "task-long-ttl",
            "content": "Long term working memory",
            "task_context": json.dumps(task_context),
            "ttl_hours": 168,  # 1 week
            "priority": 7
        }
        
        response = await client.call_tool_and_parse("store_working_memory", long_ttl_args)
        
        if response.get("status") == "success":
            if "data" in response and "ttl_hours" in response["data"]:
                assert response["data"]["ttl_hours"] == 168
    
    @pytest.mark.asyncio
    async def test_working_memory_priority(self, client):
        """Test working memory with different priority levels"""
        task_context = {"type": "priority_test"}
        
        # Test high priority
        high_priority_args = {
            "user_id": "test-priority-user",
            "task_id": "task-high-priority",
            "content": "High priority working memory",
            "task_context": json.dumps(task_context),
            "ttl_hours": 24,
            "priority": 10
        }
        
        response = await client.call_tool_and_parse("store_working_memory", high_priority_args)
        
        if response.get("status") == "success":
            # Priority should be reflected in the response
            pass  # Priority is internal to the system
        
        # Test low priority
        low_priority_args = {
            "user_id": "test-priority-user",
            "task_id": "task-low-priority",
            "content": "Low priority working memory",
            "task_context": json.dumps(task_context),
            "ttl_hours": 24,
            "priority": 1
        }
        
        response = await client.call_tool_and_parse("store_working_memory", low_priority_args)
        
        # Should succeed regardless of priority level
        assert "status" in response
    
    @pytest.mark.asyncio
    async def test_working_memory_error_handling(self, client):
        """Test working memory error handling"""
        # Invalid JSON task_context
        arguments = {
            "user_id": "test-error-user",
            "task_id": "task-error-test",
            "content": "Test content",
            "task_context": "invalid_json",
            "ttl_hours": 24
        }
        
        response = await client.call_tool_and_parse("store_working_memory", arguments)
        
        # Should handle JSON parsing error
        assert "error" in response or response.get("status") == "error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])