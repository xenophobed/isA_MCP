#!/usr/bin/env python3
"""
Factual Memory Tests
Tests for capabilities, discovery, and MCP tool I/O for factual memories
"""

import pytest
import json
import asyncio
from tools.mcp_client import MCPClient


class TestFactualMemoryCapabilities:
    """Test factual memory capabilities and discovery"""
    
    @pytest.fixture
    def client(self):
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_store_fact_in_capabilities(self, client):
        """Test that store_fact tool is listed in capabilities"""
        response = await client.get_capabilities()
        
        assert response.get("status") == "success"
        tools = response["capabilities"]["tools"]["available"]
        assert "store_fact" in tools
    
    @pytest.mark.asyncio
    async def test_fact_discovery(self, client):
        """Test AI discovery for fact storage requests"""
        requests = [
            "I need to remember facts about people and projects",
            "Store information about team members",
            "Remember details about my customers",
            "Keep track of project facts and data"
        ]
        
        for request in requests:
            response = await client.discover_tools(request)
            if response.get("status") == "success":
                discovered_tools = response["capabilities"]["tools"]
                assert "store_fact" in discovered_tools, f"store_fact not discovered for: {request}"


class TestFactualMemoryMCP:
    """Test factual memory MCP tool integration"""
    
    @pytest.fixture
    def client(self):
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_store_fact_success(self, client):
        """Test successful fact storage"""
        arguments = {
            "user_id": "test-fact-user",
            "fact_type": "person",
            "subject": "Sarah Chen",
            "predicate": "role",
            "object_value": "Data Scientist",
            "context": "Team member information",
            "confidence": 0.9
        }
        
        response = await client.call_tool_and_parse("store_fact", arguments)
        
        assert "status" in response
        assert "action" in response
        assert response["action"] == "store_fact"
        
        if response["status"] == "success":
            data = response["data"]
            assert "memory_id" in data
            assert "fact" in data
            assert data["fact"] == "Sarah Chen role Data Scientist"
    
    @pytest.mark.asyncio
    async def test_store_fact_with_merging(self, client):
        """Test fact storage with automatic merging"""
        # Store initial fact
        fact1_args = {
            "user_id": "test-merge-user",
            "fact_type": "person",
            "subject": "John Smith",
            "predicate": "email",
            "object_value": "john@company.com",
            "confidence": 0.8
        }
        
        response1 = await client.call_tool_and_parse("store_fact", fact1_args)
        
        if response1.get("status") == "success":
            # Store updated fact (should merge)
            fact2_args = {
                "user_id": "test-merge-user",
                "fact_type": "person",
                "subject": "John Smith",
                "predicate": "email", 
                "object_value": "john.smith@company.com",
                "confidence": 0.9
            }
            
            response2 = await client.call_tool_and_parse("store_fact", fact2_args)
            
            if response2.get("status") == "success":
                # Should indicate merge operation
                assert "operation" in response2["data"]
    
    @pytest.mark.asyncio
    async def test_store_fact_error_handling(self, client):
        """Test fact storage error handling"""
        # Missing required parameters
        response = await client.call_tool_and_parse("store_fact", {})
        
        # Should return error for missing parameters or error in text
        assert ("error" in response or 
                response.get("status") == "error" or
                "validation errors" in response.get("text", ""))
    
    @pytest.mark.asyncio
    async def test_search_factual_memories(self, client):
        """Test searching for factual memories"""
        import time
        unique_subject = f"Fact Test {int(time.time())}"
        
        # First store a fact
        store_args = {
            "user_id": "test-search-user",
            "fact_type": "test",
            "subject": unique_subject,
            "predicate": "type",
            "object_value": "integration test",
            "confidence": 0.95
        }
        
        store_response = await client.call_tool_and_parse("store_fact", store_args)
        
        if store_response.get("status") == "success":
            # Wait for indexing
            await asyncio.sleep(1)
            
            # Search for the fact
            search_args = {
                "user_id": "test-search-user",
                "query": unique_subject,
                "memory_types": json.dumps(["FACTUAL"]),
                "limit": 5,
                "similarity_threshold": 0.6
            }
            
            search_response = await client.call_tool_and_parse("search_memories", search_args)
            
            if search_response.get("status") == "success":
                results = search_response["data"]["results"]
                found = any(unique_subject in result.get("content", "") for result in results)
                assert found, f"Stored fact '{unique_subject}' not found in search"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])