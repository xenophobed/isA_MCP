#!/usr/bin/env python3
"""Model configuration for isA_Model integration

Centralizes all LLM and embedding model settings:
- Default LLM model and provider
- Embedding model and vector dimensions
- Model parameters (temperature, max_tokens, etc.)
"""
import os
from dataclasses import dataclass

def _int(val: str, default: int) -> int:
    try:
        return int(val) if val else default
    except ValueError:
        return default

def _float(val: str, default: float) -> float:
    try:
        return float(val) if val else default
    except ValueError:
        return default


@dataclass
class ModelConfig:
    """LLM and Embedding model configuration from isA_Model"""

    # ===========================================
    # ISA Model Service Connection
    # ===========================================
    service_url: str = "http://localhost:8082"
    api_key: str = ""

    # ===========================================
    # LLM Configuration
    # ===========================================
    # Default model for general tasks
    default_llm: str = "gpt-4.1-nano"
    default_llm_provider: str = "openai"

    # Reasoning model for complex tasks (chain-of-thought)
    reason_llm: str = "deepseek-r1"
    reason_llm_provider: str = "yyds"

    # Response model for summaries/formatting (faster, cheaper)
    response_llm: str = "gpt-4.1-nano"
    response_llm_provider: str = "openai"

    # Model parameters
    temperature: float = 0.0
    max_tokens: int = 4096
    top_p: float = 1.0

    # ===========================================
    # Embedding Configuration
    # ===========================================
    # Embedding model
    # Options: text-embedding-3-small, text-embedding-3-large, text-embedding-ada-002
    embedding_model: str = "text-embedding-3-small"
    embedding_provider: str = "openai"

    # Vector dimensions (must match model output)
    # text-embedding-3-small: 1536
    # text-embedding-3-large: 3072
    # text-embedding-ada-002: 1536
    # bge-small-en-v1.5: 384
    # bge-base-en-v1.5: 768
    # bge-large-en-v1.5: 1024
    vector_size: int = 1536

    # Distance metric for similarity search
    # Options: Cosine, Euclid, Dot, Manhattan
    distance_metric: str = "Cosine"

    @classmethod
    def from_env(cls) -> 'ModelConfig':
        """Load model configuration from environment variables"""
        return cls(
            # ISA Model Service
            service_url=os.getenv("ISA_MODEL_URL") or os.getenv("ISA_SERVICE_URL", "http://localhost:8082"),
            api_key=os.getenv("ISA_MODEL_API_KEY") or os.getenv("ISA_API_KEY", ""),

            # LLM Configuration
            default_llm=os.getenv("DEFAULT_LLM", "gpt-4.1-nano"),
            default_llm_provider=os.getenv("DEFAULT_LLM_PROVIDER", "openai"),
            reason_llm=os.getenv("REASON_LLM", "deepseek-r1"),
            reason_llm_provider=os.getenv("REASON_LLM_PROVIDER", "yyds"),
            response_llm=os.getenv("RESPONSE_LLM", "gpt-4.1-nano"),
            response_llm_provider=os.getenv("RESPONSE_LLM_PROVIDER", "openai"),

            # Model parameters
            temperature=_float(os.getenv("LLM_TEMPERATURE", "0.0"), 0.0),
            max_tokens=_int(os.getenv("LLM_MAX_TOKENS", "4096"), 4096),
            top_p=_float(os.getenv("LLM_TOP_P", "1.0"), 1.0),

            # Embedding Configuration
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            embedding_provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
            vector_size=_int(os.getenv("VECTOR_SIZE", "1536"), 1536),
            distance_metric=os.getenv("DISTANCE_METRIC", "Cosine"),
        )
