"""
Skill Repository - Data access layer for skill categories and assignments.

Provides CRUD operations for:
- skill_categories: Predefined skill categories
- tool_skill_assignments: Tool-to-skill mappings
- skill_suggestions: LLM-suggested new skills pending review
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from isa_common import AsyncPostgresClient
from core.config import get_settings

logger = logging.getLogger(__name__)


class SkillRepository:
    """
    Repository for skill-related database operations.

    Tables:
        - mcp.skill_categories: Skill category definitions
        - mcp.tool_skill_assignments: Tool-skill mappings with confidence
        - mcp.skill_suggestions: Pending skill suggestions from LLM
    """

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        """
        Initialize the skill repository.

        Args:
            host: PostgreSQL gRPC host (defaults to config)
            port: PostgreSQL gRPC port (defaults to config)
        """
        settings = get_settings()
        host = host or settings.infrastructure.postgres_grpc_host
        port = port or settings.infrastructure.postgres_grpc_port

        self.db = AsyncPostgresClient(host=host, port=port, user_id="mcp-skill-service")
        self.schema = "mcp"
        self.skill_table = "skill_categories"
        self.assignment_table = "tool_skill_assignments"
        self.suggestion_table = "skill_suggestions"

        # Fields that should never be updated
        self._immutable_fields = ["id", "created_at"]

    # =========================================================================
    # Skill Category Operations
    # =========================================================================

    async def create_skill_category(
        self,
        skill_data: Dict[str, Any],
        org_id: Optional[str] = None,
        is_global: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new skill category with multi-tenant support.

        Args:
            skill_data: Skill data including id, name, description, keywords, etc.
            org_id: Organization ID that owns this skill (None for system skills)
            is_global: Whether this skill is visible to all organizations

        Returns:
            Created skill record or None on failure
        """
        try:
            # Serialize JSON fields
            record = {
                "id": skill_data["id"],
                "name": skill_data["name"],
                "description": skill_data["description"],
                "keywords": skill_data.get("keywords", []),
                "examples": skill_data.get("examples", []),
                "parent_domain": skill_data.get("parent_domain"),
                "is_active": skill_data.get("is_active", True),
                "tool_count": 0,
                "org_id": org_id,
                "is_global": is_global,
            }

            async with self.db:
                count = await self.db.insert_into(self.skill_table, [record], schema=self.schema)

                if count > 0:
                    # Fetch the created record (internal fetch, no tenant filter)
                    return await self._get_skill_by_id_internal(skill_data["id"])

            return None

        except Exception as e:
            logger.error(f"Failed to create skill category '{skill_data.get('id')}': {e}")
            return None

    async def _get_skill_by_id_internal(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """
        Internal method to get skill by ID without tenant filtering.

        Used after create operations where we need to fetch the just-created record.

        Args:
            skill_id: The skill category ID

        Returns:
            Skill record or None if not found
        """
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.skill_table} WHERE id = $1",
                    params=[skill_id],
                )
            return result
        except Exception as e:
            logger.error(f"Failed to get skill by ID (internal) '{skill_id}': {e}")
            return None

    async def get_skill_by_id(
        self, skill_id: str, org_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a skill category by ID with tenant filtering.

        Args:
            skill_id: The skill category ID (string)
            org_id: Organization ID for tenant filtering (returns global + org-specific)
                    If None, returns only global skills (backward compatible)

        Returns:
            Skill record or None if not found or not accessible
        """
        try:
            if org_id is not None:
                # Tenant-aware: return global OR org-specific
                query = f"""
                    SELECT * FROM {self.schema}.{self.skill_table}
                    WHERE id = $1 AND (is_global = TRUE OR org_id = $2)
                """
                params = [skill_id, org_id]
            else:
                # Backward compatible: return only global skills
                query = f"""
                    SELECT * FROM {self.schema}.{self.skill_table}
                    WHERE id = $1 AND is_global = TRUE
                """
                params = [skill_id]

            async with self.db:
                result = await self.db.query_row(query, params=params)
            return result
        except Exception as e:
            logger.error(f"Failed to get skill by ID '{skill_id}': {e}")
            return None

    async def get_skill_by_name(
        self, name: str, org_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a skill category by name with tenant filtering.

        Args:
            name: The skill category name
            org_id: Organization ID for tenant filtering (returns global + org-specific)
                    If None, returns only global skills (backward compatible)

        Returns:
            Skill record or None if not found or not accessible
        """
        try:
            if org_id is not None:
                # Tenant-aware: return global OR org-specific
                query = f"""
                    SELECT * FROM {self.schema}.{self.skill_table}
                    WHERE name = $1 AND (is_global = TRUE OR org_id = $2)
                """
                params = [name, org_id]
            else:
                # Backward compatible: return only global skills
                query = f"""
                    SELECT * FROM {self.schema}.{self.skill_table}
                    WHERE name = $1 AND is_global = TRUE
                """
                params = [name]

            async with self.db:
                result = await self.db.query_row(query, params=params)
            return result
        except Exception as e:
            logger.error(f"Failed to get skill by name '{name}': {e}")
            return None

    async def list_skills(
        self,
        is_active: Optional[bool] = True,
        parent_domain: Optional[str] = None,
        org_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List skill categories with optional filters and tenant isolation.

        Args:
            is_active: Filter by active status (None = all)
            parent_domain: Filter by parent domain
            org_id: Filter by organization (returns global + org-specific)
                    If None, returns only global skills (backward compatible)
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of skill records
        """
        try:
            conditions = []
            params = []
            param_idx = 1

            if is_active is not None:
                conditions.append(f"is_active = ${param_idx}")
                params.append(is_active)
                param_idx += 1

            if org_id is not None:
                # Tenant-aware: return global + org-specific
                conditions.append(f"(is_global = TRUE OR org_id = ${param_idx})")
                params.append(org_id)
                param_idx += 1
            else:
                # Backward compatible: return only global skills
                conditions.append("is_global = TRUE")

            if parent_domain is not None:
                conditions.append(f"parent_domain = ${param_idx}")
                params.append(parent_domain)
                param_idx += 1

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            params.extend([limit, offset])

            query = f"""
                SELECT * FROM {self.schema}.{self.skill_table}
                WHERE {where_clause}
                ORDER BY name ASC
                LIMIT ${param_idx} OFFSET ${param_idx + 1}
            """

            async with self.db:
                results = await self.db.query(query, params=params)

            return results or []

        except Exception as e:
            logger.error(f"Failed to list skills: {e}")
            return []

    async def update_skill_category(
        self, skill_id: str, updates: Dict[str, Any], org_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update a skill category with ownership validation.

        Args:
            skill_id: The skill ID to update
            updates: Dictionary of fields to update
            org_id: Organization ID for ownership validation
                    If provided, validates the skill belongs to this org or is global

        Returns:
            Updated skill record or None on failure/not found/not authorized
        """
        try:
            # Filter out immutable fields
            valid_updates = {k: v for k, v in updates.items() if k not in self._immutable_fields}

            if not valid_updates:
                return await self.get_skill_by_id(skill_id, org_id=org_id)

            # Build SET clause
            set_parts = []
            params = []
            param_idx = 1

            for key, value in valid_updates.items():
                set_parts.append(f"{key} = ${param_idx}")
                # Serialize complex types
                if isinstance(value, (dict, list)):
                    params.append(json.dumps(value))
                else:
                    params.append(value)
                param_idx += 1

            # Add updated_at
            set_parts.append(f"updated_at = ${param_idx}")
            params.append(datetime.now(timezone.utc))
            param_idx += 1

            # Add WHERE clause - include org_id ownership check if provided
            params.append(skill_id)
            if org_id is not None:
                # Can only update org's own skills (not global system skills)
                params.append(org_id)
                query = f"""
                    UPDATE {self.schema}.{self.skill_table}
                    SET {', '.join(set_parts)}
                    WHERE id = ${param_idx} AND org_id = ${param_idx + 1}
                """
            else:
                query = f"""
                    UPDATE {self.schema}.{self.skill_table}
                    SET {', '.join(set_parts)}
                    WHERE id = ${param_idx}
                """

            async with self.db:
                await self.db.execute(query, params=params)
                return await self.get_skill_by_id(skill_id, org_id=org_id)

        except Exception as e:
            logger.error(f"Failed to update skill '{skill_id}': {e}")
            return None

    async def delete_skill_category(
        self, skill_id: str, org_id: Optional[str] = None
    ) -> bool:
        """
        Soft delete a skill category (set is_active=False) with ownership validation.

        Args:
            skill_id: The skill ID to delete
            org_id: Organization ID for ownership validation
                    If provided, validates the skill belongs to this org

        Returns:
            True if successful, False otherwise (including not found/not authorized)
        """
        try:
            if org_id is not None:
                # Can only delete org's own skills (not global system skills)
                query = f"""
                    UPDATE {self.schema}.{self.skill_table}
                    SET is_active = FALSE, updated_at = $1
                    WHERE id = $2 AND org_id = $3
                """
                params = [datetime.now(timezone.utc), skill_id, org_id]
            else:
                query = f"""
                    UPDATE {self.schema}.{self.skill_table}
                    SET is_active = FALSE, updated_at = $1
                    WHERE id = $2
                """
                params = [datetime.now(timezone.utc), skill_id]

            async with self.db:
                await self.db.execute(query, params=params)
            return True
        except Exception as e:
            logger.error(f"Failed to delete skill '{skill_id}': {e}")
            return False

    async def increment_tool_count(self, skill_id: str, delta: int = 1) -> bool:
        """
        Increment or decrement the tool count for a skill.

        Args:
            skill_id: The skill ID
            delta: Amount to add (negative to decrement)

        Returns:
            True if successful
        """
        try:
            async with self.db:
                await self.db.execute(
                    f"""
                    UPDATE {self.schema}.{self.skill_table}
                    SET tool_count = GREATEST(0, tool_count + $1), updated_at = $2
                    WHERE id = $3
                    """,
                    params=[delta, datetime.now(timezone.utc), skill_id],
                )
            return True
        except Exception as e:
            logger.error(f"Failed to update tool count for skill '{skill_id}': {e}")
            return False

    # =========================================================================
    # Tool-Skill Assignment Operations
    # =========================================================================

    async def create_assignment(
        self,
        tool_id: int,
        skill_id: str,
        confidence: float,
        is_primary: bool = False,
        source: str = "llm_auto",
        org_id: Optional[str] = None,
        is_global: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a tool-skill assignment with multi-tenant support.

        Args:
            tool_id: The tool database ID
            skill_id: The skill ID
            confidence: Confidence score (0.0-1.0)
            is_primary: Whether this is the primary skill
            source: Assignment source (llm_auto, human_manual, human_override)
            org_id: Organization ID that owns this assignment
            is_global: Whether this assignment is visible to all organizations

        Returns:
            Created assignment record or None
        """
        try:
            record = {
                "tool_id": tool_id,
                "skill_id": skill_id,
                "confidence": confidence,
                "is_primary": is_primary,
                "source": source,
                "org_id": org_id,
                "is_global": is_global,
            }

            async with self.db:
                count = await self.db.insert_into(
                    self.assignment_table, [record], schema=self.schema
                )

                if count is not None and count > 0:
                    # Fetch created assignment
                    return await self.db.query_row(
                        f"""
                        SELECT * FROM {self.schema}.{self.assignment_table}
                        WHERE tool_id = $1 AND skill_id = $2
                        """,
                        params=[tool_id, skill_id],
                    )

            return None

        except Exception as e:
            logger.error(f"Failed to create assignment for tool {tool_id} -> {skill_id}: {e}")
            return None

    async def get_assignments_for_tool(
        self, tool_id: int, org_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all skill assignments for a tool with tenant filtering.

        Args:
            tool_id: The tool database ID
            org_id: Filter by organization (returns global + org-specific)
                    If None, returns only global assignments (backward compatible)

        Returns:
            List of assignment records sorted by confidence DESC
        """
        try:
            conditions = ["tool_id = $1"]
            params: list = [tool_id]
            if org_id is not None:
                # Tenant-aware: return global + org-specific
                conditions.append("(is_global = TRUE OR org_id = $2)")
                params.append(org_id)
            else:
                # Backward compatible: return only global assignments
                conditions.append("is_global = TRUE")
            where = " AND ".join(conditions)
            async with self.db:
                results = await self.db.query(
                    f"""
                    SELECT * FROM {self.schema}.{self.assignment_table}
                    WHERE {where}
                    ORDER BY confidence DESC
                    """,
                    params=params,
                )
            return results or []
        except Exception as e:
            logger.error(f"Failed to get assignments for tool {tool_id}: {e}")
            return []

    async def get_assignments_for_skill(
        self, skill_id: str, limit: int = 100, offset: int = 0, org_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all tool assignments for a skill with tenant filtering.

        Args:
            skill_id: The skill ID
            limit: Maximum results
            offset: Pagination offset
            org_id: Filter by organization (returns global + org-specific)
                    If None, returns only global assignments (backward compatible)

        Returns:
            List of assignment records sorted by confidence DESC
        """
        try:
            if org_id is not None:
                # Tenant-aware: return global + org-specific
                query = f"""
                    SELECT * FROM {self.schema}.{self.assignment_table}
                    WHERE skill_id = $1 AND (is_global = TRUE OR org_id = $2)
                    ORDER BY confidence DESC
                    LIMIT $3 OFFSET $4
                """
                params = [skill_id, org_id, limit, offset]
            else:
                # Backward compatible: return only global assignments
                query = f"""
                    SELECT * FROM {self.schema}.{self.assignment_table}
                    WHERE skill_id = $1 AND is_global = TRUE
                    ORDER BY confidence DESC
                    LIMIT $2 OFFSET $3
                """
                params = [skill_id, limit, offset]

            async with self.db:
                results = await self.db.query(query, params=params)
            return results or []
        except Exception as e:
            logger.error(f"Failed to get assignments for skill '{skill_id}': {e}")
            return []

    async def delete_assignments_for_tool(self, tool_id: int) -> bool:
        """
        Delete all skill assignments for a tool.

        Used when re-classifying a tool.

        Args:
            tool_id: The tool database ID

        Returns:
            True if successful
        """
        try:
            async with self.db:
                await self.db.execute(
                    f"DELETE FROM {self.schema}.{self.assignment_table} WHERE tool_id = $1",
                    params=[tool_id],
                )
            return True
        except Exception as e:
            logger.error(f"Failed to delete assignments for tool {tool_id}: {e}")
            return False

    async def has_human_override(self, tool_id: int) -> bool:
        """
        Check if a tool has a human override assignment.

        Args:
            tool_id: The tool database ID

        Returns:
            True if tool has human_manual or human_override assignment
        """
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"""
                    SELECT 1 FROM {self.schema}.{self.assignment_table}
                    WHERE tool_id = $1 AND source IN ('human_manual', 'human_override')
                    LIMIT 1
                    """,
                    params=[tool_id],
                )
            return result is not None
        except Exception as e:
            logger.error(f"Failed to check human override for tool {tool_id}: {e}")
            return False

    # =========================================================================
    # Skill Suggestion Operations
    # =========================================================================

    async def create_suggestion(
        self,
        suggested_name: str,
        suggested_description: str,
        source_tool_id: int,
        source_tool_name: str,
        reasoning: str,
        org_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a skill suggestion from LLM with multi-tenant support.

        Args:
            suggested_name: Suggested skill name
            suggested_description: Suggested description
            source_tool_id: Tool that triggered the suggestion
            source_tool_name: Tool name for context
            reasoning: LLM reasoning for suggestion
            org_id: Organization ID that owns this suggestion

        Returns:
            Created suggestion record or None
        """
        try:
            record = {
                "suggested_name": suggested_name,
                "suggested_description": suggested_description,
                "source_tool_id": source_tool_id,
                "source_tool_name": source_tool_name,
                "reasoning": reasoning,
                "status": "pending",
                "org_id": org_id,
            }

            async with self.db:
                count = await self.db.insert_into(
                    self.suggestion_table, [record], schema=self.schema
                )

                if count > 0:
                    # Fetch by name (most recent)
                    return await self.db.query_row(
                        f"""
                        SELECT * FROM {self.schema}.{self.suggestion_table}
                        WHERE suggested_name = $1
                        ORDER BY created_at DESC
                        LIMIT 1
                        """,
                        params=[suggested_name],
                    )

            return None

        except Exception as e:
            logger.error(f"Failed to create skill suggestion '{suggested_name}': {e}")
            return None

    async def list_suggestions(
        self, status: str = "pending", limit: int = 100, offset: int = 0, org_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List skill suggestions with optional tenant filtering.

        Args:
            status: Filter by status (pending, approved, rejected, merged)
            limit: Maximum results
            offset: Pagination offset
            org_id: Filter by organization (returns only org's suggestions)
                    If None, returns all suggestions (backward compatible for admins)

        Returns:
            List of suggestion records
        """
        try:
            if org_id is not None:
                # Tenant-aware: return only org's suggestions
                query = f"""
                    SELECT * FROM {self.schema}.{self.suggestion_table}
                    WHERE status = $1 AND org_id = $2
                    ORDER BY created_at DESC
                    LIMIT $3 OFFSET $4
                """
                params = [status, org_id, limit, offset]
            else:
                # Backward compatible: return all (for admins)
                query = f"""
                    SELECT * FROM {self.schema}.{self.suggestion_table}
                    WHERE status = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                """
                params = [status, limit, offset]

            async with self.db:
                results = await self.db.query(query, params=params)
            return results or []
        except Exception as e:
            logger.error(f"Failed to list suggestions: {e}")
            return []

    async def update_suggestion_status(self, suggestion_id: int, status: str) -> bool:
        """
        Update suggestion status.

        Args:
            suggestion_id: The suggestion ID
            status: New status (approved, rejected, merged)

        Returns:
            True if successful
        """
        try:
            async with self.db:
                await self.db.execute(
                    f"""
                    UPDATE {self.schema}.{self.suggestion_table}
                    SET status = $1, updated_at = $2
                    WHERE id = $3
                    """,
                    params=[status, datetime.now(timezone.utc), suggestion_id],
                )
            return True
        except Exception as e:
            logger.error(f"Failed to update suggestion {suggestion_id}: {e}")
            return False

    async def count_similar_suggestions(self, suggested_name: str) -> int:
        """
        Count how many times a similar skill has been suggested.

        Used for auto-approval threshold.

        Args:
            suggested_name: The suggested skill name

        Returns:
            Count of similar pending suggestions
        """
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"""
                    SELECT COUNT(*) as count FROM {self.schema}.{self.suggestion_table}
                    WHERE LOWER(suggested_name) = LOWER($1) AND status = 'pending'
                    """,
                    params=[suggested_name],
                )
            return result.get("count", 0) if result else 0
        except Exception as e:
            logger.error(f"Failed to count suggestions for '{suggested_name}': {e}")
            return 0

    # =========================================================================
    # Atomic Multi-Step Operations (Transaction Boundaries)
    # =========================================================================

    async def create_assignment_atomic(
        self,
        tool_id: int,
        skill_id: str,
        confidence: float,
        is_primary: bool = False,
        source: str = "llm_auto",
    ) -> Optional[Dict[str, Any]]:
        """
        Atomically create assignment and increment skill tool count.

        TRANSACTION BOUNDARY: Assignment Creation + Tool Count Increment (atomic)

        If incrementing tool count fails, the assignment is rolled back.
        This ensures tool counts stay accurate.

        Args:
            tool_id: The tool database ID
            skill_id: The skill ID
            confidence: Confidence score (0.0-1.0)
            is_primary: Whether this is the primary skill
            source: Assignment source (llm_auto, human_manual, human_override)

        Returns:
            Created assignment record or None on failure

        Raises:
            Exception: If any step fails, entire transaction is rolled back
        """
        try:
            await self.db._ensure_connected()

            # TRANSACTION BOUNDARY: Assignment + Tool Count (atomic)
            async with self.db._pool.acquire() as conn:
                async with conn.transaction():
                    now = datetime.now(timezone.utc)

                    # Step 1: Insert assignment
                    await conn.execute(
                        f"""
                        INSERT INTO {self.schema}.{self.assignment_table}
                        (tool_id, skill_id, confidence, is_primary, source, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        tool_id,
                        skill_id,
                        confidence,
                        is_primary,
                        source,
                        now,
                    )

                    # Step 2: Increment tool count on the skill
                    await conn.execute(
                        f"""
                        UPDATE {self.schema}.{self.skill_table}
                        SET tool_count = GREATEST(0, tool_count + 1), updated_at = $1
                        WHERE id = $2
                        """,
                        now,
                        skill_id,
                    )

                    # Step 3: Fetch the created assignment
                    row = await conn.fetchrow(
                        f"""
                        SELECT * FROM {self.schema}.{self.assignment_table}
                        WHERE tool_id = $1 AND skill_id = $2
                        """,
                        tool_id,
                        skill_id,
                    )

            logger.debug(f"Atomically created assignment: tool {tool_id} -> skill {skill_id}")
            return dict(row) if row else None

        except Exception as e:
            logger.error(
                f"Failed to atomically create assignment for tool {tool_id} -> {skill_id}: {e}"
            )
            return None

    async def delete_assignments_for_tool_atomic(self, tool_id: int) -> bool:
        """
        Atomically delete all assignments and decrement skill tool counts.

        TRANSACTION BOUNDARY: Assignments Deletion + Tool Count Decrements (atomic)

        If decrementing tool counts fails, assignments are restored.
        This ensures tool counts stay accurate.

        Args:
            tool_id: The tool database ID

        Returns:
            True if successful

        Raises:
            Exception: If any step fails, entire transaction is rolled back
        """
        try:
            await self.db._ensure_connected()

            # TRANSACTION BOUNDARY: Get skill IDs + Delete + Decrement (atomic)
            async with self.db._pool.acquire() as conn:
                async with conn.transaction():
                    now = datetime.now(timezone.utc)

                    # Step 1: Get all skill IDs before deletion
                    rows = await conn.fetch(
                        f"""
                        SELECT skill_id FROM {self.schema}.{self.assignment_table}
                        WHERE tool_id = $1
                        """,
                        tool_id,
                    )
                    skill_ids = [row["skill_id"] for row in rows]

                    if not skill_ids:
                        # No assignments to delete
                        return True

                    # Step 2: Delete assignments
                    await conn.execute(
                        f"DELETE FROM {self.schema}.{self.assignment_table} WHERE tool_id = $1",
                        tool_id,
                    )

                    # Step 3: Decrement tool count for each skill
                    for skill_id in skill_ids:
                        await conn.execute(
                            f"""
                            UPDATE {self.schema}.{self.skill_table}
                            SET tool_count = GREATEST(0, tool_count - 1), updated_at = $1
                            WHERE id = $2
                            """,
                            now,
                            skill_id,
                        )

            logger.debug(f"Atomically deleted {len(skill_ids)} assignments for tool {tool_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to atomically delete assignments for tool {tool_id}: {e}")
            return False

    async def reassign_tool_skills_atomic(
        self,
        tool_id: int,
        new_skill_ids: List[str],
        confidences: List[float],
        primary_skill_id: Optional[str] = None,
        source: str = "llm_auto",
    ) -> bool:
        """
        Atomically reassign tool to new skills (delete old + create new + update counts).

        TRANSACTION BOUNDARY: Delete Old Assignments + Create New + Update Counts (atomic)

        This is used when re-classifying a tool with new skills.

        Args:
            tool_id: The tool database ID
            new_skill_ids: List of new skill IDs
            confidences: List of confidence scores (parallel to skill_ids)
            primary_skill_id: Primary skill (defaults to first skill)
            source: Assignment source

        Returns:
            True if successful

        Raises:
            Exception: If any step fails, entire transaction is rolled back
        """
        if not new_skill_ids:
            # Just delete existing assignments
            return await self.delete_assignments_for_tool_atomic(tool_id)

        if len(new_skill_ids) != len(confidences):
            logger.error("Mismatched skill_ids and confidences lengths")
            return False

        primary = primary_skill_id or new_skill_ids[0]

        try:
            await self.db._ensure_connected()

            # TRANSACTION BOUNDARY: Full reassignment (atomic)
            async with self.db._pool.acquire() as conn:
                async with conn.transaction():
                    now = datetime.now(timezone.utc)

                    # Step 1: Get old skill IDs for decrementing
                    old_rows = await conn.fetch(
                        f"""
                        SELECT skill_id FROM {self.schema}.{self.assignment_table}
                        WHERE tool_id = $1
                        """,
                        tool_id,
                    )
                    old_skill_ids = [row["skill_id"] for row in old_rows]

                    # Step 2: Delete old assignments
                    await conn.execute(
                        f"DELETE FROM {self.schema}.{self.assignment_table} WHERE tool_id = $1",
                        tool_id,
                    )

                    # Step 3: Decrement old skill counts
                    for skill_id in old_skill_ids:
                        await conn.execute(
                            f"""
                            UPDATE {self.schema}.{self.skill_table}
                            SET tool_count = GREATEST(0, tool_count - 1), updated_at = $1
                            WHERE id = $2
                            """,
                            now,
                            skill_id,
                        )

                    # Step 4: Create new assignments
                    for skill_id, confidence in zip(new_skill_ids, confidences):
                        is_primary = skill_id == primary
                        await conn.execute(
                            f"""
                            INSERT INTO {self.schema}.{self.assignment_table}
                            (tool_id, skill_id, confidence, is_primary, source, created_at)
                            VALUES ($1, $2, $3, $4, $5, $6)
                            """,
                            tool_id,
                            skill_id,
                            confidence,
                            is_primary,
                            source,
                            now,
                        )

                    # Step 5: Increment new skill counts
                    for skill_id in new_skill_ids:
                        await conn.execute(
                            f"""
                            UPDATE {self.schema}.{self.skill_table}
                            SET tool_count = GREATEST(0, tool_count + 1), updated_at = $1
                            WHERE id = $2
                            """,
                            now,
                            skill_id,
                        )

            logger.debug(
                f"Atomically reassigned tool {tool_id}: {old_skill_ids} -> {new_skill_ids}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to atomically reassign tool {tool_id}: {e}")
            return False
