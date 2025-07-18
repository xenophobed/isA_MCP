#!/usr/bin/env python3
"""
Web Tools - Clean web-related tools implementation
Based on three core services: WebSearchService, WebCrawlService, WebAutomationService
"""

import json
from typing import List
from mcp.server.fastmcp import FastMCP
from tools.base_tool import BaseTool
from tools.services.web_services.services.web_search_service import WebSearchService
from tools.services.web_services.services.web_crawl_service import WebCrawlService
from tools.services.web_services.services.web_automation_service import WebAutomationService


class WebToolsService(BaseTool):
    """Web tools service for internal use"""
    
    def __init__(self):
        super().__init__()
        self.search_service = None
        self.crawl_service = None
        self.automation_service = None
    
    def _get_search_service(self):
        """Lazy initialize search service"""
        if self.search_service is None:
            self.search_service = WebSearchService()
        return self.search_service
    
    def _get_crawl_service(self):
        """Lazy initialize crawl service"""
        if self.crawl_service is None:
            self.crawl_service = WebCrawlService()
        return self.crawl_service
    
    def _get_automation_service(self):
        """Lazy initialize automation service"""
        if self.automation_service is None:
            self.automation_service = WebAutomationService()
        return self.automation_service
    
    async def web_search(self, query: str, count: int = 10) -> str:
        """Web search implementation"""
        try:
            service = self._get_search_service()
            result = await service.search(query, count)
            
            return self.create_response(
                status="success" if result.get("success") else "error",
                action="web_search",
                data=result,
                error_message=result.get("error") if not result.get("success") else None
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="web_search", 
                data={},
                error_message=str(e)
            )
        finally:
            if self.search_service:
                await self.search_service.close()
                self.search_service = None
    
    async def web_crawl(self, url: str, analysis_request: str = "") -> str:
        """Web crawl implementation"""
        try:
            service = self._get_crawl_service()
            result = await service.crawl_and_analyze(url, analysis_request)
            
            return self.create_response(
                status="success" if result.get("success") else "error",
                action="web_crawl",
                data=result,
                error_message=result.get("error") if not result.get("success") else None
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="web_crawl",
                data={},
                error_message=str(e)
            )
        finally:
            if self.crawl_service:
                await self.crawl_service.close()
                self.crawl_service = None
    
    async def web_crawl_compare(self, urls: List[str], analysis_request: str) -> str:
        """Web crawl compare implementation"""
        try:
            service = self._get_crawl_service()
            result = await service.crawl_and_compare_multiple(urls, analysis_request)
            
            return self.create_response(
                status="success" if result.get("success") else "error",
                action="web_crawl_compare",
                data=result,
                error_message=result.get("error") if not result.get("success") else None
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="web_crawl_compare",
                data={},
                error_message=str(e)
            )
        finally:
            if self.crawl_service:
                await self.crawl_service.close()
                self.crawl_service = None
    
    async def web_automation(self, url: str, task: str) -> str:
        """Web automation implementation"""
        try:
            service = self._get_automation_service()
            result = await service.execute_task(url, task)
            
            return self.create_response(
                status="success" if result.get("success") else "error",
                action="web_automation",
                data=result,
                error_message=result.get("error") if not result.get("success") else None
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="web_automation",
                data={},
                error_message=str(e)
            )
        finally:
            if self.automation_service:
                await self.automation_service.close()
                self.automation_service = None


def register_web_tools(mcp: FastMCP):
    """Register web tools using FastMCP decorators"""
    web_service = WebToolsService()
    
    @mcp.tool()
    async def web_search(
        query: str,
        count: int = 10
    ) -> str:
        """
        Search the web for information
        
        Keywords: search, web, internet, query, results
        Category: web
        
        Args:
            query: Search query
            count: Number of results to return (default: 10)
        """
        return await web_service.web_search(query, count)
    
    @mcp.tool()
    async def web_crawl(
        url: str,
        analysis_request: str = ""
    ) -> str:
        """
        Intelligently crawl and analyze web pages using VLM+LLM
        
        Supports both single URL and multiple URL analysis:
        - Single URL: pass a single URL string
        - Multiple URLs: pass a JSON array string like '["url1", "url2"]'
        
        Keywords: crawl, web, analyze, scrape, extract, page, compare, multiple
        Category: web
        
        Args:
            url: Target web page URL or JSON array of URLs for comparison
            analysis_request: Analysis request (e.g., 'analyze product reviews', 'compare product features')
        """
        # Check if URL is a JSON array (multiple URLs)
        if url.strip().startswith('[') or url.strip().startswith('{'):
            try:
                urls_data = json.loads(url)
                
                # Reject JSON objects - only arrays are allowed
                if not isinstance(urls_data, list):
                    return web_service.create_response(
                        "error",
                        "web_crawl",
                        {},
                        "Invalid URL array format - only JSON arrays are supported, not objects"
                    )
                
                # Validate that all items in the array are strings
                if not all(isinstance(item, str) for item in urls_data):
                    return web_service.create_response(
                        "error",
                        "web_crawl",
                        {},
                        "Invalid URL array format - all items must be strings"
                    )
                
                # Validate that array is not empty
                if len(urls_data) == 0:
                    return web_service.create_response(
                        "error",
                        "web_crawl",
                        {},
                        "Invalid URL array format - array cannot be empty"
                    )
                
                if len(urls_data) > 1:
                    # Multiple URLs - use comparison analysis
                    return await web_service.web_crawl_compare(urls_data, analysis_request)
                else:
                    # Single URL in array format
                    return await web_service.web_crawl(urls_data[0], analysis_request)
                    
            except json.JSONDecodeError:
                return web_service.create_response(
                    "error",
                    "web_crawl",
                    {},
                    "Invalid JSON array format for URLs"
                )
        else:
            # Single URL
            return await web_service.web_crawl(url, analysis_request)
    
    @mcp.tool()
    async def web_automation(
        url: str,
        task: str
    ) -> str:
        """
        Automate web browser interactions
        
        Keywords: automation, browser, interact, task, web
        Category: web
        
        Args:
            url: Target web page URL
            task: Task description (e.g., 'search for airpods')
        """
        return await web_service.web_automation(url, task)
    
    print("🌐 Web tools registered successfully")