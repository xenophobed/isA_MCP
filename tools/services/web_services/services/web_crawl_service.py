#!/usr/bin/env python3
"""
Web Crawl Service - Simplified Hybrid Content Extraction

Simplified architecture:
1. Default: BS4 text extraction (fast, clean)
2. Fallback: VLM analysis (comprehensive)
3. Analysis: text_generator for final synthesis
"""

import json
import asyncio
import requests
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, Page

from core.logging import get_logger

# Import atomic functions
from tools.services.web_services.services.bs4_service import extract_text as bs4_extract
from tools.services.intelligence_service.vision.image_analyzer import analyze as image_analyze
from tools.services.intelligence_service.language.text_generator import generate

logger = get_logger(__name__)


class WebCrawlService:
    """Simplified hybrid web crawling service"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        logger.info("✅ WebCrawlService initialized with simplified hybrid approach")
    
    async def crawl_and_analyze(self, url: str, analysis_request: Optional[str] = None) -> Dict[str, Any]:
        """
        Main crawling function with simplified hybrid approach
        
        Args:
            url: Target web page URL
            analysis_request: Optional analysis request
            
        Returns:
            Dictionary containing extracted and analyzed content
        """
        try:
            logger.info(f"🚀 Starting simplified crawl for: {url}")
            logger.info(f"📋 Analysis request: {analysis_request}")
            
            # Step 1: Try BS4 extraction first (default)
            can_use_bs4 = await self._can_use_bs4(url)
            
            if can_use_bs4:
                logger.info("✅ Using BS4 extraction method")
                result = await self._bs4_extraction_path(url, analysis_request)
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
        Multi-URL comparison with simplified approach
        
        Args:
            urls: List of URLs to compare
            analysis_request: Comparison analysis request
            
        Returns:
            Dictionary containing comparison results
        """
        try:
            logger.info(f"🚀 Starting multi-URL crawl for {len(urls)} URLs")
            
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
            
            # Generate comparison report using text_generator
            comparison_report = await self._generate_comparison_report(individual_results, analysis_request)
            
            return {
                "success": True,
                "analysis_request": analysis_request,
                "urls_count": len(urls),
                "urls": urls,
                "individual_results": individual_results,
                "comparison_report": comparison_report,
                "processing_time_ms": int(asyncio.get_event_loop().time() * 1000),
                "timestamp": str(asyncio.get_event_loop().time())
            }
            
        except Exception as e:
            logger.error(f"❌ Multi-URL crawl failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "urls": urls
            }
    
    async def _can_use_bs4(self, url: str) -> bool:
        """
        Determine if BS4 extraction is viable (DEFAULT: True)
        
        Args:
            url: Target URL
            
        Returns:
            True if BS4 extraction should work (DEFAULT: True)
        """
        try:
            # Quick HEAD request to check content type
            response = requests.head(url, timeout=10, allow_redirects=True)
            
            # Check if it's HTML content
            content_type = response.headers.get('content-type', '').lower()
            if 'html' not in content_type:
                return False
            
            # Default to BS4 unless clearly problematic
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Could not determine extraction method, defaulting to BS4: {e}")
            return True  # Default to BS4 on error
    
    async def _bs4_extraction_path(self, url: str, analysis_request: Optional[str]) -> Dict[str, Any]:
        """
        BS4 extraction path using bs4_service + text_generator
        
        Args:
            url: Target URL
            analysis_request: Analysis request
            
        Returns:
            Extraction results
        """
        try:
            logger.info("🔧 Starting BS4 extraction...")
            
            # Use enhanced mode when analysis is requested for richer data
            use_enhanced = bool(analysis_request)
            
            # Extract text using BS4 service
            bs4_result = await bs4_extract(url, enhanced=use_enhanced)
            
            if not bs4_result.success:
                logger.warning(f"BS4 extraction failed: {bs4_result.error}")
                # Fall back to VLM if BS4 fails
                return await self._vlm_analysis_path(url, analysis_request)
            
            # Generate analysis using text_generator if requested
            final_analysis = ""
            if analysis_request and bs4_result.content:
                final_analysis = await self._synthesize_bs4_results(bs4_result, analysis_request)
            
            result = {
                "method": "bs4_extraction" + ("_enhanced" if use_enhanced else ""),
                "success": True,
                "content": bs4_result.content,
                "title": bs4_result.title,
                "headings": bs4_result.headings,
                "paragraphs": bs4_result.paragraphs,
                "links": bs4_result.links,
                "word_count": bs4_result.word_count,
                "processing_time": bs4_result.processing_time,
                "final_report": final_analysis,
                "raw_data": {
                    "title": bs4_result.title,
                    "content": bs4_result.content[:1000] + "..." if len(bs4_result.content) > 1000 else bs4_result.content,
                    "headings_count": len(bs4_result.headings),
                    "paragraphs_count": len(bs4_result.paragraphs),
                    "links_count": len(bs4_result.links)
                }
            }
            
            # Add enhanced data if available
            if use_enhanced:
                result["tables"] = bs4_result.tables
                result["images"] = bs4_result.images
                result["videos"] = bs4_result.videos
                result["code_blocks"] = bs4_result.code_blocks
                result["lists"] = bs4_result.lists
                result["forms"] = bs4_result.forms
                result["metadata"] = bs4_result.metadata
                result["seo_analysis"] = bs4_result.seo_analysis
                result["readability_score"] = bs4_result.readability_score
                result["extraction_stats"] = bs4_result.extraction_stats
                
                # Update raw_data with enhanced stats
                result["raw_data"].update({
                    "tables_count": len(bs4_result.tables),
                    "images_count": len(bs4_result.images),
                    "videos_count": len(bs4_result.videos),
                    "code_blocks_count": len(bs4_result.code_blocks),
                    "forms_count": len(bs4_result.forms)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ BS4 extraction path failed: {e}")
            # Fall back to VLM
            return await self._vlm_analysis_path(url, analysis_request)
    
    async def _vlm_analysis_path(self, url: str, analysis_request: Optional[str]) -> Dict[str, Any]:
        """
        VLM analysis path using image_analyzer + text_generator
        
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
            prompt = self._create_vlm_prompt(analysis_request or "extract and analyze main content")
            
            # Use image_analyzer atomic function
            vlm_result = await image_analyze(
                image=screenshot,
                prompt=prompt,
                provider="openai"
            )
            
            await self._cleanup_browser()
            
            if vlm_result.success:
                # Generate final synthesis using text_generator if needed
                final_analysis = vlm_result.response
                if analysis_request:
                    final_analysis = await self._synthesize_vlm_results(vlm_result.response, analysis_request)
                
                return {
                    "method": "vlm_analysis",
                    "success": True,
                    "content": vlm_result.response,
                    "model_used": vlm_result.model_used,
                    "processing_time": vlm_result.processing_time,
                    "final_report": final_analysis,
                    "raw_data": {
                        "analysis_length": len(vlm_result.response),
                        "model": vlm_result.model_used,
                        "processing_time": vlm_result.processing_time
                    }
                }
            else:
                return {
                    "method": "vlm_analysis",
                    "success": False,
                    "error": vlm_result.error,
                    "final_report": f"VLM analysis failed: {vlm_result.error}"
                }
                
        except Exception as e:
            logger.error(f"❌ VLM analysis failed: {e}")
            return {
                "method": "vlm_analysis",
                "success": False,
                "error": str(e),
                "final_report": f"Analysis failed: {str(e)}"
            }
    
    def _create_vlm_prompt(self, analysis_request: str) -> str:
        """Create VLM analysis prompt"""
        return f"""Analyze this webpage screenshot for: "{analysis_request}"

Please provide a comprehensive analysis including:

1. **Main Content Overview**
   - Page type and purpose
   - Key sections and layout
   - Primary content focus

2. **Specific Analysis**
   - Address the request: {analysis_request}
   - Extract relevant information
   - Identify key data points

3. **Content Summary**
   - Main findings and insights
   - Important details
   - Notable characteristics

4. **Structured Output**
   - Organize information clearly
   - Use bullet points for key items
   - Provide actionable information

Format as a clear, well-structured analysis."""
    
    async def _synthesize_bs4_results(self, bs4_result, analysis_request: str) -> str:
        """Synthesize BS4 results using text_generator"""
        try:
            # Prepare content summary
            content_summary = f"""
Title: {bs4_result.title}
Word Count: {bs4_result.word_count}
Headings: {len(bs4_result.headings)}
Paragraphs: {len(bs4_result.paragraphs)}
Links: {len(bs4_result.links)}

Content Preview:
{bs4_result.content[:1000]}...

Sample Headings:
{json.dumps([h['text'] for h in bs4_result.headings[:5]], indent=2)}
"""
            
            # Add enhanced data if available
            if hasattr(bs4_result, 'tables') and bs4_result.tables:
                content_summary += f"\nTables: {len(bs4_result.tables)} tables found"
                if bs4_result.tables:
                    content_summary += f"\nFirst table headers: {bs4_result.tables[0].get('headers', [])[:5]}"
            
            if hasattr(bs4_result, 'images') and bs4_result.images:
                content_summary += f"\nImages: {len(bs4_result.images)} images"
                img_with_alt = sum(1 for img in bs4_result.images if img.get('alt'))
                content_summary += f" ({img_with_alt} with alt text)"
            
            if hasattr(bs4_result, 'code_blocks') and bs4_result.code_blocks:
                content_summary += f"\nCode Blocks: {len(bs4_result.code_blocks)}"
                languages = set(cb.get('language', 'unknown') for cb in bs4_result.code_blocks[:10])
                content_summary += f" (languages: {', '.join(languages)})"
            
            if hasattr(bs4_result, 'seo_analysis') and bs4_result.seo_analysis:
                content_summary += f"\n\nSEO Analysis:"
                seo = bs4_result.seo_analysis
                content_summary += f"\n- Title length: {seo.get('title_length', 0)} chars"
                content_summary += f"\n- Meta description: {'Present' if seo.get('meta_description') else 'Missing'}"
                content_summary += f"\n- H1 count: {seo.get('h1_count', 0)}"
                content_summary += f"\n- Internal links: {seo.get('internal_links_count', 0)}"
                content_summary += f"\n- External links: {seo.get('external_links_count', 0)}"
            
            if hasattr(bs4_result, 'metadata') and bs4_result.metadata:
                content_summary += f"\n\nMetadata:"
                for key in ['og:title', 'og:description', 'author', 'keywords'][:4]:
                    if key in bs4_result.metadata:
                        value = str(bs4_result.metadata[key])[:100]
                        content_summary += f"\n- {key}: {value}"
            
            prompt = f"""Based on this extracted webpage content, create a comprehensive analysis for: "{analysis_request}"

{content_summary}

Please provide:
1. Summary of findings relevant to the request
2. Key insights and information
3. Structured analysis of the content
4. Actionable conclusions

Format as a clear, professional report."""
            
            response = await generate(prompt, temperature=0.7)
            return response
            
        except Exception as e:
            logger.error(f"❌ BS4 synthesis failed: {e}")
            return f"BS4 extraction completed ({bs4_result.word_count} words). Analysis synthesis failed: {str(e)}"
    
    async def _synthesize_vlm_results(self, vlm_response: str, analysis_request: str) -> str:
        """Synthesize VLM results using text_generator"""
        try:
            prompt = f"""Based on this VLM analysis of a webpage, create a refined report for: "{analysis_request}"

VLM Analysis:
{vlm_response}

Please provide:
1. Enhanced summary focused on the request
2. Key insights and findings
3. Structured analysis
4. Actionable conclusions

Format as a clear, professional report."""
            
            response = await generate(prompt, temperature=0.7)
            return response
            
        except Exception as e:
            logger.error(f"❌ VLM synthesis failed: {e}")
            return vlm_response  # Return original VLM response if synthesis fails
    
    async def _generate_comparison_report(self, individual_results: List[Dict[str, Any]], analysis_request: str) -> str:
        """Generate comparison report using text_generator"""
        try:
            # Collect successful results
            successful_results = [r for r in individual_results if r.get("success")]
            
            if not successful_results:
                return "# Comparison Report\n\n❌ All URL analyses failed. No comparison possible."
            
            # Prepare comparison data
            comparison_data = []
            for result in successful_results[:5]:  # Limit to 5 items
                analysis_result = result.get("analysis_result", {})
                result_data = analysis_result.get("result", {})
                
                comparison_data.append({
                    "url": result.get("url"),
                    "method": result_data.get("method", "unknown"),
                    "title": result_data.get("title", "No title"),
                    "content_preview": result_data.get("content", "")[:300] + "...",
                    "final_report": result_data.get("final_report", "No analysis available")[:500] + "..."
                })
            
            prompt = f"""Create a comprehensive comparison report for: "{analysis_request}"

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
    """Test the simplified web crawl service"""
    service = WebCrawlService()
    
    try:
        # Test with example.com (should use BS4)
        result1 = await service.crawl_and_analyze(
            "https://example.com", 
            "extract main content and analyze the page"
        )
        print(f"Test 1 Result: {result1.get('result', {}).get('method')} - {result1.get('success')}")
        print(f"Content: {result1.get('result', {}).get('content', '')[:200]}...")
        
    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(test_web_crawl_service())