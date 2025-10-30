"""
Prompt Service - Business logic layer for MCP prompt management
"""

import logging
from typing import Dict, Any, Optional, List

from .prompt_repository import PromptRepository

logger = logging.getLogger(__name__)


class PromptService:
    """Prompt service - business logic layer"""

    def __init__(self, repository: Optional[PromptRepository] = None):
        """Initialize prompt service"""
        self.repository = repository or PromptRepository()

    async def register_prompt(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new prompt"""
        if not prompt_data.get('name'):
            raise ValueError("Prompt name is required")

        if not prompt_data.get('content'):
            raise ValueError("Prompt content is required")

        existing = await self.repository.get_prompt_by_name(prompt_data['name'])
        if existing:
            raise ValueError(f"Prompt '{prompt_data['name']}' already exists")

        prompt = await self.repository.create_prompt(prompt_data)
        if not prompt:
            raise RuntimeError("Failed to create prompt")

        logger.info(f"Registered new prompt: {prompt['name']}")
        return prompt

    async def get_prompt(self, prompt_identifier: Any) -> Optional[Dict[str, Any]]:
        """Get prompt by ID or name"""
        if isinstance(prompt_identifier, int):
            return await self.repository.get_prompt_by_id(prompt_identifier)
        elif isinstance(prompt_identifier, str):
            return await self.repository.get_prompt_by_name(prompt_identifier)
        else:
            raise ValueError("Prompt identifier must be int (ID) or str (name)")

    async def list_prompts(
        self,
        category: Optional[str] = None,
        active_only: bool = True,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List prompts with filters"""
        return await self.repository.list_prompts(
            category=category,
            is_active=active_only if active_only else None,
            tags=tags,
            limit=limit,
            offset=offset
        )

    async def update_prompt(
        self,
        prompt_identifier: Any,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update prompt information"""
        prompt = await self.get_prompt(prompt_identifier)
        if not prompt:
            raise ValueError(f"Prompt not found: {prompt_identifier}")

        prompt_id = prompt['id']

        if 'name' in updates and updates['name'] != prompt['name']:
            existing = await self.repository.get_prompt_by_name(updates['name'])
            if existing:
                raise ValueError(f"Prompt name '{updates['name']}' already exists")

        success = await self.repository.update_prompt(prompt_id, updates)
        if not success:
            raise RuntimeError("Failed to update prompt")

        updated_prompt = await self.repository.get_prompt_by_id(prompt_id)
        logger.info(f"Updated prompt: {prompt['name']}")
        return updated_prompt

    async def delete_prompt(self, prompt_identifier: Any) -> bool:
        """Delete prompt (soft delete)"""
        prompt = await self.get_prompt(prompt_identifier)
        if not prompt:
            raise ValueError(f"Prompt not found: {prompt_identifier}")

        success = await self.repository.delete_prompt(prompt['id'])
        if success:
            logger.info(f"Deleted prompt: {prompt['name']}")
        return success

    async def record_prompt_usage(
        self,
        prompt_identifier: Any,
        generation_time_ms: int
    ) -> bool:
        """Record prompt usage"""
        prompt = await self.get_prompt(prompt_identifier)
        if not prompt:
            logger.warning(f"Cannot record usage for unknown prompt: {prompt_identifier}")
            return False

        return await self.repository.increment_usage_count(
            prompt['id'],
            generation_time_ms
        )

    async def search_prompts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search prompts"""
        return await self.repository.search_prompts(query, limit)

    async def search_by_tags(self, tags: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """Search prompts by tags"""
        return await self.repository.search_by_tags(tags, limit)

    async def get_popular_prompts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular prompts"""
        all_prompts = await self.repository.list_prompts(is_active=True, limit=1000)
        sorted_prompts = sorted(all_prompts, key=lambda p: p.get('usage_count', 0), reverse=True)
        return sorted_prompts[:limit]
