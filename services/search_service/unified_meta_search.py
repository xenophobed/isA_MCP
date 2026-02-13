"""
Unified Meta Search Service - Search across all MCP entity types.

Searches across:
- Tools (internal + external from MCP servers)
- Prompts (internal + external)
- Resources (internal + external)
- Skills (vibe + external)

Provides:
- Unified search interface
- Type filtering
- Hierarchical skill-based routing
- Combined scoring and ranking
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.config import get_settings
from core.clients.model_client import get_model_client

logger = logging.getLogger(__name__)


class EntityType(str, Enum):
    """Types of searchable entities."""

    TOOL = "tool"
    PROMPT = "prompt"
    RESOURCE = "resource"
    SKILL = "skill"  # Includes both vibe and external skills


@dataclass
class EntityMatch:
    """A matched entity from search."""

    id: str
    entity_type: EntityType
    name: str
    description: str
    score: float
    source: str = "internal"  # 'internal', 'external', 'vibe'

    # Optional metadata based on type
    db_id: Optional[int] = None
    skill_ids: List[str] = field(default_factory=list)
    primary_skill_id: Optional[str] = None

    # Type-specific fields
    input_schema: Optional[Dict[str, Any]] = None  # For tools
    uri: Optional[str] = None  # For resources/skills
    version: Optional[str] = None  # For skills


@dataclass
class SkillCategoryMatch:
    """A matched skill category for hierarchical routing."""

    id: str
    name: str
    description: str
    score: float
    entity_count: int = 0


@dataclass
class UnifiedSearchResult:
    """Complete unified search result."""

    query: str
    entities: List[EntityMatch]
    matched_skill_categories: List[SkillCategoryMatch]
    metadata: Dict[str, Any]


class UnifiedMetaSearch:
    """
    Unified search service across all MCP entity types.

    Combines:
    - HierarchicalSearchService for tools/prompts/resources
    - SkillManager for vibe/external skills

    Example:
        >>> search = UnifiedMetaSearch()
        >>> result = await search.search("test automation", entity_types=[EntityType.TOOL, EntityType.SKILL])
        >>> for entity in result.entities:
        ...     print(f"{entity.entity_type}: {entity.name} ({entity.score:.2f})")
    """

    def __init__(
        self,
        hierarchical_search=None,
        skill_manager=None,
        model_client=None,
    ):
        """
        Initialize UnifiedMetaSearch.

        Args:
            hierarchical_search: Optional HierarchicalSearchService instance
            skill_manager: Optional SkillManager instance
            model_client: Optional model client for embeddings
        """
        self._hierarchical_search = hierarchical_search
        self._skill_manager = skill_manager
        self._model_client = model_client
        self._settings = get_settings()

    async def _get_hierarchical_search(self):
        """Get or create hierarchical search service."""
        if self._hierarchical_search is None:
            from services.search_service.hierarchical_search_service import (
                HierarchicalSearchService,
            )

            self._hierarchical_search = HierarchicalSearchService(model_client=self._model_client)
        return self._hierarchical_search

    def _get_skill_manager(self):
        """Get or create skill manager."""
        if self._skill_manager is None:
            from resources.skill_resources import get_skill_manager

            self._skill_manager = get_skill_manager()
        return self._skill_manager

    async def _get_model_client(self):
        """Get or create model client."""
        if self._model_client is None:
            self._model_client = await get_model_client()
        return self._model_client

    async def search(
        self,
        query: str,
        entity_types: Optional[List[EntityType]] = None,
        limit: int = 10,
        skill_limit: int = 3,
        skill_threshold: float = 0.4,
        entity_threshold: float = 0.3,
        include_schemas: bool = False,
        use_hierarchical: bool = True,
    ) -> UnifiedSearchResult:
        """
        Search across all entity types.

        Args:
            query: Natural language search query
            entity_types: Filter by entity types (None = all types)
            limit: Maximum results per entity type
            skill_limit: Maximum skill categories for hierarchical routing
            skill_threshold: Minimum similarity for skill category matching
            entity_threshold: Minimum similarity for entity matching
            include_schemas: Whether to load full schemas for tools
            use_hierarchical: Use skill-based hierarchical routing

        Returns:
            UnifiedSearchResult with entities, skill categories, and metadata
        """
        start_time = time.time()

        # Default to all types
        if entity_types is None:
            entity_types = list(EntityType)

        # Validate query
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        all_entities: List[EntityMatch] = []
        skill_categories: List[SkillCategoryMatch] = []
        metadata = {
            "query": query,
            "entity_types_requested": [t.value for t in entity_types],
            "timings": {},
        }

        # Search tools/prompts/resources/skills via hierarchical search
        # Skills are stored as resources with resource_type="skill"
        db_types = [
            t
            for t in entity_types
            if t in (EntityType.TOOL, EntityType.PROMPT, EntityType.RESOURCE, EntityType.SKILL)
        ]
        if db_types:
            db_results = await self._search_database_entities(
                query=query,
                entity_types=db_types,
                limit=limit,
                skill_limit=skill_limit,
                skill_threshold=skill_threshold,
                entity_threshold=entity_threshold,
                include_schemas=include_schemas,
                use_hierarchical=use_hierarchical,
            )
            all_entities.extend(db_results["entities"])
            skill_categories = db_results["skill_categories"]
            metadata["timings"]["database_search_ms"] = db_results["time_ms"]

        # Sort all results by score
        all_entities.sort(key=lambda x: x.score, reverse=True)

        # Limit total results
        all_entities = all_entities[: limit * len(entity_types)]

        # Calculate totals
        metadata["total_results"] = len(all_entities)
        metadata["results_by_type"] = {}
        for t in entity_types:
            count = len([e for e in all_entities if e.entity_type == t])
            metadata["results_by_type"][t.value] = count

        metadata["total_time_ms"] = (time.time() - start_time) * 1000

        return UnifiedSearchResult(
            query=query,
            entities=all_entities,
            matched_skill_categories=skill_categories,
            metadata=metadata,
        )

    async def _search_database_entities(
        self,
        query: str,
        entity_types: List[EntityType],
        limit: int,
        skill_limit: int,
        skill_threshold: float,
        entity_threshold: float,
        include_schemas: bool,
        use_hierarchical: bool,
    ) -> Dict[str, Any]:
        """Search tools/prompts/resources/skills via HierarchicalSearchService."""
        start_time = time.time()

        hierarchical_search = await self._get_hierarchical_search()
        entities = []
        skill_categories = []

        # Map entity types to item_type strings
        # Skills are stored as resources with resource_type="skill"
        type_map = {
            EntityType.TOOL: "tool",
            EntityType.PROMPT: "prompt",
            EntityType.RESOURCE: "resource",
            EntityType.SKILL: "resource",  # Skills are a type of resource
        }

        # Search each type (or all if multiple)
        for entity_type in entity_types:
            item_type = type_map.get(entity_type)
            if not item_type:
                continue

            try:
                result = await hierarchical_search.search(
                    query=query,
                    item_type=item_type,
                    limit=limit,
                    skill_limit=skill_limit,
                    skill_threshold=skill_threshold,
                    tool_threshold=entity_threshold,
                    include_schemas=include_schemas,
                    strategy="hierarchical" if use_hierarchical else "direct",
                )

                # Convert ToolMatch to EntityMatch
                for tool in result.tools:
                    # Determine actual entity type (for SKILL, check if it's a skill resource)
                    actual_entity_type = entity_type
                    source = "external" if getattr(tool, "is_external", False) else "internal"
                    uri = None

                    # If searching for SKILL, filter to only include skill resources
                    if entity_type == EntityType.SKILL:
                        # Check metadata for resource_type
                        metadata = getattr(tool, "metadata", {}) or {}
                        resource_type = metadata.get("resource_type", "")
                        if resource_type != "skill":
                            continue  # Skip non-skill resources
                        uri = metadata.get("uri")
                        # Determine source from URI
                        if uri and "external" in uri:
                            source = "external"
                        elif uri and "vibe" in uri:
                            source = "vibe"

                    # If searching for RESOURCE, skip skill resources (to avoid duplicates)
                    if entity_type == EntityType.RESOURCE:
                        metadata = getattr(tool, "metadata", {}) or {}
                        resource_type = metadata.get("resource_type", "")
                        if resource_type == "skill":
                            continue  # Skip skill resources when searching for regular resources

                    entities.append(
                        EntityMatch(
                            id=tool.id,
                            entity_type=actual_entity_type,
                            name=tool.name,
                            description=tool.description,
                            score=tool.score,
                            source=source,
                            db_id=tool.db_id,
                            skill_ids=tool.skill_ids,
                            primary_skill_id=tool.primary_skill_id,
                            input_schema=(
                                tool.input_schema if entity_type == EntityType.TOOL else None
                            ),
                            uri=uri,
                        )
                    )

                # Collect skill categories (only from first search to avoid duplicates)
                if not skill_categories and result.matched_skills:
                    skill_categories = [
                        SkillCategoryMatch(
                            id=s.id,
                            name=s.name,
                            description=s.description,
                            score=s.score,
                            entity_count=s.tool_count,
                        )
                        for s in result.matched_skills
                    ]

            except Exception as e:
                logger.error(f"Error searching {entity_type.value}: {e}")

        return {
            "entities": entities,
            "skill_categories": skill_categories,
            "time_ms": (time.time() - start_time) * 1000,
        }

    async def _search_skills(
        self,
        query: str,
        limit: int,
        threshold: float,
    ) -> List[EntityMatch]:
        """Search skills via SkillManager."""
        skill_manager = self._get_skill_manager()

        # Use SkillManager's search
        results = skill_manager.search_skills(query)

        entities = []
        for skill in results[:limit]:
            # SkillManager uses additive scoring (0-2+ range)
            # Normalize to 0-1 range for consistency
            raw_score = skill.get("match_score", 0)
            normalized_score = min(raw_score / 2.0, 1.0)

            # Skills have lower threshold since they use keyword matching
            skill_threshold = threshold * 0.5  # More lenient for skills

            if raw_score > 0:  # Any match is valid
                entities.append(
                    EntityMatch(
                        id=f"skill_{skill['type']}_{skill['name']}",
                        entity_type=EntityType.SKILL,
                        name=skill["name"],
                        description=skill.get("description", ""),
                        score=normalized_score,
                        source=skill.get("type", "vibe"),  # 'vibe' or 'external'
                        uri=skill.get("uri"),
                    )
                )

        return entities

    async def search_by_type(
        self,
        query: str,
        entity_type: EntityType,
        limit: int = 10,
        threshold: float = 0.3,
    ) -> List[EntityMatch]:
        """
        Convenience method to search a single entity type.

        Args:
            query: Search query
            entity_type: Type to search
            limit: Maximum results
            threshold: Minimum similarity score

        Returns:
            List of matching entities
        """
        result = await self.search(
            query=query,
            entity_types=[entity_type],
            limit=limit,
            entity_threshold=threshold,
        )
        return result.entities

    def to_dict(self, result: UnifiedSearchResult) -> Dict[str, Any]:
        """Convert search result to dictionary for API response."""
        return {
            "query": result.query,
            "entities": [
                {
                    "id": e.id,
                    "type": e.entity_type.value,
                    "name": e.name,
                    "description": e.description,
                    "score": e.score,
                    "source": e.source,
                    "db_id": e.db_id,
                    "skill_ids": e.skill_ids,
                    "primary_skill_id": e.primary_skill_id,
                    "input_schema": e.input_schema,
                    "uri": e.uri,
                    "version": e.version,
                }
                for e in result.entities
            ],
            "matched_skill_categories": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "score": s.score,
                    "entity_count": s.entity_count,
                }
                for s in result.matched_skill_categories
            ],
            "metadata": result.metadata,
        }


# Convenience function for quick searches
async def unified_search(
    query: str,
    entity_types: Optional[List[str]] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Quick unified search across all entity types.

    Args:
        query: Search query
        entity_types: List of type strings ('tool', 'prompt', 'resource', 'skill')
        limit: Maximum results

    Returns:
        Dictionary with search results

    Example:
        >>> result = await unified_search("test automation", entity_types=["tool", "skill"])
    """
    search = UnifiedMetaSearch()

    # Convert string types to EntityType enum
    types = None
    if entity_types:
        type_map = {
            "tool": EntityType.TOOL,
            "prompt": EntityType.PROMPT,
            "resource": EntityType.RESOURCE,
            "skill": EntityType.SKILL,
        }
        types = [type_map[t] for t in entity_types if t in type_map]

    result = await search.search(query, entity_types=types, limit=limit)
    return search.to_dict(result)
