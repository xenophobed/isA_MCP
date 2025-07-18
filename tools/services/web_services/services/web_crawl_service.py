#!/usr/bin/env python
"""
Web Crawl Service - Intelligent Hybrid Content Extraction

Elegant, generic hybrid approach:
1. Try traditional extraction (BeautifulSoup + CSS selectors) first
2. Fall back to VLM analysis only when needed
3. Use atomic functions for clean separation
4. Synthesize final output with best from both methods
"""

import json
import asyncio
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page

from core.logging import get_logger

# Import atomic functions
from tools.services.intelligence_service.vision.image_analyzer import analyze as image_analyze
from tools.services.intelligence_service.language.text_generator import generate

# Import extraction and filtering strategies
from tools.services.web_services.strategies.extraction.css_extraction import CSSExtractionStrategy, PredefinedSchemas
from tools.services.web_services.strategies.filtering.pruning_filter import PruningFilter

logger = get_logger(__name__)


class WebCrawlService:
    """Intelligent hybrid web crawling service"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        logger.info("✅ WebCrawlService initialized with hybrid approach")
    
    async def crawl_and_analyze(self, url: str, analysis_request: Optional[str] = None) -> Dict[str, Any]:
        """
        Main crawling function with hybrid approach
        
        Args:
            url: Target web page URL
            analysis_request: Optional analysis request
            
        Returns:
            Dictionary containing extracted and analyzed content
        """
        try:
            logger.info(f"🚀 Starting hybrid crawl for: {url}")
            logger.info(f"📋 Analysis request: {analysis_request}")
            
            # Step 1: Check if traditional extraction is viable
            can_extract_traditionally = await self._can_extract_traditionally(url)
            
            result = {}
            
            if can_extract_traditionally:
                logger.info("✅ Using traditional extraction method")
                result = await self._traditional_extraction_path(url, analysis_request)
            else:
                logger.info("🔄 Falling back to VLM analysis method")
                result = await self._vlm_analysis_path(url, analysis_request)
            
            return {
                "success": True,
                "url": url,
                "analysis_request": analysis_request or "",
                "extraction_method": result.get("method", "unknown"),
                "result": result,
                "timestamp": str(asyncio.get_event_loop().time())
            }
            
        except Exception as e:
            logger.error(f"❌ Web crawl failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    async def crawl_and_compare_multiple(self, urls: List[str], analysis_request: str) -> Dict[str, Any]:
        """
        Multi-URL comparison with hybrid approach
        
        Args:
            urls: List of URLs to compare
            analysis_request: Comparison analysis request
            
        Returns:
            Dictionary containing comparison results
        """
        try:
            logger.info(f"🚀 Starting multi-URL hybrid crawl for {len(urls)} URLs")
            
            # Crawl each URL
            individual_results = []
            for i, url in enumerate(urls):
                logger.info(f"📄 Processing URL {i+1}/{len(urls)}: {url}")
                
                try:
                    result = await self.crawl_and_analyze(url, analysis_request)
                    individual_results.append({
                        "url": url,
                        "item_index": i + 1,
                        "analysis_result": result,
                        "success": result.get("success", False)
                    })
                except Exception as e:
                    logger.error(f"❌ Failed to process URL {i+1}: {e}")
                    individual_results.append({
                        "url": url,
                        "item_index": i + 1,
                        "error": str(e),
                        "success": False
                    })
            
            # Generate comparison report
            comparison_report = await self._generate_comparison_report(individual_results, analysis_request)
            
            return {
                "success": True,
                "analysis_request": analysis_request,
                "urls_count": len(urls),
                "individual_results": individual_results,
                "comparison_report": comparison_report,
                "timestamp": str(asyncio.get_event_loop().time())
            }
            
        except Exception as e:
            logger.error(f"❌ Multi-URL crawl failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "urls": urls
            }
    
    async def _can_extract_traditionally(self, url: str) -> bool:
        """
        Determine if traditional extraction (BeautifulSoup) is viable
        
        Args:
            url: Target URL
            
        Returns:
            True if traditional extraction should work
        """
        try:
            # Quick HEAD request to check content type and accessibility
            response = requests.head(url, timeout=10, allow_redirects=True)
            
            # Check if it's HTML content
            content_type = response.headers.get('content-type', '').lower()
            if 'html' not in content_type:
                return False
            
            # Check if it's a simple static page (no heavy JS)
            # Simple heuristics: if it's a known SPA framework or has specific patterns
            response = requests.get(url, timeout=15)
            html_content = response.text.lower()
            
            # Indicators that suggest heavy JS/SPA (need VLM)
            js_heavy_indicators = [
                'react', 'angular', 'vue.js', 'next.js', 'nuxt',
                'document.write', 'eval(', 'webpack',
                'data-reactroot', 'ng-app', 'v-app'
            ]
            
            # If too many JS indicators, prefer VLM
            js_score = sum(1 for indicator in js_heavy_indicators if indicator in html_content)
            
            # Check if there's substantial static content
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style tags
            for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
            
            text_content = soup.get_text(strip=True)
            word_count = len(text_content.split())
            
            # Decision logic
            has_good_content = word_count > 100
            not_too_js_heavy = js_score < 3
            
            return has_good_content and not_too_js_heavy
            
        except Exception as e:
            logger.warning(f"⚠️ Could not determine extraction method, defaulting to VLM: {e}")
            return False
    
    async def _traditional_extraction_path(self, url: str, analysis_request: Optional[str]) -> Dict[str, Any]:
        """
        Traditional extraction using BeautifulSoup + CSS selectors
        
        Args:
            url: Target URL
            analysis_request: Analysis request
            
        Returns:
            Extraction results
        """
        try:
            logger.info("🔧 Starting traditional extraction...")
            
            # Fetch content
            response = requests.get(url, timeout=30)
            html_content = response.text
            
            # Apply content filtering
            pruning_filter = PruningFilter(threshold=0.3, min_word_threshold=5)
            filtered_content = await pruning_filter.filter(html_content)
            
            # Determine extraction schema based on analysis request
            schema = self._select_extraction_schema(analysis_request, filtered_content)
            
            # Start browser for CSS extraction
            await self._start_browser()
            await self.page.goto(url, wait_until="domcontentloaded")
            
            # Extract structured data
            css_extractor = CSSExtractionStrategy(schema)
            extracted_data = await css_extractor.extract(self.page, filtered_content)
            
            # Generate final analysis if requested
            final_analysis = ""
            if analysis_request and extracted_data:
                final_analysis = await self._synthesize_traditional_results(extracted_data, analysis_request)
            
            await self._cleanup_browser()
            
            return {
                "method": "traditional_extraction",
                "process_type": "css_extraction",
                "schema_used": schema["name"],
                "extracted_items": len(extracted_data),
                "structured_data": extracted_data,
                "final_report": final_analysis,
                "content_length": len(filtered_content)
            }
            
        except Exception as e:
            logger.error(f"❌ Traditional extraction failed: {e}")
            # Fall back to VLM
            return await self._vlm_analysis_path(url, analysis_request)
    
    async def _vlm_analysis_path(self, url: str, analysis_request: Optional[str]) -> Dict[str, Any]:
        """
        VLM-based analysis using image_analyzer atomic function
        
        Args:
            url: Target URL
            analysis_request: Analysis request
            
        Returns:
            VLM analysis results
        """
        try:
            logger.info("🧠 Starting VLM analysis...")
            
            # Start browser and navigate
            await self._start_browser()
            await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)  # Let page render
            
            # Take screenshot
            screenshot = await self.page.screenshot()
            
            # Create analysis prompt
            prompt = self._create_vlm_analysis_prompt(analysis_request or "extract main content")
            
            # Use image_analyzer atomic function
            result = await image_analyze(
                image=screenshot,
                prompt=prompt,
                provider="openai"
            )
            
            await self._cleanup_browser()
            
            if result.success:
                return {
                    "method": "vlm_analysis",
                    "process_type": "vision_analysis",
                    "model_used": result.model_used,
                    "processing_time": result.processing_time,
                    "final_report": result.response,
                    "analysis_length": len(result.response)
                }
            else:
                return {
                    "method": "vlm_analysis",
                    "process_type": "vision_analysis",
                    "error": result.error,
                    "final_report": f"VLM analysis failed: {result.error}"
                }
                
        except Exception as e:
            logger.error(f"❌ VLM analysis failed: {e}")
            return {
                "method": "vlm_analysis",
                "process_type": "vision_analysis",
                "error": str(e),
                "final_report": f"Analysis failed: {str(e)}"
            }
    
    def _select_extraction_schema(self, analysis_request: Optional[str], content: str) -> Dict[str, Any]:
        """
        Select appropriate extraction schema based on request and content
        
        Args:
            analysis_request: User's analysis request
            content: HTML content to analyze
            
        Returns:
            Appropriate extraction schema
        """
        if not analysis_request:
            # Default to general content extraction
            return self._create_generic_content_schema()
        
        request_lower = analysis_request.lower()
        
        # Match request patterns to schemas
        if any(word in request_lower for word in ['product', 'price', 'shop', 'buy', 'ecommerce']):
            return PredefinedSchemas.get_product_listings_schema()
        elif any(word in request_lower for word in ['news', 'article', 'blog', 'post']):
            return PredefinedSchemas.get_news_articles_schema()
        elif any(word in request_lower for word in ['contact', 'email', 'phone', 'address']):
            return PredefinedSchemas.get_contact_info_schema()
        elif any(word in request_lower for word in ['table', 'data', 'stats', 'numbers']):
            return PredefinedSchemas.get_table_data_schema()
        elif any(word in request_lower for word in ['link', 'navigation', 'menu']):
            return PredefinedSchemas.get_navigation_links_schema()
        else:
            # Analyze content to determine type
            content_lower = content.lower()
            if content_lower.count('price') > 3 or content_lower.count('product') > 3:
                return PredefinedSchemas.get_product_listings_schema()
            elif content_lower.count('article') > 2 or content_lower.count('author') > 1:
                return PredefinedSchemas.get_news_articles_schema()
            else:
                return self._create_generic_content_schema()
    
    def _create_generic_content_schema(self) -> Dict[str, Any]:
        """Create a generic content extraction schema"""
        return {
            "name": "Generic Content",
            "baseSelector": "main, article, .content, .main, .post, .article, body",
            "fields": [
                {"name": "title", "selector": "h1, h2, .title, title", "type": "text"},
                {"name": "content", "selector": "p, .content, .text, .description", "type": "list"},
                {"name": "headings", "selector": "h1, h2, h3, h4, h5, h6", "type": "list"},
                {"name": "links", "selector": "a[href]", "type": "list"},
                {"name": "images", "selector": "img", "type": "attribute", "attribute": "src"}
            ]
        }
    
    def _create_vlm_analysis_prompt(self, analysis_request: str) -> str:
        """
        Create appropriate VLM analysis prompt
        
        Args:
            analysis_request: User's analysis request
            
        Returns:
            Formatted prompt for VLM
        """
        return f"""Analyze this webpage screenshot for the following request: "{analysis_request}"

