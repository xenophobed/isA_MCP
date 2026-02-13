"""
Mock for HTTP client.

Provides a mock implementation of httpx AsyncClient
for testing HTTP operations without real network calls.
"""

from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
import json


@dataclass
class MockResponse:
    """Mock HTTP response."""

    status_code: int = 200
    content: bytes = b""
    headers: Dict[str, str] = field(default_factory=dict)
    _json: Any = None

    def json(self) -> Any:
        """Parse JSON response."""
        if self._json is not None:
            return self._json
        return json.loads(self.content.decode())

    @property
    def text(self) -> str:
        """Get response text."""
        return self.content.decode()

    def raise_for_status(self) -> None:
        """Raise exception for error status codes."""
        if self.status_code >= 400:
            raise HTTPStatusError(f"HTTP {self.status_code}", response=self)


class HTTPStatusError(Exception):
    """HTTP status error."""

    def __init__(self, message: str, response: MockResponse):
        super().__init__(message)
        self.response = response


@dataclass
class MockRequest:
    """Recorded request."""

    method: str
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, str] = field(default_factory=dict)
    json_data: Any = None
    data: Any = None
    content: bytes = None


class MockHTTPClient:
    """
    Mock for httpx AsyncClient.

    Provides configurable responses and request recording.

    Example usage:
        client = MockHTTPClient()
        client.add_response("GET", "https://api.example.com/data", {"result": "success"})

        response = await client.get("https://api.example.com/data")
        assert response.json() == {"result": "success"}

        # Check requests
        assert len(client.requests) == 1
        assert client.requests[0].url == "https://api.example.com/data"
    """

    def __init__(self, base_url: str = ""):
        self.base_url = base_url
        self.requests: List[MockRequest] = []
        self._responses: Dict[str, MockResponse] = {}
        self._response_handlers: Dict[str, Callable] = {}
        self._default_response = MockResponse(status_code=200, content=b"{}")
        self._closed = False
        self.headers: Dict[str, str] = {}

    def add_response(
        self,
        method: str,
        url: str,
        json_data: Any = None,
        content: bytes = None,
        status_code: int = 200,
        headers: Dict[str, str] = None,
    ) -> None:
        """Add a mock response for a specific request."""
        key = f"{method.upper()}:{url}"

        if json_data is not None:
            content = json.dumps(json_data).encode()

        self._responses[key] = MockResponse(
            status_code=status_code, content=content or b"", headers=headers or {}, _json=json_data
        )

    def add_response_handler(
        self, method: str, url: str, handler: Callable[[MockRequest], MockResponse]
    ) -> None:
        """Add a handler function for dynamic responses."""
        key = f"{method.upper()}:{url}"
        self._response_handlers[key] = handler

    def set_default_response(
        self, json_data: Any = None, content: bytes = None, status_code: int = 200
    ) -> None:
        """Set default response for unmatched requests."""
        if json_data is not None:
            content = json.dumps(json_data).encode()

        self._default_response = MockResponse(
            status_code=status_code, content=content or b"", _json=json_data
        )

    async def request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str] = None,
        params: Dict[str, str] = None,
        json: Any = None,
        data: Any = None,
        content: bytes = None,
        **kwargs,
    ) -> MockResponse:
        """Make a request."""
        full_url = self._build_url(url)

        # Record request
        request = MockRequest(
            method=method.upper(),
            url=full_url,
            headers={**self.headers, **(headers or {})},
            params=params or {},
            json_data=json,
            data=data,
            content=content,
        )
        self.requests.append(request)

        # Find response
        key = f"{method.upper()}:{full_url}"

        # Check handlers first
        if key in self._response_handlers:
            return self._response_handlers[key](request)

        # Check static responses
        if key in self._responses:
            return self._responses[key]

        # Try pattern matching (simple wildcard support)
        for resp_key, response in self._responses.items():
            if self._matches_pattern(resp_key, key):
                return response

        return self._default_response

    async def get(self, url: str, **kwargs) -> MockResponse:
        """GET request."""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> MockResponse:
        """POST request."""
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> MockResponse:
        """PUT request."""
        return await self.request("PUT", url, **kwargs)

    async def patch(self, url: str, **kwargs) -> MockResponse:
        """PATCH request."""
        return await self.request("PATCH", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> MockResponse:
        """DELETE request."""
        return await self.request("DELETE", url, **kwargs)

    def _build_url(self, url: str) -> str:
        """Build full URL."""
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"

    def _matches_pattern(self, pattern: str, key: str) -> bool:
        """Check if key matches pattern (with simple wildcard support)."""
        import fnmatch

        return fnmatch.fnmatch(key, pattern)

    def get_requests(self, method: str = None, url_contains: str = None) -> List[MockRequest]:
        """Get recorded requests with optional filtering."""
        result = self.requests

        if method:
            result = [r for r in result if r.method == method.upper()]

        if url_contains:
            result = [r for r in result if url_contains in r.url]

        return result

    def clear_requests(self) -> None:
        """Clear recorded requests."""
        self.requests = []

    async def close(self) -> None:
        """Close the client."""
        self._closed = True

    async def aclose(self) -> None:
        """Close the client (async)."""
        self._closed = True

    def is_closed(self) -> bool:
        """Check if client is closed."""
        return self._closed

    async def __aenter__(self) -> "MockHTTPClient":
        """Enter async context."""
        return self

    async def __aexit__(self, *args) -> None:
        """Exit async context."""
        await self.close()


class MockStreamResponse:
    """Mock streaming response."""

    def __init__(self, chunks: List[bytes]):
        self._chunks = chunks
        self._index = 0
        self.status_code = 200

    async def aiter_bytes(self):
        """Iterate over response chunks."""
        for chunk in self._chunks:
            yield chunk

    async def aread(self) -> bytes:
        """Read all content."""
        return b"".join(self._chunks)


def create_json_response(data: Any, status_code: int = 200) -> MockResponse:
    """Helper to create a JSON response."""
    return MockResponse(
        status_code=status_code,
        content=json.dumps(data).encode(),
        headers={"content-type": "application/json"},
        _json=data,
    )


def create_error_response(
    status_code: int, message: str = "Error", details: Dict = None
) -> MockResponse:
    """Helper to create an error response."""
    error_data = {"error": message, "details": details or {}}
    return MockResponse(
        status_code=status_code,
        content=json.dumps(error_data).encode(),
        headers={"content-type": "application/json"},
        _json=error_data,
    )
