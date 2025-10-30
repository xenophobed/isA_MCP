#!/usr/bin/env python3
"""
Web Tools - Clean web-related tools implementation
Based on three core services: WebSearchService, WebCrawlService, WebAutomationService

Now using MCP-compliant Pydantic models from tools.models.tool_models
"""

import json
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP
from tools.base_tool import BaseTool
from tools.services.web_services.services.web_search_service import WebSearchService
from tools.services.web_services.services.web_crawl_service import WebCrawlService
from tools.services.web_services.services.web_automation_service import WebAutomationService
from core.security import SecurityLevel, get_security_manager

# Import MCP-compliant models
from tools.core import (
    SearchResultsResponse,
    SuccessResponse,
    ErrorResponse,
    ManualInterventionResponse,
    RequestCredentialUsageResponse,
    InterventionType,
    ToolStatus
)


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
    
    async def web_search(
        self,
        query: str,
        count: int = 10,
        freshness: str = None,
        result_filter: str = None,
        goggle_type: str = None,
        extra_snippets: bool = True,
        deep_search: bool = False
    ) -> Dict[str, Any]:
        """Enhanced web search implementation with advanced features (MCP-compliant)"""
        try:
            service = self._get_search_service()

            # Call service's search method with all parameters
            result = await service.search(
                query=query,
                count=count,
                freshness=freshness,
                result_filter=result_filter,
                goggle_type=goggle_type,
                extra_snippets=extra_snippets,
                deep_search=deep_search
            )

            # Return plain response dict (FastMCP will wrap it)
            if result.get("success"):
                return self.create_response(
                    "success",
                    "web_search",
                    {
                        "query": query,
                        "total": result.get("total", 0),
                        "results": result.get("results", []),
                        "urls": result.get("urls"),
                        "search_params": result.get("search_params")
                    }
                )
            else:
                return self.create_response(
                    "error",
                    "web_search",
                    result,
                    result.get("error", "Unknown error")
                )

        except Exception as e:
            return self.create_response(
                "error",
                "web_search",
                {},
                str(e)
            )
        finally:
            if self.search_service:
                await self.search_service.close()
                self.search_service = None
    
    async def web_crawl(self, url: str, analysis_request: str = "") -> Dict[str, Any]:
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
    
    async def web_crawl_compare(self, urls: List[str], analysis_request: str) -> Dict[str, Any]:
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
    
    async def web_automation(self, url: str, task: str, user_id: str = "default") -> Dict[str, Any]:
        """Web automation implementation"""
        try:
            service = self._get_automation_service()
            result = await service.execute_task(url, task, user_id)

            # Check if HIL is required
            if result.get("hil_required"):
                return self.create_response(
                    status=result.get("status", "human_required"),
                    action=result.get("action", "ask_human"),
                    data=result.get("data", {}),
                    error_message=result.get("message")
                )

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
    """
    Register web tools using FastMCP decorators

    NOTE: web_search has been moved to tools/web_search_tools.py
    This file now only contains web_crawl and web_automation
    """
    web_service = WebToolsService()

    # Get security manager for applying decorators
    security_manager = get_security_manager()

    # web_search has been moved to tools/web_search_tools.py for better separation

    @mcp.tool()
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def web_crawl(
        url: str,
        analysis_request: str = ""
    ) -> Dict[str, Any]:
        """
        Intelligently crawl and analyze web pages with enhanced extraction capabilities
        
        Extraction modes:
        - Basic BS4 (no analysis_request): Fast text, headings, paragraphs, links extraction
        - Enhanced BS4 (with analysis_request): Full structured data extraction including tables, 
          images, videos, code blocks, forms, metadata, SEO analysis, and readability scores
        - VLM Fallback: For non-HTML content or when BS4 fails
        
        Supports both single URL and multiple URL analysis:
        - Single URL: pass a single URL string
        - Multiple URLs: pass a JSON array string like '["url1", "url2"]'
        
        Enhanced features include:
        - Tables with preserved structure (headers and rows)
        - Images with alt text and dimensions
        - Video detection (HTML5 and iframe embeds)
        - Code block extraction with language detection
        - Form structure and fields
        - OpenGraph, Twitter Cards, JSON-LD metadata
        - Comprehensive SEO analysis (title, meta, H1/H2, links, schema.org)
        - Flesch Reading Ease readability scoring
        - Detailed extraction statistics
        
        Keywords: crawl, web, analyze, scrape, extract, page, compare, multiple, bs4, beautifulsoup, 
                  tables, images, seo, metadata, forms, code, readability
        Category: web
        
        Args:
            url: Target web page URL or JSON array of URLs for comparison
            analysis_request: Analysis request triggers enhanced mode (e.g., 'extract all structured data', 
                            'analyze SEO', 'compare product features')
        
        Examples:
            - Basic: {"url": "https://example.com"}
            - Enhanced: {"url": "https://example.com", "analysis_request": "extract tables and forms"}
            - Compare: {"url": '["https://site1.com", "https://site2.com"]', "analysis_request": "compare features"}
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
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def web_automation(
        url: str,
        task: str,
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Automate web browser interactions with HIL support

        Supports Human-in-Loop (HIL) for login, payment, wallet connections, and CAPTCHA.
        Returns HIL actions when authentication is needed:
        - request_authorization: When credentials exist in Vault, asks permission to use
        - ask_human: When credentials don't exist, asks user to provide

        Keywords: automation, browser, interact, task, web, hil, login, auth
        Category: web

        Args:
            url: Target web page URL
            task: Task description (e.g., 'search for airpods')
            user_id: User identifier for credential lookup (default: 'default')
        """
        return await web_service.web_automation(url, task, user_id)
    
    print("🌐 Web tools registered successfully")