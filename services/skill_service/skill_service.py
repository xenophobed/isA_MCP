"""
Skill Service - Business logic for skill classification and management.

Provides:
- Skill category CRUD operations
- LLM-based tool classification
- Skill embedding generation and updates
- Manual assignment overrides
"""
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

from .skill_repository import SkillRepository
from core.clients.model_client import get_model_client
from core.config import get_settings

logger = logging.getLogger(__name__)

# Classification constants
MIN_CONFIDENCE_THRESHOLD = 0.5
MAX_ASSIGNMENTS_PER_TOOL = 3
MAX_DESCRIPTION_LENGTH = 2000  # Truncate for LLM context


class SkillService:
    """
    Service for skill classification and management.

    Orchestrates:
    - Skill category management
    - LLM-based tool classification
    - Assignment storage
    - Embedding generation
    """

    def __init__(
        self,
        repository: Optional[SkillRepository] = None,
        qdrant_client=None,
        model_client=None
    ):
        """
        Initialize the skill service.

        Args:
            repository: Optional SkillRepository instance
            qdrant_client: Optional Qdrant client for embeddings
            model_client: Optional model client for LLM/embeddings
        """
        self.repository = repository or SkillRepository()
        self._qdrant_client = qdrant_client
        self._model_client = model_client
        self._settings = get_settings()

    async def _get_model_client(self):
        """Get or create model client."""
        if self._model_client is None:
            self._model_client = await get_model_client()
        return self._model_client

    async def _get_qdrant_client(self):
        """Get or create Qdrant client."""
        if self._qdrant_client is None:
            from isa_common import AsyncQdrantClient
            settings = get_settings()
            self._qdrant_client = AsyncQdrantClient(
                host=settings.infrastructure.qdrant_grpc_host,
                port=settings.infrastructure.qdrant_grpc_port,
                user_id="mcp-skill-service"
            )
        return self._qdrant_client

    # =========================================================================
    # Skill Category Management
    # =========================================================================

    async def create_skill_category(
        self,
        skill_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new skill category.

        Args:
            skill_data: Skill data including id, name, description, etc.

        Returns:
            Created skill record

        Raises:
            ValueError: If validation fails or skill already exists
            RuntimeError: If creation fails
        """
        # Validate required fields
        if not skill_data.get('id'):
            raise ValueError("Skill ID is required")
        if not skill_data.get('name'):
            raise ValueError("Skill name is required")
        if not skill_data.get('description'):
            raise ValueError("Skill description is required")
        if len(skill_data.get('description', '')) < 10:
            raise ValueError("Skill description must be at least 10 characters")

        # Validate ID format
        skill_id = skill_data['id']
        if not skill_id[0].isalpha():
            raise ValueError("Skill ID must start with a letter")
        if not all(c.isalnum() or c == '_' for c in skill_id):
            raise ValueError("Skill ID can only contain letters, numbers, and underscores")
        if skill_id != skill_id.lower():
            raise ValueError("Skill ID must be lowercase")

        # Check for duplicates
        existing = await self.repository.get_skill_by_id(skill_id)
        if existing:
            raise ValueError(f"Skill already exists: {skill_id}")

        # Normalize keywords to lowercase
        if 'keywords' in skill_data:
            skill_data['keywords'] = [
                k.lower().strip() for k in skill_data['keywords'] if k.strip()
            ]

        # Create in database
        skill = await self.repository.create_skill_category(skill_data)
        if not skill:
            raise RuntimeError(f"Failed to create skill category: {skill_id}")

        # Generate initial embedding from description
        try:
            await self._update_skill_embedding(skill_id, skill['description'])
        except Exception as e:
            logger.warning(f"Failed to generate initial embedding for skill {skill_id}: {e}")

        logger.info(f"Created skill category: {skill_id}")
        return skill

    async def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a skill category by ID.

        Args:
            skill_id: The skill ID

        Returns:
            Skill record or None if not found
        """
        return await self.repository.get_skill_by_id(skill_id)

    async def list_skills(
        self,
        is_active: Optional[bool] = True,
        parent_domain: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List skill categories.

        Args:
            is_active: Filter by active status
            parent_domain: Filter by parent domain
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of skill records
        """
        return await self.repository.list_skills(
            is_active=is_active,
            parent_domain=parent_domain,
            limit=limit,
            offset=offset
        )

    async def update_skill_category(
        self,
        skill_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a skill category.

        Args:
            skill_id: The skill ID to update
            updates: Fields to update

        Returns:
            Updated skill record

        Raises:
            ValueError: If skill not found
            RuntimeError: If update fails
        """
        existing = await self.repository.get_skill_by_id(skill_id)
        if not existing:
            raise ValueError(f"Skill not found: {skill_id}")

        # Normalize keywords if updating
        if 'keywords' in updates:
            updates['keywords'] = [
                k.lower().strip() for k in updates['keywords'] if k.strip()
            ]

        skill = await self.repository.update_skill_category(skill_id, updates)
        if not skill:
            raise RuntimeError(f"Failed to update skill: {skill_id}")

        # Update embedding if description changed
        if 'description' in updates:
            try:
                await self._update_skill_embedding(skill_id, updates['description'])
            except Exception as e:
                logger.warning(f"Failed to update embedding for skill {skill_id}: {e}")

        logger.info(f"Updated skill category: {skill_id}")
        return skill

    async def delete_skill_category(self, skill_id: str) -> bool:
        """
        Soft delete a skill category.

        Args:
            skill_id: The skill ID to delete

        Returns:
            True if successful
        """
        success = await self.repository.delete_skill_category(skill_id)
        if success:
            logger.info(f"Deleted skill category: {skill_id}")
        return success

    # =========================================================================
    # Tool Classification
    # =========================================================================

    async def classify_tool(
        self,
        tool_id: int,
        tool_name: str,
        tool_description: str,
        input_schema_summary: Optional[str] = None,
        force_reclassify: bool = False
    ) -> Dict[str, Any]:
        """
        Classify a tool into skill categories using LLM.

        Args:
            tool_id: Tool database ID
            tool_name: Tool name
            tool_description: Tool description
            input_schema_summary: Optional input schema summary
            force_reclassify: Force reclassification even if already classified

        Returns:
            Classification result with assignments and optional suggestion

        Raises:
            RuntimeError: If classification fails
        """
        # Check if already classified (unless force)
        if not force_reclassify:
            existing = await self.repository.get_assignments_for_tool(tool_id)
            if existing:
                # Check for human override
                has_override = await self.repository.has_human_override(tool_id)
                if has_override:
                    logger.info(f"Tool {tool_id} has human override, skipping classification")
                    return {
                        'tool_id': tool_id,
                        'tool_name': tool_name,
                        'assignments': existing,
                        'primary_skill_id': next(
                            (a['skill_id'] for a in existing if a.get('is_primary')),
                            existing[0]['skill_id'] if existing else None
                        ),
                        'suggested_new_skill': None,
                        'classification_timestamp': datetime.now(timezone.utc),
                        'skipped': True,
                    }

        # Get available skills
        skills = await self.repository.list_skills(is_active=True, limit=1000)
        if not skills:
            logger.warning("No skills available for classification")

        # Truncate description if too long
        description = tool_description[:MAX_DESCRIPTION_LENGTH]

        # Call LLM for classification
        classification = await self._llm_classify(
            tool_name=tool_name,
            tool_description=description,
            input_schema_summary=input_schema_summary,
            available_skills=skills
        )

        # Filter by confidence threshold
        valid_assignments = [
            a for a in classification.get('assignments', [])
            if a.get('confidence', 0) >= MIN_CONFIDENCE_THRESHOLD
        ][:MAX_ASSIGNMENTS_PER_TOOL]

        # Validate skill IDs exist
        skill_ids = {s['id'] for s in skills}
        valid_assignments = [
            a for a in valid_assignments
            if a.get('skill_id') in skill_ids
        ]

        # Delete existing assignments if re-classifying
        if force_reclassify or valid_assignments:
            await self.repository.delete_assignments_for_tool(tool_id)

        # Store new assignments
        stored_assignments = []
        primary_skill_id = None

        for i, assignment in enumerate(valid_assignments):
            is_primary = (i == 0)  # First (highest confidence) is primary
            stored = await self.repository.create_assignment(
                tool_id=tool_id,
                skill_id=assignment['skill_id'],
                confidence=assignment['confidence'],
                is_primary=is_primary,
                source='llm_auto'
            )
            if stored:
                stored_assignments.append(stored)
                if is_primary:
                    primary_skill_id = assignment['skill_id']

                # Update skill tool count
                await self.repository.increment_tool_count(assignment['skill_id'], 1)

                # Update skill embedding
                try:
                    await self._trigger_skill_embedding_update(assignment['skill_id'])
                except Exception as e:
                    logger.warning(f"Failed to update embedding for skill {assignment['skill_id']}: {e}")

        # Handle suggestion if no valid assignments
        suggested_new_skill = None
        if not valid_assignments and classification.get('suggested_new_skill'):
            suggestion = classification['suggested_new_skill']
            await self.repository.create_suggestion(
                suggested_name=suggestion.get('name', 'Unknown'),
                suggested_description=suggestion.get('description', ''),
                source_tool_id=tool_id,
                source_tool_name=tool_name,
                reasoning=suggestion.get('reasoning', 'LLM suggested')
            )
            suggested_new_skill = suggestion
            logger.info(f"Created skill suggestion for tool {tool_name}: {suggestion.get('name')}")

        result = {
            'tool_id': tool_id,
            'tool_name': tool_name,
            'assignments': [
                {
                    'skill_id': a['skill_id'],
                    'confidence': a['confidence'],
                    'reasoning': next(
                        (x.get('reasoning') for x in classification.get('assignments', [])
                         if x.get('skill_id') == a['skill_id']),
                        None
                    )
                }
                for a in stored_assignments
            ],
            'primary_skill_id': primary_skill_id,
            'suggested_new_skill': suggested_new_skill,
            'classification_timestamp': datetime.now(timezone.utc),
        }

        # BR-002: Update Qdrant tool payload with skill_ids and primary_skill_id
        if stored_assignments:
            try:
                await self._update_tool_qdrant_payload(
                    tool_id=tool_id,
                    skill_ids=[a['skill_id'] for a in stored_assignments],
                    primary_skill_id=primary_skill_id
                )
            except Exception as e:
                logger.warning(f"Failed to update Qdrant payload for tool {tool_id}: {e}")

        logger.info(f"Classified tool {tool_name} into {len(stored_assignments)} skills")
        return result

    async def _llm_classify(
        self,
        tool_name: str,
        tool_description: str,
        input_schema_summary: Optional[str],
        available_skills: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Call LLM to classify a tool.

        Args:
            tool_name: Tool name
            tool_description: Tool description
            input_schema_summary: Optional schema summary
            available_skills: List of available skill categories

        Returns:
            Classification result from LLM
        """
        # Build skill list for prompt
        skill_list = "\n".join([
            f"- {s['id']}: {s['name']} - {s['description'][:200]}"
            for s in available_skills
        ])

        prompt = f"""You are a STRICT tool classifier. Your goal is PRECISE categorization - each tool should belong to exactly 1-2 categories (rarely 3).

## CRITICAL RULES:
- Assign to the SINGLE MOST SPECIFIC category that matches the tool's PRIMARY function
- Only add a second category if the tool CLEARLY serves two distinct purposes
- NEVER assign more than 2 categories unless absolutely necessary
- Confidence must be >= 0.7 for any assignment
- When in doubt, choose the MORE SPECIFIC category over a general one

## Available Skill Categories (grouped by domain):
{skill_list}

## Tool to Classify:
Name: {tool_name}
Description: {tool_description}
{f'Input Schema: {input_schema_summary}' if input_schema_summary else ''}

## Classification Strategy:
1. Identify the tool's PRIMARY action (what does it DO?)
2. Identify the tool's TARGET domain (what does it work WITH?)
3. Find the SINGLE best matching category
4. Only add a second category if the tool genuinely spans two domains

## Output Format (JSON only, no markdown):
{{
    "assignments": [
        {{"skill_id": "...", "confidence": 0.7-1.0, "reasoning": "..."}}
    ],
    "primary_skill_id": "...",
    "suggested_new_skill": null or {{"name": "...", "description": "...", "reasoning": "..."}}
}}
"""

        try:
            model_client = await self._get_model_client()
            response = await model_client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[
                    {"role": "system", "content": "You are a tool classifier. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )

            content = response.choices[0].message.content.strip()

            # Clean up markdown code blocks if present
            if content.startswith('```'):
                content = content.split('\n', 1)[1]
            if content.endswith('```'):
                content = content.rsplit('```', 1)[0]
            content = content.strip()

            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response for tool {tool_name}: {e}")
            return {'assignments': [], 'primary_skill_id': None, 'suggested_new_skill': None}
        except Exception as e:
            logger.error(f"LLM classification failed for tool {tool_name}: {e}")
            raise RuntimeError(f"Classification failed: {e}")

    async def classify_tools_batch(
        self,
        tools: List[Dict[str, Any]],
        batch_size: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Classify multiple tools in batched LLM calls.

        Args:
            tools: List of tool dicts with 'tool_id', 'tool_name', 'description'
            batch_size: Number of tools per LLM call (default: 20)

        Returns:
            List of classification results
        """
        if not tools:
            return []

        # Get available skills once
        skills = await self.repository.list_skills(is_active=True, limit=1000)
        if not skills:
            logger.warning("No skills available for batch classification")
            return [{'tool_id': t['tool_id'], 'assignments': [], 'primary_skill_id': None} for t in tools]

        results = []

        # Process in batches
        for i in range(0, len(tools), batch_size):
            batch = tools[i:i + batch_size]
            logger.debug(f"Classifying batch {i // batch_size + 1} ({len(batch)} tools)...")

            try:
                # Call LLM for batch
                batch_results = await self._llm_classify_batch(batch, skills)

                # Process each result
                for tool, classification in zip(batch, batch_results):
                    tool_id = tool['tool_id']
                    tool_name = tool['tool_name']

                    try:
                        # Filter and store assignments
                        result = await self._store_classification(
                            tool_id=tool_id,
                            tool_name=tool_name,
                            classification=classification,
                            skills=skills
                        )
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Failed to store classification for {tool_name}: {e}")
                        results.append({
                            'tool_id': tool_id,
                            'tool_name': tool_name,
                            'assignments': [],
                            'primary_skill_id': None,
                            'error': str(e)
                        })

            except Exception as e:
                logger.error(f"Batch classification failed: {e}")
                # Return empty results for failed batch
                for tool in batch:
                    results.append({
                        'tool_id': tool['tool_id'],
                        'tool_name': tool['tool_name'],
                        'assignments': [],
                        'primary_skill_id': None,
                        'error': str(e)
                    })

        return results

    async def _llm_classify_batch(
        self,
        tools: List[Dict[str, Any]],
        available_skills: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Call LLM to classify multiple tools in one request.

        Args:
            tools: List of tools to classify
            available_skills: Available skill categories

        Returns:
            List of classification results (same order as input)
        """
        # Build skill list
        skill_list = "\n".join([
            f"- {s['id']}: {s['name']} - {s['description'][:150]}"
            for s in available_skills
        ])

        # Build tools list
        tools_list = "\n".join([
            f"{idx + 1}. **{t['tool_name']}**: {t['description'][:200]}"
            for idx, t in enumerate(tools)
        ])

        prompt = f"""You are a STRICT tool classifier. Your goal is PRECISE categorization with MINIMAL overlap.

## CRITICAL RULES - FOLLOW EXACTLY:
1. Each tool gets EXACTLY 1 primary category (the most specific match)
2. Add a second category ONLY if the tool clearly serves two distinct purposes
3. NEVER assign more than 2 categories per tool
4. Minimum confidence threshold is 0.7 - if below, don't assign
5. Prefer SPECIFIC categories over broad ones

## Available Skill Categories:
{skill_list}

## Tools to Classify:
{tools_list}

## Classification Strategy:
- Look at the tool NAME for hints (e.g., "create_calendar_event" → calendar-events)
- Match the PRIMARY function, not secondary effects
- "search_*" tools → text-search or vector-semantic (not every other category)
- "get_*" tools → match what they GET, not the action
- External service tools (notion_, slack_, redis_) → external-services OR the specific domain

## Output Format (JSON array, no markdown):
[
    {{"tool_name": "...", "assignments": [{{"skill_id": "...", "confidence": 0.85}}], "primary_skill_id": "..."}},
    ...
]

Return exactly {len(tools)} classifications. Most tools should have only 1 assignment."""

        try:
            model_client = await self._get_model_client()
            response = await model_client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[
                    {"role": "system", "content": "You are a tool classifier. Respond only with a valid JSON array."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000  # Larger for batch response
            )

            content = response.choices[0].message.content.strip()

            # Clean up markdown code blocks if present
            if content.startswith('```'):
                content = content.split('\n', 1)[1]
            if content.endswith('```'):
                content = content.rsplit('```', 1)[0]
            content = content.strip()

            parsed = json.loads(content)

            # Ensure we have the right number of results
            if len(parsed) != len(tools):
                logger.warning(f"LLM returned {len(parsed)} results for {len(tools)} tools")
                # Pad or truncate as needed
                while len(parsed) < len(tools):
                    parsed.append({'assignments': [], 'primary_skill_id': None})

            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse batch LLM response: {e}")
            return [{'assignments': [], 'primary_skill_id': None} for _ in tools]
        except Exception as e:
            logger.error(f"Batch LLM classification failed: {e}")
            raise

    async def _store_classification(
        self,
        tool_id: int,
        tool_name: str,
        classification: Dict[str, Any],
        skills: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Store classification results in PostgreSQL and update Qdrant.

        Args:
            tool_id: Tool database ID
            tool_name: Tool name
            classification: LLM classification result
            skills: Available skills for validation

        Returns:
            Stored classification result
        """
        # Validate skill IDs
        skill_ids = {s['id'] for s in skills}
        valid_assignments = [
            a for a in classification.get('assignments', [])
            if a.get('skill_id') in skill_ids and a.get('confidence', 0) >= MIN_CONFIDENCE_THRESHOLD
        ][:MAX_ASSIGNMENTS_PER_TOOL]

        # Delete existing assignments
        if valid_assignments:
            await self.repository.delete_assignments_for_tool(tool_id)

        # Store new assignments
        stored_assignments = []
        primary_skill_id = None

        for i, assignment in enumerate(valid_assignments):
            is_primary = (i == 0)
            stored = await self.repository.create_assignment(
                tool_id=tool_id,
                skill_id=assignment['skill_id'],
                confidence=assignment.get('confidence', 0.8),
                is_primary=is_primary,
                source='llm_auto'
            )
            if stored:
                stored_assignments.append(stored)
                if is_primary:
                    primary_skill_id = assignment['skill_id']

                # Update skill tool count
                await self.repository.increment_tool_count(assignment['skill_id'], 1)

        # Update Qdrant payload
        if stored_assignments:
            try:
                await self._update_tool_qdrant_payload(
                    tool_id=tool_id,
                    skill_ids=[a['skill_id'] for a in valid_assignments],
                    primary_skill_id=primary_skill_id
                )
            except Exception as e:
                logger.warning(f"Failed to update Qdrant payload for tool {tool_id}: {e}")

        return {
            'tool_id': tool_id,
            'tool_name': tool_name,
            'assignments': stored_assignments,
            'primary_skill_id': primary_skill_id,
        }

    # =========================================================================
    # Generic Entity Classification (for resources, prompts, etc.)
    # =========================================================================

    async def classify_entities_batch(
        self,
        entities: List[Dict[str, Any]],
        entity_type: str = "resource",
        batch_size: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Classify multiple entities (resources, prompts, etc.) into skill categories.

        This is a generic version of classify_tools_batch that works for any entity type.
        It uses the same LLM classification but stores results differently based on entity_type.

        Args:
            entities: List of entity dicts with 'id', 'name', 'description'
            entity_type: Type of entity ('resource', 'prompt')
            batch_size: Number of entities per LLM call (default: 20)

        Returns:
            List of classification results with skill_ids and primary_skill_id
        """
        if not entities:
            return []

        # Get available skills once
        skills = await self.repository.list_skills(is_active=True, limit=1000)
        if not skills:
            logger.warning("No skills available for entity classification")
            return [{'id': e['id'], 'skill_ids': [], 'primary_skill_id': None} for e in entities]

        results = []

        # Process in batches
        for i in range(0, len(entities), batch_size):
            batch = entities[i:i + batch_size]
            logger.debug(f"Classifying batch {i // batch_size + 1} ({len(batch)} {entity_type}s)...")

            try:
                # Call LLM for batch
                batch_results = await self._llm_classify_entities_batch(batch, skills, entity_type)

                # Process each result
                for entity, classification in zip(batch, batch_results):
                    entity_id = entity['id']
                    entity_name = entity['name']

                    # Validate and extract skill assignments
                    skill_id_set = {s['id'] for s in skills}
                    valid_assignments = [
                        a for a in classification.get('assignments', [])
                        if a.get('skill_id') in skill_id_set and a.get('confidence', 0) >= MIN_CONFIDENCE_THRESHOLD
                    ][:MAX_ASSIGNMENTS_PER_TOOL]

                    skill_ids = [a['skill_id'] for a in valid_assignments]
                    primary_skill_id = classification.get('primary_skill_id')
                    if primary_skill_id not in skill_ids and skill_ids:
                        primary_skill_id = skill_ids[0]

                    # Store classification based on entity type
                    try:
                        await self._store_entity_classification(
                            entity_id=entity_id,
                            entity_type=entity_type,
                            skill_ids=skill_ids,
                            primary_skill_id=primary_skill_id
                        )
                        results.append({
                            'id': entity_id,
                            'name': entity_name,
                            'skill_ids': skill_ids,
                            'primary_skill_id': primary_skill_id,
                        })
                    except Exception as e:
                        logger.error(f"Failed to store classification for {entity_type} {entity_name}: {e}")
                        results.append({
                            'id': entity_id,
                            'name': entity_name,
                            'skill_ids': [],
                            'primary_skill_id': None,
                            'error': str(e)
                        })

            except Exception as e:
                logger.error(f"Batch entity classification failed: {e}")
                for entity in batch:
                    results.append({
                        'id': entity['id'],
                        'name': entity['name'],
                        'skill_ids': [],
                        'primary_skill_id': None,
                        'error': str(e)
                    })

        return results

    async def _llm_classify_entities_batch(
        self,
        entities: List[Dict[str, Any]],
        available_skills: List[Dict[str, Any]],
        entity_type: str
    ) -> List[Dict[str, Any]]:
        """
        Call LLM to classify multiple entities in one request.

        Args:
            entities: List of entities to classify
            available_skills: Available skill categories
            entity_type: Type of entity for prompt context

        Returns:
            List of classification results (same order as input)
        """
        # Build skill list
        skill_list = "\n".join([
            f"- {s['id']}: {s['name']} - {s['description'][:150]}"
            for s in available_skills
        ])

        # Build entities list
        entity_type_label = entity_type.title()
        entities_list = "\n".join([
            f"{idx + 1}. **{e['name']}**: {e.get('description', '')[:200]}"
            for idx, e in enumerate(entities)
        ])

        prompt = f"""You are a STRICT {entity_type} classifier. Each {entity_type} gets exactly 1-2 categories (rarely more).

## CRITICAL RULES:
1. Assign the SINGLE MOST SPECIFIC category that matches the {entity_type}'s primary purpose
2. Add a second category ONLY if it clearly serves two distinct functions
3. NEVER assign more than 2 categories unless absolutely essential
4. Minimum confidence is 0.7 - lower means don't assign

## Available Skill Categories:
{skill_list}

## {entity_type_label}s to Classify:
{entities_list}

## Classification Strategy:
- Match the PRIMARY purpose, not secondary uses
- Prefer specific categories over general ones
- Most {entity_type}s should have exactly 1 category

## Output Format (JSON array, no markdown):
[
    {{"name": "...", "assignments": [{{"skill_id": "...", "confidence": 0.85}}], "primary_skill_id": "..."}},
    ...
]

Return exactly {len(entities)} classifications. Most should have only 1 assignment."""

        try:
            model_client = await self._get_model_client()
            response = await model_client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[
                    {"role": "system", "content": f"You are a {entity_type} classifier. Respond only with a valid JSON array."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )

            content = response.choices[0].message.content.strip()

            # Clean up markdown code blocks if present
            if content.startswith('```'):
                content = content.split('\n', 1)[1]
            if content.endswith('```'):
                content = content.rsplit('```', 1)[0]
            content = content.strip()

            parsed = json.loads(content)

            # Ensure we have the right number of results
            if len(parsed) != len(entities):
                logger.warning(f"LLM returned {len(parsed)} results for {len(entities)} {entity_type}s")
                while len(parsed) < len(entities):
                    parsed.append({'assignments': [], 'primary_skill_id': None})

            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse batch LLM response: {e}")
            return [{'assignments': [], 'primary_skill_id': None} for _ in entities]
        except Exception as e:
            logger.error(f"Batch LLM entity classification failed: {e}")
            raise

    async def _store_entity_classification(
        self,
        entity_id: int,
        entity_type: str,
        skill_ids: List[str],
        primary_skill_id: Optional[str]
    ) -> None:
        """
        Store classification results for an entity.

        Args:
            entity_id: Entity database ID
            entity_type: Type of entity ('resource', 'prompt')
            skill_ids: List of skill IDs
            primary_skill_id: Primary skill ID
        """
        if entity_type == "resource":
            from services.resource_service.resource_repository import ResourceRepository
            repo = ResourceRepository()
            await repo.update_resource_skills(entity_id, skill_ids, primary_skill_id)
        elif entity_type == "prompt":
            from services.prompt_service.prompt_repository import PromptRepository
            repo = PromptRepository()
            await repo.update_prompt_skills(entity_id, skill_ids, primary_skill_id)
        else:
            logger.warning(f"Unknown entity type for classification: {entity_type}")

        # Update Qdrant payload
        try:
            await self._update_entity_qdrant_payload(
                entity_id=entity_id,
                entity_type=entity_type,
                skill_ids=skill_ids,
                primary_skill_id=primary_skill_id
            )
        except Exception as e:
            logger.warning(f"Failed to update Qdrant payload for {entity_type} {entity_id}: {e}")

    async def _update_entity_qdrant_payload(
        self,
        entity_id: int,
        entity_type: str,
        skill_ids: List[str],
        primary_skill_id: Optional[str]
    ) -> None:
        """Update Qdrant payload with skill classification for any entity type."""
        from services.vector_service.vector_repository import VectorRepository

        vector_repo = VectorRepository()
        offset = vector_repo.TYPE_OFFSETS.get(entity_type, 2_000_000)  # Default to resource offset
        qdrant_id = offset + entity_id

        try:
            qdrant_client = await self._get_qdrant_client()
            await qdrant_client.set_payload(
                collection_name="mcp_unified_search",
                points=[qdrant_id],
                payload={
                    "skill_ids": skill_ids,
                    "primary_skill_id": primary_skill_id,
                }
            )
            logger.debug(f"Updated Qdrant payload for {entity_type} {entity_id}")
        except Exception as e:
            logger.warning(f"Failed to update Qdrant payload: {e}")
            raise

    # =========================================================================
    # Manual Assignment
    # =========================================================================

    async def assign_tool_to_skills(
        self,
        tool_id: int,
        skill_ids: List[str],
        primary_skill_id: str,
        source: str = 'human_manual'
    ) -> List[Dict[str, Any]]:
        """
        Manually assign a tool to skills.

        Args:
            tool_id: Tool database ID
            skill_ids: List of skill IDs to assign
            primary_skill_id: Primary skill ID (must be in skill_ids)
            source: Assignment source (human_manual or human_override)

        Returns:
            List of created assignments

        Raises:
            ValueError: If validation fails
        """
        if not skill_ids:
            raise ValueError("At least one skill ID is required")
        if primary_skill_id not in skill_ids:
            raise ValueError("Primary skill must be in skill_ids list")

        # Validate all skill IDs exist
        for skill_id in skill_ids:
            skill = await self.repository.get_skill_by_id(skill_id)
            if not skill:
                raise ValueError(f"Skill not found: {skill_id}")

        # Delete existing assignments
        await self.repository.delete_assignments_for_tool(tool_id)

        # Create new assignments
        assignments = []
        for skill_id in skill_ids:
            is_primary = (skill_id == primary_skill_id)
            assignment = await self.repository.create_assignment(
                tool_id=tool_id,
                skill_id=skill_id,
                confidence=1.0,  # Human assignments have full confidence
                is_primary=is_primary,
                source=source
            )
            if assignment:
                assignments.append(assignment)
                await self.repository.increment_tool_count(skill_id, 1)

        logger.info(f"Manually assigned tool {tool_id} to {len(assignments)} skills")
        return assignments

    # =========================================================================
    # Get Tools by Skill
    # =========================================================================

    async def get_tools_by_skill(
        self,
        skill_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all tools assigned to a skill.

        Args:
            skill_id: The skill ID
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of tool assignments

        Raises:
            ValueError: If skill not found
        """
        skill = await self.repository.get_skill_by_id(skill_id)
        if not skill:
            raise ValueError(f"Skill not found: {skill_id}")

        return await self.repository.get_assignments_for_skill(
            skill_id=skill_id,
            limit=limit,
            offset=offset
        )

    # =========================================================================
    # Skill Embedding Management
    # =========================================================================

    async def _update_skill_embedding(
        self,
        skill_id: str,
        description: str
    ) -> None:
        """
        Update skill embedding from description.

        Args:
            skill_id: The skill ID
            description: Skill description for embedding
        """
        try:
            model_client = await self._get_model_client()
            qdrant_client = await self._get_qdrant_client()

            # Generate embedding
            response = await model_client.embeddings.create(
                input=description,
                model="text-embedding-3-small"
            )
            embedding = response.data[0].embedding

            # Get skill metadata
            skill = await self.repository.get_skill_by_id(skill_id)
            if not skill:
                return

            # Convert string skill_id to deterministic UUID for Qdrant
            # Qdrant requires point IDs to be unsigned integer or UUID
            skill_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"mcp.skill.{skill_id}"))

            # Upsert to Qdrant
            await qdrant_client.upsert_points(
                collection_name="mcp_skills",
                points=[{
                    'id': skill_uuid,
                    'vector': embedding,
                    'payload': {
                        'id': skill_id,  # Keep original string ID in payload for reference
                        'name': skill['name'],
                        'description': skill['description'],
                        'tool_count': skill.get('tool_count', 0),
                        'is_active': skill.get('is_active', True),
                    }
                }]
            )

            logger.debug(f"Updated embedding for skill {skill_id}")

        except Exception as e:
            logger.error(f"Failed to update skill embedding for {skill_id}: {e}")
            raise

    async def _update_tool_qdrant_payload(
        self,
        tool_id: int,
        skill_ids: List[str],
        primary_skill_id: Optional[str]
    ) -> None:
        """
        Update Qdrant tool payload with skill_ids and primary_skill_id.

        BR-002: Tool updated in Qdrant with `skill_ids[]` payload

        Args:
            tool_id: Tool database ID
            skill_ids: List of assigned skill IDs
            primary_skill_id: Primary skill ID
        """
        try:
            from services.vector_service.vector_repository import VectorRepository
            vector_repo = VectorRepository()

            success = await vector_repo.update_payload(
                item_id=tool_id,
                payload_updates={
                    'skill_ids': skill_ids,
                    'primary_skill_id': primary_skill_id,
                }
            )

            if success:
                logger.debug(f"Updated Qdrant payload for tool {tool_id}: skill_ids={skill_ids}")
            else:
                logger.warning(f"Failed to update Qdrant payload for tool {tool_id}")

        except Exception as e:
            logger.error(f"Failed to update Qdrant payload for tool {tool_id}: {e}")
            raise

    async def _trigger_skill_embedding_update(self, skill_id: str) -> None:
        """
        Trigger an embedding update for a skill based on its assigned tools.

        This computes a weighted average of tool embeddings.

        Args:
            skill_id: The skill ID to update
        """
        try:
            # Get skill info
            skill = await self.repository.get_skill_by_id(skill_id)
            if not skill:
                return

            # Get tool assignments
            assignments = await self.repository.get_assignments_for_skill(skill_id, limit=1000)

            if not assignments:
                # No tools - use description embedding
                await self._update_skill_embedding(skill_id, skill['description'])
                return

            # For now, just update with description
            # TODO: Implement weighted average of tool embeddings
            await self._update_skill_embedding(skill_id, skill['description'])

        except Exception as e:
            logger.error(f"Failed to trigger embedding update for skill {skill_id}: {e}")

    # =========================================================================
    # Skill Suggestions
    # =========================================================================

    async def list_suggestions(
        self,
        status: str = 'pending',
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List skill suggestions.

        Args:
            status: Filter by status
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of suggestions
        """
        return await self.repository.list_suggestions(status, limit, offset)

    async def approve_suggestion(
        self,
        suggestion_id: int
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """
        Approve a skill suggestion and create the skill.

        Args:
            suggestion_id: The suggestion ID

        Returns:
            Tuple of (created skill, assignment if source tool exists)

        Raises:
            ValueError: If suggestion not found
        """
        # Get suggestion
        suggestions = await self.repository.list_suggestions(status='pending', limit=1000)
        suggestion = next((s for s in suggestions if s['id'] == suggestion_id), None)

        if not suggestion:
            raise ValueError(f"Suggestion not found: {suggestion_id}")

        # Create the skill
        skill_id = suggestion['suggested_name'].lower().replace(' ', '_')
        skill = await self.create_skill_category({
            'id': skill_id,
            'name': suggestion['suggested_name'],
            'description': suggestion['suggested_description'],
            'keywords': [],
            'examples': [suggestion['source_tool_name']],
        })

        # Update suggestion status
        await self.repository.update_suggestion_status(suggestion_id, 'approved')

        # Assign the source tool
        assignment = None
        if suggestion.get('source_tool_id'):
            assignments = await self.assign_tool_to_skills(
                tool_id=suggestion['source_tool_id'],
                skill_ids=[skill_id],
                primary_skill_id=skill_id,
                source='human_manual'
            )
            assignment = assignments[0] if assignments else None

        logger.info(f"Approved suggestion {suggestion_id}, created skill {skill_id}")
        return skill, assignment

    async def reject_suggestion(self, suggestion_id: int) -> bool:
        """
        Reject a skill suggestion.

        Args:
            suggestion_id: The suggestion ID

        Returns:
            True if successful
        """
        success = await self.repository.update_suggestion_status(suggestion_id, 'rejected')
        if success:
            logger.info(f"Rejected suggestion {suggestion_id}")
        return success
