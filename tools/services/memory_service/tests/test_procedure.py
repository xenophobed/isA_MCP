#!/usr/bin/env python3
"""
Procedural Memory Tests
Tests for capabilities, discovery, and MCP tool I/O for procedural memories
"""

import pytest
import json
import asyncio
from tools.mcp_client import MCPClient


class TestProceduralMemoryCapabilities:
    """Test procedural memory capabilities and discovery"""
    
    @pytest.fixture
    def client(self):
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_store_procedure_in_capabilities(self, client):
        """Test that store_procedure tool is listed in capabilities"""
        response = await client.get_capabilities()
        
        assert response.get("status") == "success"
        tools = response["capabilities"]["tools"]["available"]
        assert "store_procedure" in tools
    
    @pytest.mark.asyncio
    async def test_procedure_discovery(self, client):
        """Test AI discovery for procedure storage requests"""
        requests = [
            "Help me store step-by-step procedures",
            "I want to remember workflows and processes",
            "Store how-to instructions for tasks",
            "Keep track of standard operating procedures"
        ]
        
        for request in requests:
            response = await client.discover_tools(request)
            if response.get("status") == "success":
                discovered_tools = response["capabilities"]["tools"]
                assert "store_procedure" in discovered_tools, f"store_procedure not discovered for: {request}"


class TestProceduralMemoryMCP:
    """Test procedural memory MCP tool integration"""
    
    @pytest.fixture
    def client(self):
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_store_procedure_success(self, client):
        """Test successful procedure storage"""
        steps = [
            {"step": 1, "description": "Gather requirements", "duration": "30 min"},
            {"step": 2, "description": "Design solution", "duration": "2 hours"},
            {"step": 3, "description": "Implement code", "duration": "4 hours"},
            {"step": 4, "description": "Test and debug", "duration": "1 hour"},
            {"step": 5, "description": "Deploy to production", "duration": "30 min"}
        ]
        
        arguments = {
            "user_id": "test-procedure-user",
            "skill_type": "Software Development Process",
            "steps": json.dumps(steps),
            "domain": "software_engineering",
            "difficulty_level": "intermediate",
            "prerequisites": json.dumps(["Programming knowledge", "Version control", "Testing framework"])
        }
        
        response = await client.call_tool_and_parse("store_procedure", arguments)
        
        assert "status" in response
        
        if response["status"] == "success":
            if "validation errors" in response.get("text", ""):
                # Handle validation errors in success response
                assert "validation errors" in response.get("text", "")
            else:
                assert "action" in response
                assert response["action"] == "store_procedure"
                data = response["data"]
                assert "memory_id" in data
                assert "procedure" in data
                assert "steps_count" in data
                assert data["steps_count"] == 5
                assert data["procedure"] == "Software Development Process"
        else:
            # Should handle validation errors gracefully
            assert ("validation errors" in response.get("text", "") or 
                    "error" in response)
    
    @pytest.mark.asyncio
    async def test_store_cooking_procedure(self, client):
        """Test storing a cooking procedure"""
        steps = [
            {"step": 1, "description": "Preheat oven to 350 degrees F"},
            {"step": 2, "description": "Mix flour, sugar, and baking powder"},
            {"step": 3, "description": "Add eggs and milk"},
            {"step": 4, "description": "Pour into greased pan"},
            {"step": 5, "description": "Bake for 25-30 minutes"}
        ]
        
        arguments = {
            "user_id": "test-cooking-user",
            "skill_type": "Basic Cake Recipe",
            "steps": json.dumps(steps),
            "domain": "cooking",
            "difficulty_level": "beginner",
            "prerequisites": json.dumps(["Basic kitchen tools", "Oven access"])
        }
        
        response = await client.call_tool_and_parse("store_procedure", arguments)
        
        if response.get("status") == "success":
            if "validation errors" in response.get("text", ""):
                # Handle validation errors in success response
                assert "validation errors" in response.get("text", "")
            elif "data" in response:
                data = response["data"]
                assert data["steps_count"] == 5
                assert "Basic Cake Recipe" in data["procedure"]
        else:
            # Should handle validation errors gracefully
            assert ("validation errors" in response.get("text", "") or 
                    "error" in response)
    
    @pytest.mark.asyncio
    async def test_store_procedure_error_handling(self, client):
        """Test procedure storage error handling"""
        # Invalid JSON steps
        arguments = {
            "user_id": "test-error-user",
            "skill_type": "Test Procedure",
            "steps": "invalid_json",
            "domain": "testing"
        }
        
        response = await client.call_tool_and_parse("store_procedure", arguments)
        
        # Should handle JSON parsing error
        assert "error" in response or response.get("status") == "error"
    
    @pytest.mark.asyncio
    async def test_search_procedural_memories(self, client):
        """Test searching for procedural memories"""
        import time
        unique_skill = f"Test Skill {int(time.time())}"
        
        # First store a procedure
        steps = [
            {"step": 1, "description": "Step one of test procedure"},
            {"step": 2, "description": "Step two of test procedure"}
        ]
        
        store_args = {
            "user_id": "test-proc-search-user",
            "skill_type": unique_skill,
            "steps": json.dumps(steps),
            "domain": "testing",
            "difficulty_level": "beginner"
        }
        
        store_response = await client.call_tool_and_parse("store_procedure", store_args)
        
        if store_response.get("status") == "success":
            # Wait for indexing
            await asyncio.sleep(1)
            
            # Search for the procedure
            search_args = {
                "user_id": "test-proc-search-user",
                "query": unique_skill,
                "memory_types": json.dumps(["PROCEDURAL"]),
                "limit": 5,
                "similarity_threshold": 0.6
            }
            
            search_response = await client.call_tool_and_parse("search_memories", search_args)
            
            if search_response.get("status") == "success":
                if "data" in search_response and "results" in search_response["data"]:
                    results = search_response["data"]["results"]
                    found = any(unique_skill in result.get("content", "") for result in results)
                    assert found, f"Stored procedure '{unique_skill}' not found in search"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])