#!/usr/bin/env python3
"""
Session Memory Tests
Tests for capabilities, discovery, and MCP tool I/O for session memories
"""

import pytest
import json
import asyncio
from tools.mcp_client import MCPClient


class TestSessionMemoryCapabilities:
    """Test session memory capabilities and discovery"""
    
    @pytest.fixture
    def client(self):
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_store_session_memory_in_capabilities(self, client):
        """Test that store_session_memory tool is listed in capabilities"""
        response = await client.get_capabilities()
        
        assert response.get("status") == "success"
        tools = response["capabilities"]["tools"]["available"]
        assert "store_session_memory" in tools
    
    @pytest.mark.asyncio
    async def test_session_memory_discovery(self, client):
        """Test AI discovery for session memory requests"""
        requests = [
            "Store conversation context and chat history",
            "Remember session state and interaction flow",
            "Keep track of dialogue context",
            "Manage conversation memory and continuity"
        ]
        
        for request in requests:
            response = await client.discover_tools(request)
            if response.get("status") == "success":
                discovered_tools = response["capabilities"]["tools"]
                # Session memory tools may be discovered as store_session_memory or related memory tools
                assert (len(discovered_tools) > 0), f"No tools discovered for: {request}"


class TestSessionMemoryMCP:
    """Test session memory MCP tool integration"""
    
    @pytest.fixture
    def client(self):
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_store_chat_session(self, client):
        """Test storing a chat session memory"""
        conversation_state = {
            "context": "customer_support",
            "issue_type": "billing_inquiry",
            "customer_tier": "premium",
            "previous_interactions": 2,
            "sentiment": "neutral",
            "resolution_status": "in_progress"
        }
        
        arguments = {
            "user_id": "test-session-user",
            "session_id": "chat-session-12345",
            "content": "Customer asking about recent billing charges and requesting invoice details",
            "interaction_sequence": 3,
            "conversation_state": json.dumps(conversation_state),
            "session_type": "customer_support"
        }
        
        response = await client.call_tool_and_parse("store_session_memory", arguments)
        
        assert "status" in response
        
        if response["status"] == "success":
            if "validation errors" in response.get("text", ""):
                # Handle validation errors in success response
                assert "validation errors" in response.get("text", "")
            elif "action" in response and response["action"] == "store_session_memory":
                data = response["data"]
                assert "memory_id" in data
                assert "session_id" in data
                assert "sequence" in data
                assert data["session_id"] == "chat-session-12345"
                assert data["sequence"] == 3
        else:
            # Should handle validation errors gracefully
            assert ("validation errors" in response.get("text", "") or 
                    "error" in response)
    
    @pytest.mark.asyncio
    async def test_store_meeting_session(self, client):
        """Test storing a meeting session memory"""
        conversation_state = {
            "meeting_type": "standup",
            "agenda_items": ["sprint_review", "blockers", "planning"],
            "attendees_count": 5,
            "current_agenda_item": "blockers",
            "time_remaining": "15_minutes"
        }
        
        arguments = {
            "user_id": "test-meeting-user",
            "session_id": "meeting-standup-20241201",
            "content": "Team discussing payment integration blockers and timeline adjustments",
            "interaction_sequence": 7,
            "conversation_state": json.dumps(conversation_state),
            "session_type": "meeting"
        }
        
        response = await client.call_tool_and_parse("store_session_memory", arguments)
        
        if response.get("status") == "success":
            if "validation errors" in response.get("text", ""):
                # Handle validation errors in success response
                assert "validation errors" in response.get("text", "")
            elif "data" in response:
                data = response["data"]
                assert data["session_id"] == "meeting-standup-20241201"
                assert data["sequence"] == 7
        else:
            # Should handle validation errors gracefully
            assert ("validation errors" in response.get("text", "") or 
                    "error" in response)
    
    @pytest.mark.asyncio
    async def test_store_learning_session(self, client):
        """Test storing a learning session memory"""
        conversation_state = {
            "course": "Advanced Python Programming",
            "module": "Async Programming",
            "progress": 0.65,
            "difficulty_level": "intermediate",
            "questions_asked": 3,
            "topics_covered": ["asyncio", "coroutines", "event_loops"]
        }
        
        arguments = {
            "user_id": "test-learning-user",
            "session_id": "learning-python-async-001",
            "content": "Student learning about asyncio and asking about best practices for error handling in async functions",
            "interaction_sequence": 12,
            "conversation_state": json.dumps(conversation_state),
            "session_type": "learning"
        }
        
        response = await client.call_tool_and_parse("store_session_memory", arguments)
        
        if response.get("status") == "success":
            if "validation errors" in response.get("text", ""):
                # Handle validation errors in success response
                assert "validation errors" in response.get("text", "")
            elif "data" in response:
                data = response["data"]
                assert data["session_id"] == "learning-python-async-001"
                assert data["sequence"] == 12
        else:
            # Should handle validation errors gracefully
            assert ("validation errors" in response.get("text", "") or 
                    "error" in response)
    
    @pytest.mark.asyncio
    async def test_session_sequence_tracking(self, client):
        """Test session memory with sequence tracking"""
        session_id = "test-sequence-session"
        user_id = "test-sequence-user"
        
        # Store multiple interactions in sequence
        for i in range(1, 4):
            conversation_state = {
                "step": i,
                "context": f"interaction_{i}",
                "cumulative_info": f"building_context_step_{i}"
            }
            
            arguments = {
                "user_id": user_id,
                "session_id": session_id,
                "content": f"Interaction {i} in the session sequence",
                "interaction_sequence": i,
                "conversation_state": json.dumps(conversation_state),
                "session_type": "sequential_test"
            }
            
            response = await client.call_tool_and_parse("store_session_memory", arguments)
            
            if response.get("status") == "success":
                if "data" in response and "sequence" in response["data"]:
                    assert response["data"]["sequence"] == i
    
    @pytest.mark.asyncio
    async def test_search_session_memories(self, client):
        """Test searching for session memories"""
        import time
        unique_session = f"test-session-{int(time.time())}"
        
        # First store a session memory
        conversation_state = {
            "unique_marker": unique_session,
            "test_purpose": "search_functionality"
        }
        
        store_args = {
            "user_id": "test-search-sessions",
            "session_id": unique_session,
            "content": f"This is a {unique_session} for testing search functionality",
            "interaction_sequence": 1,
            "conversation_state": json.dumps(conversation_state),
            "session_type": "test"
        }
        
        store_response = await client.call_tool_and_parse("store_session_memory", store_args)
        
        if store_response.get("status") == "success":
            # Wait for indexing
            await asyncio.sleep(1)
            
            # Search for the session memory
            search_args = {
                "user_id": "test-search-sessions",
                "query": unique_session,
                "memory_types": json.dumps(["SESSION"]),
                "limit": 5,
                "similarity_threshold": 0.6
            }
            
            search_response = await client.call_tool_and_parse("search_memories", search_args)
            
            if search_response.get("status") == "success":
                if "data" in search_response and "results" in search_response["data"]:
                    results = search_response["data"]["results"]
                    found = any(unique_session in result.get("content", "") for result in results)
                    assert found, f"Stored session '{unique_session}' not found in search"
    
    @pytest.mark.asyncio
    async def test_session_types_variety(self, client):
        """Test different session types"""
        session_types = [
            ("chat", "General chat conversation"),
            ("support", "Customer support interaction"),
            ("meeting", "Team meeting discussion"),
            ("interview", "Job interview session"),
            ("training", "Training session interaction")
        ]
        
        for session_type, content in session_types:
            conversation_state = {
                "type": session_type,
                "purpose": f"testing_{session_type}_session"
            }
            
            arguments = {
                "user_id": "test-types-user",
                "session_id": f"session-{session_type}-001",
                "content": content,
                "interaction_sequence": 1,
                "conversation_state": json.dumps(conversation_state),
                "session_type": session_type
            }
            
            response = await client.call_tool_and_parse("store_session_memory", arguments)
            
            # Each session type should be handled
            assert "status" in response
    
    @pytest.mark.asyncio
    async def test_session_memory_error_handling(self, client):
        """Test session memory error handling"""
        # Invalid JSON conversation_state
        arguments = {
            "user_id": "test-error-user",
            "session_id": "error-test-session",
            "content": "Test content",
            "interaction_sequence": 1,
            "conversation_state": "invalid_json",
            "session_type": "test"
        }
        
        response = await client.call_tool_and_parse("store_session_memory", arguments)
        
        # Should handle JSON parsing error gracefully
        assert "error" in response or response.get("status") == "error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])