Please provide a comprehensive analysis including:

1. **Main Content Overview**
   - What type of page is this?
   - What is the primary purpose/content?
   - Key sections and layout

2. **Specific Analysis for Request**
   - Address the specific request: {analysis_request}
   - Extract relevant information
   - Identify key data points

3. **Content Summary**
   - Main findings and insights
   - Important details or specifications
   - Any notable characteristics

4. **Structured Findings**
   - Organize information clearly
   - Use bullet points for key items
   - Provide actionable information

Format your response as a clear, well-structured analysis that directly addresses the request."""
    
    async def _synthesize_traditional_results(self, extracted_data: List[Dict[str, Any]], analysis_request: str) -> str:
        """
        Synthesize traditional extraction results using text generation
        
        Args:
            extracted_data: Extracted structured data
            analysis_request: User's analysis request
            
        Returns:
            Synthesized analysis report
        """
        try:
            # Prepare data summary
            data_summary = json.dumps(extracted_data[:10], indent=2)  # Limit to first 10 items
            
            prompt = f"""Based on the following extracted data from a webpage, create a comprehensive analysis report for this request: "{analysis_request}"

Extracted Data:
{data_summary}

Please provide:
1. Summary of findings
2. Key insights related to the request
3. Structured analysis of the data
4. Actionable conclusions

