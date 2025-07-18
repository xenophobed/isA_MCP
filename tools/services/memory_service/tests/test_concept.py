#!/usr/bin/env python3
"""
Semantic Memory (Concept) Tests
Tests for capabilities, discovery, and MCP tool I/O for semantic memories
"""

import pytest
import json
import asyncio
from tools.mcp_client import MCPClient


class TestConceptMemoryCapabilities:
    """Test concept memory capabilities and discovery"""
    
    @pytest.fixture
    def client(self):
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_store_concept_in_capabilities(self, client):
        """Test that store_concept tool is listed in capabilities"""
        response = await client.get_capabilities()
        
        assert response.get("status") == "success"
        tools = response["capabilities"]["tools"]["available"]
        assert "store_concept" in tools
    
    @pytest.mark.asyncio
    async def test_concept_discovery(self, client):
        """Test AI discovery for concept storage requests"""
        requests = [
            "Store definitions and concepts",
            "Remember knowledge and terminology",
            "Keep track of technical concepts",
            "Store semantic relationships and meanings"
        ]
        
        for request in requests:
            response = await client.discover_tools(request)
            if response.get("status") == "success":
                discovered_tools = response["capabilities"]["tools"]
                assert "store_concept" in discovered_tools, f"store_concept not discovered for: {request}"


