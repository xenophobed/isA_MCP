"""
Mock for ISA Model Service client.

Provides a mock implementation of the model client
for testing AI operations without real API calls.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class MockEmbeddingResponse:
    """Mock embedding response."""
    embedding: List[float]
    model: str = "text-embedding-3-small"
    usage: Dict[str, int] = field(default_factory=lambda: {"tokens": 100})


@dataclass
class MockCompletionResponse:
    """Mock completion response."""
    content: str
    model: str = "gpt-4"
    usage: Dict[str, int] = field(default_factory=lambda: {
        "prompt_tokens": 50,
        "completion_tokens": 100,
        "total_tokens": 150
    })
    finish_reason: str = "stop"


@dataclass
class MockVisionResponse:
    """Mock vision analysis response."""
    description: str
    objects: List[str] = field(default_factory=list)
    text: List[str] = field(default_factory=list)
    confidence: float = 0.95


class MockModelClient:
    """
    Mock for ISA Model Service client.

    Provides configurable responses for AI model operations.

    Example usage:
        client = MockModelClient()
        client.set_response("embedding", [0.1] * 1536)

        embedding = await client.generate_embedding("Hello world")
        assert len(embedding) == 1536
    """

    def __init__(self):
        self._responses: Dict[str, Any] = {}
        self._calls: List[Dict[str, Any]] = []
        self._default_embedding_size = 1536

    async def generate_embedding(
        self,
        text: str,
        model: str = "text-embedding-3-small"
    ) -> List[float]:
        """Generate text embedding."""
        self._record_call("embedding", {"text": text, "model": model})

        if "embedding" in self._responses:
            return self._responses["embedding"]

        # Return default embedding
        return [0.1] * self._default_embedding_size

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        model: str = "text-embedding-3-small"
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        self._record_call("embedding_batch", {"texts": texts, "model": model})

        if "embedding_batch" in self._responses:
            return self._responses["embedding_batch"]

        # Return default embeddings
        return [[0.1] * self._default_embedding_size for _ in texts]

    async def generate_text(
        self,
        prompt: str,
        model: str = "gpt-4",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate text completion."""
        self._record_call("text", {
            "prompt": prompt,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        })

        if "text" in self._responses:
            return self._responses["text"]

        return f"Mock generated text for: {prompt[:50]}..."

    async def generate_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
        **kwargs
    ) -> MockCompletionResponse:
        """Generate chat completion."""
        self._record_call("completion", {
            "messages": messages,
            "model": model,
            **kwargs
        })

        if "completion" in self._responses:
            resp = self._responses["completion"]
            if isinstance(resp, MockCompletionResponse):
                return resp
            return MockCompletionResponse(content=resp)

        return MockCompletionResponse(
            content="Mock completion response",
            model=model
        )

    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str = "Describe this image",
        model: str = "gpt-4-vision-preview",
        **kwargs
    ) -> MockVisionResponse:
        """Analyze image with vision model."""
        self._record_call("vision", {
            "image_size": len(image_data),
            "prompt": prompt,
            "model": model,
            **kwargs
        })

        if "vision" in self._responses:
            resp = self._responses["vision"]
            if isinstance(resp, MockVisionResponse):
                return resp
            return MockVisionResponse(description=resp)

        return MockVisionResponse(
            description="Mock image description",
            objects=["object1", "object2"],
            text=[]
        )

    async def transcribe_audio(
        self,
        audio_data: bytes,
        model: str = "whisper-1",
        language: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Transcribe audio to text."""
        self._record_call("transcribe", {
            "audio_size": len(audio_data),
            "model": model,
            "language": language,
            **kwargs
        })

        if "transcribe" in self._responses:
            return self._responses["transcribe"]

        return {
            "text": "Mock transcription of audio",
            "language": language or "en",
            "duration": 10.0
        }

    async def summarize(
        self,
        text: str,
        max_length: int = 200,
        **kwargs
    ) -> str:
        """Summarize text."""
        self._record_call("summarize", {
            "text": text,
            "max_length": max_length,
            **kwargs
        })

        if "summarize" in self._responses:
            return self._responses["summarize"]

        return f"Summary: {text[:100]}..."

    async def extract(
        self,
        text: str,
        schema: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Extract structured data from text."""
        self._record_call("extract", {
            "text": text,
            "schema": schema,
            **kwargs
        })

        if "extract" in self._responses:
            return self._responses["extract"]

        # Return mock extraction based on schema
        result = {}
        for key, type_info in schema.get("properties", {}).items():
            if type_info.get("type") == "string":
                result[key] = f"extracted_{key}"
            elif type_info.get("type") == "number":
                result[key] = 0
            elif type_info.get("type") == "array":
                result[key] = []
        return result

    def set_response(self, method: str, response: Any) -> None:
        """Set mock response for a method."""
        self._responses[method] = response

    def set_embedding_size(self, size: int) -> None:
        """Set default embedding size."""
        self._default_embedding_size = size

    def _record_call(self, method: str, params: Dict[str, Any]) -> None:
        """Record a method call."""
        self._calls.append({"method": method, "params": params})

    def get_calls(self, method: str = None) -> List[Dict[str, Any]]:
        """Get recorded calls, optionally filtered by method."""
        if method:
            return [c for c in self._calls if c["method"] == method]
        return self._calls

    def clear_calls(self) -> None:
        """Clear recorded calls."""
        self._calls = []

    def reset(self) -> None:
        """Reset all state."""
        self._responses = {}
        self._calls = []