Format as a clear, professional report."""
            
            response = await generate(prompt, temperature=0.7)
            return response
            
        except Exception as e:
            logger.error(f"❌ Synthesis failed: {e}")
            return f"Extracted {len(extracted_data)} items. Analysis synthesis failed: {str(e)}"
    
    async def _generate_comparison_report(self, individual_results: List[Dict[str, Any]], analysis_request: str) -> str:
        """
        Generate comparison report using text generation
        
        Args:
            individual_results: Results from individual URL analysis
            analysis_request: Comparison request
            
        Returns:
            Comparison report
        """
        try:
            # Collect successful results
            successful_results = [r for r in individual_results if r.get("success")]
            
            if not successful_results:
                return "# Comparison Report\n\n❌ All URL analyses failed. No comparison possible."
            
            # Prepare comparison data
            comparison_data = []
            for result in successful_results[:5]:  # Limit to 5 items
                analysis_result = result.get("analysis_result", {})
                final_report = analysis_result.get("result", {}).get("final_report", "No report available")
                
                comparison_data.append({
                    "url": result.get("url"),
                    "method": analysis_result.get("result", {}).get("method", "unknown"),
                    "summary": final_report[:500] + "..." if len(final_report) > 500 else final_report
                })
            
            # Generate comparison using text generation
            prompt = f"""Create a comprehensive comparison report for this request: "{analysis_request}"

