#!/usr/bin/env python3
"""
Resource Selector using isa_model embeddings
Similar to tool_selector but for resources
"""
import sqlite3
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from isa_model.inference import AIFactory

from core.logging import get_logger

logger = get_logger(__name__)

class ResourceSelector:
    """AI-powered resource selector"""
    
    def __init__(self):
        self.embed_service = None
        self.resources_info = {}
        self.embeddings_cache = {}
        self.threshold = 0.25
    
    async def initialize(self):
        """Initialize embedding service"""
        try:
            # Load resource information dynamically
            await self._load_resource_info()
            
            # Initialize embedding service
            self.embed_service = AIFactory().get_embed()
            await self._compute_resource_embeddings()
            logger.info("Resource selector initialized")
        except Exception as e:
            logger.error(f"Failed to initialize resource selector: {e}")
    
    async def initialize_with_mcp(self, mcp_server):
        """Initialize resource selector with MCP server integration"""
        try:
            logger.info("Initializing resource selector with MCP server...")
            
            # Load resource information from MCP server
            await self._load_resource_info_from_mcp(mcp_server)
            
            # Initialize embedding service
            self.embed_service = AIFactory().get_embed()
            await self._compute_resource_embeddings()
            logger.info(f"Resource selector initialized with {len(self.resources_info)} MCP resources")
        except Exception as e:
            logger.error(f"Failed to initialize resource selector with MCP: {e}")
            # Fallback to normal initialization
            await self.initialize()
    
    async def _load_resource_info(self):
        """Load resource information dynamically"""
        try:
            logger.info("Loading resource information dynamically...")
            
            # Define resource information manually based on the resources we found
            self.resources_info = {
                # Memory resources
                "memory://all": {
                    "description": "Get all memories with monitoring and categorization",
                    "keywords": ["memory", "all", "complete", "list", "memories", "storage"],
                    "category": "memory",
                    "type": "data"
                },
                "memory://category/{category}": {
                    "description": "Get memories filtered by specific category",
                    "keywords": ["memory", "category", "filtered", "organized", "specific"],
                    "category": "memory",
                    "type": "data"
                },
                "weather://cache": {
                    "description": "Get cached weather data for various locations",
                    "keywords": ["weather", "cache", "forecast", "temperature", "location"],
                    "category": "weather",
                    "type": "data"
                },
                
                # Event sourcing resources
                "event://tasks": {
                    "description": "Get all tasks from event sourcing system",
                    "keywords": ["event", "tasks", "all", "sourcing", "workflow"],
                    "category": "event",
                    "type": "data"
                },
                "event://status": {
                    "description": "Get service status and health information",
                    "keywords": ["event", "status", "health", "service", "monitoring"],
                    "category": "event", 
                    "type": "status"
                },
                "event://tasks/active": {
                    "description": "Get currently active tasks from event system",
                    "keywords": ["event", "tasks", "active", "current", "running"],
                    "category": "event",
                    "type": "data"
                },
                "event://tasks/by-type/{task_type}": {
                    "description": "Get tasks filtered by specific type",
                    "keywords": ["event", "tasks", "type", "filtered", "category"],
                    "category": "event",
                    "type": "data"
                },
                "event://config/examples": {
                    "description": "Get configuration examples for event system",
                    "keywords": ["event", "config", "examples", "configuration", "setup"],
                    "category": "event",
                    "type": "config"
                },
                
                # Monitoring resources
                "monitoring://metrics": {
                    "description": "Get system monitoring metrics and performance data",
                    "keywords": ["monitoring", "metrics", "performance", "system", "data"],
                    "category": "monitoring",
                    "type": "metrics"
                },
                "monitoring://health": {
                    "description": "Get system health status and diagnostics",
                    "keywords": ["monitoring", "health", "status", "diagnostics", "system"],
                    "category": "monitoring",
                    "type": "status"
                },
                "monitoring://audit": {
                    "description": "Get audit logs and security monitoring data",
                    "keywords": ["monitoring", "audit", "logs", "security", "history"],
                    "category": "monitoring",
                    "type": "audit"
                },
                
                # Shopify resources
                "shopify://catalog/collections": {
                    "description": "Get product catalog collections and categories",
                    "keywords": ["shopify", "catalog", "collections", "products", "store"],
                    "category": "shopify",
                    "type": "catalog"
                },
                "shopify://knowledge/fashion_guide": {
                    "description": "Get fashion knowledge base and style guide",
                    "keywords": ["shopify", "fashion", "knowledge", "style", "guide"],
                    "category": "shopify",
                    "type": "knowledge"
                },
                "shopify://preferences/user_profiles": {
                    "description": "Get user shopping profiles and preferences",
                    "keywords": ["shopify", "user", "profiles", "preferences", "shopping"],
                    "category": "shopify",
                    "type": "profile"
                },
                "shopify://analytics/shopping_trends": {
                    "description": "Get shopping trends and analytics data",
                    "keywords": ["shopify", "analytics", "trends", "shopping", "data"],
                    "category": "shopify",
                    "type": "analytics"
                },
                "shopify://cache/product_recommendations": {
                    "description": "Get cached product recommendations for users",
                    "keywords": ["shopify", "recommendations", "products", "cache", "suggestions"],
                    "category": "shopify",
                    "type": "recommendations"
                },
                "shopify://inventory/stock_alerts": {
                    "description": "Get stock level alerts and inventory information",
                    "keywords": ["shopify", "inventory", "stock", "alerts", "availability"],
                    "category": "shopify",
                    "type": "inventory"
                }
            }
            
            logger.info(f"Loaded {len(self.resources_info)} resources: {list(self.resources_info.keys())}")
            
            # Log each resource's information
            for resource_name, info in self.resources_info.items():
                logger.info(f"  {resource_name}: {info['description'][:50]}...")
                logger.info(f"    Keywords: {info['keywords']}")
                logger.info(f"    Category: {info['category']}")
                
        except Exception as e:
            logger.error(f"Failed to load resource info: {e}")
    
    async def _load_resource_info_from_mcp(self, mcp_server):
        """Load resource information directly from MCP server"""
        try:
            logger.info("Loading resource information from MCP server...")
            
            # Get resources from MCP server
            resources = await mcp_server.list_resources()
            logger.info(f"Found {len(resources)} resources in MCP server")
            
            self.resources_info = {}
            for resource in resources:
                resource_uri = str(resource.uri)  # Convert AnyUrl to string
                description = resource.description or f"Resource: {resource_uri}"
                
                # Extract keywords from resource URI and description
                keywords = []
                if resource_uri:
                    # Extract from URI pattern (e.g., "memory://category/{category}")
                    uri_parts = resource_uri.replace('://', ' ').replace('/', ' ').replace('{', ' ').replace('}', ' ')
                    keywords.extend(uri_parts.split())
                if description:
                    # Simple keyword extraction from description
                    words = description.lower().split()
                    keywords.extend([w for w in words if len(w) > 3])
                
                # Remove duplicates and limit
                keywords = list(set(keywords))[:10]
                
                # Categorize based on resource URI patterns
                category = self._categorize_resource(resource_uri)
                
                self.resources_info[resource_uri] = {
                    "description": description,
                    "keywords": keywords,
                    "category": category,
                    "type": "mcp"
                }
                
                logger.info(f"  {resource_uri}: {description[:50]}...")
                logger.info(f"    Keywords: {keywords}")
                logger.info(f"    Category: {category}")
            
            # If no MCP resources found, fallback to hardcoded ones
            if not self.resources_info:
                logger.warning("No MCP resources found, using fallback resources")
                await self._load_resource_info()
                
        except Exception as e:
            logger.error(f"Failed to load resource info from MCP: {e}")
            # Fallback to hardcoded resources
            await self._load_resource_info()
    
    def _categorize_resource(self, resource_uri: str) -> str:
        """Categorize resource based on URI patterns"""
        resource_uri_lower = resource_uri.lower()
        
        if resource_uri_lower.startswith("memory://"):
            return "memory"
        elif resource_uri_lower.startswith("weather://"):
            return "weather"
        elif resource_uri_lower.startswith("event://"):
            return "event"
        elif resource_uri_lower.startswith("monitoring://"):
            return "monitoring"
        elif resource_uri_lower.startswith("shopify://"):
            return "shopify"
        elif resource_uri_lower.startswith("guardrail://"):
            return "security"
        elif resource_uri_lower.startswith("symbolic://"):
            return "reasoning"
        elif resource_uri_lower.startswith("rag://"):
            return "rag"
        else:
            return "general"
    
    async def _compute_resource_embeddings(self):
        """Compute resource embeddings"""
        try:
            # Check cache
            if await self._load_cached_embeddings():
                logger.info("Loaded cached resource embeddings")
                return
            
            # Compute new embeddings
            descriptions = []
            resource_names = []
            
            for resource_name, info in self.resources_info.items():
                combined_text = f"{info['description']} {' '.join(info['keywords'])}"
                descriptions.append(combined_text)
                resource_names.append(resource_name)
            
            # Batch compute
            if not self.embed_service:
                raise Exception("Embedding service not initialized")
                
            embeddings = []
            for desc in descriptions:
                embedding = await self.embed_service.create_text_embedding(desc)
                embeddings.append(embedding)
            
            # Cache results
            for resource_name, embedding in zip(resource_names, embeddings):
                self.embeddings_cache[resource_name] = embedding
            
            await self._save_embeddings_cache()
            logger.info(f"Computed embeddings for {len(embeddings)} resources")
            
        except Exception as e:
            logger.error(f"Failed to compute resource embeddings: {e}")
    
    async def _load_cached_embeddings(self) -> bool:
        """Load cached embeddings"""
        try:
            conn = sqlite3.connect("user_data.db")
            
            # Create table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS resource_embeddings (
                    resource_name TEXT PRIMARY KEY,
                    embedding TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            cursor = conn.execute("SELECT resource_name, embedding FROM resource_embeddings")
            results = cursor.fetchall()
            conn.close()
            
            if len(results) == len(self.resources_info):
                for resource_name, embedding_json in results:
                    self.embeddings_cache[resource_name] = json.loads(embedding_json)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to load cached resource embeddings: {e}")
            return False
    
    async def _save_embeddings_cache(self):
        """Save embeddings to cache"""
        try:
            conn = sqlite3.connect("user_data.db")
            
            now = datetime.now().isoformat()
            for resource_name, embedding in self.embeddings_cache.items():
                conn.execute(
                    "INSERT OR REPLACE INTO resource_embeddings (resource_name, embedding, created_at) VALUES (?, ?, ?)",
                    (resource_name, json.dumps(embedding), now)
                )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save resource embeddings cache: {e}")
    
    async def select_resources(self, user_request: str, max_resources: int = 3) -> List[str]:
        """Select relevant resources"""
        logger.info(f"Resource selector: analyzing request '{user_request}'")
        logger.info(f"Embed service ready: {self.embed_service is not None}")
        logger.info(f"Embeddings cache ready: {bool(self.embeddings_cache)}")
        logger.info(f"Max resources: {max_resources}, Threshold: {self.threshold}")
        
        if not self.embed_service or not self.embeddings_cache:
            logger.warning("Resource selector not ready, returning default resources")
            fallback_resources = ["memory://all", "monitoring://health"]
            logger.warning(f"Fallback resources: {fallback_resources}")
            return fallback_resources
        
        try:
            # Compute user request embedding
            logger.info("Computing user request embedding...")
            user_embedding = await self.embed_service.create_text_embedding(user_request)
            logger.info(f"User embedding computed, length: {len(user_embedding) if user_embedding else 0}")
            
            # Compute similarities
            logger.info(f"Computing similarities with {len(self.embeddings_cache)} resources...")
            similarities = {}
            for resource_name, resource_embedding in self.embeddings_cache.items():
                similarity = await self.embed_service.compute_similarity(
                    user_embedding, resource_embedding
                )
                similarities[resource_name] = similarity
                logger.info(f"  {resource_name}: {similarity:.4f}")
            
            # Select most relevant resources
            sorted_resources = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
            logger.info(f"Sorted resources by similarity: {sorted_resources}")
            
            # Apply threshold filtering
            selected = []
            for resource_name, score in sorted_resources:
                if score >= self.threshold and len(selected) < max_resources:
                    selected.append(resource_name)
                    logger.info(f"  Selected {resource_name} (score: {score:.4f} >= {self.threshold})")
                else:
                    logger.info(f"  Skipped {resource_name} (score: {score:.4f} < {self.threshold} or max reached)")
            
            # If no resources above threshold, select at least one most relevant
            if not selected and sorted_resources:
                selected = [sorted_resources[0][0]]
                logger.info(f"No resources above threshold, selecting best: {selected[0]} (score: {sorted_resources[0][1]:.4f})")
            
            # Log selection
            await self._log_selection(user_request, similarities, selected)
            
            logger.info(f"Final resource selection: {selected}")
            return selected
            
        except Exception as e:
            logger.error(f"Error in resource selection: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            fallback = ["memory://all", "monitoring://health"]  # Default fallback resources
            logger.error(f"Using fallback resources: {fallback}")
            return fallback
    
    async def _log_selection(self, request: str, similarities: Dict[str, float], selected: List[str]):
        """Log selection history"""
        try:
            conn = sqlite3.connect("user_data.db")
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS resource_selections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_request TEXT NOT NULL,
                    similarities TEXT NOT NULL,
                    selected_resources TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            
            conn.execute(
                "INSERT INTO resource_selections (user_request, similarities, selected_resources, timestamp) VALUES (?, ?, ?, ?)",
                (request, json.dumps(similarities), json.dumps(selected), datetime.now().isoformat())
            )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to log resource selection: {e}")
    
    async def get_stats(self) -> Dict:
        """Get statistics"""
        try:
            conn = sqlite3.connect("user_data.db")
            
            cursor = conn.execute("""
                SELECT selected_resources FROM resource_selections 
                ORDER BY timestamp DESC LIMIT 50
            """)
            
            results = cursor.fetchall()
            conn.close()
            
            # Count resource usage frequency
            resource_usage = {}
            for (selected_json,) in results:
                resources = json.loads(selected_json)
                for resource in resources:
                    resource_usage[resource] = resource_usage.get(resource, 0) + 1
            
            return {
                "total_selections": len(results),
                "resource_usage": resource_usage,
                "available_resources": list(self.resources_info.keys()),
                "threshold": self.threshold
            }
            
        except Exception as e:
            logger.error(f"Failed to get resource stats: {e}")
            return {}
    
    async def close(self):
        """Close service"""
        if self.embed_service:
            await self.embed_service.close()

# Global instance
_resource_selector = None

async def get_resource_selector():
    """Get resource selector instance"""
    global _resource_selector
    if _resource_selector is None:
        _resource_selector = ResourceSelector()
        await _resource_selector.initialize()
    return _resource_selector