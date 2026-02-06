"""
Skill Service Data Contract

Defines canonical data structures for skill service testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for skill service test data.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class SkillStatus(str, Enum):
    """Skill category status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_REVIEW = "pending_review"


class AssignmentSource(str, Enum):
    """How the assignment was created"""
    LLM_AUTO = "llm_auto"           # Automatically by LLM
    HUMAN_MANUAL = "human_manual"   # Manually by admin
    HUMAN_OVERRIDE = "human_override"  # Human corrected LLM assignment


# ============================================================================
# Request Contracts (Input Schemas)
# ============================================================================

class SkillCategoryCreateRequestContract(BaseModel):
    """
    Contract: Skill category creation request schema

    Used for creating predefined skill categories (admin operation).
    """
    id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Unique skill ID (lowercase, underscores allowed)"
    )
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable skill name")
    description: str = Field(..., min_length=10, max_length=1000, description="Skill description for LLM context")
    keywords: List[str] = Field(default_factory=list, description="Hint keywords for LLM classification")
    examples: List[str] = Field(default_factory=list, description="Example tool names that belong here")
    parent_domain: Optional[str] = Field(None, description="Optional parent domain for grouping")
    is_active: bool = Field(True, description="Whether skill is active")

    @field_validator('id')
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Validate skill ID format: lowercase, start with letter, underscores allowed"""
        if not v[0].isalpha():
            raise ValueError("Skill ID must start with a letter")
        return v

    @field_validator('keywords')
    @classmethod
    def validate_keywords(cls, v: List[str]) -> List[str]:
        """Ensure keywords are lowercase"""
        return [k.lower().strip() for k in v if k.strip()]

    class Config:
        json_schema_extra = {
            "example": {
                "id": "calendar_management",
                "name": "Calendar Management",
                "description": "Tools for managing calendars, events, scheduling, and appointments",
                "keywords": ["calendar", "event", "schedule", "meeting", "appointment"],
                "examples": ["create_event", "list_events", "delete_event"],
                "parent_domain": "productivity",
                "is_active": True,
            }
        }


class ToolClassificationRequestContract(BaseModel):
    """
    Contract: Tool classification request schema

    Used for classifying a tool into skill categories via LLM.
    """
    tool_id: int = Field(..., ge=1, description="Tool database ID")
    tool_name: str = Field(..., min_length=1, description="Tool name")
    tool_description: str = Field(..., min_length=1, description="Tool description")
    input_schema_summary: Optional[str] = Field(None, description="Summary of input schema for context")
    force_reclassify: bool = Field(False, description="Force reclassification even if already classified")

    class Config:
        json_schema_extra = {
            "example": {
                "tool_id": 1,
                "tool_name": "create_calendar_event",
                "tool_description": "Create a new event on the calendar with title, time, and attendees",
                "input_schema_summary": "title: string, start_time: datetime, attendees: list[string]",
                "force_reclassify": False,
            }
        }


class SkillAssignmentRequestContract(BaseModel):
    """
    Contract: Manual skill assignment request schema

    Used for manually assigning a tool to skills (admin override).
    """
    tool_id: int = Field(..., ge=1, description="Tool database ID")
    skill_ids: List[str] = Field(..., min_length=1, max_length=5, description="Skill IDs to assign")
    primary_skill_id: str = Field(..., description="Primary skill ID")
    source: AssignmentSource = Field(AssignmentSource.HUMAN_MANUAL, description="Assignment source")

    @field_validator('skill_ids')
    @classmethod
    def validate_skill_ids(cls, v: List[str]) -> List[str]:
        """Ensure no duplicates and all lowercase"""
        return list(dict.fromkeys([s.lower().strip() for s in v]))

    @field_validator('primary_skill_id')
    @classmethod
    def validate_primary_in_list(cls, v: str, info) -> str:
        """Primary skill must be in skill_ids list"""
        skill_ids = info.data.get('skill_ids', [])
        if skill_ids and v not in skill_ids:
            raise ValueError("Primary skill must be in skill_ids list")
        return v


class SkillSuggestionRequestContract(BaseModel):
    """
    Contract: New skill suggestion request schema

    Used when LLM suggests a new skill category.
    """
    suggested_name: str = Field(..., min_length=1, max_length=255, description="Suggested skill name")
    suggested_description: str = Field(..., min_length=10, max_length=1000, description="Suggested description")
    source_tool_id: int = Field(..., ge=1, description="Tool ID that triggered suggestion")
    source_tool_name: str = Field(..., description="Tool name for context")
    reasoning: str = Field(..., description="LLM reasoning for suggestion")


# ============================================================================
# Response Contracts (Output Schemas)
# ============================================================================

class SkillCategoryResponseContract(BaseModel):
    """
    Contract: Skill category response schema

    Validates API response structure for skill categories.
    """
    id: str = Field(..., description="Skill ID")
    name: str = Field(..., description="Skill name")
    description: str = Field(..., description="Skill description")
    keywords: List[str] = Field(default_factory=list, description="Hint keywords")
    examples: List[str] = Field(default_factory=list, description="Example tools")
    parent_domain: Optional[str] = Field(None, description="Parent domain")
    tool_count: int = Field(0, ge=0, description="Number of tools in this skill")
    is_active: bool = Field(..., description="Active status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class SkillAssignmentContract(BaseModel):
    """
    Contract: Single skill assignment in classification response
    """
    skill_id: str = Field(..., description="Assigned skill ID")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    reasoning: Optional[str] = Field(None, description="LLM reasoning for this assignment")


class ToolClassificationResponseContract(BaseModel):
    """
    Contract: Tool classification response schema

    Validates response from LLM-based tool classification.
    """
    tool_id: int = Field(..., description="Classified tool ID")
    tool_name: str = Field(..., description="Tool name")
    assignments: List[SkillAssignmentContract] = Field(
        default_factory=list,
        description="Skill assignments with confidence scores"
    )
    primary_skill_id: Optional[str] = Field(None, description="Primary skill (highest confidence)")
    suggested_new_skill: Optional[SkillSuggestionRequestContract] = Field(
        None,
        description="Suggested new skill if no match found"
    )
    classification_timestamp: datetime = Field(..., description="When classification occurred")

    @field_validator('assignments')
    @classmethod
    def validate_assignments_sorted(cls, v: List[SkillAssignmentContract]) -> List[SkillAssignmentContract]:
        """Ensure assignments are sorted by confidence descending"""
        return sorted(v, key=lambda x: x.confidence, reverse=True)


class SkillAssignmentResponseContract(BaseModel):
    """
    Contract: Skill assignment response (stored assignment)

    Represents a tool-skill assignment stored in database.
    """
    id: int = Field(..., description="Assignment ID")
    tool_id: int = Field(..., description="Tool ID")
    skill_id: str = Field(..., description="Skill ID")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    is_primary: bool = Field(..., description="Is this the primary skill")
    source: AssignmentSource = Field(..., description="How assignment was created")
    assigned_at: datetime = Field(..., description="Assignment timestamp")


class SkillEmbeddingResponseContract(BaseModel):
    """
    Contract: Skill embedding response

    Validates skill embedding in vector database.
    """
    skill_id: str = Field(..., description="Skill ID")
    name: str = Field(..., description="Skill name")
    description: str = Field(..., description="Skill description")
    embedding_dimension: int = Field(1536, description="Embedding vector dimension")
    tool_count: int = Field(..., ge=0, description="Number of tools")
    last_updated: datetime = Field(..., description="Last embedding update")


class SkillSuggestionResponseContract(BaseModel):
    """
    Contract: Skill suggestion response (pending review)
    """
    id: int = Field(..., description="Suggestion ID")
    suggested_name: str = Field(..., description="Suggested name")
    suggested_description: str = Field(..., description="Suggested description")
    source_tool_id: int = Field(..., description="Source tool ID")
    source_tool_name: str = Field(..., description="Source tool name")
    reasoning: str = Field(..., description="LLM reasoning")
    status: str = Field(..., description="pending/approved/rejected")
    created_at: datetime = Field(..., description="Creation timestamp")


# ============================================================================
# Test Data Factory
# ============================================================================

class SkillTestDataFactory:
    """
    Factory for creating test data conforming to contracts.

    Provides methods to generate valid/invalid test data for all scenarios.
    """

    # ========================================================================
    # ID Generators
    # ========================================================================

    @staticmethod
    def make_skill_id() -> str:
        """Generate unique test skill ID"""
        return f"skill_test_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def make_tool_id() -> int:
        """Generate test tool ID"""
        return abs(hash(uuid.uuid4().hex)) % 1000000

    # ========================================================================
    # Valid Data Generators
    # ========================================================================

    @staticmethod
    def make_skill_category(**overrides) -> SkillCategoryCreateRequestContract:
        """
        Create valid skill category request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            SkillCategoryCreateRequestContract with valid data

        Example:
            skill = SkillTestDataFactory.make_skill_category(
                id="calendar_management",
                name="Calendar Management",
            )
        """
        skill_id = overrides.pop('id', None) or SkillTestDataFactory.make_skill_id()
        defaults = {
            "id": skill_id,
            "name": f"Test Skill {skill_id}",
            "description": f"Test skill category for {skill_id}. Used for testing purposes.",
            "keywords": ["test", "automated"],
            "examples": ["test_tool_1", "test_tool_2"],
            "parent_domain": None,
            "is_active": True,
        }
        defaults.update(overrides)
        return SkillCategoryCreateRequestContract(**defaults)

    @staticmethod
    def make_classification_request(**overrides) -> ToolClassificationRequestContract:
        """
        Create valid tool classification request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            ToolClassificationRequestContract with valid data
        """
        defaults = {
            "tool_id": SkillTestDataFactory.make_tool_id(),
            "tool_name": f"test_tool_{uuid.uuid4().hex[:8]}",
            "tool_description": "A test tool that performs various operations for testing purposes",
            "input_schema_summary": "param1: string, param2: int",
            "force_reclassify": False,
        }
        defaults.update(overrides)
        return ToolClassificationRequestContract(**defaults)

    @staticmethod
    def make_assignment_request(**overrides) -> SkillAssignmentRequestContract:
        """
        Create valid skill assignment request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            SkillAssignmentRequestContract with valid data
        """
        skill_id = overrides.get('primary_skill_id', 'test_skill')
        skill_ids = overrides.get('skill_ids', [skill_id])
        defaults = {
            "tool_id": SkillTestDataFactory.make_tool_id(),
            "skill_ids": skill_ids,
            "primary_skill_id": skill_id,
            "source": AssignmentSource.HUMAN_MANUAL,
        }
        defaults.update(overrides)
        return SkillAssignmentRequestContract(**defaults)

    @staticmethod
    def make_classification_response(**overrides) -> ToolClassificationResponseContract:
        """
        Create expected classification response for assertions.

        Used in tests to validate API responses match contract.
        """
        tool_id = overrides.pop('tool_id', None) or SkillTestDataFactory.make_tool_id()
        defaults = {
            "tool_id": tool_id,
            "tool_name": f"test_tool_{tool_id}",
            "assignments": [
                SkillAssignmentContract(
                    skill_id="calendar_management",
                    confidence=0.85,
                    reasoning="Tool handles calendar operations"
                )
            ],
            "primary_skill_id": "calendar_management",
            "suggested_new_skill": None,
            "classification_timestamp": datetime.now(timezone.utc),
        }
        defaults.update(overrides)
        return ToolClassificationResponseContract(**defaults)

    # ========================================================================
    # Predefined Skill Categories (Seed Data)
    # ========================================================================

    @staticmethod
    def get_seed_skills() -> List[SkillCategoryCreateRequestContract]:
        """
        Get predefined skill categories for seeding.

        Returns list of skill categories to initialize the system.
        """
        return [
            SkillCategoryCreateRequestContract(
                id="calendar_management",
                name="Calendar Management",
                description="Tools for managing calendars, events, scheduling, and appointments. Includes creating, updating, deleting events and checking availability.",
                keywords=["calendar", "event", "schedule", "meeting", "appointment", "reminder", "booking"],
                examples=["create_event", "list_events", "delete_event", "update_event", "check_availability"],
                parent_domain="productivity",
            ),
            SkillCategoryCreateRequestContract(
                id="data_query",
                name="Data Query & Analysis",
                description="Tools for querying databases, searching data, filtering records, and performing data analysis operations.",
                keywords=["query", "sql", "database", "search", "filter", "aggregate", "data", "analytics"],
                examples=["query_database", "search_records", "get_statistics", "run_sql"],
                parent_domain="data",
            ),
            SkillCategoryCreateRequestContract(
                id="file_operations",
                name="File Operations",
                description="Tools for reading, writing, uploading, downloading, and managing files in various storage systems.",
                keywords=["file", "read", "write", "upload", "download", "delete", "storage", "document"],
                examples=["read_file", "write_file", "list_files", "upload_file", "download_file"],
                parent_domain="storage",
            ),
            SkillCategoryCreateRequestContract(
                id="communication",
                name="Communication & Messaging",
                description="Tools for sending emails, messages, notifications, and other communication channels.",
                keywords=["email", "message", "notify", "send", "slack", "teams", "sms", "notification"],
                examples=["send_email", "send_message", "notify_user", "post_to_slack"],
                parent_domain="communication",
            ),
            SkillCategoryCreateRequestContract(
                id="web_browsing",
                name="Web Browsing & Scraping",
                description="Tools for fetching web pages, scraping content, searching the web, and interacting with websites.",
                keywords=["web", "browser", "scrape", "fetch", "url", "http", "search", "crawl"],
                examples=["fetch_url", "search_web", "scrape_page", "get_html"],
                parent_domain="web",
            ),
            SkillCategoryCreateRequestContract(
                id="code_execution",
                name="Code Execution & Development",
                description="Tools for running code, executing scripts, managing development environments, and coding assistance.",
                keywords=["code", "execute", "run", "script", "python", "javascript", "compile", "debug"],
                examples=["run_python", "execute_code", "run_script", "lint_code"],
                parent_domain="development",
            ),
            SkillCategoryCreateRequestContract(
                id="knowledge_retrieval",
                name="Knowledge Retrieval & RAG",
                description="Tools for semantic search, vector retrieval, knowledge base queries, and RAG operations.",
                keywords=["search", "retrieve", "knowledge", "vector", "semantic", "rag", "embedding", "similarity"],
                examples=["semantic_search", "query_knowledge_base", "find_similar", "retrieve_context"],
                parent_domain="ai",
            ),
            SkillCategoryCreateRequestContract(
                id="image_processing",
                name="Image & Vision Processing",
                description="Tools for image analysis, generation, editing, OCR, and computer vision tasks.",
                keywords=["image", "vision", "photo", "ocr", "generate", "edit", "analyze", "detect"],
                examples=["analyze_image", "generate_image", "extract_text", "detect_objects"],
                parent_domain="media",
            ),
        ]

    # ========================================================================
    # Invalid Data Generators (for negative testing)
    # ========================================================================

    @staticmethod
    def make_invalid_skill_empty_id() -> dict:
        """Generate skill request with empty ID"""
        return {
            "id": "",
            "name": "Test Skill",
            "description": "Test description that is long enough",
        }

    @staticmethod
    def make_invalid_skill_invalid_id_format() -> dict:
        """Generate skill request with invalid ID format (starts with number)"""
        return {
            "id": "123_invalid",
            "name": "Test Skill",
            "description": "Test description that is long enough",
        }

    @staticmethod
    def make_invalid_skill_id_with_spaces() -> dict:
        """Generate skill request with spaces in ID"""
        return {
            "id": "invalid skill id",
            "name": "Test Skill",
            "description": "Test description that is long enough",
        }

    @staticmethod
    def make_invalid_skill_short_description() -> dict:
        """Generate skill request with too short description"""
        return {
            "id": "valid_id",
            "name": "Test Skill",
            "description": "Too short",  # Less than 10 chars
        }

    @staticmethod
    def make_invalid_classification_missing_tool_id() -> dict:
        """Generate classification request missing tool_id"""
        return {
            "tool_name": "test_tool",
            "tool_description": "Test description",
        }

    @staticmethod
    def make_invalid_assignment_primary_not_in_list() -> dict:
        """Generate assignment with primary_skill_id not in skill_ids"""
        return {
            "tool_id": 1,
            "skill_ids": ["skill_a", "skill_b"],
            "primary_skill_id": "skill_c",  # Not in list
        }

    @staticmethod
    def make_invalid_assignment_confidence_out_of_range() -> dict:
        """Generate assignment with confidence > 1.0"""
        return {
            "skill_id": "test_skill",
            "confidence": 1.5,  # Out of range
        }


# ============================================================================
# Request Builders (for complex test scenarios)
# ============================================================================

class SkillCategoryBuilder:
    """
    Builder pattern for creating complex skill category requests.

    Example:
        skill = (
            SkillCategoryBuilder()
            .with_id("calendar_management")
            .with_name("Calendar Management")
            .with_keywords(["calendar", "event"])
            .with_examples(["create_event"])
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "id": SkillTestDataFactory.make_skill_id(),
            "name": "Test Skill",
            "description": "A test skill category for automated testing purposes.",
            "keywords": [],
            "examples": [],
            "parent_domain": None,
            "is_active": True,
        }

    def with_id(self, skill_id: str) -> "SkillCategoryBuilder":
        """Set skill ID"""
        self._data["id"] = skill_id
        self._data["name"] = f"Skill {skill_id.replace('_', ' ').title()}"
        return self

    def with_name(self, name: str) -> "SkillCategoryBuilder":
        """Set skill name"""
        self._data["name"] = name
        return self

    def with_description(self, description: str) -> "SkillCategoryBuilder":
        """Set skill description"""
        self._data["description"] = description
        return self

    def with_keywords(self, keywords: List[str]) -> "SkillCategoryBuilder":
        """Set keywords"""
        self._data["keywords"] = keywords
        return self

    def with_examples(self, examples: List[str]) -> "SkillCategoryBuilder":
        """Set example tool names"""
        self._data["examples"] = examples
        return self

    def with_parent_domain(self, domain: str) -> "SkillCategoryBuilder":
        """Set parent domain"""
        self._data["parent_domain"] = domain
        return self

    def inactive(self) -> "SkillCategoryBuilder":
        """Set as inactive"""
        self._data["is_active"] = False
        return self

    def build(self) -> SkillCategoryCreateRequestContract:
        """Build the final request"""
        return SkillCategoryCreateRequestContract(**self._data)


