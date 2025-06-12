from app.config.config_manager import config_manager
from .memory_searcher import GraphSearcher as searcher
from app.services.agent.capabilities.contextual.mem.graphs.tools import (
    EXTRACT_ENTITIES_STRUCT_TOOL,
    RELATIONS_STRUCT_TOOL,
)
from app.services.ai.models.ai_factory import AIFactory
from typing import List, Dict, Tuple, Optional

import logging 

logger = logging.getLogger(__name__)

class GraphWriter:
    """
    Handles all write operations to the graph database including
    adding new nodes, updating relationships, and linking memory IDs.
    """
    
    def __init__(self, config, searcher):
        """
        Initialize GraphWriter with configuration and dependencies.
        
        Args:
            config: Configuration object containing necessary settings
            searcher: GraphSearcher instance for querying existing data
        """
        self.config = config
        self.searcher = searcher
        self.embedding_model = None
        self.llm = None
        self.graph = None
        self.threshold = 0.7
        
    async def setup(self):
        """Initialize required services"""
        self.graph = await config_manager.get_db('neo4j')
        config = config_manager.get_config('llm')
        self.embedding_model = AIFactory.get_instance().get_embedding(
            model_name="bge-m3",
            provider="ollama",
            config=config
        )
        self.llm = AIFactory.get_instance().get_llm(
            model_name="llama3.1",
            provider="ollama",
            config=config
        )
    async def process_dialogue(
        self,
        messages: List[Dict[str, str]],
        filters: Dict[str, str],
        memory_ids: Optional[List[str]] = None
    ) -> List[Dict[str, str]]:
        """
        Process dialogue messages to update the graph.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            filters: Must contain 'user_id'
            memory_ids: Optional list of vector store memory IDs
            
        Returns:
            List of created/updated relationships
        """
        try:
            # Extract context from messages
            context = self._extract_context(messages, filters)
            
            # Extract entities and create embeddings
            entities = await self._extract_entities(context)
            if not entities:
                logger.info("No entities found in dialogue")
                return []
                
            # Create embeddings for entities
            entity_embeddings = await self._create_entity_embeddings(entities)
            
            # Determine operations needed
            operations = await self._determine_operations(
                context=context,
                entities=entities,
                filters=filters
            )
            
            # Process operations
            results = await self._process_operations(
                operations=operations,
                entity_embeddings=entity_embeddings,
                filters=filters,
                memory_ids=memory_ids
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing dialogue: {e}")
            return []
            
    def _extract_context(self, messages: List[Dict[str, str]], filters: Dict[str, str]) -> str:
        """
        Combine messages into a single context string with role and user information.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            filters: Dictionary containing user_id
            
        Returns:
            Formatted context string with user identity
        """
        user_id = filters.get("user_id", "unknown_user")
        formatted_messages = []
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "user":
                formatted_messages.append(f"{user_id} said: '{content}'")
            elif role == "assistant":
                formatted_messages.append(f"assistant responded to {user_id}: '{content}'")
            else:
                formatted_messages.append(f"{role} said to {user_id}: '{content}'")
                
        return " ".join(formatted_messages)
        
    async def _extract_entities(self, context: str) -> List[Dict[str, str]]:
        """Extract entities and their types from context"""
        try:
            response = await self.llm.generate_response(
                messages=[
                    {
                        "role": "system",
                        "content": "Extract entities and their types from the text. Focus on meaningful entities. there is implicit role, create entity for each role"
                    },
                    {"role": "user", "content": context}
                ],
                tools=[EXTRACT_ENTITIES_STRUCT_TOOL]
            )
            
            entities = response["tool_calls"][0]["arguments"]["entities"]
            logger.info(f"Extracted entities: {entities}")
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []
            
    async def _create_entity_embeddings(
        self,
        entities: List[Dict[str, str]]
    ) -> Dict[str, List[float]]:
        """Create embeddings for entities"""
        embeddings = {}
        embedding_dimension = None
        
        logger.info(f"Creating embeddings for {len(entities)} entities")
        
        for entity in entities:
            try:
                entity_name = entity["entity"].lower()
                logger.debug(f"Creating embedding for entity: {entity_name}")
                
                embedding = await self.embedding_model.create_text_embeddings(entity_name)
                logger.debug(f"Raw embedding type: {type(embedding)}, shape/len: {len(embedding)}")
                
                # Convert to list if needed
                if hasattr(embedding, 'tolist'):
                    embedding = embedding.tolist()
                    logger.debug("Converted embedding from numpy to list")
                
                # Handle nested lists
                if isinstance(embedding[0], list):
                    embedding = embedding[0]
                    logger.debug("Flattened nested embedding list")
                    
                # Validate dimension consistency
                if embedding_dimension is None:
                    embedding_dimension = len(embedding)
                    logger.info(f"Set initial embedding dimension to {embedding_dimension}")
                elif len(embedding) != embedding_dimension:
                    logger.warning(f"Dimension mismatch for {entity_name}: got {len(embedding)}, expected {embedding_dimension}")
                    continue
                    
                embeddings[entity_name] = embedding
                logger.debug(f"Successfully stored embedding for {entity_name} with dimension {len(embedding)}")
                
            except Exception as e:
                logger.error(f"Error creating embedding for {entity_name}: {e}", exc_info=True)
                continue
            
        if not embeddings:
            logger.error("No valid embeddings were created")
            raise ValueError("Failed to create any valid embeddings")
        
        return embeddings

    async def _determine_operations(
        self,
        context: str,
        entities: List[Dict[str, str]],
        filters: Dict[str, str]
    ) -> Dict[str, List[Dict]]:
        """
        Determine what operations need to be performed based on context and existing data.
        
        Args:
            context: The text context
            entities: List of extracted entities
            filters: Must contain 'user_id'
            
        Returns:
            Dictionary with 'updates' and 'additions' lists
        """
        try:
            # Extract relationships from context
            relationships = await self._extract_relationships(context, entities)
            if not relationships:
                return {"updates": [], "additions": []}
            
            # Get existing relationships for these entities
            existing = await self.searcher.find_existing_relations(
                entities=[e["entity"].lower() for e in entities],
                filters=filters
            )
            
            updates = []
            additions = []
            
            # Helper function to get sanitized entity type
            def get_entity_type(entity_name: str) -> str:
                entity_type = next(
                    (e["entity_type"] for e in entities if e["entity"].lower() == entity_name),
                    "ENTITY"
                )
                return entity_type.replace(" ", "_")
            
            # Categorize each relationship
            for rel in relationships:
                source = rel["source_entity"].lower()
                target = rel["destination_entity"].lower()
                
                # Check if relationship exists
                existing_rel = next(
                    (r for r in existing 
                     if r["source"] == source and r["target"] == target),
                    None
                )
                
                if existing_rel and existing_rel["relationship"] != rel["relation"].upper():
                    # Relationship exists but with different type -> Update
                    updates.append({
                        "source": source,
                        "target": target,
                        "old_relation": existing_rel["relationship"],
                        "new_relation": rel["relation"],
                        "source_type": get_entity_type(source),
                        "target_type": get_entity_type(target)
                    })
                elif not existing_rel:
                    # New relationship -> Add
                    additions.append({
                        "source": source,
                        "target": target,
                        "relation": rel["relation"],
                        "source_type": get_entity_type(source),
                        "target_type": get_entity_type(target)
                    })
                
            return {
                "updates": updates,
                "additions": additions
            }
            
        except Exception as e:
            logger.error(f"Error determining operations: {e}")
            return {"updates": [], "additions": []}

    async def _extract_relationships(
        self,
        context: str,
        entities: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Extract relationships between entities from context"""
        try:
            # Format entities for context
            entity_context = ", ".join([f"{e['entity']} ({e['entity_type']})" for e in entities])
            
            response = await self.llm.generate_response(
                messages=[
                    {
                        "role": "system",
                        "content": "Extract relationships between entities. Entities: " + entity_context
                    },
                    {"role": "user", "content": context}
                ],
                tools=[RELATIONS_STRUCT_TOOL]
            )
            
            relationships = response["tool_calls"][0]["arguments"]["entities"]
            logger.info(f"Extracted relationships: {relationships}")
            return relationships
            
        except Exception as e:
            logger.error(f"Error extracting relationships: {e}")
            return []

    async def _process_operations(
        self,
        operations: Dict[str, List[Dict]],
        entity_embeddings: Dict[str, List[float]],
        filters: Dict[str, str],
        memory_ids: Optional[List[str]] = None
    ) -> List[Dict[str, str]]:
        """
        Process determined operations to update the graph.
        
        Args:
            operations: Dictionary with 'updates' and 'additions' lists
            entity_embeddings: Dictionary of entity embeddings
            filters: Must contain 'user_id'
            memory_ids: Optional list of vector store memory IDs
            
        Returns:
            List of processed relationships
        """
        results = []
        
        try:
            # Process updates first
            for update in operations["updates"]:
                try:
                    await self._update_relationship(
                        source=update["source"],
                        target=update["target"],
                        relationship=update["new_relation"],
                        source_type=update["source_type"],
                        target_type=update["target_type"],
                        entity_embeddings=entity_embeddings,
                        filters=filters,
                        memory_ids=memory_ids
                    )
                    results.append({
                        "source": update["source"],
                        "relationship": update["new_relation"],
                        "target": update["target"]
                    })
                except Exception as e:
                    logger.error(f"Error processing update {update}: {e}")
                    continue
                
            # Process additions
            for addition in operations["additions"]:
                try:
                    await self._create_relationship(
                        source=addition["source"],
                        target=addition["target"],
                        relationship=addition["relation"],
                        source_type=addition["source_type"],
                        target_type=addition["target_type"],
                        entity_embeddings=entity_embeddings,
                        filters=filters,
                        memory_ids=memory_ids
                    )
                    results.append({
                        "source": addition["source"],
                        "relationship": addition["relation"],
                        "target": addition["target"]
                    })
                except Exception as e:
                    logger.error(f"Error processing addition {addition}: {e}")
                    continue
                
            return results
            
        except Exception as e:
            logger.error(f"Error processing operations: {e}")
            return []

    async def _update_relationship(
        self,
        source: str,
        target: str,
        relationship: str,
        source_type: str,
        target_type: str,
        entity_embeddings: Dict[str, List[float]],
        filters: Dict[str, str],
        memory_ids: Optional[List[str]] = None
    ) -> None:
        """
        Update an existing relationship between nodes.
        
        Args:
            source: Source node name
            target: Target node name
            relationship: New relationship type
            source_type: Type of source node
            target_type: Type of target node
            entity_embeddings: Dictionary of entity embeddings
            filters: Must contain 'user_id'
            memory_ids: Optional list of vector store memory IDs
        """
        logger.info(f"Updating relationship: {source} -{relationship}-> {target}")
        
        try:
            # Standardize relationship name
            relationship = relationship.upper().replace(" ", "_")
            
            # Update nodes with embeddings
            await self._ensure_nodes_exist(
                source=source,
                target=target,
                source_type=source_type,
                target_type=target_type,
                entity_embeddings=entity_embeddings,
                filters=filters
            )
            
            # Delete existing relationship
            delete_query = """
            MATCH (n1 {name: $source, user_id: $user_id})-[r]->(n2 {name: $target, user_id: $user_id})
            DELETE r
            """
            await self.graph.query(
                delete_query,
                params={"source": source, "target": target, "user_id": filters["user_id"]}
            )
            
            # Create new relationship
            create_query = f"""
            MATCH (n1 {{name: $source, user_id: $user_id}}), (n2 {{name: $target, user_id: $user_id}})
            CREATE (n1)-[r:{relationship} {{created_at: datetime()}}]->(n2)
            RETURN n1, r, n2
            """
            result = await self.graph.query(
                create_query,
                params={"source": source, "target": target, "user_id": filters["user_id"]}
            )
            
            if not result:
                raise Exception(f"Failed to create new relationship between {source} and {target}")
            
            # Link memory IDs if provided
            if memory_ids:
                await self._link_memory_ids(
                    source=source,
                    target=target,
                    memory_ids=memory_ids,
                    filters=filters
                )
            
        except Exception as e:
            logger.error(f"Error updating relationship: {e}")
            raise

    async def _create_relationship(
        self,
        source: str,
        target: str,
        relationship: str,
        source_type: str,
        target_type: str,
        entity_embeddings: Dict[str, List[float]],
        filters: Dict[str, str],
        memory_ids: Optional[List[str]] = None
    ) -> None:
        """Create a new relationship between nodes."""
        logger.info(f"Creating relationship: {source} -{relationship}-> {target}")
        
        try:
            # 标准化关系名称和方向
            standard_relations = {
                "graduated_from": ("person", "institution"),
                "graduated_in": ("person", "year"),
                "works_at": ("person", "company"),
                "lives_in": ("person", "location"),
                "located_in": ("entity", "location"),
                "has_name": ("person", "name"),
                "has_job_title": ("person", "title")
            }
            
            relationship = relationship.upper().replace(" ", "_")
            if relationship.lower() in standard_relations:
                expected_source_type, expected_target_type = standard_relations[relationship.lower()]
                if expected_source_type == "person" and source_type != "Person":
                    source, target = target, source
                    source_type, target_type = target_type, source_type
            
            # 使用 MATCH...WITH...MATCH 模式避免笛卡尔积
            create_query = f"""
            MATCH (n1 {{name: $source, user_id: $user_id}})
            WITH n1
            MATCH (n2 {{name: $target, user_id: $user_id}})
            WHERE n1 <> n2  // 避免自环
            MERGE (n1)-[r:{relationship} {{created_at: datetime()}}]->(n2)
            RETURN n1, r, n2
            """
            
            result = await self.graph.query(
                create_query,
                params={
                    "source": source,
                    "target": target,
                    "user_id": filters["user_id"],
                    "relationship": relationship
                }
            )
            
            if not result:
                raise Exception(f"Failed to create relationship between {source} and {target}")
            
            # Link memory IDs if provided
            if memory_ids:
                await self._link_memory_ids(
                    source=source,
                    target=target,
                    memory_ids=memory_ids,
                    filters=filters
                )
            
        except Exception as e:
            logger.error(f"Error creating relationship: {e}")
            raise

    async def _ensure_nodes_exist(
        self,
        source: str,
        target: str,
        source_type: str,
        target_type: str,
        entity_embeddings: Dict[str, List[float]],
        filters: Dict[str, str]
    ) -> None:
        try:
            logger.info(f"Ensuring nodes exist - source: {source}, target: {target}")
            logger.debug(f"Available embeddings: {list(entity_embeddings.keys())}")
            
            # Get embeddings using lowercase keys
            source_embedding = entity_embeddings.get(source.lower(), [])
            target_embedding = entity_embeddings.get(target.lower(), [])
            
            logger.debug(f"Source embedding dimension: {len(source_embedding) if source_embedding else 'None'}")
            logger.debug(f"Target embedding dimension: {len(target_embedding) if target_embedding else 'None'}")
            
            # Validate embeddings before storing
            if not source_embedding or not target_embedding:
                logger.warning("Missing embeddings, creating new ones")
                source_embedding = await self.embedding_model.create_text_embeddings(source)
                target_embedding = await self.embedding_model.create_text_embeddings(target)
            
            # Ensure embeddings are flat lists
            if hasattr(source_embedding, 'tolist'):
                source_embedding = source_embedding.tolist()
            if hasattr(target_embedding, 'tolist'):
                target_embedding = target_embedding.tolist()
            
            # Flatten if nested
            if isinstance(source_embedding[0], list):
                source_embedding = source_embedding[0]
            if isinstance(target_embedding[0], list):
                target_embedding = target_embedding[0]
            
            # Convert embeddings to list of floats
            source_embedding = [float(x) for x in source_embedding]
            target_embedding = [float(x) for x in target_embedding]
            
            # Store source node with embedding
            source_query = f"""
            MERGE (n:{source_type} {{name: $name, user_id: $user_id}})
            ON CREATE SET 
                n.created_at = datetime(),
                n.embedding = $embedding,
                n.last_updated = datetime()
            ON MATCH SET 
                n.last_updated = datetime(),
                n.embedding = $embedding
            RETURN n
            """
            await self.graph.query(
                source_query,
                params={
                    "name": source,
                    "user_id": filters["user_id"],
                    "embedding": source_embedding
                }
            )
            
            # Store target node with embedding
            target_query = f"""
            MERGE (n:{target_type} {{name: $name, user_id: $user_id}})
            ON CREATE SET 
                n.created_at = datetime(),
                n.embedding = $embedding,
                n.last_updated = datetime()
            ON MATCH SET 
                n.last_updated = datetime(),
                n.embedding = $embedding
            RETURN n
            """
            await self.graph.query(
                target_query,
                params={
                    "name": target,
                    "user_id": filters["user_id"],
                    "embedding": target_embedding
                }
            )
            
        except Exception as e:
            logger.error(f"Error ensuring nodes exist: {e}")
            raise

    async def _link_memory_ids(
        self,
        source: str,
        target: str,
        memory_ids: List[str],
        filters: Dict[str, str]
    ) -> None:
        """
        Link memory IDs to nodes.
        
        Args:
            source: Source node name
            target: Target node name
            memory_ids: List of memory IDs to link
            filters: Must contain 'user_id'
        """
        try:
            for memory_id in memory_ids:
                memory_query = """
                MATCH (n {name: $name, user_id: $user_id})
                WITH n
                MERGE (m:Memory {id: $memory_id, user_id: $user_id})
                ON CREATE SET m.created_at = datetime()
                MERGE (n)-[r:REFERENCED_IN]->(m)
                ON CREATE SET r.created_at = datetime()
                """
                await self.graph.query(
                    memory_query,
                    params={
                        "name": source,
                        "memory_id": memory_id,
                        "user_id": filters["user_id"]
                    }
                )

                # 对目标节点也创建引用
                await self.graph.query(
                    memory_query,
                    params={
                        "name": target,
                        "memory_id": memory_id,
                        "user_id": filters["user_id"]
                    }
                )
                
        except Exception as e:
            logger.error(f"Error linking memory IDs: {e}")
            raise