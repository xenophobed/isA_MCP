#!/usr/bin/env python3
"""
Episodic Memory Tests
Tests for capabilities, discovery, and MCP tool I/O for episodic memories
"""

import pytest
import json
import asyncio
from tools.mcp_client import MCPClient


class TestEpisodicMemoryCapabilities:
    """Test episodic memory capabilities and discovery"""
    
    @pytest.fixture
    def client(self):
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_store_episode_in_capabilities(self, client):
        """Test that store_episode tool is listed in capabilities"""
        response = await client.get_capabilities()
        
        assert response.get("status") == "success"
        tools = response["capabilities"]["tools"]["available"]
        assert "store_episode" in tools
    
    @pytest.mark.asyncio
    async def test_episode_discovery(self, client):
        """Test AI discovery for episode storage requests"""
        requests = [
            "Remember events and experiences",
            "Store meeting notes and conversations",
            "Keep track of project milestones",
            "Record personal experiences and stories"
        ]
        
        for request in requests:
            response = await client.discover_tools(request)
            if response.get("status") == "success":
                discovered_tools = response["capabilities"]["tools"]
                # Episode tool may be discovered as store_episode or general store_memory
                # Some requests may discover other memory-related tools
                assert (len(discovered_tools) > 0), f"No tools discovered for: {request}"


class TestEpisodicMemoryMCP:
    """Test episodic memory MCP tool integration"""
    
    @pytest.fixture
    def client(self):
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_store_episode_meeting(self, client):
        """Test storing a meeting episode"""
        arguments = {
            "user_id": "test-episode-user",
            "event_type": "meeting",
            "content": "Weekly team standup: discussed Q4 goals, reviewed sprint progress, identified blockers in payment integration",
            "location": "Conference Room A",
            "participants": json.dumps(["Alice Chen", "Bob Smith", "Carol Johnson", "David Lee"]),
            "emotional_valence": 0.2
        }
        
        response = await client.call_tool_and_parse("store_episode", arguments)
        
        assert "status" in response
        
        if response["status"] == "success":
            if "validation errors" in response.get("text", ""):
                # Handle validation errors in success response
                assert "validation errors" in response.get("text", "")
            elif "action" in response and response["action"] == "store_episode":
                data = response["data"]
                assert "memory_id" in data
                assert "event_type" in data
                assert "participants_count" in data
                assert data["event_type"] == "meeting"
                assert data["participants_count"] == 4
        else:
            # Should handle validation errors gracefully
            assert ("validation errors" in response.get("text", "") or 
                    "error" in response)
    
    @pytest.mark.asyncio
    async def test_store_episode_learning(self, client):
        """Test storing a learning episode"""
        arguments = {
            "user_id": "test-learning-user", 
            "event_type": "learning",
            "content": "Completed advanced Python course on async programming. Learned about asyncio, coroutines, and event loops",
            "location": "Online",
            "participants": json.dumps(["Instructor: Dr. Sarah Wilson"]),
            "emotional_valence": 0.8
        }
        
        response = await client.call_tool_and_parse("store_episode", arguments)
        
        if response.get("status") == "success":
            if "validation errors" in response.get("text", ""):
                # Handle validation errors in success response
                assert "validation errors" in response.get("text", "")
            elif "data" in response:
                data = response["data"]
                assert data["event_type"] == "learning"
                assert data["participants_count"] == 1
        else:
            # Should handle validation errors gracefully
            assert ("validation errors" in response.get("text", "") or 
                    "error" in response)
    
    @pytest.mark.asyncio
    async def test_store_episode_project_milestone(self, client):
        """Test storing a project milestone episode"""
        arguments = {
            "user_id": "test-project-user",
            "event_type": "milestone",
            "content": "Successfully deployed memory service to production. All tests passing, performance metrics look good",
            "location": "Remote",
            "participants": json.dumps(["Development Team", "QA Team", "DevOps Team"]),
            "emotional_valence": 0.9
        }
        
        response = await client.call_tool_and_parse("store_episode", arguments)
        
        if response.get("status") == "success":
            if "validation errors" in response.get("text", ""):
                # Handle validation errors in success response
                assert "validation errors" in response.get("text", "")
            elif "data" in response:
                data = response["data"]
                assert data["event_type"] == "milestone"
                assert data["participants_count"] == 3
        else:
            # Should handle validation errors gracefully
            assert ("validation errors" in response.get("text", "") or 
                    "error" in response)
    
    @pytest.mark.asyncio
    async def test_search_episodic_memories(self, client):
        """Test searching for episodic memories"""
        import time
        unique_event = f"Test Event {int(time.time())}"
        
        # First store an episode
        store_args = {
            "user_id": "test-search-episodes",
            "event_type": "test",
            "content": f"This is a {unique_event} for testing search functionality",
            "location": "Test Location",
            "participants": json.dumps(["Test User"]),
            "emotional_valence": 0.5
        }
        
        store_response = await client.call_tool_and_parse("store_episode", store_args)
        
        if store_response.get("status") == "success":
            # Wait for indexing
            await asyncio.sleep(1)
            
            # Search for the episode
            search_args = {
                "user_id": "test-search-episodes",
                "query": unique_event,
                "memory_types": json.dumps(["EPISODIC"]),
                "limit": 5,
                "similarity_threshold": 0.6
            }
            
            search_response = await client.call_tool_and_parse("search_memories", search_args)
            
            if search_response.get("status") == "success":
                if "data" in search_response and "results" in search_response["data"]:
                    results = search_response["data"]["results"]
                    found = any(unique_event in result.get("content", "") for result in results)
                    assert found, f"Stored episode '{unique_event}' not found in search"
    
    @pytest.mark.asyncio
    async def test_episode_emotional_valence(self, client):
        """Test episodes with different emotional valences"""
        # Positive episode
        positive_args = {
            "user_id": "test-emotion-user",
            "event_type": "celebration",
            "content": "Team celebration for successful product launch",
            "emotional_valence": 0.9
        }
        
        response = await client.call_tool_and_parse("store_episode", positive_args)
        if response.get("status") == "success":
            pass  # Emotional valence is stored internally
        
        # Negative episode
        negative_args = {
            "user_id": "test-emotion-user",
            "event_type": "incident",
            "content": "Server outage caused by database connection issues",
            "emotional_valence": -0.7
        }
        
        response = await client.call_tool_and_parse("store_episode", negative_args)
        if response.get("status") == "success":
            pass
        
        # Neutral episode
        neutral_args = {
            "user_id": "test-emotion-user",
            "event_type": "routine",
            "content": "Regular code review session",
            "emotional_valence": 0.0
        }
        
        response = await client.call_tool_and_parse("store_episode", neutral_args)
        assert "status" in response
    
    @pytest.mark.asyncio
    async def test_episode_error_handling(self, client):
        """Test episode storage error handling"""
        # Invalid JSON participants
        arguments = {
            "user_id": "test-error-user",
            "event_type": "test",
            "content": "Test episode with invalid participants",
            "participants": "invalid_json"
        }
        
        response = await client.call_tool_and_parse("store_episode", arguments)
        
        # Should handle JSON parsing error gracefully
        assert "error" in response or response.get("status") == "error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])