class ToolClassificationBuilder:
    """
    Builder pattern for creating tool classification requests.

    Example:
        request = (
            ToolClassificationBuilder()
            .with_tool_id(123)
            .with_name("create_event")
            .with_description("Create calendar event")
            .force_reclassify()
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "tool_id": SkillTestDataFactory.make_tool_id(),
            "tool_name": "test_tool",
            "tool_description": "A test tool for automated testing",
            "input_schema_summary": None,
            "force_reclassify": False,
        }

    def with_tool_id(self, tool_id: int) -> "ToolClassificationBuilder":
        """Set tool ID"""
        self._data["tool_id"] = tool_id
        return self

    def with_name(self, name: str) -> "ToolClassificationBuilder":
        """Set tool name"""
        self._data["tool_name"] = name
        return self

    def with_description(self, description: str) -> "ToolClassificationBuilder":
        """Set tool description"""
        self._data["tool_description"] = description
        return self

    def with_schema_summary(self, summary: str) -> "ToolClassificationBuilder":
        """Set input schema summary"""
        self._data["input_schema_summary"] = summary
        return self

    def force_reclassify(self) -> "ToolClassificationBuilder":
        """Enable force reclassification"""
        self._data["force_reclassify"] = True
        return self

    def build(self) -> ToolClassificationRequestContract:
        """Build the final request"""
        return ToolClassificationRequestContract(**self._data)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enums
    "SkillStatus",
    "AssignmentSource",

    # Request Contracts
    "SkillCategoryCreateRequestContract",
    "ToolClassificationRequestContract",
    "SkillAssignmentRequestContract",
    "SkillSuggestionRequestContract",

    # Response Contracts
    "SkillCategoryResponseContract",
    "SkillAssignmentContract",
    "ToolClassificationResponseContract",
    "SkillAssignmentResponseContract",
    "SkillEmbeddingResponseContract",
    "SkillSuggestionResponseContract",

    # Factory
    "SkillTestDataFactory",

    # Builders
    "SkillCategoryBuilder",
    "ToolClassificationBuilder",
]