Data from {len(comparison_data)} websites:

{json.dumps(comparison_data, indent=2)}

Please provide:
1. **Executive Summary** - Key findings across all sites
2. **Detailed Comparison** - Compare specific aspects
3. **Insights and Patterns** - Common themes and differences  
4. **Recommendations** - Conclusions and suggestions

Format as a professional markdown report."""
            
            response = await generate(prompt, temperature=0.7)
            return response
            
        except Exception as e:
            logger.error(f"❌ Comparison report generation failed: {e}")
            return f"# Comparison Report\n\nGeneration failed: {str(e)}"
    
    async def _start_browser(self):
        """Start browser if not already running"""
        if self.browser is None:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            self.page = await context.new_page()
    
    async def _cleanup_browser(self):
        """Clean up browser resources"""
        try:
            if self.page:
                await self.page.close()
                self.page = None
            if self.browser:
                await self.browser.close()
                self.browser = None
        except Exception as e:
            logger.warning(f"⚠️ Browser cleanup error: {e}")
    
    async def close(self):
        """Close service and cleanup resources"""
        await self._cleanup_browser()
        logger.info("✅ WebCrawlService closed")


# Test function
async def test_web_crawl_service():
    """Test the hybrid web crawl service"""
    service = WebCrawlService()
    
    try:
        # Test with a simple page (should use traditional extraction)
        result1 = await service.crawl_and_analyze(
            "https://httpbin.org/html", 
            "extract main content"
        )
        print(f"Test 1 Result: {result1.get('result', {}).get('method')} - {result1.get('success')}")
        
        # Test with a complex page (should use VLM)
        result2 = await service.crawl_and_analyze(
            "https://www.google.com", 
            "analyze page layout and functionality"
        )
        print(f"Test 2 Result: {result2.get('result', {}).get('method')} - {result2.get('success')}")
        
    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(test_web_crawl_service())