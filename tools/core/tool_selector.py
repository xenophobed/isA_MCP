#!/usr/bin/env python3
"""
Tool Selector using isa_model embeddings
Based on embedding-based simple tool selection
"""
from core.supabase_client import get_supabase_client
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
        self.supabase = get_supabase_client()
    
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
    
    async def initialize_with_mcp(self, mcp_server):
        """Initialize tool selector with MCP server integration"""
        try:
            logger.info("Initializing tool selector with MCP server...")
            
            # Load tool information from MCP server
            await self._load_tool_info_from_mcp(mcp_server)
            
            # Initialize embedding service
            self.embed_service = AIFactory().get_embed()
            await self._compute_tool_embeddings()
            logger.info(f"Tool selector initialized with {len(self.tools_info)} MCP tools")
        except Exception as e:
            logger.error(f"Failed to initialize tool selector with MCP: {e}")
            # Fallback to normal initialization
            await self.initialize()
    

    
    async def _load_tool_info(self):
        """Load tool information dynamically (legacy method - use initialize_with_mcp instead)"""
        logger.warning("Using legacy tool loading method - consider using initialize_with_mcp")
        self.tools_info = {}
    
    async def _load_tool_info_from_mcp(self, mcp_server):
        """Load tool information directly from MCP server"""
        try:
            logger.info("Loading tool information from MCP server...")
            
            # Get tools from MCP server
            tools = await mcp_server.list_tools()
            logger.info(f"Found {len(tools)} tools in MCP server")
            
            self.tools_info = {}
            for tool in tools:
                tool_name = tool.name
                description = tool.description or f"Tool: {tool_name}"
                
                # Extract keywords from tool name and description
                keywords = []
                if tool_name:
                    keywords.extend(tool_name.replace('_', ' ').split())
                if description:
                    # Simple keyword extraction from description
                    words = description.lower().split()
                    keywords.extend([w for w in words if len(w) > 3])
                
                # Remove duplicates and limit
                keywords = list(set(keywords))[:10]
                
                # Categorize based on tool name patterns
                category = self._categorize_tool(tool_name)
                
                self.tools_info[tool_name] = {
                    "description": description,
                    "keywords": keywords,
                    "category": category
                }
                
                # 减少初始化日志
                
        except Exception as e:
            logger.error(f"Failed to load tool info from MCP: {e}")
            self.tools_info = {}
    
    def _categorize_tool(self, tool_name: str) -> str:
        """Categorize tool based on name patterns"""
        tool_name_lower = tool_name.lower()
        
        if any(word in tool_name_lower for word in ["weather", "temperature", "forecast"]):
            return "weather"
        elif any(word in tool_name_lower for word in ["image", "generate", "picture", "visual"]):
            return "image"
        elif any(word in tool_name_lower for word in ["remember", "memory", "recall", "forget"]):
            return "memory"
        elif any(word in tool_name_lower for word in ["shopify", "product", "order", "cart", "checkout"]):
            return "shopify"
        elif any(word in tool_name_lower for word in ["admin", "system", "manage", "authorization"]):
            return "admin"
        elif any(word in tool_name_lower for word in ["web", "browser", "automation", "login", "search"]):
            return "web"
        elif any(word in tool_name_lower for word in ["event", "sourcing", "task", "background"]):
            return "event"
        elif any(word in tool_name_lower for word in ["autonomous", "plan", "execute"]):
            return "autonomous"
        else:
            return "general"
    
    async def _compute_tool_embeddings(self):
        """Compute tool embeddings"""
        try:
            # Check cache first
            if await self._load_cached_embeddings():
                logger.info("Loaded cached embeddings")
                # 只计算缺失的embeddings
                missing_tools = [name for name in self.tools_info.keys() if name not in self.embeddings_cache]
                if missing_tools:
                    logger.info(f"Computing embeddings for {len(missing_tools)} new tools")
                    await self._compute_missing_embeddings(missing_tools)
                return
            
            # Compute all embeddings if no cache
            logger.info(f"Computing embeddings for all {len(self.tools_info)} tools")
            await self._compute_all_embeddings()
            
        except Exception as e:
            logger.error(f"Failed to compute embeddings: {e}")
    
    async def _compute_missing_embeddings(self, missing_tools: List[str]):
        """只计算缺失的embeddings"""
        try:
            if not self.embed_service:
                raise Exception("Embedding service not initialized")
            
            new_embeddings = {}
            for tool_name in missing_tools:
                tool_info = self.tools_info[tool_name]
                combined_text = f"{tool_info['description']} {' '.join(tool_info['keywords'])}"
                embedding = await self.embed_service.create_text_embedding(combined_text)
                new_embeddings[tool_name] = embedding
                self.embeddings_cache[tool_name] = embedding
            
            # 只保存新的embeddings
            await self._save_new_embeddings(new_embeddings)
            
        except Exception as e:
            logger.error(f"Failed to compute missing embeddings: {e}")
    
    async def _compute_all_embeddings(self):
        """计算所有embeddings"""
        try:
            if not self.embed_service:
                raise Exception("Embedding service not initialized")
                
            for tool_name, tool_info in self.tools_info.items():
                combined_text = f"{tool_info['description']} {' '.join(tool_info['keywords'])}"
                embedding = await self.embed_service.create_text_embedding(combined_text)
                self.embeddings_cache[tool_name] = embedding
            
            await self._save_embeddings_cache()
            logger.info(f"Computed embeddings for {len(self.embeddings_cache)} tools")
            
        except Exception as e:
            logger.error(f"Failed to compute all embeddings: {e}")
    
    async def _save_new_embeddings(self, new_embeddings: Dict[str, List[float]]):
        """只保存新的embeddings"""
        try:
            batch_data = []
            for tool_name, embedding in new_embeddings.items():
                tool_info = self.tools_info.get(tool_name, {})
                batch_data.append({
                    'tool_name': tool_name,
                    'description': tool_info.get('description', ''),
                    'keywords': tool_info.get('keywords', []),
                    'category': tool_info.get('category', 'general'),
                    'embedding': embedding
                })
            
            if batch_data:
                self.supabase.client.table('tool_embeddings').upsert(batch_data).execute()
                logger.info(f"Saved {len(new_embeddings)} new embeddings to Supabase")
            
        except Exception as e:
            logger.error(f"Failed to save new embeddings: {e}")
    
    async def _load_cached_embeddings(self) -> bool:
        """从Supabase加载缓存的嵌入向量"""
        try:
            # 查询工具嵌入向量
            result = self.supabase.client.table('tool_embeddings').select('tool_name, embedding').execute()
            
            if result.data and len(result.data) >= len(self.tools_info) * 0.8:  # 80%的工具有缓存就认为有效
                for row in result.data:
                    tool_name = row['tool_name']
                    embedding = row['embedding']
                    
                    # 确保embedding是List[float]格式，跳过None值
                    if embedding is None:
                        logger.warning(f"Skipping tool {tool_name} with None embedding")
                        continue
                    elif isinstance(embedding, str):
                        import json
                        embedding = json.loads(embedding)
                    elif isinstance(embedding, list) and len(embedding) > 0 and isinstance(embedding[0], str):
                        embedding = [float(x) for x in embedding]
                    
                    # 只保存有效的embedding
                    if embedding and isinstance(embedding, list) and len(embedding) > 0:
                        self.embeddings_cache[tool_name] = embedding
                    else:
                        logger.warning(f"Skipping tool {tool_name} with invalid embedding: {type(embedding)}")
                
                logger.info(f"Loaded cached embeddings for {len(result.data)} tools")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to load cached embeddings from Supabase: {e}")
            return False
    
    async def _save_embeddings_cache(self):
        """保存嵌入向量到Supabase"""
        try:
            # 批量插入/更新工具嵌入向量
            for tool_name, embedding in self.embeddings_cache.items():
                tool_info = self.tools_info.get(tool_name, {})
                
                data = {
                    'tool_name': tool_name,
                    'description': tool_info.get('description', ''),
                    'keywords': tool_info.get('keywords', []),
                    'category': tool_info.get('category', 'general'),
                    'embedding': embedding
                }
                
                # 使用upsert进行插入或更新
                self.supabase.client.table('tool_embeddings').upsert(data).execute()
            
            logger.info(f"Saved embeddings cache for {len(self.embeddings_cache)} tools to Supabase")
            
        except Exception as e:
            logger.error(f"Failed to save embeddings cache to Supabase: {e}")
    
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
                # 移除冗长的跳过日志
            
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
        """记录选择历史到Supabase"""
        try:
            data = {
                'user_query': request,
                'selection_type': 'tool',
                'selected_items': selected,
                'similarity_scores': similarities,
                'user_id': 'system'
            }
            
            self.supabase.client.table('selection_history').insert(data).execute()
            logger.info(f"Logged tool selection for query: {request}")
            
        except Exception as e:
            logger.error(f"Failed to log selection to Supabase: {e}")
    
    async def get_stats(self) -> Dict:
        """从Supabase获取统计信息"""
        try:
            # 查询最近的工具选择历史
            result = self.supabase.client.table('selection_history').select('selected_items').eq('selection_type', 'tool').order('created_at', desc=True).limit(50).execute()
            
            # 统计工具使用频率
            tool_usage = {}
            for row in result.data:
                tools = row['selected_items']
                for tool in tools:
                    tool_usage[tool] = tool_usage.get(tool, 0) + 1
            
            return {
                "total_selections": len(result.data),
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