"""
Search Service Data Contract (Hierarchical Search)

Defines canonical data structures for hierarchical search service testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for search service test data.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from enum import Enum

# ============================================================================
# Enums
# ============================================================================


class SearchItemType(str, Enum):
    """Types of searchable items"""

    TOOL = "tool"
    PROMPT = "prompt"
    RESOURCE = "resource"


class SearchStrategy(str, Enum):
    """Search strategy options"""

    HIERARCHICAL = "hierarchical"  # Skill → Tools (default)
    DIRECT = "direct"  # Skip skill layer
    HYBRID = "hybrid"  # Parallel skill + direct, merge results


# ============================================================================
# Request Contracts (Input Schemas)
# ============================================================================


class HierarchicalSearchRequestContract(BaseModel):
    """
    Contract: Hierarchical search request schema

    Main entry point for skill-based hierarchical search.
    Stage 1: Match skills → Stage 2: Search tools within matched skills
    """

    query: str = Field(
        ..., min_length=1, max_length=1000, description="Natural language search query"
    )
    item_type: Optional[SearchItemType] = Field(
        None, description="Filter by item type (tool/prompt/resource). None = all types"
    )
    limit: int = Field(5, ge=1, le=50, description="Maximum tools to return")
    skill_limit: int = Field(3, ge=1, le=10, description="Maximum skills to match in stage 1")
    skill_threshold: float = Field(
        0.4, ge=0.0, le=1.0, description="Minimum similarity score for skill matching"
    )
    tool_threshold: float = Field(
        0.3, ge=0.0, le=1.0, description="Minimum similarity score for tool matching"
    )
    include_schemas: bool = Field(
        True, description="Include full input schemas in response (lazy loaded)"
    )
    strategy: SearchStrategy = Field(
        SearchStrategy.HIERARCHICAL, description="Search strategy to use"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "schedule a meeting with John tomorrow",
                "item_type": "tool",
                "limit": 5,
                "skill_limit": 3,
                "skill_threshold": 0.4,
                "tool_threshold": 0.3,
                "include_schemas": True,
                "strategy": "hierarchical",
            }
        }


class SkillSearchRequestContract(BaseModel):
    """
    Contract: Skill-only search request (Stage 1)

    Used for searching skills directly.
    """

    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    limit: int = Field(5, ge=1, le=20, description="Maximum skills to return")
    threshold: float = Field(0.4, ge=0.0, le=1.0, description="Minimum similarity score")
    include_inactive: bool = Field(False, description="Include inactive skills")


class ToolSearchRequestContract(BaseModel):
    """
    Contract: Tool search within skills request (Stage 2)

    Used for searching tools within specific skills.
    """

    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    skill_ids: Optional[List[str]] = Field(
        None, description="Filter by skill IDs. None = search all"
    )
    item_type: Optional[SearchItemType] = Field(None, description="Filter by type")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")
    threshold: float = Field(0.3, ge=0.0, le=1.0, description="Minimum similarity score")


# ============================================================================
# Response Contracts (Output Schemas)
# ============================================================================


class SkillMatchContract(BaseModel):
    """
    Contract: Skill match in search response

    Represents a matched skill from Stage 1.
    """

    id: str = Field(..., description="Skill ID")
    name: str = Field(..., description="Skill name")
    description: str = Field(..., description="Skill description")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    tool_count: int = Field(..., ge=0, description="Number of tools in this skill")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "calendar_management",
                "name": "Calendar Management",
                "description": "Tools for managing calendars and events",
                "score": 0.87,
                "tool_count": 15,
            }
        }


class ToolMatchContract(BaseModel):
    """
    Contract: Tool match in search response (without schema)

    Represents a matched tool from Stage 2 before enrichment.
    """

    id: str = Field(..., description="Vector DB ID")
    db_id: int = Field(..., description="PostgreSQL ID")
    type: SearchItemType = Field(..., description="Item type")
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    skill_ids: List[str] = Field(default_factory=list, description="Assigned skill IDs")
    primary_skill_id: Optional[str] = Field(None, description="Primary skill ID")


class EnrichedToolContract(BaseModel):
    """
    Contract: Enriched tool with full schema

    Final tool format returned to client after lazy schema loading.
    """

    id: str = Field(..., description="Vector DB ID")
    db_id: int = Field(..., description="PostgreSQL ID")
    type: SearchItemType = Field(..., description="Item type")
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    skill_ids: List[str] = Field(default_factory=list, description="Assigned skill IDs")
    primary_skill_id: Optional[str] = Field(None, description="Primary skill ID")
    input_schema: Optional[Dict[str, Any]] = Field(
        None, description="Full input schema (lazy loaded)"
    )
    output_schema: Optional[Dict[str, Any]] = Field(None, description="Full output schema")
    annotations: Optional[Dict[str, Any]] = Field(None, description="MCP annotations")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "1",
                "db_id": 1,
                "type": "tool",
                "name": "create_calendar_event",
                "description": "Create a new event on the calendar",
                "score": 0.92,
                "skill_ids": ["calendar_management"],
                "primary_skill_id": "calendar_management",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "start_time": {"type": "string", "format": "date-time"},
                    },
                    "required": ["title", "start_time"],
                },
                "output_schema": None,
                "annotations": None,
            }
        }


class SearchMetadataContract(BaseModel):
    """
    Contract: Search metadata for debugging/analytics

    Provides insight into how search was executed.
    """

    strategy_used: SearchStrategy = Field(..., description="Search strategy used")
    skill_ids_used: Optional[List[str]] = Field(
        None, description="Skill IDs used for filtering (None = unfiltered)"
    )
    stage1_skill_count: int = Field(..., ge=0, description="Skills matched in stage 1")
    stage2_candidate_count: int = Field(..., ge=0, description="Tools found in stage 2")
    final_count: int = Field(..., ge=0, description="Tools returned after filtering")
    query_embedding_time_ms: float = Field(
        ..., ge=0, description="Time to generate query embedding"
    )
    skill_search_time_ms: float = Field(..., ge=0, description="Time for skill search (stage 1)")
    tool_search_time_ms: float = Field(..., ge=0, description="Time for tool search (stage 2)")
    schema_load_time_ms: float = Field(..., ge=0, description="Time to load schemas")
    total_time_ms: float = Field(..., ge=0, description="Total search time")


class HierarchicalSearchResponseContract(BaseModel):
    """
    Contract: Hierarchical search response schema

    Complete response from hierarchical search.
    """

    query: str = Field(..., description="Original search query")
    tools: List[EnrichedToolContract] = Field(
        default_factory=list, description="Matched tools (enriched with schemas)"
    )
    matched_skills: List[SkillMatchContract] = Field(
        default_factory=list, description="Skills matched in stage 1"
    )
    metadata: SearchMetadataContract = Field(..., description="Search metadata")

    @field_validator("tools")
    @classmethod
    def validate_tools_sorted(cls, v: List[EnrichedToolContract]) -> List[EnrichedToolContract]:
        """Ensure tools are sorted by score descending"""
        return sorted(v, key=lambda x: x.score, reverse=True)


# ============================================================================
# Test Data Factory
# ============================================================================


class SearchTestDataFactory:
    """
    Factory for creating test data conforming to contracts.

    Provides methods to generate valid/invalid test data for all scenarios.
    """

    # ========================================================================
    # Valid Data Generators
    # ========================================================================

    @staticmethod
    def make_search_request(**overrides) -> HierarchicalSearchRequestContract:
        """
        Create valid hierarchical search request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            HierarchicalSearchRequestContract with valid data
        """
        defaults = {
            "query": "find tools for scheduling meetings",
            "item_type": None,
            "limit": 5,
            "skill_limit": 3,
            "skill_threshold": 0.4,
            "tool_threshold": 0.3,
            "include_schemas": True,
            "strategy": SearchStrategy.HIERARCHICAL,
        }
        defaults.update(overrides)
        return HierarchicalSearchRequestContract(**defaults)

    @staticmethod
    def make_skill_search_request(**overrides) -> SkillSearchRequestContract:
        """Create valid skill search request"""
        defaults = {
            "query": "calendar scheduling",
            "limit": 5,
            "threshold": 0.4,
            "include_inactive": False,
        }
        defaults.update(overrides)
        return SkillSearchRequestContract(**defaults)

    @staticmethod
    def make_tool_search_request(**overrides) -> ToolSearchRequestContract:
        """Create valid tool search request"""
        defaults = {
            "query": "create event",
            "skill_ids": None,
            "item_type": SearchItemType.TOOL,
            "limit": 10,
            "threshold": 0.3,
        }
        defaults.update(overrides)
        return ToolSearchRequestContract(**defaults)

    @staticmethod
    def make_skill_match(**overrides) -> SkillMatchContract:
        """Create skill match for assertions"""
        defaults = {
            "id": "calendar_management",
            "name": "Calendar Management",
            "description": "Tools for managing calendars and events",
            "score": 0.85,
            "tool_count": 10,
        }
        defaults.update(overrides)
        return SkillMatchContract(**defaults)

    @staticmethod
    def make_tool_match(**overrides) -> ToolMatchContract:
        """Create tool match for assertions"""
        defaults = {
            "id": "1",
            "db_id": 1,
            "type": SearchItemType.TOOL,
            "name": "create_calendar_event",
            "description": "Create a new event on the calendar",
            "score": 0.9,
            "skill_ids": ["calendar_management"],
            "primary_skill_id": "calendar_management",
        }
        defaults.update(overrides)
        return ToolMatchContract(**defaults)

    @staticmethod
    def make_enriched_tool(**overrides) -> EnrichedToolContract:
        """Create enriched tool for assertions"""
        defaults = {
            "id": "1",
            "db_id": 1,
            "type": SearchItemType.TOOL,
            "name": "create_calendar_event",
            "description": "Create a new event on the calendar",
            "score": 0.9,
            "skill_ids": ["calendar_management"],
            "primary_skill_id": "calendar_management",
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                },
                "required": ["title"],
            },
            "output_schema": None,
            "annotations": None,
        }
        defaults.update(overrides)
        return EnrichedToolContract(**defaults)

    @staticmethod
    def make_search_metadata(**overrides) -> SearchMetadataContract:
        """Create search metadata for assertions"""
        defaults = {
            "strategy_used": SearchStrategy.HIERARCHICAL,
            "skill_ids_used": ["calendar_management"],
            "stage1_skill_count": 2,
            "stage2_candidate_count": 15,
            "final_count": 5,
            "query_embedding_time_ms": 50.0,
            "skill_search_time_ms": 10.0,
            "tool_search_time_ms": 25.0,
            "schema_load_time_ms": 15.0,
            "total_time_ms": 100.0,
        }
        defaults.update(overrides)
        return SearchMetadataContract(**defaults)

    @staticmethod
    def make_search_response(**overrides) -> HierarchicalSearchResponseContract:
        """Create complete search response for assertions"""
        defaults = {
            "query": "schedule a meeting",
            "tools": [SearchTestDataFactory.make_enriched_tool()],
            "matched_skills": [SearchTestDataFactory.make_skill_match()],
            "metadata": SearchTestDataFactory.make_search_metadata(),
        }
        defaults.update(overrides)
        return HierarchicalSearchResponseContract(**defaults)

    # ========================================================================
    # Test Query Sets
    # ========================================================================

    @staticmethod
    def get_calendar_queries() -> List[str]:
        """Get test queries that should match calendar skill"""
        return [
            "schedule a meeting tomorrow",
            "create an event on my calendar",
            "what meetings do I have today",
            "cancel my 3pm appointment",
            "check availability for next week",
        ]

    @staticmethod
    def get_data_queries() -> List[str]:
        """Get test queries that should match data skill"""
        return [
            "query the database for users",
            "search records by name",
            "get statistics from sales table",
            "run SQL query",
            "find data matching criteria",
        ]

    @staticmethod
    def get_ambiguous_queries() -> List[str]:
        """Get queries that could match multiple skills"""
        return [
            "export calendar to csv",  # calendar + file
            "send meeting invite",  # calendar + communication
            "search for documents about sales",  # data + file
        ]

    @staticmethod
    def get_no_match_queries() -> List[str]:
        """Get queries unlikely to match any skill strongly"""
        return [
            "xyzabc random gibberish",
            "asdfghjkl qwerty",
        ]

    # ========================================================================
    # Invalid Data Generators (for negative testing)
    # ========================================================================

    @staticmethod
    def make_invalid_search_empty_query() -> dict:
        """Generate search request with empty query"""
        return {
            "query": "",
            "limit": 5,
        }

    @staticmethod
    def make_invalid_search_limit_too_high() -> dict:
        """Generate search request with limit > max"""
        return {
            "query": "test query",
            "limit": 1000,  # Max is 50
        }

    @staticmethod
    def make_invalid_search_negative_threshold() -> dict:
        """Generate search request with negative threshold"""
        return {
            "query": "test query",
            "skill_threshold": -0.5,
        }

    @staticmethod
    def make_invalid_search_threshold_above_one() -> dict:
        """Generate search request with threshold > 1"""
        return {
            "query": "test query",
            "tool_threshold": 1.5,
        }


# ============================================================================
# Request Builders (for complex test scenarios)
# ============================================================================


class HierarchicalSearchRequestBuilder:
    """
    Builder pattern for creating complex search requests.

    Example:
        request = (
            HierarchicalSearchRequestBuilder()
            .with_query("schedule meeting")
            .tools_only()
            .with_high_thresholds()
            .limit_results(3)
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "query": "test query",
            "item_type": None,
            "limit": 5,
            "skill_limit": 3,
            "skill_threshold": 0.4,
            "tool_threshold": 0.3,
            "include_schemas": True,
            "strategy": SearchStrategy.HIERARCHICAL,
        }

    def with_query(self, query: str) -> "HierarchicalSearchRequestBuilder":
        """Set search query"""
        self._data["query"] = query
        return self

    def tools_only(self) -> "HierarchicalSearchRequestBuilder":
        """Filter to tools only"""
        self._data["item_type"] = SearchItemType.TOOL
        return self

    def prompts_only(self) -> "HierarchicalSearchRequestBuilder":
        """Filter to prompts only"""
        self._data["item_type"] = SearchItemType.PROMPT
        return self

    def resources_only(self) -> "HierarchicalSearchRequestBuilder":
        """Filter to resources only"""
        self._data["item_type"] = SearchItemType.RESOURCE
        return self

    def limit_results(self, limit: int) -> "HierarchicalSearchRequestBuilder":
        """Set result limit"""
        self._data["limit"] = limit
        return self

    def limit_skills(self, limit: int) -> "HierarchicalSearchRequestBuilder":
        """Set skill limit"""
        self._data["skill_limit"] = limit
        return self

    def with_skill_threshold(self, threshold: float) -> "HierarchicalSearchRequestBuilder":
        """Set skill similarity threshold"""
        self._data["skill_threshold"] = threshold
        return self

    def with_tool_threshold(self, threshold: float) -> "HierarchicalSearchRequestBuilder":
        """Set tool similarity threshold"""
        self._data["tool_threshold"] = threshold
        return self

    def with_high_thresholds(self) -> "HierarchicalSearchRequestBuilder":
        """Set high thresholds for strict matching"""
        self._data["skill_threshold"] = 0.7
        self._data["tool_threshold"] = 0.6
        return self

    def with_low_thresholds(self) -> "HierarchicalSearchRequestBuilder":
        """Set low thresholds for permissive matching"""
        self._data["skill_threshold"] = 0.2
        self._data["tool_threshold"] = 0.1
        return self

    def without_schemas(self) -> "HierarchicalSearchRequestBuilder":
        """Disable schema loading"""
        self._data["include_schemas"] = False
        return self

    def direct_search(self) -> "HierarchicalSearchRequestBuilder":
        """Use direct search strategy (skip skills)"""
        self._data["strategy"] = SearchStrategy.DIRECT
        return self

    def hybrid_search(self) -> "HierarchicalSearchRequestBuilder":
        """Use hybrid search strategy"""
        self._data["strategy"] = SearchStrategy.HYBRID
        return self

    def build(self) -> HierarchicalSearchRequestContract:
        """Build the final request"""
        return HierarchicalSearchRequestContract(**self._data)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enums
    "SearchItemType",
    "SearchStrategy",
    # Request Contracts
    "HierarchicalSearchRequestContract",
    "SkillSearchRequestContract",
    "ToolSearchRequestContract",
    # Response Contracts
    "SkillMatchContract",
    "ToolMatchContract",
    "EnrichedToolContract",
    "SearchMetadataContract",
    "HierarchicalSearchResponseContract",
    # Factory
    "SearchTestDataFactory",
    # Builders
    "HierarchicalSearchRequestBuilder",
]
