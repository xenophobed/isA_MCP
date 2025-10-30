"""
Sync Service - Synchronize tools/prompts/resources from MCP Server to database

Architecture:
    MCP Server API (list_tools/prompts/resources)
        → PostgreSQL (tool_service/prompt_service/resource_service)
        → Generate embeddings
        → Qdrant (vector_service)
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class SyncService:
    """
    Synchronization service

    Responsibilities:
    1. Get tools/prompts/resources from MCP Server API
    2. Sync to PostgreSQL (using tool/prompt/resource services)
    3. Generate embeddings
    4. Sync to Qdrant (using vector service)
    """

    def __init__(self, mcp_server=None):
        """Initialize sync service

        Args:
            mcp_server: MCP Server instance (will be set via set_mcp_server if not provided)
        """
        # Import services
        from services.tool_service import ToolService
        from services.prompt_service import PromptService
        from services.resource_service import ResourceService
        from services.vector_service import VectorRepository
        from tools.services.intelligence_service.language.embedding_generator import EmbeddingGenerator

        self.mcp_server = mcp_server
        self.tool_service = ToolService()
        self.prompt_service = PromptService()
        self.resource_service = ResourceService()
        self.vector_repo = VectorRepository()
        self.embedding_gen = EmbeddingGenerator()

        logger.info("SyncService initialized")

    def set_mcp_server(self, mcp_server):
        """Set MCP Server instance after initialization"""
        self.mcp_server = mcp_server
        logger.info("MCP Server instance set")

    async def initialize(self):
        """Initialize sync service (ensure Qdrant collection exists)"""
        try:
            await self.vector_repo.ensure_collection()
            logger.info("SyncService ready")
        except Exception as e:
            logger.error(f"Failed to initialize SyncService: {e}")
            raise

    async def sync_all(self) -> Dict[str, Any]:
        """
        Sync all tools, prompts, and resources

        Returns:
            Sync results summary
        """
        logger.info("Starting full sync...")

        results = {
            'tools': await self.sync_tools(),
            'prompts': await self.sync_prompts(),
            'resources': await self.sync_resources()
        }

        # Summary
        total_synced = sum(r['synced'] for r in results.values())
        total_failed = sum(r['failed'] for r in results.values())

        logger.info(f"Sync completed: {total_synced} synced, {total_failed} failed")

        return {
            'success': True,
            'total_synced': total_synced,
            'total_failed': total_failed,
            'details': results
        }

    async def sync_tools(self) -> Dict[str, Any]:
        """
        Sync tools from MCP Server API to database

        Returns:
            Sync results
        """
        logger.info("Syncing tools from MCP Server...")

        if not self.mcp_server:
            logger.error("MCP Server not set, cannot sync tools")
            return {
                'total': 0,
                'synced': 0,
                'failed': 0,
                'errors': ['MCP Server not initialized']
            }

        try:
            # 1. Get tools from MCP Server API
            mcp_tools = await self.mcp_server.list_tools()
            logger.info(f"Retrieved {len(mcp_tools)} tools from MCP Server")

            synced = 0
            failed = 0
            errors = []

            # 2. Sync each tool
            for tool in mcp_tools:
                try:
                    # Convert MCP tool format to our format
                    tool_info = {
                        'name': tool.name,
                        'description': tool.description or '',
                        'input_schema': tool.inputSchema if hasattr(tool, 'inputSchema') else {},
                        'category': 'general'  # MCP tools don't have category, use default
                    }
                    await self._sync_single_tool(tool.name, tool_info)
                    synced += 1
                except Exception as e:
                    logger.error(f"Failed to sync tool {tool.name}: {e}")
                    failed += 1
                    errors.append({'tool': tool.name, 'error': str(e)})

            return {
                'total': len(mcp_tools),
                'synced': synced,
                'failed': failed,
                'errors': errors
            }

        except Exception as e:
            logger.error(f"Tools sync failed: {e}")
            return {
                'total': 0,
                'synced': 0,
                'failed': 0,
                'errors': [str(e)]
            }

    async def _sync_single_tool(self, tool_name: str, tool_info: Dict[str, Any]):
        """
        Sync a single tool to PostgreSQL and Qdrant

        增量同步逻辑：
        1. 检查工具是否存在
        2. 如果存在，比较 description 是否变化
        3. 只有在变化时才重新生成 embedding
        """
        # 1. Check if exists
        existing_tool = await self.tool_service.get_tool(tool_name)

        # 2. Prepare tool data
        tool_data = {
            'name': tool_name,
            'description': tool_info.get('description', ''),
            'category': tool_info.get('category', 'general'),
            'input_schema': tool_info.get('input_schema', {}),
            'metadata': {
                'module_path': tool_info.get('module_path', ''),
                'file_path': tool_info.get('file_path', '')
            },
            'is_active': True
        }

        # 3. Update or create tool in PostgreSQL
        if existing_tool:
            # 更新 PostgreSQL
            db_record = await self.tool_service.update_tool(tool_name, tool_data)
            logger.info(f"Updated tool '{tool_name}' in PostgreSQL")
        else:
            # 新工具
            db_record = await self.tool_service.register_tool(tool_data)
            logger.info(f"Registered new tool '{tool_name}' in PostgreSQL")

        # 4. Always generate embedding and sync to Qdrant
        # (Embedding generation is fast, no need to optimize by skipping)
        # Build search-friendly text
        search_text = self._build_tool_search_text(tool_data)

        # Generate embedding
        embedding = await self.embedding_gen.embed_single(search_text)

        # Upsert to Qdrant (use db_id as Qdrant point ID)
        success = await self.vector_repo.upsert_vector(
            item_id=int(db_record['id']),  # Convert to int
            item_type='tool',
            name=tool_name,
            description=tool_data['description'],
            embedding=embedding,
            db_id=db_record['id'],
            is_active=True,
            metadata={
                'category': tool_data.get('category'),
                'has_schema': bool(tool_data.get('input_schema'))
            }
        )

        if success:
            logger.info(f"✅ Synced tool to Qdrant: {tool_name}")
        else:
            raise Exception(f"Failed to upsert to Qdrant: {tool_name}")

    def _build_tool_search_text(self, tool_data: Dict[str, Any]) -> str:
        """
        Build search-friendly text for embedding

        Strategy: Keep it simple - just use description for natural semantic matching
        """
        # Only use description - this matches how users naturally search
        description = tool_data.get('description', '')

        # If description is empty, fall back to name
        if not description:
            return tool_data.get('name', '')

        return description

    async def sync_prompts(self) -> Dict[str, Any]:
        """Sync prompts from MCP Server API to database"""
        logger.info("Syncing prompts from MCP Server...")

        if not self.mcp_server:
            logger.error("MCP Server not set, cannot sync prompts")
            return {
                'total': 0,
                'synced': 0,
                'failed': 0,
                'errors': ['MCP Server not initialized']
            }

        try:
            # 1. Get prompts from MCP Server API
            mcp_prompts = await self.mcp_server.list_prompts()
            logger.info(f"Retrieved {len(mcp_prompts)} prompts from MCP Server")

            synced = 0
            failed = 0
            errors = []

            for prompt in mcp_prompts:
                try:
                    # Convert MCP prompt format to our format
                    prompt_info = {
                        'name': prompt.name,
                        'description': prompt.description or '',
                        'arguments': prompt.arguments if hasattr(prompt, 'arguments') else [],
                        'template': prompt.description or f'Prompt: {prompt.name}'  # Use description as template
                    }
                    await self._sync_single_prompt(prompt.name, prompt_info)
                    synced += 1
                except Exception as e:
                    logger.error(f"Failed to sync prompt {prompt.name}: {e}")
                    failed += 1
                    errors.append({'prompt': prompt.name, 'error': str(e)})

            return {
                'total': len(mcp_prompts),
                'synced': synced,
                'failed': failed,
                'errors': errors
            }

        except Exception as e:
            logger.error(f"Prompts sync failed: {e}")
            return {
                'total': 0,
                'synced': 0,
                'failed': 0,
                'errors': [str(e)]
            }

    async def _sync_single_prompt(self, prompt_name: str, prompt_info: Dict[str, Any]):
        """Sync a single prompt (增量同步)"""
        # Check if exists
        existing_prompt = await self.prompt_service.get_prompt(prompt_name)

        # Prepare data
        prompt_data = {
            'name': prompt_name,
            'content': prompt_info.get('template', ''),
            'description': prompt_info.get('description', ''),
            'arguments': prompt_info.get('arguments', []),
            'metadata': {
                'file_path': prompt_info.get('file_path', '')
            },
            'is_active': True
        }

        # Update or create in PostgreSQL
        if existing_prompt:
            db_record = await self.prompt_service.update_prompt(prompt_name, prompt_data)
            logger.info(f"Updated prompt '{prompt_name}' in PostgreSQL")
        else:
            db_record = await self.prompt_service.register_prompt(prompt_data)
            logger.info(f"Registered new prompt '{prompt_name}' in PostgreSQL")

        # Always generate embedding and sync to Qdrant
        search_text = self._build_prompt_search_text(prompt_data)
        embedding = await self.embedding_gen.embed_single(search_text)

        success = await self.vector_repo.upsert_vector(
            item_id=int(db_record['id']),  # Convert to int
            item_type='prompt',
            name=prompt_name,
            description=prompt_data['description'],
            embedding=embedding,
            db_id=db_record['id'],
            is_active=True
        )

        if success:
            logger.info(f"✅ Synced prompt to Qdrant: {prompt_name}")
        else:
            raise Exception(f"Failed to upsert to Qdrant: {prompt_name}")

    def _build_prompt_search_text(self, prompt_data: Dict[str, Any]) -> str:
        """Build search-friendly text for prompt - just use description"""
        description = prompt_data.get('description', '')

        # Fall back to name if no description
        if not description:
            return prompt_data.get('name', '')

        return description

    async def sync_resources(self) -> Dict[str, Any]:
        """Sync resources from MCP Server API to database"""
        logger.info("Syncing resources from MCP Server...")

        if not self.mcp_server:
            logger.error("MCP Server not set, cannot sync resources")
            return {
                'total': 0,
                'synced': 0,
                'failed': 0,
                'errors': ['MCP Server not initialized']
            }

        try:
            # 1. Get resources from MCP Server API
            mcp_resources = await self.mcp_server.list_resources()
            logger.info(f"Retrieved {len(mcp_resources)} resources from MCP Server")

            synced = 0
            failed = 0
            errors = []

            for resource in mcp_resources:
                try:
                    # Convert MCP resource format to our format
                    # Important: Convert AnyUrl to string!
                    resource_uri = str(resource.uri)
                    resource_info = {
                        'uri': resource_uri,
                        'name': resource.name or resource_uri.split('://')[-1],
                        'description': resource.description or '',
                        'mime_type': resource.mimeType if hasattr(resource, 'mimeType') else 'text/plain',
                        'type': 'resource'  # Default type
                    }
                    await self._sync_single_resource(resource_uri, resource_info)
                    synced += 1
                except Exception as e:
                    logger.error(f"Failed to sync resource {resource.uri}: {e}")
                    failed += 1
                    errors.append({'resource': resource.uri, 'error': str(e)})

            return {
                'total': len(mcp_resources),
                'synced': synced,
                'failed': failed,
                'errors': errors
            }

        except Exception as e:
            logger.error(f"Resources sync failed: {e}")
            return {
                'total': 0,
                'synced': 0,
                'failed': 0,
                'errors': [str(e)]
            }

    async def _sync_single_resource(self, resource_uri: str, resource_info: Dict[str, Any]):
        """Sync a single resource (增量同步)"""
        # Check if exists
        existing_resource = await self.resource_service.get_resource(resource_uri)

        # Prepare data
        resource_data = {
            'uri': resource_uri,
            'name': resource_info.get('name', ''),
            'description': resource_info.get('description', ''),
            'resource_type': resource_info.get('type', 'unknown'),
            'mime_type': resource_info.get('mime_type', ''),
            'metadata': {
                'file_path': resource_info.get('file_path', '')
            },
            'is_active': True,
            'is_public': True  # Default to public
        }

        # Update or create in PostgreSQL
        if existing_resource:
            db_record = await self.resource_service.update_resource(resource_uri, resource_data)
            logger.info(f"Updated resource '{resource_uri}' in PostgreSQL")
        else:
            db_record = await self.resource_service.register_resource(resource_data)
            logger.info(f"Registered new resource '{resource_uri}' in PostgreSQL")

        # Always generate embedding and sync to Qdrant
        search_text = self._build_resource_search_text(resource_data)
        embedding = await self.embedding_gen.embed_single(search_text)

        success = await self.vector_repo.upsert_vector(
            item_id=int(db_record['id']),  # Convert to int
            item_type='resource',
            name=resource_data['name'],
            description=resource_data['description'],
            embedding=embedding,
            db_id=db_record['id'],
            is_active=True,
            metadata={
                'resource_type': resource_data.get('resource_type'),
                'uri': resource_uri
            }
        )

        if success:
            logger.info(f"✅ Synced resource to Qdrant: {resource_uri}")
        else:
            raise Exception(f"Failed to upsert to Qdrant: {resource_uri}")

    def _build_resource_search_text(self, resource_data: Dict[str, Any]) -> str:
        """Build search-friendly text for resource - just use description"""
        description = resource_data.get('description', '')

        # Fall back to name if no description
        if not description:
            name = resource_data.get('name', '')
            return name if name else resource_data.get('uri', '')

        return description
