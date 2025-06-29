#!/usr/bin/env python3
"""
Prompt Selector using isa_model embeddings
Similar to tool_selector but for prompts
"""
from core.supabase_client import get_supabase_client
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from isa_model.inference import AIFactory

from core.logging import get_logger

logger = get_logger(__name__)

class PromptSelector:
    """AI-powered prompt selector"""
    
    def __init__(self):
        self.embed_service = None
        self.prompts_info = {}
        self.embeddings_cache = {}
        self.threshold = 0.25
        self.supabase = get_supabase_client()
    
    async def initialize(self):
        """Initialize embedding service"""
        try:
            # Load prompt information dynamically
            await self._load_prompt_info()
            
            # Initialize embedding service
            self.embed_service = AIFactory().get_embed()
            await self._compute_prompt_embeddings()
            logger.info("Prompt selector initialized")
        except Exception as e:
            logger.error(f"Failed to initialize prompt selector: {e}")
    
    async def initialize_with_mcp(self, mcp_server):
        """Initialize prompt selector with MCP server integration"""
        try:
            logger.info("Initializing prompt selector with MCP server...")
            
            # Load prompt information from MCP server
            await self._load_prompt_info_from_mcp(mcp_server)
            
            # Initialize embedding service
            self.embed_service = AIFactory().get_embed()
            await self._compute_prompt_embeddings()
            logger.info(f"Prompt selector initialized with {len(self.prompts_info)} MCP prompts")
        except Exception as e:
            logger.error(f"Failed to initialize prompt selector with MCP: {e}")
            # Fallback to normal initialization
            await self.initialize()
    
    async def _load_prompt_info(self):
        """Load prompt information dynamically"""
        try:
            logger.info("Loading prompt information dynamically...")
            
            # Define prompt information manually since we can't dynamically extract from decorators
            self.prompts_info = {
                # System prompts
                "security_analysis_prompt": {
                    "description": "Generate a security analysis prompt for evaluating operations and risks",
                    "keywords": ["security", "analysis", "risk", "evaluation", "authorization", "audit"],
                    "category": "security",
                    "type": "system"
                },
                "memory_organization_prompt": {
                    "description": "Generate a prompt for organizing and categorizing memories effectively",
                    "keywords": ["memory", "organization", "categorization", "knowledge", "structure"],
                    "category": "memory",
                    "type": "system"
                },
                "monitoring_report_prompt": {
                    "description": "Generate a monitoring and performance analysis prompt for system metrics",
                    "keywords": ["monitoring", "performance", "metrics", "analysis", "system", "health"],
                    "category": "monitoring",
                    "type": "system"
                },
                "user_assistance_prompt": {
                    "description": "Generate a user assistance prompt for helping with general queries",
                    "keywords": ["assistance", "help", "support", "query", "user", "general"],
                    "category": "assistance",
                    "type": "system"
                },
                
                # Shopping prompts
                "personal_stylist_prompt": {
                    "description": "Generate a personal stylist consultation prompt for fashion advice",
                    "keywords": ["stylist", "fashion", "style", "consultation", "clothing", "outfit"],
                    "category": "shopping",
                    "type": "shopping"
                },
                "product_comparison_prompt": {
                    "description": "Generate a detailed product comparison analysis prompt",
                    "keywords": ["product", "comparison", "analysis", "evaluation", "review", "decision"],
                    "category": "shopping",
                    "type": "shopping"
                },
                "outfit_coordination_prompt": {
                    "description": "Generate outfit coordination and styling suggestions prompt",
                    "keywords": ["outfit", "coordination", "styling", "fashion", "clothing", "ensemble"],
                    "category": "shopping",
                    "type": "shopping"
                },
                "shopping_assistant_prompt": {
                    "description": "Generate a comprehensive shopping assistant interaction prompt",
                    "keywords": ["shopping", "assistant", "purchase", "recommendation", "retail", "customer"],
                    "category": "shopping",
                    "type": "shopping"
                },
                "trend_analysis_prompt": {
                    "description": "Generate fashion trend analysis and forecasting prompt",
                    "keywords": ["trend", "analysis", "fashion", "forecasting", "market", "style"],
                    "category": "shopping",
                    "type": "shopping"
                },
                "size_fit_consultant_prompt": {
                    "description": "Generate size and fit consultation guidance prompt",
                    "keywords": ["size", "fit", "consultation", "measurements", "sizing", "garment"],
                    "category": "shopping",
                    "type": "shopping"
                }
            }
            
            logger.info(f"Loaded {len(self.prompts_info)} prompts: {list(self.prompts_info.keys())}")
            
            # Log each prompt's information
            for prompt_name, info in self.prompts_info.items():
                logger.info(f"  {prompt_name}: {info['description'][:50]}...")
                logger.info(f"    Keywords: {info['keywords']}")
                logger.info(f"    Category: {info['category']}")
                
        except Exception as e:
            logger.error(f"Failed to load prompt info: {e}")
    
    async def _load_prompt_info_from_mcp(self, mcp_server):
        """Load prompt information directly from MCP server"""
        try:
            logger.info("Loading prompt information from MCP server...")
            
            # Get prompts from MCP server
            prompts = await mcp_server.list_prompts()
            logger.info(f"Found {len(prompts)} prompts in MCP server")
            
            self.prompts_info = {}
            for prompt in prompts:
                prompt_name = prompt.name
                description = prompt.description or f"Prompt: {prompt_name}"
                
                # Extract keywords from prompt name and description
                keywords = []
                if prompt_name:
                    keywords.extend(prompt_name.replace('_', ' ').split())
                if description:
                    # Simple keyword extraction from description
                    words = description.lower().split()
                    keywords.extend([w for w in words if len(w) > 3])
                
                # Remove duplicates and limit
                keywords = list(set(keywords))[:10]
                
                # Categorize based on prompt name patterns
                category = self._categorize_prompt(prompt_name)
                
                self.prompts_info[prompt_name] = {
                    "description": description,
                    "keywords": keywords,
                    "category": category,
                    "type": "mcp"
                }
                
                # 减少初始化日志
            
            # If no MCP prompts found, fallback to hardcoded ones
            if not self.prompts_info:
                logger.warning("No MCP prompts found, using fallback prompts")
                await self._load_prompt_info()
                
        except Exception as e:
            logger.error(f"Failed to load prompt info from MCP: {e}")
            # Fallback to hardcoded prompts
            await self._load_prompt_info()
    
    def _categorize_prompt(self, prompt_name: str) -> str:
        """Categorize prompt based on name patterns"""
        prompt_name_lower = prompt_name.lower()
        
        if any(word in prompt_name_lower for word in ["security", "analysis", "audit"]):
            return "security"
        elif any(word in prompt_name_lower for word in ["memory", "organization", "recall"]):
            return "memory"
        elif any(word in prompt_name_lower for word in ["monitoring", "performance", "metrics"]):
            return "monitoring"
        elif any(word in prompt_name_lower for word in ["assistance", "help", "support"]):
            return "assistance"
        elif any(word in prompt_name_lower for word in ["stylist", "fashion", "style", "outfit"]):
            return "shopping"
        elif any(word in prompt_name_lower for word in ["shopping", "product", "comparison"]):
            return "shopping"
        elif any(word in prompt_name_lower for word in ["autonomous", "execution", "planning"]):
            return "autonomous"
        else:
            return "general"
    
    async def _compute_prompt_embeddings(self):
        """Compute prompt embeddings"""
        try:
            # Check cache
            if await self._load_cached_embeddings():
                logger.info("Loaded cached prompt embeddings")
                return
            
            # Compute new embeddings
            descriptions = []
            prompt_names = []
            
            for prompt_name, info in self.prompts_info.items():
                combined_text = f"{info['description']} {' '.join(info['keywords'])}"
                descriptions.append(combined_text)
                prompt_names.append(prompt_name)
            
            # Batch compute
            if not self.embed_service:
                raise Exception("Embedding service not initialized")
                
            embeddings = []
            for desc in descriptions:
                embedding = await self.embed_service.create_text_embedding(desc)
                embeddings.append(embedding)
            
            # Cache results
            for prompt_name, embedding in zip(prompt_names, embeddings):
                self.embeddings_cache[prompt_name] = embedding
            
            await self._save_embeddings_cache()
            logger.info(f"Computed embeddings for {len(embeddings)} prompts")
            
        except Exception as e:
            logger.error(f"Failed to compute prompt embeddings: {e}")
    
    async def _load_cached_embeddings(self) -> bool:
        """从Supabase加载缓存的提示词嵌入向量"""
        try:
            result = self.supabase.client.table('prompt_embeddings').select('prompt_name, embedding').execute()
            
            if result.data and len(result.data) >= len(self.prompts_info) * 0.8:
                for row in result.data:
                    prompt_name = row['prompt_name']
                    embedding = row['embedding']
                    
                    # 确保embedding是List[float]格式
                    if isinstance(embedding, str):
                        import json
                        embedding = json.loads(embedding)
                    elif isinstance(embedding, list) and len(embedding) > 0 and isinstance(embedding[0], str):
                        embedding = [float(x) for x in embedding]
                    
                    self.embeddings_cache[prompt_name] = embedding
                
                logger.info(f"Loaded cached embeddings for {len(result.data)} prompts")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to load cached prompt embeddings from Supabase: {e}")
            return False
    
    async def _save_embeddings_cache(self):
        """保存提示词嵌入向量到Supabase"""
        try:
            for prompt_name, embedding in self.embeddings_cache.items():
                prompt_info = self.prompts_info.get(prompt_name, {})
                
                data = {
                    'prompt_name': prompt_name,
                    'description': prompt_info.get('description', ''),
                    'keywords': prompt_info.get('keywords', []),
                    'category': prompt_info.get('category', 'general'),
                    'embedding': embedding
                }
                
                self.supabase.client.table('prompt_embeddings').upsert(data).execute()
            
            logger.info(f"Saved prompt embeddings cache for {len(self.embeddings_cache)} prompts to Supabase")
            
        except Exception as e:
            logger.error(f"Failed to save prompt embeddings cache to Supabase: {e}")
    
    async def select_prompts(self, user_request: str, max_prompts: int = 3) -> List[str]:
        """Select relevant prompts"""
        logger.info(f"Prompt selector: analyzing request '{user_request}'")
        logger.info(f"Embed service ready: {self.embed_service is not None}")
        logger.info(f"Embeddings cache ready: {bool(self.embeddings_cache)}")
        logger.info(f"Max prompts: {max_prompts}, Threshold: {self.threshold}")
        
        if not self.embed_service or not self.embeddings_cache:
            logger.warning("Prompt selector not ready, returning default prompts")
            fallback_prompts = ["user_assistance_prompt", "memory_organization_prompt"]
            logger.warning(f"Fallback prompts: {fallback_prompts}")
            return fallback_prompts
        
        try:
            # Compute user request embedding
            logger.info("Computing user request embedding...")
            user_embedding = await self.embed_service.create_text_embedding(user_request)
            logger.info(f"User embedding computed, length: {len(user_embedding) if user_embedding else 0}")
            
            # Compute similarities
            logger.info(f"Computing similarities with {len(self.embeddings_cache)} prompts...")
            similarities = {}
            for prompt_name, prompt_embedding in self.embeddings_cache.items():
                similarity = await self.embed_service.compute_similarity(
                    user_embedding, prompt_embedding
                )
                similarities[prompt_name] = similarity
                logger.info(f"  {prompt_name}: {similarity:.4f}")
            
            # Select most relevant prompts
            sorted_prompts = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
            logger.info(f"Sorted prompts by similarity: {sorted_prompts}")
            
            # Apply threshold filtering
            selected = []
            for prompt_name, score in sorted_prompts:
                if score >= self.threshold and len(selected) < max_prompts:
                    selected.append(prompt_name)
                    logger.info(f"  Selected {prompt_name} (score: {score:.4f} >= {self.threshold})")
                # 移除冗长的跳过日志
            
            # If no prompts above threshold, select at least one most relevant
            if not selected and sorted_prompts:
                selected = [sorted_prompts[0][0]]
                logger.info(f"No prompts above threshold, selecting best: {selected[0]} (score: {sorted_prompts[0][1]:.4f})")
            
            # Log selection
            await self._log_selection(user_request, similarities, selected)
            
            logger.info(f"Final prompt selection: {selected}")
            return selected
            
        except Exception as e:
            logger.error(f"Error in prompt selection: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            fallback = ["user_assistance_prompt", "memory_organization_prompt"]  # Default fallback prompts
            logger.error(f"Using fallback prompts: {fallback}")
            return fallback
    
    async def _log_selection(self, request: str, similarities: Dict[str, float], selected: List[str]):
        """记录提示词选择历史到Supabase"""
        try:
            data = {
                'user_query': request,
                'selection_type': 'prompt',
                'selected_items': selected,
                'similarity_scores': similarities,
                'user_id': 'system'
            }
            
            self.supabase.client.table('selection_history').insert(data).execute()
            logger.info(f"Logged prompt selection for query: {request}")
            
        except Exception as e:
            logger.error(f"Failed to log prompt selection to Supabase: {e}")
    
    async def get_stats(self) -> Dict:
        """从Supabase获取提示词统计信息"""
        try:
            result = self.supabase.client.table('selection_history').select('selected_items').eq('selection_type', 'prompt').order('created_at', desc=True).limit(50).execute()
            
            # 统计提示词使用频率
            prompt_usage = {}
            for row in result.data:
                prompts = row['selected_items']
                for prompt in prompts:
                    prompt_usage[prompt] = prompt_usage.get(prompt, 0) + 1
            
            return {
                "total_selections": len(result.data),
                "prompt_usage": prompt_usage,
                "available_prompts": list(self.prompts_info.keys()),
                "threshold": self.threshold
            }
            
        except Exception as e:
            logger.error(f"Failed to get prompt stats from Supabase: {e}")
            return {}
    
    async def close(self):
        """Close service"""
        if self.embed_service:
            await self.embed_service.close()

# Global instance
_prompt_selector = None

async def get_prompt_selector():
    """Get prompt selector instance"""
    global _prompt_selector
    if _prompt_selector is None:
        _prompt_selector = PromptSelector()
        await _prompt_selector.initialize()
    return _prompt_selector