#!/usr/bin/env python3
"""
Neo4j Adapter

Adapter class for Neo4j database operations, providing a standardized
interface that can be extended for other graph databases.
"""

import logging
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class GraphDatabaseAdapter(ABC):
    """Abstract base class for graph database adapters."""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the graph database."""
        pass
        
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the graph database."""
        pass
        
    @abstractmethod
    async def create_node(self, labels: List[str], properties: Dict[str, Any]) -> Dict[str, Any]:
        """Create a node in the graph."""
        pass
        
    @abstractmethod
    async def create_relationship(self, source_id: str, target_id: str, rel_type: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Create a relationship between nodes."""
        pass
        
    @abstractmethod
    async def query(self, query_string: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a custom query."""
        pass

class Neo4jAdapter(GraphDatabaseAdapter):
    """
    Neo4j-specific adapter implementation.
    
    Provides standardized interface for Neo4j operations that can be
    easily swapped for other graph database implementations.
    """
    
    def __init__(self, neo4j_client):
        """Initialize with Neo4j client."""
        self.neo4j_client = neo4j_client
        self._connected = False
        
    async def connect(self) -> bool:
        """Connect to Neo4j database."""
        try:
            if self.neo4j_client:
                # Test connection
                await self.neo4j_client.execute_query("RETURN 1")
                self._connected = True
                logger.info("Neo4j adapter connected successfully")
                return True
            return False
        except Exception as e:
            logger.error(f"Neo4j adapter connection failed: {e}")
            return False
            
    async def disconnect(self) -> None:
        """Disconnect from Neo4j database."""
        try:
            if self.neo4j_client:
                await self.neo4j_client.close()
                self._connected = False
                logger.info("Neo4j adapter disconnected")
        except Exception as e:
            logger.error(f"Neo4j adapter disconnect failed: {e}")
            
    async def create_node(self, labels: List[str], properties: Dict[str, Any]) -> Dict[str, Any]:
        """Create a node with specified labels and properties."""
        try:
            if not self._connected:
                raise Exception("Neo4j adapter not connected")
                
            # Convert labels list to Cypher format
            labels_str = ":".join(labels)
            
            # Build properties string
            props_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
            
            query = f"CREATE (n:{labels_str} {{{props_str}}}) RETURN n"
            
            results = await self.neo4j_client.execute_query(query, properties)
            
            if results:
                node = dict(results[0]["n"])
                return {
                    "success": True,
                    "node": node,
                    "id": node.get("id") or node.get("name")
                }
            return {"success": False, "error": "No node created"}
            
        except Exception as e:
            logger.error(f"Node creation failed: {e}")
            return {"success": False, "error": str(e)}
            
    async def create_relationship(self, source_id: str, target_id: str, rel_type: str, properties: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a relationship between two nodes."""
        try:
            if not self._connected:
                raise Exception("Neo4j adapter not connected")
                
            properties = properties or {}
            
            # Build properties string
            props_str = ""
            if properties:
                props_str = "{" + ", ".join([f"{k}: ${k}" for k in properties.keys()]) + "}"
                
            query = f"""
            MATCH (source {{name: $source_id}}), (target {{name: $target_id}})
            CREATE (source)-[r:{rel_type} {props_str}]->(target)
            RETURN r
            """
            
            params = {
                "source_id": source_id,
                "target_id": target_id,
                **properties
            }
            
            results = await self.neo4j_client.execute_query(query, params)
            
            if results:
                relationship = dict(results[0]["r"])
                return {
                    "success": True,
                    "relationship": relationship,
                    "type": rel_type
                }
            return {"success": False, "error": "No relationship created"}
            
        except Exception as e:
            logger.error(f"Relationship creation failed: {e}")
            return {"success": False, "error": str(e)}
            
    async def query(self, query_string: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a custom Cypher query."""
        try:
            if not self._connected:
                raise Exception("Neo4j adapter not connected")
                
            results = await self.neo4j_client.execute_query(query_string, parameters or {})
            return results
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []
            
    async def get_node_by_property(self, label: str, property_name: str, property_value: Any) -> Optional[Dict[str, Any]]:
        """Get a node by a specific property value."""
        try:
            query = f"MATCH (n:{label} {{{property_name}: $value}}) RETURN n LIMIT 1"
            results = await self.query(query, {"value": property_value})
            
            if results:
                return dict(results[0]["n"])
            return None
            
        except Exception as e:
            logger.error(f"Node lookup failed: {e}")
            return None
            
    async def get_node_relationships(self, node_id: str, direction: str = "both") -> List[Dict[str, Any]]:
        """Get all relationships for a node."""
        try:
            if direction == "outgoing":
                query = "MATCH (n {name: $node_id})-[r]->(m) RETURN r, m"
            elif direction == "incoming":
                query = "MATCH (n {name: $node_id})<-[r]-(m) RETURN r, m"
            else:  # both
                query = "MATCH (n {name: $node_id})-[r]-(m) RETURN r, m"
                
            results = await self.query(query, {"node_id": node_id})
            
            relationships = []
            for result in results:
                relationships.append({
                    "relationship": dict(result["r"]),
                    "connected_node": dict(result["m"])
                })
                
            return relationships
            
        except Exception as e:
            logger.error(f"Relationship lookup failed: {e}")
            return []
            
    async def delete_node(self, node_id: str) -> bool:
        """Delete a node and all its relationships."""
        try:
            query = "MATCH (n {name: $node_id}) DETACH DELETE n"
            await self.query(query, {"node_id": node_id})
            return True
            
        except Exception as e:
            logger.error(f"Node deletion failed: {e}")
            return False
            
    async def update_node_properties(self, node_id: str, properties: Dict[str, Any]) -> bool:
        """Update properties of an existing node."""
        try:
            # Build SET clause
            set_clauses = [f"n.{k} = ${k}" for k in properties.keys()]
            set_clause = ", ".join(set_clauses)
            
            query = f"MATCH (n {{name: $node_id}}) SET {set_clause} RETURN n"
            
            params = {"node_id": node_id, **properties}
            results = await self.query(query, params)
            
            return len(results) > 0
            
        except Exception as e:
            logger.error(f"Node update failed: {e}")
            return False