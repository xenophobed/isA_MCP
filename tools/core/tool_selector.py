#!/usr/bin/env python3
"""
Tool Selector using isa_model embeddings
Based on embedding-based simple tool selection
"""
import sqlite3
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from isa_model.inference import AIFactory

from core.logging import get_logger

logger = get_logger(__name__)

class ToolSelector:
    """AI-powered tool selector"""
    
    def __init__(self):
        self.embed_service = None
        self.tools_info = {}
        self.embeddings_cache = {}
        self.threshold = 0.25
    
    async def initialize(self):
        """Initialize embedding service"""
        try:
            # Load tool information dynamically
            await self._load_tool_info()
            
            # Initialize embedding service
            self.embed_service = AIFactory().get_embed()
            await self._compute_tool_embeddings()
            logger.info("Tool selector initialized")
        except Exception as e:
            logger.error(f"Failed to initialize tool selector: {e}")
    
    async def initialize_with_metadata(self, metadata: Dict[str, Any]):
        """Initialize tool selector with pre-discovered metadata"""
        try:
            logger.info("Initializing tool selector with auto-discovered metadata...")
            
            # Use tools from auto-discovery
            self.tools_info = {}
            for tool_name, tool_data in metadata.get("tools", {}).items():
                self.tools_info[tool_name] = {
                    "description": tool_data.get("description", ""),
                    "keywords": tool_data.get("keywords", []),
                }
            
            logger.info(f"Loaded {len(self.tools_info)} auto-discovered tools")
            
            # Initialize embedding service
            self.embed_service = AIFactory().get_embed()
            await self._compute_tool_embeddings()
            logger.info("Tool selector initialized with auto-discovered metadata")
        except Exception as e:
            logger.error(f"Failed to initialize with metadata: {e}")
            # Fallback to normal initialization
            await self.initialize()
    
    async def _load_tool_info(self):
        """Load tool information dynamically"""
        try:
            from tools.core.smart_tools import get_all_tool_info
            logger.info("Loading tool information dynamically...")
            
            self.tools_info = await get_all_tool_info()
            logger.info(f"Loaded {len(self.tools_info)} tools: {list(self.tools_info.keys())}")
            
            # Log each tool's information
            for tool_name, info in self.tools_info.items():
                logger.info(f"  {tool_name}: {info['description'][:50]}...")
                logger.info(f"    Keywords: {info['keywords']}")
                logger.info(f"    Category: {info['category']}")
                
        except Exception as e:
            logger.error(f"Failed to load tool info: {e}")
            # Initialize empty - will be populated by actual MCP tools
            self.tools_info = {}
    
    async def _compute_tool_embeddings(self):
        """Compute tool embeddings"""
        try:
            # Check cache
            if await self._load_cached_embeddings():
                logger.info("Loaded cached embeddings")
                return
            
            # Compute new embeddings
            descriptions = []
            tool_names = []
            
            for tool_name, info in self.tools_info.items():
                combined_text = f"{info['description']} {' '.join(info['keywords'])}"
                descriptions.append(combined_text)
                tool_names.append(tool_name)
            
            # Batch compute
            if not self.embed_service:
                raise Exception("Embedding service not initialized")
                
            embeddings = []
            for desc in descriptions:
                embedding = await self.embed_service.create_text_embedding(desc)
                embeddings.append(embedding)
            
            # Cache results
            for tool_name, embedding in zip(tool_names, embeddings):
                self.embeddings_cache[tool_name] = embedding
            
            await self._save_embeddings_cache()
            logger.info(f"Computed embeddings for {len(embeddings)} tools")
            
        except Exception as e:
            logger.error(f"Failed to compute embeddings: {e}")
    
    async def _load_cached_embeddings(self) -> bool:
        """Load cached embeddings"""
        try:
            conn = sqlite3.connect("user_data.db")
            
            # Create table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tool_embeddings (
                    tool_name TEXT PRIMARY KEY,
                    embedding TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            cursor = conn.execute("SELECT tool_name, embedding FROM tool_embeddings")
            results = cursor.fetchall()
            conn.close()
            
            if len(results) == len(self.tools_info):
                for tool_name, embedding_json in results:
                    self.embeddings_cache[tool_name] = json.loads(embedding_json)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to load cached embeddings: {e}")
            return False
    
    async def _save_embeddings_cache(self):
        """Save embeddings to cache"""
        try:
            conn = sqlite3.connect("user_data.db")
            
            now = datetime.now().isoformat()
            for tool_name, embedding in self.embeddings_cache.items():
                conn.execute(
                    "INSERT OR REPLACE INTO tool_embeddings (tool_name, embedding, created_at) VALUES (?, ?, ?)",
                    (tool_name, json.dumps(embedding), now)
                )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save embeddings cache: {e}")
    
    async def select_tools(self, user_request: str, max_tools: int = 3) -> List[str]:
        """Select relevant tools"""
        logger.info(f"Tool selector: analyzing request '{user_request}'")
        logger.info(f"Embed service ready: {self.embed_service is not None}")
        logger.info(f"Embeddings cache ready: {bool(self.embeddings_cache)}")
        logger.info(f"Max tools: {max_tools}, Threshold: {self.threshold}")
        
        if not self.embed_service or not self.embeddings_cache:
            logger.warning("Tool selector not ready, returning all tools")
            fallback_tools = list(self.tools_info.keys())
            logger.warning(f"Fallback tools: {fallback_tools}")
            return fallback_tools
        
        try:
            # Compute user request embedding
            logger.info("Computing user request embedding...")
            user_embedding = await self.embed_service.create_text_embedding(user_request)
            logger.info(f"User embedding computed, length: {len(user_embedding) if user_embedding else 0}")
            
            # Compute similarities
            logger.info(f"Computing similarities with {len(self.embeddings_cache)} tools...")
            similarities = {}
            for tool_name, tool_embedding in self.embeddings_cache.items():
                similarity = await self.embed_service.compute_similarity(
                    user_embedding, tool_embedding
                )
                similarities[tool_name] = similarity
                logger.info(f"  {tool_name}: {similarity:.4f}")
            
            # Select most relevant tools
            sorted_tools = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
            logger.info(f"Sorted tools by similarity: {sorted_tools}")
            
            # Apply threshold filtering
            selected = []
            for tool_name, score in sorted_tools:
                if score >= self.threshold and len(selected) < max_tools:
                    selected.append(tool_name)
                    logger.info(f"  Selected {tool_name} (score: {score:.4f} >= {self.threshold})")
                else:
                    logger.info(f"  Skipped {tool_name} (score: {score:.4f} < {self.threshold} or max reached)")
            
            # If no tools above threshold, select at least one most relevant
            if not selected and sorted_tools:
                selected = [sorted_tools[0][0]]
                logger.info(f"No tools above threshold, selecting best: {selected[0]} (score: {sorted_tools[0][1]:.4f})")
            
            # Log selection
            await self._log_selection(user_request, similarities, selected)
            
            logger.info(f"Final selection: {selected}")
            return selected
            
        except Exception as e:
            logger.error(f"Error in tool selection: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            fallback = ["weather", "memory"]  # Default fallback tools
            logger.error(f"Using fallback tools: {fallback}")
            return fallback
    
    async def _log_selection(self, request: str, similarities: Dict[str, float], selected: List[str]):
        """Log selection history"""
        try:
            conn = sqlite3.connect("user_data.db")
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tool_selections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_request TEXT NOT NULL,
                    similarities TEXT NOT NULL,
                    selected_tools TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            
            conn.execute(
                "INSERT INTO tool_selections (user_request, similarities, selected_tools, timestamp) VALUES (?, ?, ?, ?)",
                (request, json.dumps(similarities), json.dumps(selected), datetime.now().isoformat())
            )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to log selection: {e}")
    
    async def get_stats(self) -> Dict:
        """Get statistics"""
        try:
            conn = sqlite3.connect("user_data.db")
            
            cursor = conn.execute("""
                SELECT selected_tools FROM tool_selections 
                ORDER BY timestamp DESC LIMIT 50
            """)
            
            results = cursor.fetchall()
            conn.close()
            
            # Count tool usage frequency
            tool_usage = {}
            for (selected_json,) in results:
                tools = json.loads(selected_json)
                for tool in tools:
                    tool_usage[tool] = tool_usage.get(tool, 0) + 1
            
            return {
                "total_selections": len(results),
                "tool_usage": tool_usage,
                "available_tools": list(self.tools_info.keys()),
                "threshold": self.threshold
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
    
    async def close(self):
        """Close service"""
        if self.embed_service:
            await self.embed_service.close()

# Global instance
_tool_selector = None

async def get_tool_selector():
    """Get tool selector instance"""
    global _tool_selector
    if _tool_selector is None:
        _tool_selector = ToolSelector()
        await _tool_selector.initialize()
    return _tool_selector