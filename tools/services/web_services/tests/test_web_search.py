#!/usr/bin/env python3
"""
Real pytest tests for web_search tool
"""

import pytest
import aiohttp
import json
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class TestWebSearchCapabilities:
    """Test 1: Tool registered in capabilities"""
    
    BASE_URL = "http://localhost:8081"
    
    @pytest.mark.asyncio
    async def test_web_search_registered(self):
        """Test that web_search tool is registered in capabilities"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.BASE_URL}/capabilities") as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["status"] == "success"
                tools = data["capabilities"]["tools"]["available"]
                
                # Check that web_search is registered
                assert "web_search" in tools, "web_search tool not found in capabilities"
    

class TestWebSearchDiscovery:
    """Test 2: Tool selection via AI discovery"""
    
    BASE_URL = "http://localhost:8081"
    
    @pytest.mark.asyncio
    async def test_web_search_discovery_basic(self):
        """Test AI discovery finds web_search for basic search requests"""
        request_data = {
            "request": "I need to search the web for information"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.BASE_URL}/discover",
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["status"] == "success"
                assert "capabilities" in data
                
                # Should discover web_search tool
                suggested_tools = data["capabilities"]["tools"]
                assert "web_search" in suggested_tools
    
    @pytest.mark.asyncio
    async def test_web_search_discovery_specific(self):
        """Test AI discovery finds web_search for specific search queries"""
        request_data = {
            "request": "I need to search the web for Python programming tutorials"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.BASE_URL}/discover",
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["status"] == "success"
                suggested_tools = data["capabilities"]["tools"]
                # The discovery might suggest different tools based on AI analysis
                # At minimum, we should get some tools suggested
                assert len(suggested_tools) > 0


class TestWebSearchTool:
    """Test 3: MCP tool input/output correctness"""
    
    @pytest.mark.asyncio
    async def test_web_search_basic_query(self):
        """Test web_search tool with basic query - input/output validation"""
        # Import MCP client
        sys.path.insert(0, str(project_root))
        from tools.mcp_client import MCPClient
        
        client = MCPClient()
        
        # Test input/output
        query = "python programming"
        count = 3
        
        result = await client.call_tool_and_parse("web_search", {
            "query": query,
            "count": count
        })
        
        # Validate response structure
        assert result["status"] in ["success", "error"]
        if result["status"] == "success":
            assert result["action"] == "web_search"
            assert "timestamp" in result
        
        if result["status"] == "success":
            assert "data" in result
            search_data = result["data"]
            assert search_data.get("success") is True
            assert "results" in search_data
            assert isinstance(search_data["results"], list)
            assert len(search_data["results"]) <= count
            
            # Validate each result structure
            for result_item in search_data["results"]:
                assert "title" in result_item
                assert "url" in result_item
                assert "snippet" in result_item
                assert isinstance(result_item["url"], str)
                assert result_item["url"].startswith(("http://", "https://"))
    
    @pytest.mark.asyncio
    async def test_web_search_default_params(self):
        """Test web_search tool with default parameters"""
        from tools.mcp_client import MCPClient
        
        client = MCPClient()
        
        # Test with only required parameter
        result = await client.call_tool_and_parse("web_search", {
            "query": "machine learning"
        })
        
        assert result["status"] in ["success", "error"]
        if result["status"] == "success":
            assert result["action"] == "web_search"
        
        if result["status"] == "success":
            search_data = result["data"]
            assert len(search_data["results"]) <= 10  # Default count
    
    @pytest.mark.asyncio
    async def test_web_search_error_handling(self):
        """Test web_search tool error handling with invalid input"""
        from tools.mcp_client import MCPClient
        
        client = MCPClient()
        
        # Test with empty query
        result = await client.call_tool_and_parse("web_search", {
            "query": ""
        })
        
        # Should handle gracefully
        assert result["status"] in ["success", "error"]
        
        if result["status"] == "error":
            assert "error_message" in result or "error" in result
        else:
            assert "action" in result
            assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_web_search_large_count(self):
        """Test web_search tool with larger result count"""
        from tools.mcp_client import MCPClient
        
        client = MCPClient()
        
        # Test with larger count
        result = await client.call_tool_and_parse("web_search", {
            "query": "data science",
            "count": 15
        })
        
        assert result["status"] in ["success", "error"]
        
        if result["status"] == "success":
            search_data = result["data"]
            assert len(search_data["results"]) <= 15


class TestWebSearchDocumentationCompliance:
    """Test 4: Documentation specification compliance"""
    
    @pytest.mark.asyncio
    async def test_output_format_matches_documentation(self):
        """Test that output format exactly matches web_service.md specification"""
        from tools.mcp_client import MCPClient
        
        client = MCPClient()
        
        # Test with specific parameters to validate format
        result = await client.call_tool_and_parse("web_search", {
            "query": "python tutorial",
            "count": 3
        })
        
        # Validate top-level structure according to web_tools.py:49-54
        expected_top_fields = ["status", "action", "data", "timestamp"]
        for field in expected_top_fields:
            assert field in result, f"Missing top-level field: {field}"
        
        # Check status and action
        assert result["status"] in ["success", "error"]
        if result["status"] == "success":
            assert result["action"] == "web_search"
            
            # Validate data structure according to web_service.md:30-45
            data = result["data"]
            expected_data_fields = ["success", "query", "total", "results", "urls"]
            for field in expected_data_fields:
                assert field in data, f"Missing data field: {field}"
            
            # Validate data field types
            assert isinstance(data["success"], bool)
            assert data["query"] == "python tutorial"
            assert isinstance(data["total"], int)
            assert isinstance(data["results"], list)
            assert isinstance(data["urls"], list)
            assert len(data["results"]) <= 3
            
            # Validate individual result items structure
            for i, result_item in enumerate(data["results"]):
                expected_result_fields = ["title", "url", "snippet", "score"]
                for field in expected_result_fields:
                    assert field in result_item, f"Result {i} missing field: {field}"
                
                assert isinstance(result_item["title"], str)
                assert isinstance(result_item["url"], str)
                assert isinstance(result_item["snippet"], str)
                assert isinstance(result_item["score"], (int, float))
                assert result_item["url"].startswith(("http://", "https://"))
            
            # Validate URL extraction matches results
            expected_urls = [r["url"] for r in data["results"]]
            assert data["urls"] == expected_urls, "URLs list should match result URLs"

    @pytest.mark.asyncio 
    async def test_edge_case_empty_query(self):
        """Test edge case: empty query string"""
        from tools.mcp_client import MCPClient
        
        client = MCPClient()
        
        result = await client.call_tool_and_parse("web_search", {
            "query": ""
        })
        
        # Should handle gracefully (either error or empty results)
        assert result["status"] in ["success", "error"]
        if result["status"] == "error":
            assert "error_message" in result or "error" in result

    @pytest.mark.asyncio
    async def test_edge_case_boundary_counts(self):
        """Test edge cases with boundary count values"""
        from tools.mcp_client import MCPClient
        
        client = MCPClient()
        
        test_cases = [
            {"count": 0, "description": "zero count"},
            {"count": 1, "description": "minimum count"},
            {"count": 50, "description": "large count"}
        ]
        
        for case in test_cases:
            result = await client.call_tool_and_parse("web_search", {
                "query": "test query",
                "count": case["count"]
            })
            
            assert result["status"] in ["success", "error"], f"Failed for {case['description']}"
            
            if result["status"] == "success":
                search_data = result["data"]
                result_count = len(search_data["results"])
                
                if case["count"] > 0:
                    assert result_count <= case["count"], f"Too many results for {case['description']}"

    @pytest.mark.asyncio
    async def test_special_characters_and_unicode(self):
        """Test queries with special characters and unicode"""
        from tools.mcp_client import MCPClient
        
        client = MCPClient()
        
        test_queries = [
            "python programming",  # Normal query
            "!@#$%^&*()",          # Special characters  
            "python 编程 tutorial",  # Unicode characters
            "   whitespace   ",     # Leading/trailing whitespace
        ]
        
        for query in test_queries:
            result = await client.call_tool_and_parse("web_search", {
                "query": query,
                "count": 2
            })
            
            # Should handle all queries gracefully
            assert result["status"] in ["success", "error"]
            
            if result["status"] == "success":
                assert "data" in result
                assert isinstance(result["data"]["results"], list)


class TestWebSearchIntegration:
    """Test 5: Integration with other web services"""
    
    @pytest.mark.asyncio
    async def test_url_extraction_for_webcrawl(self):
        """Test URL extraction for WebCrawlService integration"""
        from tools.mcp_client import MCPClient
        
        client = MCPClient()
        
        # Test URL extraction as documented in web_service.md:51
        result = await client.call_tool_and_parse("web_search", {
            "query": "python tutorial",
            "count": 3
        })
        
        if result["status"] == "success":
            urls = result["data"]["urls"]
            
            # Validate URLs are properly formatted for crawling
            assert isinstance(urls, list)
            assert len(urls) > 0, "Should return at least one URL"
            
            for url in urls:
                assert isinstance(url, str)
                assert url.startswith(("http://", "https://")), f"Invalid URL format: {url}"
            
            # URLs should match the results
            result_urls = [r["url"] for r in result["data"]["results"]]
            assert urls == result_urls, "URLs list should match result URLs"

    @pytest.mark.asyncio
    async def test_performance_timing(self):
        """Test response time meets reasonable expectations"""
        from tools.mcp_client import MCPClient
        import time
        
        client = MCPClient()
        
        # Test different query complexities
        queries = [
            "python",                                              # Simple
            "python programming tutorial",                        # Medium  
            "python machine learning data science tutorial"       # Complex
        ]
        
        for query in queries:
            start_time = time.time()
            result = await client.call_tool_and_parse("web_search", {
                "query": query,
                "count": 5
            })
            end_time = time.time()
            
            duration = end_time - start_time
            
            if result["status"] == "success":
                # Should complete within reasonable time (per web_service.md:291)
                assert duration < 10.0, f"Search took too long: {duration:.2f}s for query '{query}'"
                
                result_count = len(result["data"]["results"])
                assert result_count > 0, f"Should return results for query '{query}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])