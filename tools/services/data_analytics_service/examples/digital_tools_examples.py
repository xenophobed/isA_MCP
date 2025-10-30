"""
Digital Tools Client Example

Professional MCP client for knowledge management operations with RAG, vector search, and multimodal support.
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result data"""
    status: str
    total_results: int
    total_pages: int
    total_photos: int
    search_method: str
    results: List[Dict[str, Any]]


@dataclass
class RAGResponse:
    """RAG response data"""
    status: str
    response: str
    response_type: str
    page_count: int
    photo_count: int
    inline_citations_enabled: bool
    sources: List[Dict[str, Any]]


class DigitalToolsClient:
    """Professional Digital Tools MCP Client"""

    def __init__(
        self,
        base_url: str = "http://localhost:8081",
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip('/')
        self.mcp_endpoint = f"{self.base_url}/mcp"
        self.timeout = timeout
        self.max_retries = max_retries
        self.client: Optional[httpx.AsyncClient] = None
        self.request_count = 0
        self.error_count = 0

    async def __aenter__(self):
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=60.0
        )
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=limits,
            headers={
                "User-Agent": "digital-tools-client/1.0",
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    def _parse_sse_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse SSE response and extract JSON data"""
        for line in response_text.split('\n'):
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])  # Remove 'data: ' prefix
                    if 'result' in data:
                        result = data['result']
                        if isinstance(result, dict) and 'content' in result:
                            for content_item in result['content']:
                                if content_item.get('type') == 'text':
                                    return json.loads(content_item['text'])
                except json.JSONDecodeError:
                    continue
        return None

    async def _call_mcp_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Call MCP tool and parse response"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        last_exception = None
        for attempt in range(self.max_retries):
            try:
                self.request_count += 1
                response = await self.client.post(self.mcp_endpoint, json=payload)
                response.raise_for_status()

                result = self._parse_sse_response(response.text)
                if result:
                    return result
                else:
                    raise Exception("Failed to parse SSE response")

            except httpx.HTTPStatusError as e:
                last_exception = e
                self.error_count += 1
                if 400 <= e.response.status_code < 500:
                    raise Exception(f"Client error: {e.response.status_code} - {e.response.text}")
            except httpx.ConnectError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))
            except Exception as e:
                last_exception = e
                self.error_count += 1
                raise

        self.error_count += 1
        raise Exception(f"Request failed after {self.max_retries} attempts: {last_exception}")

    async def store_knowledge(
        self,
        user_id: str,
        content: str,
        content_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Store knowledge (text, document, PDF, image)"""
        arguments = {
            "user_id": user_id,
            "content": content,
            "content_type": content_type,
            "metadata": metadata or {},
            "tags": tags or []
        }
        return await self._call_mcp_tool("store_knowledge", arguments)

    async def search_knowledge(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        content_type: Optional[str] = None,
        content_types: Optional[List[str]] = None,
        search_mode: str = "hybrid",
        enable_rerank: bool = False,
        return_format: str = "results"
    ) -> SearchResult:
        """Search knowledge base"""
        search_options = {
            "top_k": top_k,
            "search_mode": search_mode,
            "enable_rerank": enable_rerank,
            "return_format": return_format
        }

        if content_type:
            search_options["content_type"] = content_type
        if content_types:
            search_options["content_types"] = content_types

        arguments = {
            "user_id": user_id,
            "query": query,
            "search_options": search_options
        }

        result = await self._call_mcp_tool("search_knowledge", arguments)

        return SearchResult(
            status=result.get("status", "error"),
            total_results=result.get("data", {}).get("total_results", 0),
            total_pages=result.get("data", {}).get("total_pages", 0),
            total_photos=result.get("data", {}).get("total_photos", 0),
            search_method=result.get("data", {}).get("search_method", "unknown"),
            results=result.get("data", {}).get("results", [])
        )

    async def knowledge_response(
        self,
        user_id: str,
        query: str,
        rag_mode: str = "simple",
        context_limit: int = 5,
        model: str = "gpt-4o-mini",
        provider: str = "yyds",
        temperature: float = 0.3,
        use_pdf_context: bool = False,
        auto_detect_pdf: bool = False,
        include_images: bool = False,
        enable_citations: bool = True
    ) -> RAGResponse:
        """Generate RAG response"""
        response_options = {
            "rag_mode": rag_mode,
            "context_limit": context_limit,
            "model": model,
            "provider": provider,
            "temperature": temperature,
            "use_pdf_context": use_pdf_context,
            "auto_detect_pdf": auto_detect_pdf,
            "include_images": include_images,
            "enable_citations": enable_citations
        }

        arguments = {
            "user_id": user_id,
            "query": query,
            "response_options": response_options
        }

        result = await self._call_mcp_tool("knowledge_response", arguments)

        return RAGResponse(
            status=result.get("status", "error"),
            response=result.get("data", {}).get("response", result.get("data", {}).get("answer", "")),
            response_type=result.get("data", {}).get("response_type", "simple_rag"),
            page_count=result.get("data", {}).get("page_count", 0),
            photo_count=result.get("data", {}).get("photo_count", 0),
            inline_citations_enabled=result.get("data", {}).get("inline_citations_enabled", False),
            sources=result.get("data", {}).get("sources", [])
        )

    async def get_service_status(self) -> Dict[str, Any]:
        """Get service health and status"""
        return await self._call_mcp_tool("get_service_status", {})

    async def health_check(self) -> Dict[str, Any]:
        """Check MCP server health"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_metrics(self) -> Dict[str, Any]:
        """Get client performance metrics"""
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0
        }


# Example Usage
async def main():
    print("=" * 80)
    print("Digital Tools MCP Client Examples")
    print("=" * 80)

    async with DigitalToolsClient() as client:
        # Example 1: Health Check
        print("\n1. Health Check")
        print("-" * 80)
        health = await client.health_check()
        print(f" Server: {health.get('service', 'Unknown')}")
        print(f"  Status: {health.get('status', 'Unknown')}")

        # Example 2: Service Status
        print("\n2. Service Status")
        print("-" * 80)
        status = await client.get_service_status()
        version = status.get("simplified_interface", {}).get("version", "unknown")
        rag_modes = status.get("simplified_interface", {}).get("supported_rag_modes", [])
        print(f" Version: {version}")
        print(f"  RAG Modes: {len(rag_modes)} supported")
        print(f"  Modes: {', '.join(rag_modes[:3])}...")

        user_id = "test_user_rag_page"

        # Example 3: PDF Search
        print("\n3. Search Knowledge - PDF Search")
        print("-" * 80)
        search_result = await client.search_knowledge(
            user_id=user_id,
            query="7,��A",
            top_k=3,
            content_type="pdf"
        )
        print(f" Status: {search_result.status}")
        print(f"  Total Results: {search_result.total_results}")
        print(f"  Pages: {search_result.total_pages}")
        print(f"  Photos: {search_result.total_photos}")
        print(f"  Method: {search_result.search_method}")

        # Example 4: Text Search (Hybrid Mode)
        print("\n4. Search Knowledge - Text Search (Hybrid)")
        print("-" * 80)
        search_result = await client.search_knowledge(
            user_id=user_id,
            query="sample collection",
            top_k=5,
            search_mode="hybrid"
        )
        print(f" Status: {search_result.status}")
        print(f"  Total Results: {search_result.total_results}")
        print(f"  Search Mode: {search_result.search_method}")

        # Example 5: Semantic Search
        print("\n5. Search Knowledge - Semantic Search")
        print("-" * 80)
        search_result = await client.search_knowledge(
            user_id=user_id,
            query="�ިX",
            top_k=3,
            search_mode="semantic"
        )
        print(f" Status: {search_result.status}")
        print(f"  Total Results: {search_result.total_results}")

        # Example 6: Mixed Content Search
        print("\n6. Search Knowledge - Mixed Content")
        print("-" * 80)
        search_result = await client.search_knowledge(
            user_id=user_id,
            query="��",
            top_k=10
        )
        print(f" Status: {search_result.status}")
        print(f"  Total Results: {search_result.total_results}")

        # Example 7: Search with Reranking
        print("\n7. Search Knowledge - With Reranking")
        print("-" * 80)
        search_result = await client.search_knowledge(
            user_id=user_id,
            query="(���",
            top_k=5,
            enable_rerank=True
        )
        print(f" Status: {search_result.status}")
        print(f"  Total Results: {search_result.total_results}")

        # Example 8: Simple RAG
        print("\n8. Knowledge Response - Simple RAG")
        print("-" * 80)
        rag_result = await client.knowledge_response(
            user_id=user_id,
            query="�H/O�",
            rag_mode="simple",
            context_limit=3
        )
        print(f" Status: {rag_result.status}")
        print(f"  Response Type: {rag_result.response_type}")
        print(f"  Response Length: {len(rag_result.response)} chars")
        print(f"  Sources: {len(rag_result.sources)}")
        print(f"  Preview: {rag_result.response[:100]}...")

        # Example 9: PDF Context RAG
        print("\n9. Knowledge Response - PDF Context RAG")
        print("-" * 80)
        rag_result = await client.knowledge_response(
            user_id=user_id,
            query="7,��A/�H	�s.e�",
            use_pdf_context=True,
            context_limit=3,
            temperature=0.3
        )
        print(f" Status: {rag_result.status}")
        print(f"  Response Type: {rag_result.response_type}")
        print(f"  Pages Used: {rag_result.page_count}")
        print(f"  Photos: {rag_result.photo_count}")
        print(f"  Citations: {rag_result.inline_citations_enabled}")
        print(f"  Preview: {rag_result.response[:100]}...")

        # Example 10: Auto-detect PDF Content
        print("\n10. Knowledge Response - Auto-detect PDF")
        print("-" * 80)
        rag_result = await client.knowledge_response(
            user_id=user_id,
            query="(ϧ6A",
            auto_detect_pdf=True,
            context_limit=5
        )
        print(f" Status: {rag_result.status}")
        print(f"  Response Type: {rag_result.response_type}")
        print(f"  Auto-detected: PDF content found" if rag_result.page_count > 0 else "  Auto-detected: Text only")

        # Example 11: Multimodal RAG with Images
        print("\n11. Knowledge Response - Multimodal with Images")
        print("-" * 80)
        rag_result = await client.knowledge_response(
            user_id=user_id,
            query="U:A�",
            include_images=True,
            context_limit=3
        )
        print(f" Status: {rag_result.status}")
        print(f"  Response Type: {rag_result.response_type}")
        print(f"  Photos: {rag_result.photo_count}")

        # Example 12: RAG with Citations
        print("\n12. Knowledge Response - With Citations")
        print("-" * 80)
        rag_result = await client.knowledge_response(
            user_id=user_id,
            query="�6A",
            use_pdf_context=True,
            enable_citations=True,
            context_limit=3
        )
        print(f" Status: {rag_result.status}")
        print(f"  Citations Enabled: {rag_result.inline_citations_enabled}")
        print(f"  Sources: {len(rag_result.sources)}")

        # Example 13: Variable Context Limit
        print("\n13. Knowledge Response - Variable Context Limit")
        print("-" * 80)
        rag_result = await client.knowledge_response(
            user_id=user_id,
            query="��W�",
            use_pdf_context=True,
            context_limit=10
        )
        print(f" Status: {rag_result.status}")
        print(f"  Context Limit: 10")
        print(f"  Pages Used: {rag_result.page_count}")

        # Example 14: Temperature Variation
        print("\n14. Knowledge Response - Temperature Variation")
        print("-" * 80)
        rag_result = await client.knowledge_response(
            user_id=user_id,
            query="7,�o",
            use_pdf_context=True,
            context_limit=3,
            temperature=0.7
        )
        print(f" Status: {rag_result.status}")
        print(f"  Temperature: 0.7 (high)")
        print(f"  Response: More creative/varied")

        # Example 15: Context Format Return
        print("\n15. Search Knowledge - Context Format")
        print("-" * 80)
        search_result = await client.search_knowledge(
            user_id=user_id,
            query="Г",
            top_k=3,
            return_format="context"
        )
        print(f" Status: {search_result.status}")
        print(f"  Format: context")
        print(f"  Results: {search_result.total_results}")

        # Show Client Metrics
        print("\n16. Client Performance Metrics")
        print("-" * 80)
        metrics = client.get_metrics()
        print(f"Total requests: {metrics['total_requests']}")
        print(f"Total errors: {metrics['total_errors']}")
        print(f"Error rate: {metrics['error_rate']:.2%}")

    print("\n" + "=" * 80)
    print("All Examples Completed Successfully!")
    print("=" * 80)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
