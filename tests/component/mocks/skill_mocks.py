"""
Mock implementations for Skill Service testing.

Provides mock repositories and clients for component tests.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass


class MockSkillRepository:
    """
    Mock for SkillRepository.

    Stores data in memory and tracks method calls.
    """

    def __init__(self):
        self.skills: Dict[str, Dict[str, Any]] = {}
        self.assignments: List[Dict[str, Any]] = []
        self.suggestions: List[Dict[str, Any]] = []
        self._calls: List[Dict[str, Any]] = []
        self._next_suggestion_id = 1

    def _record_call(self, method: str, **kwargs):
        """Record a method call."""
        self._calls.append({"method": method, "args": kwargs})

    def get_calls(self, method: str = None) -> List[Dict[str, Any]]:
        """Get recorded calls, optionally filtered by method."""
        if method:
            return [c for c in self._calls if c["method"] == method]
        return self._calls

    def clear(self):
        """Clear all stored data."""
        self.skills = {}
        self.assignments = []
        self.suggestions = []
        self._calls = []

    # =========================================================================
    # Skill Category Operations
    # =========================================================================

    async def create_skill_category(self, skill_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a skill category."""
        self._record_call("create_skill_category", skill_data=skill_data)

        skill_id = skill_data["id"]
        now = datetime.now(timezone.utc)

        skill = {
            "id": skill_id,
            "name": skill_data.get("name", ""),
            "description": skill_data.get("description", ""),
            "keywords": skill_data.get("keywords", []),
            "examples": skill_data.get("examples", []),
            "parent_domain": skill_data.get("parent_domain"),
            "is_active": skill_data.get("is_active", True),
            "tool_count": 0,
            "created_at": now,
            "updated_at": now,
        }

        self.skills[skill_id] = skill
        return skill

    async def get_skill_by_id(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get a skill by ID."""
        self._record_call("get_skill_by_id", skill_id=skill_id)
        return self.skills.get(skill_id)

    async def get_skill_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a skill by name."""
        self._record_call("get_skill_by_name", name=name)
        for skill in self.skills.values():
            if skill["name"] == name:
                return skill
        return None

    async def list_skills(
        self,
        is_active: Optional[bool] = True,
        parent_domain: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List skills with optional filters."""
        self._record_call(
            "list_skills",
            is_active=is_active,
            parent_domain=parent_domain,
            limit=limit,
            offset=offset,
        )

        results = []
        for skill in self.skills.values():
            if is_active is not None and skill["is_active"] != is_active:
                continue
            if parent_domain is not None and skill.get("parent_domain") != parent_domain:
                continue
            results.append(skill)

        # Sort by name
        results.sort(key=lambda x: x["name"])
        return results[offset : offset + limit]

    async def update_skill_category(
        self, skill_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a skill."""
        self._record_call("update_skill_category", skill_id=skill_id, updates=updates)

        if skill_id not in self.skills:
            return None

        skill = self.skills[skill_id]
        for key, value in updates.items():
            if key not in ["id", "created_at"]:
                skill[key] = value
        skill["updated_at"] = datetime.now(timezone.utc)
        return skill

    async def delete_skill_category(self, skill_id: str) -> bool:
        """Soft delete a skill."""
        self._record_call("delete_skill_category", skill_id=skill_id)

        if skill_id not in self.skills:
            return False

        self.skills[skill_id]["is_active"] = False
        self.skills[skill_id]["updated_at"] = datetime.now(timezone.utc)
        return True

    async def increment_tool_count(self, skill_id: str, delta: int = 1) -> bool:
        """Increment tool count."""
        self._record_call("increment_tool_count", skill_id=skill_id, delta=delta)

        if skill_id not in self.skills:
            return False

        self.skills[skill_id]["tool_count"] = max(0, self.skills[skill_id]["tool_count"] + delta)
        return True

    # =========================================================================
    # Assignment Operations
    # =========================================================================

    async def create_assignment(
        self,
        tool_id: int,
        skill_id: str,
        confidence: float,
        is_primary: bool = False,
        source: str = "llm_auto",
    ) -> Optional[Dict[str, Any]]:
        """Create a tool-skill assignment."""
        self._record_call(
            "create_assignment",
            tool_id=tool_id,
            skill_id=skill_id,
            confidence=confidence,
            is_primary=is_primary,
            source=source,
        )

        now = datetime.now(timezone.utc)
        assignment = {
            "tool_id": tool_id,
            "skill_id": skill_id,
            "confidence": confidence,
            "is_primary": is_primary,
            "source": source,
            "created_at": now,
            "updated_at": now,
        }

        # Remove existing assignment for same tool+skill
        self.assignments = [
            a
            for a in self.assignments
            if not (a["tool_id"] == tool_id and a["skill_id"] == skill_id)
        ]
        self.assignments.append(assignment)
        return assignment

    async def get_assignments_for_tool(self, tool_id: int) -> List[Dict[str, Any]]:
        """Get assignments for a tool."""
        self._record_call("get_assignments_for_tool", tool_id=tool_id)

        results = [a for a in self.assignments if a["tool_id"] == tool_id]
        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results

    async def get_assignments_for_skill(
        self, skill_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get assignments for a skill."""
        self._record_call(
            "get_assignments_for_skill", skill_id=skill_id, limit=limit, offset=offset
        )

        results = [a for a in self.assignments if a["skill_id"] == skill_id]
        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results[offset : offset + limit]

    async def delete_assignments_for_tool(self, tool_id: int) -> bool:
        """Delete all assignments for a tool."""
        self._record_call("delete_assignments_for_tool", tool_id=tool_id)

        before_count = len(self.assignments)
        self.assignments = [a for a in self.assignments if a["tool_id"] != tool_id]
        return len(self.assignments) < before_count

    async def has_human_override(self, tool_id: int) -> bool:
        """Check if tool has human override."""
        self._record_call("has_human_override", tool_id=tool_id)

        for a in self.assignments:
            if a["tool_id"] == tool_id and a["source"] in ("human_manual", "human_override"):
                return True
        return False

    # =========================================================================
    # Suggestion Operations
    # =========================================================================

    async def create_suggestion(
        self,
        suggested_name: str,
        suggested_description: str,
        source_tool_id: int,
        source_tool_name: str,
        reasoning: str,
    ) -> Optional[Dict[str, Any]]:
        """Create a skill suggestion."""
        self._record_call(
            "create_suggestion",
            suggested_name=suggested_name,
            suggested_description=suggested_description,
            source_tool_id=source_tool_id,
            source_tool_name=source_tool_name,
            reasoning=reasoning,
        )

        now = datetime.now(timezone.utc)
        suggestion = {
            "id": self._next_suggestion_id,
            "suggested_name": suggested_name,
            "suggested_description": suggested_description,
            "source_tool_id": source_tool_id,
            "source_tool_name": source_tool_name,
            "reasoning": reasoning,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }

        self._next_suggestion_id += 1
        self.suggestions.append(suggestion)
        return suggestion

    async def list_suggestions(
        self, status: str = "pending", limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List skill suggestions."""
        self._record_call("list_suggestions", status=status, limit=limit, offset=offset)

        results = [s for s in self.suggestions if s["status"] == status]
        results.sort(key=lambda x: x["created_at"], reverse=True)
        return results[offset : offset + limit]

    async def update_suggestion_status(self, suggestion_id: int, status: str) -> bool:
        """Update suggestion status."""
        self._record_call("update_suggestion_status", suggestion_id=suggestion_id, status=status)

        for s in self.suggestions:
            if s["id"] == suggestion_id:
                s["status"] = status
                s["updated_at"] = datetime.now(timezone.utc)
                return True
        return False

    async def count_similar_suggestions(self, suggested_name: str) -> int:
        """Count similar pending suggestions."""
        self._record_call("count_similar_suggestions", suggested_name=suggested_name)

        count = 0
        name_lower = suggested_name.lower()
        for s in self.suggestions:
            if s["status"] == "pending" and s["suggested_name"].lower() == name_lower:
                count += 1
        return count


class MockAsyncQdrantClient:
    """
    Mock for AsyncQdrantClient from isa_common.

    Provides in-memory vector storage with the same interface.
    """

    def __init__(self, host: str = None, port: int = None, user_id: str = None):
        self.host = host
        self.port = port
        self.user_id = user_id
        self.collections: Dict[str, List[Dict[str, Any]]] = {}
        self._calls: List[Dict[str, Any]] = []

    def _record_call(self, method: str, **kwargs):
        """Record a method call."""
        self._calls.append({"method": method, "args": kwargs})

    def get_calls(self, method: str = None) -> List[Dict[str, Any]]:
        """Get recorded calls."""
        if method:
            return [c for c in self._calls if c["method"] == method]
        return self._calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def search_with_filter(
        self,
        collection_name: str,
        vector: List[float],
        filter_conditions: Optional[Dict] = None,
        limit: int = 10,
        with_payload: bool = True,
        with_vectors: bool = False,
    ) -> List[Dict[str, Any]]:
        """Search with filter."""
        self._record_call(
            "search_with_filter",
            collection_name=collection_name,
            vector_size=len(vector) if vector else 0,
            filter_conditions=filter_conditions,
            limit=limit,
        )

        if collection_name not in self.collections:
            return []

        results = []
        for point in self.collections[collection_name]:
            # Simple mock scoring based on vector similarity
            score = 0.7 + (hash(str(point.get("id", ""))) % 30) / 100

            # Apply filter if provided
            if filter_conditions and "must" in filter_conditions:
                payload = point.get("payload", {})
                match = True
                for condition in filter_conditions["must"]:
                    field = condition.get("field")
                    if field and field in payload:
                        if "match" in condition:
                            if "any" in condition["match"]:
                                # Match any in list
                                field_vals = payload.get(field, [])
                                if not isinstance(field_vals, list):
                                    field_vals = [field_vals]
                                if not any(v in condition["match"]["any"] for v in field_vals):
                                    match = False
                            elif "keyword" in condition["match"]:
                                if payload.get(field) != condition["match"]["keyword"]:
                                    match = False
                if not match:
                    continue

            result = {"id": point.get("id"), "score": score}
            if with_payload:
                result["payload"] = point.get("payload", {})
            if with_vectors:
                result["vector"] = point.get("vector", [])
            results.append(result)

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    async def upsert(self, collection_name: str, points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Upsert points (legacy interface)."""
        self._record_call("upsert", collection_name=collection_name, point_count=len(points))
        return await self._do_upsert(collection_name, points)

    async def upsert_points(self, collection_name: str, points: List[Dict[str, Any]]) -> str:
        """Upsert points — matches production AsyncQdrantClient interface."""
        self._record_call("upsert_points", collection_name=collection_name, point_count=len(points))
        await self._do_upsert(collection_name, points)
        return "mock_operation_id"

    async def _do_upsert(
        self, collection_name: str, points: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Internal upsert implementation."""
        if collection_name not in self.collections:
            self.collections[collection_name] = []

        for point in points:
            # Remove existing point with same ID
            self.collections[collection_name] = [
                p for p in self.collections[collection_name] if p.get("id") != point.get("id")
            ]
            self.collections[collection_name].append(point)

        return {"status": "ok"}

    async def delete(self, collection_name: str, point_ids: List[str]) -> Dict[str, Any]:
        """Delete points (legacy interface)."""
        self._record_call("delete", collection_name=collection_name, point_ids=point_ids)
        return await self._do_delete(collection_name, point_ids)

    async def delete_points(self, collection_name: str, point_ids: List) -> str:
        """Delete points — matches production AsyncQdrantClient interface."""
        self._record_call("delete_points", collection_name=collection_name, point_ids=point_ids)
        await self._do_delete(collection_name, point_ids)
        return "mock_operation_id"

    async def _do_delete(self, collection_name: str, point_ids: List) -> Dict[str, Any]:
        """Internal delete implementation."""
        if collection_name in self.collections:
            self.collections[collection_name] = [
                p for p in self.collections[collection_name] if p.get("id") not in point_ids
            ]
        return {"status": "ok"}

    async def update_payload(
        self,
        collection_name: str,
        ids: List,
        payload: Dict[str, Any],
    ) -> str:
        """Update payload for specific points — matches production interface."""
        self._record_call(
            "update_payload", collection_name=collection_name, ids=ids, payload=payload
        )
        if collection_name in self.collections:
            for point in self.collections[collection_name]:
                if point.get("id") in ids:
                    point.setdefault("payload", {}).update(payload)
        return "mock_operation_id"

    async def list_collections(self) -> List[str]:
        """List all collection names."""
        self._record_call("list_collections")
        return list(self.collections.keys())

    async def create_collection(
        self, collection_name: str, vector_size: int, distance: str = "Cosine"
    ) -> bool:
        """Create a collection."""
        self._record_call(
            "create_collection",
            collection_name=collection_name,
            vector_size=vector_size,
            distance=distance,
        )
        if collection_name not in self.collections:
            self.collections[collection_name] = []
        return True

    async def create_field_index(
        self, collection_name: str, field_name: str, field_type: str
    ) -> bool:
        """Create a field index (no-op in mock)."""
        self._record_call(
            "create_field_index",
            collection_name=collection_name,
            field_name=field_name,
            field_type=field_type,
        )
        return True

    async def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Get collection info."""
        self._record_call("get_collection_info", collection_name=collection_name)
        if collection_name not in self.collections:
            return None
        return {
            "points_count": len(self.collections[collection_name]),
            "status": "green",
        }

    def seed_collection(self, collection_name: str, points: List[Dict[str, Any]]):
        """Seed a collection with test data."""
        self.collections[collection_name] = points


class MockOpenAIEmbeddings:
    """
    Mock for model client embeddings interface.

    Mimics the OpenAI embeddings.create() interface.
    """

    def __init__(self):
        self._calls = []
        self._default_size = 1536

    @dataclass
    class EmbeddingResponse:
        data: List[Any]

    @dataclass
    class EmbeddingData:
        embedding: List[float]

    async def create(self, input: str, model: str = "text-embedding-3-small") -> EmbeddingResponse:
        """Create embedding."""
        self._calls.append({"input": input, "model": model})
        embedding = [0.1] * self._default_size
        return self.EmbeddingResponse(data=[self.EmbeddingData(embedding=embedding)])


@dataclass
class MockChatMessage:
    """Mock chat message."""

    content: str


@dataclass
class MockChatChoice:
    """Mock chat choice."""

    message: MockChatMessage


@dataclass
class MockChatCompletion:
    """Mock chat completion response."""

    choices: List[MockChatChoice]


class MockChatCompletions:
    """Mock for chat.completions interface."""

    def __init__(self, parent: "MockModelClient"):
        self._parent = parent

    async def create(
        self,
        model: str = "gpt-4",
        messages: List[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs,
    ) -> MockChatCompletion:
        """Create chat completion."""
        self._parent._calls.append(
            {
                "method": "chat.completions.create",
                "messages": messages,
                "model": model,
            }
        )

        response_content = self._parent._completion_response
        if not response_content:
            # Default mock response for classification
            response_content = '{"assignments": [{"skill_id": "calendar-management", "confidence": 0.85, "reasoning": "Tool handles calendar operations"}], "suggested_new_skill": null}'

        return MockChatCompletion(
            choices=[MockChatChoice(message=MockChatMessage(content=response_content))]
        )


class MockChat:
    """Mock for chat interface."""

    def __init__(self, parent: "MockModelClient"):
        self.completions = MockChatCompletions(parent)


class MockModelClient:
    """
    Mock for model client that supports embeddings and completions.

    Mimics the OpenAI client interface:
    - client.embeddings.create(...)
    - client.chat.completions.create(...)
    """

    def __init__(self):
        self.embeddings = MockOpenAIEmbeddings()
        self.chat = MockChat(self)
        self._completion_response = None
        self._calls = []

    def set_completion_response(self, response: str):
        """Set the response for completions."""
        self._completion_response = response

    def get_calls(self, method: str = None) -> List[Dict]:
        """Get recorded calls."""
        if method:
            return [c for c in self._calls if c.get("method") == method]
        return self._calls
