#!/usr/bin/env python3
"""
Memory Tools for MCP Server
Comprehensive MCP tool wrappers around the enhanced memory service
Supports intelligent processing and advanced search capabilities
"""

import json
from typing import Optional
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger
from tools.base_tool import BaseTool

from tools.services.memory_service.memory_service import memory_service
from tools.services.memory_service.models import MemoryType, MemorySearchQuery

logger = get_logger(__name__)

# Global tools instance
tools = BaseTool()


def register_memory_tools(mcp: FastMCP):
    """Register all memory tools with the MCP server"""

    security_manager = get_security_manager()

    # ========== INTELLIGENT PROCESSING TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def store_factual_memory_from_dialog(
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> str:
        """Store factual memory from natural dialog using intelligent processing

        Process natural human-AI dialog to extract and store factual information
        automatically. Uses advanced text analysis to identify facts in subject-predicate-object format.

        Args:
            user_id: User identifier
            dialog_content: Natural dialog content between human and AI
            importance_score: Importance level (0.0-1.0, default 0.5)

        Keywords: memory, fact, dialog, intelligent, extraction, natural, conversation
        Category: memory
        """
        try:
            tools.reset_billing()

            result = await memory_service.store_factual_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                importance_score=importance_score
            )

            logger.info(f"Factual memory from dialog stored for user {user_id}: {result.success}")

            return tools.create_response(
                status="success" if result.success else "error",
                action="store_factual_memory_from_dialog",
                data={
                    "memory_id": result.memory_id,
                    "operation": result.operation,
                    "message": result.message,
                    "total_facts": result.data.get("total_facts", 0) if result.data else 0,
                    "stored_facts": result.data.get("stored_facts", []) if result.data else []
                }
            )

        except Exception as e:
            logger.error(f"Error storing factual memory from dialog: {e}")
            return tools.create_response(
                status="error",
                action="store_factual_memory_from_dialog",
                data={"user_id": user_id},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def store_episodic_memory_from_dialog(
        user_id: str,
        dialog_content: str,
        episode_date: Optional[str] = None,
        importance_score: float = 0.5
    ) -> str:
        """Store episodic memory from natural dialog using intelligent processing

        Process natural human-AI dialog to extract and store episodic experiences
        automatically. Uses advanced text analysis to identify events, experiences, and contextual information.

        Args:
            user_id: User identifier
            dialog_content: Natural dialog content between human and AI
            episode_date: ISO date string for when the episode occurred (optional)
            importance_score: Importance level (0.0-1.0, default 0.5)

        Keywords: memory, episode, dialog, intelligent, extraction, experience, event, story
        Category: memory
        """
        try:
            tools.reset_billing()

            # Parse episode date if provided
            parsed_date = None
            if episode_date:
                parsed_date = datetime.fromisoformat(episode_date.replace('Z', '+00:00'))

            result = await memory_service.store_episodic_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                episode_date=parsed_date,
                importance_score=importance_score
            )

            logger.info(f"Episodic memory from dialog stored for user {user_id}: {result.success}")

            return tools.create_response(
                status="success" if result.success else "error",
                action="store_episodic_memory_from_dialog",
                data={
                    "memory_id": result.memory_id,
                    "operation": result.operation,
                    "message": result.message,
                    "total_episodes": result.data.get("total_episodes", 0) if result.data else 0
                }
            )

        except Exception as e:
            logger.error(f"Error storing episodic memory from dialog: {e}")
            return tools.create_response(
                status="error",
                action="store_episodic_memory_from_dialog",
                data={"user_id": user_id},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def store_semantic_memory_from_dialog(
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> str:
        """Store semantic memory from natural dialog using intelligent processing

        Process natural human-AI dialog to extract and store semantic concepts
        automatically. Uses advanced text analysis to identify concepts, definitions, and relationships.

        Args:
            user_id: User identifier
            dialog_content: Natural dialog content between human and AI
            importance_score: Importance level (0.0-1.0, default 0.5)

        Keywords: memory, semantic, dialog, intelligent, extraction, concept, definition, knowledge
        Category: memory
        """
        try:
            tools.reset_billing()

            result = await memory_service.store_semantic_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                importance_score=importance_score
            )

            logger.info(f"Semantic memory from dialog stored for user {user_id}: {result.success}")

            return tools.create_response(
                status="success" if result.success else "error",
                action="store_semantic_memory_from_dialog",
                data={
                    "memory_id": result.memory_id,
                    "operation": result.operation,
                    "message": result.message,
                    "total_concepts": result.data.get("total_concepts", 0) if result.data else 0
                }
            )

        except Exception as e:
            logger.error(f"Error storing semantic memory from dialog: {e}")
            return tools.create_response(
                status="error",
                action="store_semantic_memory_from_dialog",
                data={"user_id": user_id},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def store_procedural_memory_from_dialog(
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> str:
        """Store procedural memory from natural dialog using intelligent processing

        Process natural human-AI dialog to extract and store procedural knowledge
        automatically. Uses advanced text analysis to identify steps, processes, and how-to information.

        Args:
            user_id: User identifier
            dialog_content: Natural dialog content between human and AI
            importance_score: Importance level (0.0-1.0, default 0.5)

        Keywords: memory, procedure, dialog, intelligent, extraction, process, steps, how-to
        Category: memory
        """
        try:
            tools.reset_billing()

            result = await memory_service.store_procedural_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                importance_score=importance_score
            )

            logger.info(f"Procedural memory from dialog stored for user {user_id}: {result.success}")

            return tools.create_response(
                status="success" if result.success else "error",
                action="store_procedural_memory_from_dialog",
                data={
                    "memory_id": result.memory_id,
                    "operation": result.operation,
                    "message": result.message,
                    "total_procedures": result.data.get("total_procedures", 0) if result.data else 0
                }
            )

        except Exception as e:
            logger.error(f"Error storing procedural memory from dialog: {e}")
            return tools.create_response(
                status="error",
                action="store_procedural_memory_from_dialog",
                data={"user_id": user_id},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def store_working_memory_from_dialog(
        user_id: str,
        dialog_content: str,
        current_task_context: Optional[str] = None,
        ttl_hours: int = 24,
        importance_score: float = 0.5
    ) -> str:
        """Store working memory from natural dialog using intelligent processing

        Process natural human-AI dialog to extract and store working memory
        automatically. Uses advanced text analysis to identify tasks, contexts, and temporary information.

        Args:
            user_id: User identifier
            dialog_content: Natural dialog content between human and AI
            current_task_context: JSON object with current task context (optional)
            ttl_hours: Time to live in hours (default 24)
            importance_score: Importance level (0.0-1.0, default 0.5)

        Keywords: memory, working, dialog, intelligent, extraction, task, temporary, context
        Category: memory
        """
        try:
            tools.reset_billing()

            # Parse task context if provided
            context_dict = None
            if current_task_context:
                context_dict = json.loads(current_task_context)

            result = await memory_service.store_working_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                current_task_context=context_dict,
                ttl_seconds=ttl_hours * 3600,
                importance_score=importance_score
            )

            logger.info(f"Working memory from dialog stored for user {user_id}: {result.success}")

            return tools.create_response(
                status="success" if result.success else "error",
                action="store_working_memory_from_dialog",
                data={
                    "memory_id": result.memory_id,
                    "operation": result.operation,
                    "message": result.message,
                    "ttl_hours": ttl_hours
                }
            )

        except Exception as e:
            logger.error(f"Error storing working memory from dialog: {e}")
            return tools.create_response(
                status="error",
                action="store_working_memory_from_dialog",
                data={"user_id": user_id},
                error_message=str(e)
            )

    # ========== DIRECT STORAGE TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def store_fact(
        user_id: str,
        fact_type: str,
        subject: str,
        predicate: str,
        object_value: str,
        context: Optional[str] = None,
        confidence: float = 0.8
    ) -> str:
        """Store factual memory with automatic merging

        Store structured factual information in subject-predicate-object format.
        Automatically merges with existing facts to avoid duplicates.

        Args:
            user_id: User identifier
            fact_type: Type of fact (personal_info, preference, skill, knowledge, relationship)
            subject: What the fact is about
            predicate: Relationship or attribute
            object_value: Value or related entity
            context: Additional context (optional)
            confidence: Confidence level (0.0-1.0, default 0.8)

        Keywords: memory, fact, store, knowledge, information, remember
        Category: memory
        """
        try:
            tools.reset_billing()

            # Convert structured input to dialog format for intelligent processing
            dialog_content = f"Fact: {subject} {predicate} {object_value}"
            if context:
                dialog_content += f" (Context: {context})"
            dialog_content += f" This is a {fact_type} type fact."
            
            # Calculate importance from confidence
            importance_score = min(confidence, 1.0)
            
            result = await memory_service.store_factual_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                importance_score=importance_score
            )

            logger.info(f"Factual memory stored for user {user_id}: {result.success}")

            return tools.create_response(
                status="success" if result.success else "error",
                action="store_fact",
                data={
                    "memory_id": result.memory_id,
                    "operation": result.operation,
                    "message": result.message,
                    "fact": f"{subject} {predicate} {object_value}",
                    "total_facts": result.data.get("total_facts", 1) if result.data else 1
                }
            )

        except Exception as e:
            logger.error(f"Error storing factual memory: {e}")
            return tools.create_response(
                status="error",
                action="store_fact",
                data={"user_id": user_id, "fact_type": fact_type},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def store_episode(
        user_id: str,
        event_type: str,
        content: str,
        location: Optional[str] = None,
        participants: Optional[str] = None,
        emotional_valence: float = 0.0
    ) -> str:
        """Store episodic memory for personal experiences

        Store specific events and experiences with contextual information.

        Args:
            user_id: User identifier
            event_type: Type of event (meeting, learning, project, etc.)
            content: Description of the event/experience
            location: Where the event occurred
            participants: JSON array of people involved
            emotional_valence: Emotional tone (-1.0 negative to 1.0 positive)

        Keywords: memory, episode, event, experience, story, context, personal
        Category: memory
        """
        try:
            tools.reset_billing()

            # Convert structured input to dialog format for intelligent processing
            dialog_content = f"Event: {content}"
            if location:
                dialog_content += f" Location: {location}."
            if participants:
                try:
                    participants_list = json.loads(participants)
                    dialog_content += f" Participants: {', '.join(participants_list)}."
                except json.JSONDecodeError:
                    dialog_content += f" Participants: {participants}."
            dialog_content += f" This was a {event_type} event."
            if emotional_valence != 0.0:
                emotion = "positive" if emotional_valence > 0 else "negative"
                dialog_content += f" The emotional tone was {emotion}."
            
            # Calculate importance from emotional intensity
            importance_score = min(0.5 + abs(emotional_valence) * 0.3, 1.0)
            
            result = await memory_service.store_episodic_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                importance_score=importance_score,
                participants=participants_list,
                emotional_valence=emotional_valence
            )

            logger.info(f"Episodic memory stored for user {user_id}: {result.success}")

            return tools.create_response(
                status="success" if result.success else "error",
                action="store_episode",
                data={
                    "memory_id": result.memory_id,
                    "operation": result.operation,
                    "message": result.message,
                    "event_type": event_type,
                    "total_episodes": result.data.get("total_episodes", 1) if result.data else 1
                }
            )

        except Exception as e:
            logger.error(f"Error storing episodic memory: {e}")
            return tools.create_response(
                status="error",
                action="store_episode",
                data={"user_id": user_id, "event_type": event_type},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def store_concept(
        user_id: str,
        concept_type: str,
        definition: str,
        category: str,
        properties: Optional[str] = None,
        related_concepts: Optional[str] = None
    ) -> str:
        """Store semantic memory for concepts and knowledge

        Store conceptual knowledge, definitions, and relationships.

        Args:
            user_id: User identifier
            concept_type: Type/name of the concept
            definition: Clear definition of the concept
            category: Category or domain of the concept
            properties: JSON object with concept properties
            related_concepts: JSON array of related concept names

        Keywords: memory, concept, definition, knowledge, semantic, relationship
        Category: memory
        """
        try:
            tools.reset_billing()

            # Convert structured input to dialog format for intelligent processing
            dialog_content = f"Concept: {concept_type}. Definition: {definition}. Category: {category}."
            
            if properties:
                try:
                    properties_dict = json.loads(properties)
                    dialog_content += f" Properties: {', '.join([f'{k}: {v}' for k, v in properties_dict.items()])}."
                except json.JSONDecodeError:
                    dialog_content += f" Properties: {properties}."
            
            if related_concepts:
                try:
                    related_list = json.loads(related_concepts)
                    dialog_content += f" Related concepts: {', '.join(related_list)}."
                except json.JSONDecodeError:
                    dialog_content += f" Related concepts: {related_concepts}."
            
            result = await memory_service.store_semantic_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                importance_score=0.7  # Concepts are generally important
            )

            logger.info(f"Semantic memory stored for user {user_id}: {result.success}")

            return tools.create_response(
                status="success" if result.success else "error",
                action="store_concept",
                data={
                    "memory_id": result.memory_id,
                    "operation": result.operation,
                    "message": result.message,
                    "concept": concept_type,
                    "category": category,
                    "total_concepts": result.data.get("total_concepts", 1) if result.data else 1
                }
            )

        except Exception as e:
            logger.error(f"Error storing semantic memory: {e}")
            return tools.create_response(
                status="error",
                action="store_concept",
                data={"user_id": user_id, "concept_type": concept_type},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def store_procedure(
        user_id: str,
        skill_type: str,
        steps: str,
        domain: str,
        difficulty_level: str = "medium",
        prerequisites: Optional[str] = None
    ) -> str:
        """Store procedural memory for step-by-step processes

        Store how-to knowledge and procedures with detailed steps.

        Args:
            user_id: User identifier
            skill_type: Name/type of the skill or procedure
            steps: JSON array of step objects with descriptions
            domain: Domain or category (e.g., 'programming', 'cooking')
            difficulty_level: Difficulty level (beginner, medium, advanced)
            prerequisites: JSON array of prerequisite skills/knowledge

        Keywords: memory, procedure, workflow, steps, process, method, how-to
        Category: memory
        """
        try:
            tools.reset_billing()

            # Convert structured input to dialog format for intelligent processing
            dialog_content = f"Procedure: {skill_type} in {domain} domain. Difficulty: {difficulty_level}."
            
            try:
                steps_list = json.loads(steps)
                dialog_content += f" Steps: "
                for i, step in enumerate(steps_list, 1):
                    if isinstance(step, dict):
                        step_desc = step.get('description', step.get('action', str(step)))
                    else:
                        step_desc = str(step)
                    dialog_content += f"{i}. {step_desc}. "
            except json.JSONDecodeError:
                dialog_content += f" Steps: {steps}."
            
            if prerequisites:
                try:
                    prerequisites_list = json.loads(prerequisites)
                    dialog_content += f" Prerequisites: {', '.join(prerequisites_list)}."
                except json.JSONDecodeError:
                    dialog_content += f" Prerequisites: {prerequisites}."
            
            # Calculate importance based on difficulty
            difficulty_scores = {"beginner": 0.4, "medium": 0.6, "advanced": 0.8}
            importance_score = difficulty_scores.get(difficulty_level.lower(), 0.6)
            
            result = await memory_service.store_procedural_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                importance_score=importance_score
            )

            logger.info(f"Procedural memory stored for user {user_id}: {result.success}")

            return tools.create_response(
                status="success" if result.success else "error",
                action="store_procedure",
                data={
                    "memory_id": result.memory_id,
                    "operation": result.operation,
                    "message": result.message,
                    "procedure": skill_type,
                    "total_procedures": result.data.get("total_procedures", 1) if result.data else 1
                }
            )

        except Exception as e:
            logger.error(f"Error storing procedural memory: {e}")
            return tools.create_response(
                status="error",
                action="store_procedure",
                data={"user_id": user_id, "skill_type": skill_type},
                error_message=str(e)
            )

    # ========== SEARCH TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def search_memories(
        user_id: str,
        query: str,
        memory_types: Optional[str] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7,
        importance_min: Optional[float] = None,
        confidence_min: Optional[float] = None
    ) -> str:
        """Search memories using semantic similarity

        Search across all memory types using natural language queries.
        Uses vector embeddings for intelligent semantic matching.

        Args:
            user_id: User identifier
            query: Natural language search query
            memory_types: JSON array of memory types to search (optional)
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0.0-1.0)
            importance_min: Minimum importance score filter (optional)
            confidence_min: Minimum confidence score filter (optional)

        Keywords: memory, search, find, query, semantic, similarity, retrieve
        Category: memory
        """
        try:
            tools.reset_billing()

            # Parse memory types if provided
            types_list = None
            if memory_types:
                type_names = json.loads(memory_types)
                types_list = [MemoryType(name) for name in type_names]

            search_query = MemorySearchQuery(
                query=query,
                user_id=user_id,
                memory_types=types_list,
                top_k=limit,
                similarity_threshold=similarity_threshold,
                importance_min=importance_min,
                confidence_min=confidence_min
            )

            results = await memory_service.search_memories(search_query)

            # Format results for response
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "memory_id": result.memory.id,
                    "memory_type": result.memory.memory_type.value,
                    "content": result.memory.content,
                    "similarity_score": result.similarity_score,
                    "rank": result.rank,
                    "importance": result.memory.importance_score,
                    "confidence": result.memory.confidence
                })

            logger.info(f"Memory search completed for user {user_id}: {len(results)} results")

            return tools.create_response(
                status="success",
                action="search_memories",
                data={
                    "query": query,
                    "results": formatted_results,
                    "count": len(results),
                    "threshold": similarity_threshold
                }
            )

        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return tools.create_response(
                status="error",
                action="search_memories",
                data={"user_id": user_id, "query": query},
                error_message=str(e)
            )

    # ========== SPECIALIZED SEARCH TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def search_facts_by_type(
        user_id: str,
        fact_type: str,
        limit: int = 10
    ) -> str:
        """Search facts by type

        Find factual memories of a specific type (personal_info, preference, skill, knowledge, relationship).

        Args:
            user_id: User identifier
            fact_type: Type of fact to search for
            limit: Maximum number of results to return

        Keywords: memory, fact, search, type, category, filter
        Category: memory
        """
        try:
            tools.reset_billing()

            results = await memory_service.search_facts_by_fact_type(user_id, fact_type, limit)

            # Format results
            formatted_results = []
            for fact in results:
                formatted_results.append({
                    "memory_id": fact.id,
                    "subject": fact.subject,
                    "predicate": fact.predicate,
                    "object_value": fact.object_value,
                    "confidence": fact.confidence,
                    "importance": fact.importance_score,
                    "created_at": fact.created_at.isoformat()
                })

            logger.info(f"Facts search by type completed for user {user_id}: {len(results)} results")

            return tools.create_response(
                status="success",
                action="search_facts_by_type",
                data={
                    "fact_type": fact_type,
                    "results": formatted_results,
                    "count": len(results)
                }
            )

        except Exception as e:
            logger.error(f"Error searching facts by type: {e}")
            return tools.create_response(
                status="error",
                action="search_facts_by_type",
                data={"user_id": user_id, "fact_type": fact_type},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def search_episodes_by_participant(
        user_id: str,
        participant: str,
        limit: int = 10
    ) -> str:
        """Search episodes by participant

        Find episodic memories involving a specific person.

        Args:
            user_id: User identifier
            participant: Name of the participant to search for
            limit: Maximum number of results to return

        Keywords: memory, episode, search, participant, person, people
        Category: memory
        """
        try:
            tools.reset_billing()

            results = await memory_service.search_episodes_by_participant(user_id, participant, limit)

            # Format results
            formatted_results = []
            for episode in results:
                formatted_results.append({
                    "memory_id": episode.id,
                    "event_type": episode.event_type,
                    "content": episode.content,
                    "participants": episode.participants,
                    "location": episode.location,
                    "emotional_valence": episode.emotional_valence,
                    "importance": episode.importance_score,
                    "created_at": episode.created_at.isoformat()
                })

            logger.info(f"Episodes search by participant completed for user {user_id}: {len(results)} results")

            return tools.create_response(
                status="success",
                action="search_episodes_by_participant",
                data={
                    "participant": participant,
                    "results": formatted_results,
                    "count": len(results)
                }
            )

        except Exception as e:
            logger.error(f"Error searching episodes by participant: {e}")
            return tools.create_response(
                status="error",
                action="search_episodes_by_participant",
                data={"user_id": user_id, "participant": participant},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def search_concepts_by_category(
        user_id: str,
        category: str,
        limit: int = 10
    ) -> str:
        """Search concepts by category

        Find semantic memories (concepts) in a specific category or domain.

        Args:
            user_id: User identifier
            category: Category or domain to search in
            limit: Maximum number of results to return

        Keywords: memory, concept, search, category, domain, semantic
        Category: memory
        """
        try:
            tools.reset_billing()

            results = await memory_service.search_concepts_by_category(user_id, category, limit)

            # Format results
            formatted_results = []
            for concept in results:
                formatted_results.append({
                    "memory_id": concept.id,
                    "concept_type": concept.concept_type,
                    "definition": concept.definition,
                    "category": concept.category,
                    "properties": concept.properties,
                    "related_concepts": concept.related_concepts,
                    "importance": concept.importance_score,
                    "created_at": concept.created_at.isoformat()
                })

            logger.info(f"Concepts search by category completed for user {user_id}: {len(results)} results")

            return tools.create_response(
                status="success",
                action="search_concepts_by_category",
                data={
                    "category": category,
                    "results": formatted_results,
                    "count": len(results)
                }
            )

        except Exception as e:
            logger.error(f"Error searching concepts by category: {e}")
            return tools.create_response(
                status="error",
                action="search_concepts_by_category",
                data={"user_id": user_id, "category": category},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def search_procedures_by_domain(
        user_id: str,
        domain: str,
        limit: int = 10
    ) -> str:
        """Search procedures by domain

        Find procedural memories in a specific domain or category.

        Args:
            user_id: User identifier
            domain: Domain or category to search in
            limit: Maximum number of results to return

        Keywords: memory, procedure, search, domain, category, process
        Category: memory
        """
        try:
            tools.reset_billing()

            results = await memory_service.search_procedures_by_domain(user_id, domain, limit)

            # Format results
            formatted_results = []
            for procedure in results:
                formatted_results.append({
                    "memory_id": procedure.id,
                    "skill_type": procedure.skill_type,
                    "domain": procedure.domain,
                    "steps": procedure.steps,
                    "difficulty_level": procedure.difficulty_level,
                    "prerequisites": procedure.prerequisites,
                    "importance": procedure.importance_score,
                    "created_at": procedure.created_at.isoformat()
                })

            logger.info(f"Procedures search by domain completed for user {user_id}: {len(results)} results")

            return tools.create_response(
                status="success",
                action="search_procedures_by_domain",
                data={
                    "domain": domain,
                    "results": formatted_results,
                    "count": len(results)
                }
            )

        except Exception as e:
            logger.error(f"Error searching procedures by domain: {e}")
            return tools.create_response(
                status="error",
                action="search_procedures_by_domain",
                data={"user_id": user_id, "domain": domain},
                error_message=str(e)
            )

    # ========== SESSION MEMORY TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def store_session_message(
        user_id: str,
        session_id: str,
        message_content: str,
        message_type: str = "human",
        role: str = "user",
        importance_score: float = 0.5
    ) -> str:
        """Store session message with intelligent processing

        Store individual messages in a session with automatic intelligent processing.
        Uses advanced text analysis to analyze message content and trigger summarization when needed.

        Args:
            user_id: User identifier
            session_id: Unique session identifier
            message_content: Content of the message
            message_type: Type of message ('human', 'ai', 'system')
            role: Role of the message sender ('user', 'assistant', 'system')
            importance_score: Importance level (0.0-1.0, default 0.5)

        Keywords: memory, session, message, intelligent, conversation, dialog, chat
        Category: memory
        """
        try:
            tools.reset_billing()

            result = await memory_service.store_session_message(
                user_id=user_id,
                session_id=session_id,
                message_content=message_content,
                message_type=message_type,
                role=role,
                importance_score=importance_score
            )

            logger.info(f"Session message stored for user {user_id}: {result.success}")

            return tools.create_response(
                status="success" if result.success else "error",
                action="store_session_message",
                data={
                    "memory_id": result.memory_id,
                    "operation": result.operation,
                    "message": result.message,
                    "session_id": session_id,
                    "message_type": message_type
                }
            )

        except Exception as e:
            logger.error(f"Error storing session message: {e}")
            return tools.create_response(
                status="error",
                action="store_session_message",
                data={"user_id": user_id, "session_id": session_id},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def summarize_session(
        user_id: str,
        session_id: str,
        force_update: bool = False,
        compression_level: str = "medium"
    ) -> str:
        """Summarize session conversation intelligently

        Generate intelligent summaries of session conversations to prevent data explosion.
        Uses advanced text summarization to create comprehensive conversation summaries.

        Args:
            user_id: User identifier
            session_id: Unique session identifier
            force_update: Force summarization even if not needed
            compression_level: Level of compression ('brief', 'medium', 'detailed')

        Keywords: memory, session, summary, intelligent, conversation, compression, context
        Category: memory
        """
        try:
            tools.reset_billing()

            result = await memory_service.summarize_session(
                user_id=user_id,
                session_id=session_id,
                force_update=force_update,
                compression_level=compression_level
            )

            logger.info(f"Session summarized for user {user_id}: {result.success}")

            return tools.create_response(
                status="success" if result.success else "error",
                action="summarize_session",
                data={
                    "memory_id": result.memory_id,
                    "operation": result.operation,
                    "message": result.message,
                    "session_id": session_id,
                    "summary_data": result.data
                }
            )

        except Exception as e:
            logger.error(f"Error summarizing session: {e}")
            return tools.create_response(
                status="error",
                action="summarize_session",
                data={"user_id": user_id, "session_id": session_id},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def get_session_context(
        user_id: str,
        session_id: str,
        include_summaries: bool = True,
        max_recent_messages: int = 5
    ) -> str:
        """Get comprehensive session context

        Retrieve complete session context including summaries and recent messages.
        Provides intelligent context for continuing conversations.

        Args:
            user_id: User identifier
            session_id: Unique session identifier
            include_summaries: Whether to include session summaries
            max_recent_messages: Maximum number of recent messages to include

        Keywords: memory, session, context, conversation, history, summary, recent
        Category: memory
        """
        try:
            tools.reset_billing()

            context = await memory_service.get_session_context(
                user_id=user_id,
                session_id=session_id,
                include_summaries=include_summaries,
                max_recent_messages=max_recent_messages
            )

            logger.info(f"Session context retrieved for user {user_id}")

            return tools.create_response(
                status="success",
                action="get_session_context",
                data=context
            )

        except Exception as e:
            logger.error(f"Error getting session context: {e}")
            return tools.create_response(
                status="error",
                action="get_session_context",
                data={"user_id": user_id, "session_id": session_id},
                error_message=str(e)
            )

    # ========== WORKING MEMORY TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def get_active_working_memories(user_id: str) -> str:
        """Get active working memories for user

        Retrieve all non-expired working memories for ongoing tasks.

        Args:
            user_id: User identifier

        Keywords: memory, working, active, tasks, current, ongoing
        Category: memory
        """
        try:
            tools.reset_billing()

            working_memories = await memory_service.get_active_working_memories(user_id)

            # Format working memories for response
            formatted_memories = []
            for memory in working_memories:
                formatted_memories.append({
                    "memory_id": memory.id,
                    "task_id": memory.task_id,
                    "content": memory.content,
                    "task_context": memory.task_context,
                    "priority": memory.priority,
                    "expires_at": memory.expires_at.isoformat(),
                    "created_at": memory.created_at.isoformat()
                })

            logger.info(f"Active working memories for user {user_id}: {len(working_memories)} found")

            return tools.create_response(
                status="success",
                action="get_active_working_memories",
                data={
                    "user_id": user_id,
                    "working_memories": formatted_memories,
                    "count": len(working_memories)
                }
            )

        except Exception as e:
            logger.error(f"Error getting active working memories: {e}")
            return tools.create_response(
                status="error",
                action="get_active_working_memories",
                data={"user_id": user_id},
                error_message=str(e)
            )

    # ========== UTILITY TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    async def get_memory_statistics(user_id: str) -> str:
        """Get comprehensive memory statistics

        Retrieve detailed statistics about user's memory system including
        counts by type, usage patterns, and quality metrics.

        Args:
            user_id: User identifier

        Keywords: memory, statistics, stats, analytics, summary, metrics
        Category: memory
        """
        try:
            tools.reset_billing()

            stats = await memory_service.get_memory_statistics(user_id)

            logger.info(f"Memory statistics retrieved for user {user_id}")

            return tools.create_response(
                status="success",
                action="get_memory_statistics",
                data=stats
            )

        except Exception as e:
            logger.error(f"Error getting memory statistics: {e}")
            return tools.create_response(
                status="error",
                action="get_memory_statistics",
                data={"user_id": user_id},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def cleanup_expired_memories(user_id: Optional[str] = None) -> str:
        """Clean up expired working memories

        Remove expired working memories to maintain system performance.

        Args:
            user_id: User identifier (optional, if None cleans all users)

        Keywords: memory, cleanup, expire, maintenance, working, temporary
        Category: memory
        """
        try:
            tools.reset_billing()

            result = await memory_service.cleanup_expired_memories(user_id)

            logger.info(f"Memory cleanup completed: {result.message}")

            return tools.create_response(
                status="success" if result.success else "error",
                action="cleanup_expired_memories",
                data={
                    "operation": result.operation,
                    "message": result.message,
                    "user_id": user_id
                }
            )

        except Exception as e:
            logger.error(f"Error cleaning up memories: {e}")
            return tools.create_response(
                status="error",
                action="cleanup_expired_memories",
                data={"user_id": user_id},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def intelligent_memory_consolidation(user_id: str) -> str:
        """Perform intelligent memory consolidation and optimization

        Analyze and optimize user's memory system for better performance and organization.

        Args:
            user_id: User identifier

        Keywords: memory, consolidation, optimization, intelligence, analysis
        Category: memory
        """
        try:
            tools.reset_billing()

            result = await memory_service.intelligent_memory_consolidation(user_id)

            logger.info(f"Memory consolidation completed for user {user_id}")

            return tools.create_response(
                status="success",
                action="intelligent_memory_consolidation",
                data=result
            )

        except Exception as e:
            logger.error(f"Error performing memory consolidation: {e}")
            return tools.create_response(
                status="error",
                action="intelligent_memory_consolidation",
                data={"user_id": user_id},
                error_message=str(e)
            )

    logger.info("Enhanced memory tools registered successfully with comprehensive functionality")