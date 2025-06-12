from typing import List, Dict, Optional, Tuple
from app.config.config_manager import config_manager
from rank_bm25 import BM25Okapi
from app.services.ai.models.ai_factory import AIFactory

import logging 
from datetime import datetime

logger = logging.getLogger(__name__)

class GraphSearcher:
    """
    Handles all search operations in the graph database including
    similarity search, relationship queries, and context expansion.
    """
    
    def __init__(self, config):
        self.config = config
        self.graph = None
        self.embedding_model = None
        self.threshold = 0.7
        self.manager = None
        
    async def setup(self):
        """Initialize required services"""
        self.graph = await config_manager.get_db('neo4j')
        # 直接获取嵌入服务，不使用await
        self.embedding_model = AIFactory.get_instance().get_embed_service(
            model_name="bge-m3",
            provider="ollama"
        )
        
        # Check GDS library
        self.gds_available = False  # Track GDS availability
        try:
            # Check if GDS is installed using explicit YIELD
            result = await self.graph.query("""
            CALL gds.list()
            YIELD name
            RETURN count(name) as count
            """)
            if result and result[0]['count'] >= 0:
                logger.info("Graph Data Science library is available")
                self.gds_available = True  # Set GDS availability
        except Exception as e:
            logger.error(f"Failed to verify GDS library: {e}")
            # Continue anyway - we'll use fallback similarity if needed
            pass
        
    async def find_similar_entities(
        self,
        query: str,
        filters: Dict[str, str],
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """Find entities similar to query using GDS vector similarity."""
        try:
            logger.info(f"Finding similar entities for query: {query}")
            
            # Create query embedding
            query_embedding = await self.embedding_model.create_text_embeddings(query)
            logger.debug(f"Query embedding type: {type(query_embedding)}, initial shape/len: {len(query_embedding)}")
            
            # Ensure embedding is in correct format
            if hasattr(query_embedding, 'tolist'):
                query_embedding = query_embedding.tolist()
                logger.debug("Converted query embedding from numpy to list")
            
            if isinstance(query_embedding[0], list):
                query_embedding = query_embedding[0]
                logger.debug("Flattened nested query embedding")
            
            logger.debug(f"Final query embedding dimension: {len(query_embedding)}")

            # Use direct vector similarity without projection
            if self.gds_available:
                search_query = """
                MATCH (n {user_id: $user_id})
                WHERE n.embedding IS NOT NULL
                WITH n, 
                     $query_embedding AS qvec,
                     [x IN n.embedding | toFloat(x)] AS nvec
                WHERE size(nvec) = $expected_dimension
                WITH DISTINCT n, 
                     gds.similarity.cosine(nvec, qvec) AS score,
                     n.created_at AS created_at
                MATCH (n)-[r]-(m)
                RETURN DISTINCT
                    n.name AS entity,
                    labels(n)[0] AS type,
                    score,
                    created_at,
                    collect(DISTINCT {
                        type: type(r),
                        direction: CASE WHEN startNode(r) = n THEN 'outgoing' ELSE 'incoming' END,
                        node: m.name,
                        created_at: r.created_at
                    }) as relationships
                ORDER BY score DESC, created_at DESC
                LIMIT $limit
                """
            else:
                search_query = """
                MATCH (n {user_id: $user_id})
                WHERE n.embedding IS NOT NULL
                WITH n, 
                     $query_embedding AS qvec,
                     [x IN n.embedding | toFloat(x)] AS nvec
                WHERE size(nvec) = $expected_dimension
                WITH n,
                     reduce(s = 0.0, i IN range(0, size(nvec)-1) | 
                         s + nvec[i] * qvec[i]) / 
                         (sqrt(reduce(s = 0.0, x IN nvec | s + x * x)) * 
                          sqrt(reduce(s = 0.0, x IN qvec | s + x * x))) AS score
                WHERE score >= $threshold
                RETURN 
                    n.name AS entity,
                    labels(n)[0] AS type,
                    score,
                    n.created_at AS created_at,
                    [(n)-[r]->(m) | {type: type(r), target: m.name}] as connections
                ORDER BY score DESC
                LIMIT $limit
                """
            
            results = await self.graph.query(
                search_query,
                params={
                    "query_embedding": query_embedding,
                    "user_id": filters["user_id"],
                    "threshold": 0.6,
                    "limit": limit,
                    "expected_dimension": len(query_embedding)
                }
            )
            
            logger.info(f"Found {len(results)} similar entities")
            logger.debug(f"Search results: {results}")

            # 添加结果过滤
            filtered_results = []
            for result in results:
                # 只保留相似度高于 0.6 的结果
                if result.get('score', 0) < 0.6:
                    continue
                    
                # 检查实体类型是否与查询相关
                entity_type = result.get('type', '').lower()
                if not self._is_relevant_type(query, entity_type):
                    continue
                    
                filtered_results.append(result)
                
            logger.info(f"Found {len(filtered_results)} relevant entities after filtering")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error in similarity search: {e}", exc_info=True)
            return []
            
    async def find_existing_relations(
        self,
        entities: List[str],
        filters: Dict[str, str]
    ) -> List[Dict[str, str]]:
        """
        Find existing relationships for given entities.
        
        Args:
            entities: List of entity names
            filters: Must contain 'user_id'
            
        Returns:
            List of existing relationships
        """
        try:
            cypher = """
            MATCH (n {user_id: $user_id})
            WHERE n.name IN $entities
            MATCH (n)-[r]->(m {user_id: $user_id})
            RETURN 
                n.name AS source,
                type(r) AS relationship,
                m.name AS target,
                r.created_at AS created_at
            UNION
            MATCH (n {user_id: $user_id})
            WHERE n.name IN $entities
            MATCH (m {user_id: $user_id})-[r]->(n)
            RETURN 
                m.name AS source,
                type(r) AS relationship,
                n.name AS target,
                r.created_at AS created_at
            """
            
            results = await self.graph.query(
                cypher,
                params={
                    "user_id": filters["user_id"],
                    "entities": entities
                }
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error finding existing relations: {e}")
            return []
            
    async def expand_context(
        self,
        entities: List[str],
        filters: Dict[str, str],
        depth: int = 2,
        limit: int = 50
    ) -> List[Dict[str, str]]:
        """
        Expand graph context from seed entities.
        
        Args:
            entities: List of seed entity names
            filters: Must contain 'user_id'
            depth: How many hops to expand
            limit: Maximum number of relationships to return
        """
        try:
            logger.info(f"Expanding context for entities: {entities}")
            
            # Simplified query to get all relationships
            cypher = """
            MATCH (n)-[r]-(m)
            WHERE n.name IN $entities 
            AND n.user_id = $user_id
            WITH DISTINCT n.name AS source,
                 type(r) AS relationship,
                 m.name AS target,
                 r.created_at AS created_at
            ORDER BY created_at DESC
            LIMIT $limit
            RETURN source, relationship, target, created_at
            """
            
            logger.debug(f"Executing expand context query with params: {filters}")
            
            results = await self.graph.query(
                cypher,
                params={
                    "user_id": filters["user_id"],
                    "entities": entities,
                    "limit": limit
                }
            )
            
            logger.info(f"Found {len(results)} relationships in context expansion")
            logger.debug(f"Relationship results: {results}")
            
            # Convert results to the expected format
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "source": result["source"],
                    "relationship": result["relationship"],
                    "target": result["target"],
                    "type": "relationship"  # Add type to distinguish from entities
                })
                
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error expanding context: {e}", exc_info=True)
            return []
            
    async def find_by_memory_ids(
        self,
        memory_ids: List[str],
        filters: Dict[str, str]
    ) -> List[Dict[str, str]]:
        """
        Find entities and relationships linked to memory IDs.
        
        Args:
            memory_ids: List of memory IDs
            filters: Must contain 'user_id'
            
        Returns:
            List of related entities and relationships
        """
        try:
            cypher = """
            MATCH (n {user_id: $user_id})-[:REFERENCED_IN]->(m:Memory)
            WHERE m.id IN $memory_ids
            WITH COLLECT(n) as nodes
            UNWIND nodes as n1
            MATCH (n1)-[r]->(n2)
            WHERE n2 IN nodes
            RETURN DISTINCT
                n1.name AS source,
                type(r) AS relationship,
                n2.name AS target,
                m.id AS memory_id
            """
            
            results = await self.graph.query(
                cypher,
                params={
                    "user_id": filters["user_id"],
                    "memory_ids": memory_ids
                }
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error finding by memory IDs: {e}")
            return []
            
    def rank_results(
        self,
        results: List[Dict[str, str]],
        query: str,
        top_n: int = 5
    ) -> List[Dict[str, str]]:
        """Rank search results using BM25."""
        try:
            if not results:
                return []

            # Convert results to sequences for ranking
            sequences = []
            for result in results:
                if "entity" in result:
                    # For entity results
                    sequence = [
                        result["entity"],
                        result.get("type", ""),
                        " ".join(str(rel.get("type", "")) + " " + str(rel.get("node", "")) 
                                for rel in result.get("relationships", []))
                    ]
                else:
                    # For relationship results
                    sequence = [
                        result.get("source", ""),
                        result.get("relationship", ""),
                        result.get("target", "")
                    ]
                sequences.append(" ".join(filter(None, sequence)).split())

            # Initialize BM25
            bm25 = BM25Okapi(sequences)

            # Tokenize query into meaningful words
            tokenized_query = query.lower().split()

            # Rank results
            scores = bm25.get_scores(tokenized_query)
            ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_n]

            # Return ranked results
            ranked_results = []
            for idx in ranked_indices:
                ranked_results.append(results[idx])

            return ranked_results

        except Exception as e:
            logger.error(f"Error ranking results: {e}")
            return results  # Return original results if ranking fails
            
    def format_results_to_text(self, results: List[Dict[str, str]], filters: Dict[str, str]) -> str:
        try:
            if not results:
                return "No information found."
            
            memory_groups = {
                "entities": [],
                "attributes": [],
                "actions": [],
                "locations": [],
                "other": []
            }
            
            now = datetime.now()
            seen_facts = set()
            seen_entities = set()
            
            def _classify_relationship(rel_time: str, source: str, rel_type: str, target: str):
                """根据关系类型分类"""
                if not source or not target or not rel_type:
                    return
                    
                try:
                    # 标准化关系
                    rel_type = str(rel_type).lower()
                    
                    # 忽略系统关系
                    if rel_type in ["referenced_in"]:
                        return
                        
                    # 创建关系描述
                    rel_str = f"{source} {rel_type.replace('_', ' ')} {target} at {self._format_timestamp(rel_time)}"
                    
                    # 避免重复
                    if rel_str in seen_facts:
                        return
                    seen_facts.add(rel_str)
                    
                    # 基于关系类型分类
                    if any(x in rel_type for x in ["is", "has", "name", "title"]):
                        memory_groups["attributes"].append((rel_time, rel_str))
                    elif any(x in rel_type for x in ["work", "study", "graduate"]):
                        memory_groups["actions"].append((rel_time, rel_str))
                    elif any(x in rel_type for x in ["live", "locate"]):
                        memory_groups["locations"].append((rel_time, rel_str))
                        
                except Exception as e:
                    logger.warning(f"Error classifying relationship: {e} - source: {source}, target: {target}, type: {rel_type}")

            # 处理结果
            for item in results:
                if "entity" in item:
                    entity_key = f"{item['type']}:{item['entity']}"
                    if entity_key not in seen_entities:
                        seen_entities.add(entity_key)
                        created_at = item.get("created_at", "unknown time")
                        score = f" (confidence: {item.get('score', 0):.2f})" if "score" in item else ""
                        fact = f"Found {item['type'].lower()}: {item['entity']} at {self._format_timestamp(created_at)}{score}"
                        memory_groups["entities"].append((created_at, fact))
                        seen_facts.add(fact)
                    
                    if "relationships" in item:
                        for rel in item["relationships"]:
                            _classify_relationship(
                                rel.get("created_at", "unknown time"),
                                item["entity"],
                                rel["type"],
                                rel["node"]
                            )

            # 对于位置搜索，优先显示位置相关信息
            if any("location" in item.get("type", "").lower() for item in results):
                sections = []
                sections.append("Here's what I remember:")
                
                # 优先显示位置信息
                if memory_groups["locations"]:
                    sections.append("\nLocations:")
                    sections.extend(f"- {fact[1]}" for fact in memory_groups["locations"])
                    
                # 其他信息按相关度显示
                for group_name in ["attributes", "actions", "other"]:
                    if memory_groups[group_name]:
                        sections.append(f"\n{group_name.title()}:")
                        sections.extend(f"- {fact[1]}" for fact in memory_groups[group_name])
                        
                return "\n".join(sections)
            
            # 格式化输出
            sections = []
            sections.append("Here's what I remember:")

            # 对每个分组内部按时间排序
            for group in memory_groups.values():
                group.sort(key=lambda x: x[0] if x[0] != "unknown time" else "", reverse=True)

            # 1. 实体基本信息
            if memory_groups["entities"]:
                sections.append("\nEntity Information:")
                sections.extend(f"- {fact[1]}" for fact in memory_groups["entities"])

            # 2. 属性关系
            if memory_groups["attributes"]:
                sections.append("\nAttributes:")
                sections.extend(f"- {fact[1]}" for fact in memory_groups["attributes"])

            # 3. 动作关系
            if memory_groups["actions"]:
                sections.append("\nActions:")
                sections.extend(f"- {fact[1]}" for fact in memory_groups["actions"])

            # 4. 位置关系
            if memory_groups["locations"]:
                sections.append("\nLocations:")
                sections.extend(f"- {fact[1]}" for fact in memory_groups["locations"])

            # 5. 其他关系
            if memory_groups["other"]:
                sections.append("\nOther Information:")
                sections.extend(f"- {fact[1]}" for fact in memory_groups["other"])

            return "\n".join(sections)

        except Exception as e:
            logger.error(f"Error formatting results: {e}", exc_info=True)
            return "Error formatting search results."

    def _format_timestamp(self, timestamp) -> str:
        """格式化时间戳为可读格式"""
        if not timestamp or timestamp == "unknown time":
            return "unknown time"
        try:
            if isinstance(timestamp, str):
                # 修复时间戳解析
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00').split('.')[0])
            else:
                dt = timestamp
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.warning(f"Failed to format timestamp {timestamp}: {e}")
            return str(timestamp)

    def _is_relevant_type(self, query: str, entity_type: str) -> bool:
        """检查实体类型是否与查询相关"""
        # 定义查询类型与实体类型的映射
        type_mappings = {
            'weather': ['weather', 'location', 'climate'],
            'shipping': ['courier', 'carrier', 'delivery'],
            # ... 添加更多映射
        }
        
        # 基于查询内容判断相关类型
        query = query.lower()
        if 'weather' in query:
            return entity_type in type_mappings['weather']
        if any(word in query for word in ['shipping', 'delivery', 'track']):
            return entity_type in type_mappings['shipping']
            
        return True  # 默认保留