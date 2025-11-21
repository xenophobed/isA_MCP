"""
Sync Service - Synchronize tools/prompts/resources from MCP Server to database

Architecture:
    MCP Server API (list_tools/prompts/resources)
        → PostgreSQL (tool_service/prompt_service/resource_service)
        → Generate embeddings (BATCH MODE via ISA Model)
        → Qdrant (vector_service)
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SyncService:
    """
    Synchronization service with batch embedding support via ISA Model

    Responsibilities:
    1. Get tools/prompts/resources from MCP Server API
    2. Sync to PostgreSQL (using tool/prompt/resource services)
    3. Generate embeddings in BATCH via ISA Model (avoid rate limits!)
    4. Sync to Qdrant (using vector service)
    """

    def __init__(self, mcp_server=None):
        """Initialize sync service

        Args:
            mcp_server: MCP Server instance (will be set via set_mcp_server if not provided)
        """
        # Import services
        from isa_model.inference_client import AsyncISAModel

        from services.prompt_service import PromptService
        from services.resource_service import ResourceService
        from services.tool_service import ToolService
        from services.vector_service import VectorRepository

        self.mcp_server = mcp_server
        self.tool_service = ToolService()
        self.prompt_service = PromptService()
        self.resource_service = ResourceService()
        self.vector_repo = VectorRepository()

        # Initialize ISA Model client for embeddings
        isa_api_url = os.getenv(
            "ISA_API_URL", "http://model.isa-cloud-staging.svc.cluster.local:8082"
        )
        self.isa_model = AsyncISAModel(
            base_url=isa_api_url,
            api_key="dummy",  # ISA Model doesn't require API key
        )
        self.embedding_model = "text-embedding-3-small"

        logger.info("SyncService initialized with BATCH embedding via ISA Model")
        logger.info(f"  ISA Model URL: {isa_api_url}")

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
        Sync all tools, prompts, and resources with automatic cleanup

        Returns:
            Sync results summary
        """
        logger.info("Starting full sync with batch embeddings...")

        results = {
            "tools": await self.sync_tools(),
            "prompts": await self.sync_prompts(),
            "resources": await self.sync_resources(),
        }

        # Summary
        total_synced = sum(r["synced"] for r in results.values())
        total_skipped = sum(r.get("skipped", 0) for r in results.values())
        total_failed = sum(r["failed"] for r in results.values())
        total_deleted = sum(r.get("deleted", 0) for r in results.values())

        logger.info(
            f"🎯 Batch sync completed: {total_synced} updated, {total_skipped} skipped (no changes), {total_failed} failed, {total_deleted} orphaned entries deleted"
        )

        return {
            "success": True,
            "total_synced": total_synced,
            "total_skipped": total_skipped,
            "total_failed": total_failed,
            "total_deleted": total_deleted,
            "details": results,
        }

    async def sync_tools(self) -> Dict[str, Any]:
        """
        Sync tools from MCP Server API to database with BATCH embeddings

        Returns:
            Sync results
        """
        logger.info("Syncing tools from MCP Server...")

        if not self.mcp_server:
            logger.error("MCP Server not set, cannot sync tools")
            return {
                "total": 0,
                "synced": 0,
                "failed": 0,
                "deleted": 0,
                "errors": ["MCP Server not initialized"],
            }

        try:
            # 1. Get tools from MCP Server API
            mcp_tools = await self.mcp_server.list_tools()
            logger.info(f"Retrieved {len(mcp_tools)} tools from MCP Server")

            # 2. Get existing tools from Qdrant
            qdrant_tools = await self.vector_repo.get_all_by_type("tool")
            logger.info(f"Found {len(qdrant_tools)} existing tools in Qdrant")

            # Build a dict for quick lookup: name -> qdrant_tool
            qdrant_tools_dict = {tool["name"]: tool for tool in qdrant_tools}

            # 3. Find orphaned tools (exist in Qdrant but not in MCP)
            mcp_tool_names = {tool.name for tool in mcp_tools}
            orphaned_ids = []
            orphaned_names = []

            for qdrant_tool in qdrant_tools:
                if qdrant_tool["name"] not in mcp_tool_names:
                    orphaned_ids.append(qdrant_tool["id"])
                    orphaned_names.append(qdrant_tool["name"])

            # 4. Delete orphaned tools from Qdrant
            deleted = 0
            if orphaned_ids:
                logger.info(
                    f"Found {len(orphaned_ids)} orphaned tools to clean up: {orphaned_names}"
                )
                deleted = await self.vector_repo.delete_multiple_vectors(orphaned_ids)
                logger.info(f"Deleted {deleted} orphaned tools from Qdrant")

            # 5. Prepare tools for sync (check which ones need embedding updates)
            items_to_embed = []  # List of (db_record, tool_data, search_text)
            skipped = 0
            failed = 0
            errors = []

            for tool in mcp_tools:
                try:
                    # Convert MCP tool format to our format
                    tool_info = {
                        "name": tool.name,
                        "description": tool.description or "",
                        "input_schema": tool.inputSchema
                        if hasattr(tool, "inputSchema")
                        else {},
                        "category": "general",
                    }

                    existing_qdrant = qdrant_tools_dict.get(tool.name)
                    (
                        db_record,
                        tool_data,
                        needs_update,
                    ) = await self._prepare_tool_for_sync(
                        tool.name, tool_info, existing_qdrant
                    )

                    if needs_update:
                        search_text = self._build_tool_search_text(tool_data)
                        items_to_embed.append((db_record, tool_data, search_text))
                    else:
                        skipped += 1

                except Exception as e:
                    logger.error(f"Failed to prepare tool {tool.name}: {e}")
                    failed += 1
                    errors.append({"tool": tool.name, "error": str(e)})

            # 6. Generate embeddings concurrently via ISA Model
            synced = 0
            if items_to_embed:
                logger.info(
                    f"Generating embeddings for {len(items_to_embed)} tools CONCURRENTLY via ISA Model..."
                )
                search_texts = [item[2] for item in items_to_embed]

                try:
                    import asyncio

                    # Concurrent single embedding calls (ISA Model doesn't support batch input)
                    async def generate_single_embedding(text):
                        response = await self.isa_model.embeddings.create(
                            input=text, model=self.embedding_model
                        )
                        return response.data[0].embedding

                    embeddings = await asyncio.gather(
                        *[generate_single_embedding(text) for text in search_texts]
                    )
                    logger.info(
                        f"✅ Generated {len(embeddings)} embeddings concurrently via ISA Model"
                    )

                    # 7. Upsert to Qdrant
                    logger.info(
                        f"🔄 Starting Qdrant upsert for {len(items_to_embed)} tools..."
                    )
                    for idx, ((db_record, tool_data, _), embedding) in enumerate(
                        zip(items_to_embed, embeddings)
                    ):
                        try:
                            tool_id = int(db_record["id"])
                            tool_name = tool_data["name"]
                            logger.debug(
                                f"  [{idx + 1}/{len(items_to_embed)}] Upserting tool '{tool_name}' (ID: {tool_id})..."
                            )

                            success = await self.vector_repo.upsert_vector(
                                item_id=tool_id,
                                item_type="tool",
                                name=tool_name,
                                description=tool_data["description"],
                                embedding=embedding,
                                db_id=db_record["id"],
                                is_active=True,
                                metadata={
                                    "category": tool_data.get("category"),
                                    "has_schema": bool(tool_data.get("input_schema")),
                                },
                            )
                            if success:
                                synced += 1
                                logger.debug(
                                    f"  ✅ [{idx + 1}/{len(items_to_embed)}] Successfully upserted '{tool_name}' (ID: {tool_id})"
                                )
                            else:
                                logger.error(
                                    f"  ❌ [{idx + 1}/{len(items_to_embed)}] Upsert returned False for '{tool_name}' (ID: {tool_id})"
                                )
                                raise Exception(
                                    f"Upsert returned False for tool ID {tool_id}"
                                )
                        except Exception as e:
                            logger.error(
                                f"  ❌ [{idx + 1}/{len(items_to_embed)}] Failed to sync tool '{tool_name}' (ID: {tool_id}) to Qdrant: {e}"
                            )
                            import traceback

                            logger.error(f"  Traceback: {traceback.format_exc()}")
                            failed += 1
                            errors.append(
                                {
                                    "tool": tool_data["name"],
                                    "id": tool_id,
                                    "error": str(e),
                                }
                            )

                except Exception as e:
                    logger.error(f"Batch embedding failed: {e}")
                    failed += len(items_to_embed)
                    errors.append({"error": f"Batch embedding failed: {str(e)}"})

            logger.info(
                f"Tools sync: {synced} updated, {skipped} skipped (no changes), {failed} failed"
            )

            return {
                "total": len(mcp_tools),
                "synced": synced,
                "skipped": skipped,
                "failed": failed,
                "deleted": deleted,
                "orphaned_tools": orphaned_names,
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"Tools sync failed: {e}")
            return {
                "total": 0,
                "synced": 0,
                "failed": 0,
                "deleted": 0,
                "errors": [str(e)],
            }

    async def _prepare_tool_for_sync(
        self,
        tool_name: str,
        tool_info: Dict[str, Any],
        existing_qdrant: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any], bool]:
        """
        Prepare tool for sync (PostgreSQL update + change detection)

        Returns:
            (db_record, tool_data, needs_embedding_update)
        """
        # Check if exists in PostgreSQL
        existing_tool = await self.tool_service.get_tool(tool_name)

        # Prepare tool data
        tool_data = {
            "name": tool_name,
            "description": tool_info.get("description", ""),
            "category": tool_info.get("category", "general"),
            "input_schema": tool_info.get("input_schema", {}),
            "metadata": {
                "module_path": tool_info.get("module_path", ""),
                "file_path": tool_info.get("file_path", ""),
            },
            "is_active": True,
        }

        # Update or create in PostgreSQL FIRST
        if existing_tool:
            db_record = await self.tool_service.update_tool(tool_name, tool_data)
            logger.debug(f"Updated tool '{tool_name}' in PostgreSQL")
        else:
            db_record = await self.tool_service.register_tool(tool_data)
            logger.info(f"Registered new tool '{tool_name}' in PostgreSQL")

        # Check if embedding needs update
        # CRITICAL: Must check BOTH description AND db_id to avoid stale data
        needs_update = True
        if existing_qdrant and existing_tool:
            # Both exist: check if content AND db_id match
            if (existing_qdrant.get("description") == tool_data["description"] and
                existing_qdrant.get("db_id") == db_record["id"]):
                needs_update = False
                logger.debug(f"⏭️  Tool '{tool_name}' unchanged, skipping embedding")
            elif existing_qdrant.get("db_id") != db_record["id"]:
                logger.warning(f"🔄 Tool '{tool_name}' PostgreSQL ID changed: {existing_qdrant.get('db_id')} → {db_record['id']}, forcing resync")
        elif existing_qdrant and not existing_tool:
            # Qdrant exists but PostgreSQL was empty (database reset case)
            logger.warning(f"🔄 Tool '{tool_name}' found in Qdrant but PostgreSQL was empty, forcing resync")

        return db_record, tool_data, needs_update

    def _build_tool_search_text(self, tool_data: Dict[str, Any]) -> str:
        """Build search-friendly text for embedding"""
        description = tool_data.get("description", "")
        if not description:
            return tool_data.get("name", "")
        return description

    async def sync_prompts(self) -> Dict[str, Any]:
        """Sync prompts from MCP Server API to database with BATCH embeddings"""
        logger.info("Syncing prompts from MCP Server...")

        if not self.mcp_server:
            logger.error("MCP Server not set, cannot sync prompts")
            return {
                "total": 0,
                "synced": 0,
                "failed": 0,
                "deleted": 0,
                "errors": ["MCP Server not initialized"],
            }

        try:
            # 1. Get prompts from MCP Server
            mcp_prompts = await self.mcp_server.list_prompts()
            logger.info(f"Retrieved {len(mcp_prompts)} prompts from MCP Server")

            # 2. Get existing prompts from Qdrant
            qdrant_prompts = await self.vector_repo.get_all_by_type("prompt")
            logger.info(f"Found {len(qdrant_prompts)} existing prompts in Qdrant")

            qdrant_prompts_dict = {prompt["name"]: prompt for prompt in qdrant_prompts}

            # 3. Find orphaned prompts
            mcp_prompt_names = {prompt.name for prompt in mcp_prompts}
            orphaned_ids = []
            orphaned_names = []

            for qdrant_prompt in qdrant_prompts:
                if qdrant_prompt["name"] not in mcp_prompt_names:
                    orphaned_ids.append(qdrant_prompt["id"])
                    orphaned_names.append(qdrant_prompt["name"])

            # 4. Delete orphaned prompts
            deleted = 0
            if orphaned_ids:
                logger.info(f"Found {len(orphaned_ids)} orphaned prompts to clean up")
                deleted = await self.vector_repo.delete_multiple_vectors(orphaned_ids)

            # 5. Prepare prompts for batch embedding
            items_to_embed = []
            skipped = 0
            failed = 0
            errors = []

            for prompt in mcp_prompts:
                try:
                    # Convert arguments
                    arguments = []
                    if hasattr(prompt, "arguments") and prompt.arguments:
                        for arg in prompt.arguments:
                            arguments.append(
                                {
                                    "name": arg.name,
                                    "description": arg.description or "",
                                    "required": arg.required
                                    if hasattr(arg, "required")
                                    else False,
                                }
                            )

                    prompt_info = {
                        "name": prompt.name,
                        "description": prompt.description or "",
                        "arguments": arguments,
                        "template": prompt.description or f"Prompt: {prompt.name}",
                    }

                    existing_qdrant = qdrant_prompts_dict.get(prompt.name)
                    (
                        db_record,
                        prompt_data,
                        needs_update,
                    ) = await self._prepare_prompt_for_sync(
                        prompt.name, prompt_info, existing_qdrant
                    )

                    if needs_update:
                        search_text = self._build_prompt_search_text(prompt_data)
                        items_to_embed.append((db_record, prompt_data, search_text))
                    else:
                        skipped += 1

                except Exception as e:
                    logger.error(f"Failed to prepare prompt {prompt.name}: {e}")
                    failed += 1
                    errors.append({"prompt": prompt.name, "error": str(e)})

            # 6. Generate embeddings concurrently via ISA Model
            synced = 0
            if items_to_embed:
                logger.info(
                    f"Generating embeddings for {len(items_to_embed)} prompts CONCURRENTLY via ISA Model..."
                )
                search_texts = [item[2] for item in items_to_embed]

                try:
                    import asyncio

                    async def generate_single_embedding(text):
                        response = await self.isa_model.embeddings.create(
                            input=text, model=self.embedding_model
                        )
                        return response.data[0].embedding

                    embeddings = await asyncio.gather(
                        *[generate_single_embedding(text) for text in search_texts]
                    )
                    logger.info(
                        f"✅ Generated {len(embeddings)} embeddings concurrently via ISA Model"
                    )

                    # 7. Upsert to Qdrant
                    for (db_record, prompt_data, _), embedding in zip(
                        items_to_embed, embeddings
                    ):
                        try:
                            success = await self.vector_repo.upsert_vector(
                                item_id=int(db_record["id"]),
                                item_type="prompt",
                                name=prompt_data["name"],
                                description=prompt_data["description"],
                                embedding=embedding,
                                db_id=db_record["id"],
                                is_active=True,
                            )
                            if success:
                                synced += 1
                        except Exception as e:
                            logger.error(
                                f"Failed to sync prompt {prompt_data['name']}: {e}"
                            )
                            failed += 1
                            errors.append(
                                {"prompt": prompt_data["name"], "error": str(e)}
                            )

                except Exception as e:
                    logger.error(f"Batch embedding failed: {e}")
                    failed += len(items_to_embed)
                    errors.append({"error": f"Batch embedding failed: {str(e)}"})

            logger.info(
                f"Prompts sync: {synced} updated, {skipped} skipped, {failed} failed"
            )

            return {
                "total": len(mcp_prompts),
                "synced": synced,
                "skipped": skipped,
                "failed": failed,
                "deleted": deleted,
                "orphaned_prompts": orphaned_names,
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"Prompts sync failed: {e}")
            return {
                "total": 0,
                "synced": 0,
                "failed": 0,
                "deleted": 0,
                "errors": [str(e)],
            }

    async def _prepare_prompt_for_sync(
        self,
        prompt_name: str,
        prompt_info: Dict[str, Any],
        existing_qdrant: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any], bool]:
        """Prepare prompt for sync"""
        existing_prompt = await self.prompt_service.get_prompt(prompt_name)

        prompt_data = {
            "name": prompt_name,
            "content": prompt_info.get("template", ""),
            "description": prompt_info.get("description", ""),
            "arguments": prompt_info.get("arguments", []),
            "metadata": {"file_path": prompt_info.get("file_path", "")},
            "is_active": True,
        }

        # Update or create in PostgreSQL FIRST
        if existing_prompt:
            db_record = await self.prompt_service.update_prompt(
                prompt_name, prompt_data
            )
        else:
            db_record = await self.prompt_service.register_prompt(prompt_data)

        # Check if embedding needs update (check both description AND db_id)
        needs_update = True
        if existing_qdrant and existing_prompt:
            if (existing_qdrant.get("description") == prompt_data["description"] and
                existing_qdrant.get("db_id") == db_record["id"]):
                needs_update = False
            elif existing_qdrant.get("db_id") != db_record["id"]:
                logger.warning(f"🔄 Prompt '{prompt_name}' PostgreSQL ID changed, forcing resync")
        elif existing_qdrant and not existing_prompt:
            logger.warning(f"🔄 Prompt '{prompt_name}' found in Qdrant but PostgreSQL was empty, forcing resync")

        return db_record, prompt_data, needs_update

    def _build_prompt_search_text(self, prompt_data: Dict[str, Any]) -> str:
        """Build search text for prompt"""
        description = prompt_data.get("description", "")
        if not description:
            return prompt_data.get("name", "")
        return description

    async def sync_resources(self) -> Dict[str, Any]:
        """Sync resources from MCP Server API with BATCH embeddings"""
        logger.info("Syncing resources from MCP Server...")

        if not self.mcp_server:
            logger.error("MCP Server not set, cannot sync resources")
            return {
                "total": 0,
                "synced": 0,
                "failed": 0,
                "deleted": 0,
                "errors": ["MCP Server not initialized"],
            }

        try:
            # 1. Get resources from MCP Server
            mcp_resources = await self.mcp_server.list_resources()
            logger.info(f"Retrieved {len(mcp_resources)} resources from MCP Server")

            # 2. Get existing resources from Qdrant
            qdrant_resources = await self.vector_repo.get_all_by_type("resource")
            logger.info(f"Found {len(qdrant_resources)} existing resources in Qdrant")

            qdrant_resources_dict = {
                resource["name"]: resource for resource in qdrant_resources
            }

            # 3. Find orphaned resources
            mcp_resource_names = {
                resource.name or str(resource.uri).split("://")[-1]
                for resource in mcp_resources
            }
            orphaned_ids = []
            orphaned_names = []

            for qdrant_resource in qdrant_resources:
                if qdrant_resource["name"] not in mcp_resource_names:
                    orphaned_ids.append(qdrant_resource["id"])
                    orphaned_names.append(qdrant_resource["name"])

            # 4. Delete orphaned resources
            deleted = 0
            if orphaned_ids:
                logger.info(f"Found {len(orphaned_ids)} orphaned resources to clean up")
                deleted = await self.vector_repo.delete_multiple_vectors(orphaned_ids)

            # 5. Prepare resources for batch embedding
            items_to_embed = []
            skipped = 0
            failed = 0
            errors = []

            for resource in mcp_resources:
                try:
                    resource_uri = str(resource.uri)
                    resource_name = resource.name or resource_uri.split("://")[-1]
                    resource_info = {
                        "uri": resource_uri,
                        "name": resource_name,
                        "description": resource.description or "",
                        "mime_type": resource.mimeType
                        if hasattr(resource, "mimeType")
                        else "text/plain",
                        "type": "resource",
                    }

                    existing_qdrant = qdrant_resources_dict.get(resource_name)
                    (
                        db_record,
                        resource_data,
                        needs_update,
                    ) = await self._prepare_resource_for_sync(
                        resource_uri, resource_info, existing_qdrant
                    )

                    if needs_update:
                        search_text = self._build_resource_search_text(resource_data)
                        items_to_embed.append((db_record, resource_data, search_text))
                    else:
                        skipped += 1

                except Exception as e:
                    logger.error(f"Failed to prepare resource {resource.uri}: {e}")
                    failed += 1
                    errors.append({"resource": str(resource.uri), "error": str(e)})

            # 6. Generate embeddings concurrently via ISA Model
            synced = 0
            if items_to_embed:
                logger.info(
                    f"Generating embeddings for {len(items_to_embed)} resources CONCURRENTLY via ISA Model..."
                )
                search_texts = [item[2] for item in items_to_embed]

                try:
                    import asyncio

                    async def generate_single_embedding(text):
                        response = await self.isa_model.embeddings.create(
                            input=text, model=self.embedding_model
                        )
                        return response.data[0].embedding

                    embeddings = await asyncio.gather(
                        *[generate_single_embedding(text) for text in search_texts]
                    )
                    logger.info(
                        f"✅ Generated {len(embeddings)} embeddings concurrently via ISA Model"
                    )

                    # 7. Upsert to Qdrant
                    for (db_record, resource_data, _), embedding in zip(
                        items_to_embed, embeddings
                    ):
                        try:
                            success = await self.vector_repo.upsert_vector(
                                item_id=int(db_record["id"]),
                                item_type="resource",
                                name=resource_data["name"],
                                description=resource_data["description"],
                                embedding=embedding,
                                db_id=db_record["id"],
                                is_active=True,
                                metadata={
                                    "resource_type": resource_data.get("resource_type"),
                                    "uri": resource_data.get("uri"),
                                },
                            )
                            if success:
                                synced += 1
                        except Exception as e:
                            logger.error(
                                f"Failed to sync resource {resource_data['name']}: {e}"
                            )
                            failed += 1
                            errors.append(
                                {"resource": resource_data["name"], "error": str(e)}
                            )

                except Exception as e:
                    logger.error(f"Batch embedding failed: {e}")
                    failed += len(items_to_embed)
                    errors.append({"error": f"Batch embedding failed: {str(e)}"})

            logger.info(
                f"Resources sync: {synced} updated, {skipped} skipped, {failed} failed"
            )

            return {
                "total": len(mcp_resources),
                "synced": synced,
                "skipped": skipped,
                "failed": failed,
                "deleted": deleted,
                "orphaned_resources": orphaned_names,
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"Resources sync failed: {e}")
            return {
                "total": 0,
                "synced": 0,
                "failed": 0,
                "deleted": 0,
                "errors": [str(e)],
            }

    async def _prepare_resource_for_sync(
        self,
        resource_uri: str,
        resource_info: Dict[str, Any],
        existing_qdrant: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any], bool]:
        """Prepare resource for sync"""
        existing_resource = await self.resource_service.get_resource(resource_uri)

        resource_data = {
            "uri": resource_uri,
            "name": resource_info.get("name", ""),
            "description": resource_info.get("description", ""),
            "resource_type": resource_info.get("type", "unknown"),
            "mime_type": resource_info.get("mime_type", ""),
            "metadata": {"file_path": resource_info.get("file_path", "")},
            "is_active": True,
            "is_public": True,
        }

        # Update or create in PostgreSQL FIRST
        if existing_resource:
            db_record = await self.resource_service.update_resource(
                resource_uri, resource_data
            )
        else:
            db_record = await self.resource_service.register_resource(resource_data)

        # Check if embedding needs update (check both description AND db_id)
        needs_update = True
        if existing_qdrant and existing_resource:
            if (existing_qdrant.get("description") == resource_data["description"] and
                existing_qdrant.get("db_id") == db_record["id"]):
                needs_update = False
            elif existing_qdrant.get("db_id") != db_record["id"]:
                logger.warning(f"🔄 Resource '{resource_uri}' PostgreSQL ID changed, forcing resync")
        elif existing_qdrant and not existing_resource:
            logger.warning(f"🔄 Resource '{resource_uri}' found in Qdrant but PostgreSQL was empty, forcing resync")

        return db_record, resource_data, needs_update

    def _build_resource_search_text(self, resource_data: Dict[str, Any]) -> str:
        """Build search text for resource"""
        description = resource_data.get("description", "")
        if not description:
            name = resource_data.get("name", "")
            return name if name else resource_data.get("uri", "")
        return description