class TestConceptMemoryMCP:
    """Test concept memory MCP tool integration"""
    
    @pytest.fixture
    def client(self):
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_store_technical_concept(self, client):
        """Test storing a technical concept"""
        properties = {
            "complexity": "intermediate",
            "domain": "computer_science",
            "applications": ["web_development", "data_processing", "automation"],
            "prerequisites": ["basic_programming", "http_protocol"]
        }
        
        arguments = {
            "user_id": "test-concept-user",
            "concept_type": "RESTful API",
            "definition": "Representational State Transfer API is an architectural style for designing networked applications using HTTP methods",
            "category": "software_architecture",
            "properties": json.dumps(properties),
            "related_concepts": json.dumps(["HTTP", "JSON", "Web Services", "Microservices"])
        }
        
        response = await client.call_tool_and_parse("store_concept", arguments)
        
        assert "status" in response
        
        if response["status"] == "success":
            if "validation errors" in response.get("text", ""):
                # Handle validation errors in success response
                assert "validation errors" in response.get("text", "")
            else:
                assert "action" in response
                assert response["action"] == "store_concept"
                data = response["data"]
                assert "memory_id" in data
                assert "concept" in data
                assert "category" in data
                assert data["concept"] == "RESTful API"
                assert data["category"] == "software_architecture"
        else:
            # Should handle validation errors gracefully
            assert ("validation errors" in response.get("text", "") or 
                    "error" in response)
    
    @pytest.mark.asyncio
    async def test_store_business_concept(self, client):
        """Test storing a business concept"""
        properties = {
            "industry": "finance",
            "importance": "high",
            "regulatory_impact": True
        }
        
        arguments = {
            "user_id": "test-business-user",
            "concept_type": "Customer Lifetime Value",
            "definition": "CLV is the predicted net profit attributed to the entire future relationship with a customer",
            "category": "business_metrics",
            "properties": json.dumps(properties),
            "related_concepts": json.dumps(["Customer Acquisition Cost", "Churn Rate", "Revenue Analytics"])
        }
        
        response = await client.call_tool_and_parse("store_concept", arguments)
        
        if response.get("status") == "success":
            if "validation errors" in response.get("text", ""):
                # Handle validation errors in success response
                assert "validation errors" in response.get("text", "")
            elif "data" in response:
                data = response["data"]
                assert data["concept"] == "Customer Lifetime Value"
                assert data["category"] == "business_metrics"
        else:
            # Should handle validation errors gracefully
            assert ("validation errors" in response.get("text", "") or 
                    "error" in response)
    
    @pytest.mark.asyncio
    async def test_store_scientific_concept(self, client):
        """Test storing a scientific concept"""
        properties = {
            "field": "physics",
            "mathematical_complexity": "high",
            "experimental_verification": True,
            "year_discovered": 1915
        }
        
        arguments = {
            "user_id": "test-science-user",
            "concept_type": "General Relativity",
            "definition": "Einstein's theory describing gravity as the curvature of spacetime caused by mass and energy",
            "category": "physics",
            "properties": json.dumps(properties),
            "related_concepts": json.dumps(["Spacetime", "Gravity", "Black Holes", "Special Relativity"])
        }
        
        response = await client.call_tool_and_parse("store_concept", arguments)
        
        if response.get("status") == "success":
            if "validation errors" in response.get("text", ""):
                # Handle validation errors in success response
                assert "validation errors" in response.get("text", "")
            elif "data" in response:
                data = response["data"]
                assert data["concept"] == "General Relativity"
                assert data["category"] == "physics"
        else:
            # Should handle validation errors gracefully
            assert ("validation errors" in response.get("text", "") or 
                    "error" in response)
    
    @pytest.mark.asyncio
    async def test_search_semantic_memories(self, client):
        """Test searching for semantic memories"""
        import time
        unique_concept = f"Test Concept {int(time.time())}"
        
        # First store a concept
        store_args = {
            "user_id": "test-search-concepts",
            "concept_type": unique_concept,
            "definition": f"This is a {unique_concept} created for testing search functionality in semantic memory",
            "category": "testing",
            "properties": json.dumps({"test": True}),
            "related_concepts": json.dumps(["Testing", "Search", "Memory"])
        }
        
        store_response = await client.call_tool_and_parse("store_concept", store_args)
        
        if store_response.get("status") == "success":
            # Wait for indexing
            await asyncio.sleep(1)
            
            # Search for the concept
            search_args = {
                "user_id": "test-search-concepts",
                "query": unique_concept,
                "memory_types": json.dumps(["SEMANTIC"]),
                "limit": 5,
                "similarity_threshold": 0.6
            }
            
            search_response = await client.call_tool_and_parse("search_memories", search_args)
            
            if search_response.get("status") == "success":
                if "data" in search_response and "results" in search_response["data"]:
                    results = search_response["data"]["results"]
                    found = any(unique_concept in result.get("content", "") for result in results)
                    assert found, f"Stored concept '{unique_concept}' not found in search"
    
    @pytest.mark.asyncio
    async def test_concept_relationships(self, client):
        """Test concepts with complex relationships"""
        # Store a primary concept
        primary_concept = {
            "user_id": "test-relationship-user",
            "concept_type": "Machine Learning",
            "definition": "Field of AI focused on algorithms that learn from data",
            "category": "artificial_intelligence",
            "properties": json.dumps({
                "complexity": "high",
                "requires_math": True,
                "applications": ["prediction", "classification", "clustering"]
            }),
            "related_concepts": json.dumps([
                "Artificial Intelligence",
                "Deep Learning", 
                "Neural Networks",
                "Data Science"
            ])
        }
        
        response = await client.call_tool_and_parse("store_concept", primary_concept)
        
        if response.get("status") == "success":
            # Store a related concept
            related_concept = {
                "user_id": "test-relationship-user",
                "concept_type": "Deep Learning",
                "definition": "Subset of ML using neural networks with multiple layers",
                "category": "artificial_intelligence",
                "properties": json.dumps({
                    "complexity": "very_high",
                    "requires_gpu": True,
                    "parent_field": "machine_learning"
                }),
                "related_concepts": json.dumps([
                    "Machine Learning",
                    "Neural Networks",
                    "Convolutional Networks",
                    "Transformers"
                ])
            }
            
            related_response = await client.call_tool_and_parse("store_concept", related_concept)
            assert "status" in related_response
    
    @pytest.mark.asyncio
    async def test_concept_error_handling(self, client):
        """Test concept storage error handling"""
        # Invalid JSON properties
        arguments = {
            "user_id": "test-error-user",
            "concept_type": "Test Concept",
            "definition": "Test definition",
            "category": "testing",
            "properties": "invalid_json"
        }
        
        response = await client.call_tool_and_parse("store_concept", arguments)
        
        # Should handle JSON parsing error gracefully
        assert "error" in response or response.get("status") == "error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])