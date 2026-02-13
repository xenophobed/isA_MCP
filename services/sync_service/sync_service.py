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
import uuid
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# DEFAULT TOOLS - Meta-tools that are always available in agent context
# ==============================================================================
# These tools are marked as is_default=True in PostgreSQL.
# All other tools are accessed via discover → execute pattern.
# SDK can add additional tools via allowed_tools option.
# ==============================================================================
DEFAULT_TOOL_NAMES = frozenset(
    [
        "discover",
        "get_tool_schema",
        "execute",
        "list_skills",
        "list_prompts",
        "get_prompt",
        "list_resources",
        "read_resource",
    ]
)


def _normalize_db_id(value: Any) -> Optional[int]:
    """Normalize db_id to int for comparison (handles Qdrant float, PostgreSQL int)."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _build_qdrant_dict_and_find_duplicates(
    qdrant_items: List[Dict[str, Any]],
) -> Tuple[Dict[str, Dict[str, Any]], List[int], set]:
    """
    Build name->item dict and identify duplicates for cleanup.

    Returns:
        (items_dict, duplicate_ids_to_delete, names_with_duplicates)
    """
    items_dict = {}
    duplicate_ids_to_delete = []
    names_with_duplicates = set()

    for item in qdrant_items:
        name = item["name"]
        if name in items_dict:
            # Duplicate found - mark both for deletion
            names_with_duplicates.add(name)
            duplicate_ids_to_delete.append(item["id"])
            if items_dict[name]["id"] not in duplicate_ids_to_delete:
                duplicate_ids_to_delete.append(items_dict[name]["id"])
            del items_dict[name]
        elif name not in names_with_duplicates:
            items_dict[name] = item

    return items_dict, duplicate_ids_to_delete, names_with_duplicates


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
        from services.skill_service import SkillService

        self.mcp_server = mcp_server
        self.tool_service = ToolService()
        self.prompt_service = PromptService()
        self.resource_service = ResourceService()
        self.vector_repo = VectorRepository()
        self.skill_service = SkillService()
        self._skill_collection = "mcp_skills"

        # Initialize ISA Model client for embeddings
        isa_api_url = os.getenv(
            "ISA_API_URL", "http://model.isa-cloud-staging.svc.cluster.local:8082"
        )
        self.isa_model = AsyncISAModel(
            base_url=isa_api_url,
            api_key="dummy",  # ISA Model doesn't require API key
        )
        self.embedding_model = "text-embedding-3-small"

        logger.debug(f"SyncService initialized (ISA Model: {isa_api_url})")

    def set_mcp_server(self, mcp_server):
        """Set MCP Server instance after initialization"""
        self.mcp_server = mcp_server
        logger.debug("MCP Server instance set")

    async def initialize(self):
        """Initialize sync service (ensure Qdrant collection exists)"""
        try:
            await self.vector_repo.ensure_collection()
            logger.debug("SyncService ready")
        except Exception as e:
            logger.error(f"Failed to initialize SyncService: {e}")
            raise

    async def sync_all(self) -> Dict[str, Any]:
        """
        Sync all tools, prompts, resources, and skills with automatic cleanup

        Returns:
            Sync results summary
        """
        logger.info("Starting full sync with batch embeddings...")

        results = {
            "tools": await self.sync_tools(),
            "prompts": await self.sync_prompts(),
            "resources": await self.sync_resources(),
            "skills": await self.sync_skills(),  # BR-004: Batch sync skills to Qdrant
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
        logger.debug("Syncing tools from MCP Server...")

        # Ensure fresh Qdrant connection (fixes "Channel is closed" errors)
        try:
            await self.vector_repo.client.reconnect()
            logger.debug("Reconnected to Qdrant for tools sync")
        except Exception as e:
            logger.warning(f"Failed to reconnect Qdrant client: {e}")

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
            logger.debug(f"Retrieved {len(mcp_tools)} tools from MCP Server")

            # 2. Get existing tools from Qdrant
            qdrant_tools = await self.vector_repo.get_all_by_type("tool")
            logger.debug(f"Found {len(qdrant_tools)} existing tools in Qdrant")

            # Build lookup dict and find duplicates
            qdrant_tools_dict, duplicate_ids, dup_names = _build_qdrant_dict_and_find_duplicates(
                qdrant_tools
            )

            # Delete duplicate entries first
            if duplicate_ids:
                logger.info(
                    f"🧹 Cleaning up {len(duplicate_ids)} duplicate Qdrant entries for {len(dup_names)} tools..."
                )
                await self.vector_repo.delete_multiple_vectors(duplicate_ids)
                logger.info(
                    f"✅ Deleted duplicates, tools with duplicates will be re-synced: {list(dup_names)[:5]}..."
                )

            # 3. Find orphaned tools (exist in Qdrant but not in MCP)
            mcp_tool_names = {tool.name for tool in mcp_tools}
            orphaned_ids = []
            orphaned_names = []

            for qdrant_tool in qdrant_tools_dict.values():  # Use dict values, not original list
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

            # 5. Prepare tools for sync (check which ones need embedding/classification)
            items_to_embed = []  # List of (db_record, tool_data, search_text)
            items_to_classify_only = (
                []
            )  # List of (db_record, tool_data) - need classification but not embedding
            skipped = 0
            failed = 0
            errors = []

            for tool in mcp_tools:
                try:
                    # Convert MCP tool format to our format
                    tool_info = {
                        "name": tool.name,
                        "description": tool.description or "",
                        "input_schema": tool.inputSchema if hasattr(tool, "inputSchema") else {},
                        "category": "general",
                    }

                    existing_qdrant = qdrant_tools_dict.get(tool.name)
                    (
                        db_record,
                        tool_data,
                        needs_embedding,
                        needs_classification,
                    ) = await self._prepare_tool_for_sync(tool.name, tool_info, existing_qdrant)

                    if needs_embedding:
                        # Needs full sync (embed + classify)
                        search_text = self._build_search_text(tool_data)
                        # If db_id changed, we need to delete the old Qdrant entry
                        old_qdrant_id = None
                        if existing_qdrant:
                            qdrant_db_id_int = _normalize_db_id(existing_qdrant.get("db_id"))
                            pg_db_id_int = _normalize_db_id(db_record["id"])
                            if qdrant_db_id_int != pg_db_id_int:
                                old_qdrant_id = existing_qdrant.get("id")
                        items_to_embed.append((db_record, tool_data, search_text, old_qdrant_id))
                    elif needs_classification:
                        # Already embedded, just needs classification
                        items_to_classify_only.append((db_record, tool_data))
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
                    f"Generating embeddings for {len(items_to_embed)} tools via ISA Model BATCH API..."
                )
                search_texts = [item[2] for item in items_to_embed]

                try:
                    # BATCH embedding - single API call with all texts
                    # ISA Model supports Union[str, List[str]] for input parameter
                    response = await self.isa_model.embeddings.create(
                        input=search_texts, model=self.embedding_model  # Pass all texts as batch
                    )
                    # Extract embeddings in order (API returns in same order as input)
                    embeddings = [item.embedding for item in response.data]
                    logger.info(
                        f"✅ Generated {len(embeddings)} embeddings via ISA Model BATCH API"
                    )

                    # 7. Delete old Qdrant entries first (for tools with changed db_id)
                    old_ids_to_delete = [item[3] for item in items_to_embed if item[3] is not None]
                    if old_ids_to_delete:
                        logger.info(
                            f"🗑️ Deleting {len(old_ids_to_delete)} old Qdrant entries before upsert..."
                        )
                        await self.vector_repo.delete_multiple_vectors(old_ids_to_delete)
                        logger.info(f"✅ Deleted {len(old_ids_to_delete)} old entries")

                    # 8. Upsert to Qdrant
                    logger.info(f"🔄 Starting Qdrant upsert for {len(items_to_embed)} tools...")
                    logger.info(f"   items_to_embed count: {len(items_to_embed)}")
                    logger.info(f"   embeddings count: {len(embeddings)}")

                    # Collect tools for classification after upsert
                    tools_to_classify = []

                    for idx, ((db_record, tool_data, _, old_qdrant_id), embedding) in enumerate(
                        zip(items_to_embed, embeddings)
                    ):
                        try:
                            tool_id = int(db_record["id"])
                            tool_name = tool_data["name"]
                            logger.info(
                                f"  [{idx + 1}/{len(items_to_embed)}] Upserting tool '{tool_name}' (ID: {tool_id})..."
                            )

                            success = await self.vector_repo.upsert_vector(
                                item_type="tool",
                                name=tool_name,
                                description=tool_data["description"],
                                embedding=embedding,
                                db_id=db_record["id"],
                                is_active=True,
                                metadata={
                                    "category": tool_data.get("category"),
                                    "has_schema": bool(tool_data.get("input_schema")),
                                    "org_id": db_record.get("org_id"),
                                    "is_global": db_record.get("is_global", True),
                                },
                            )
                            if success:
                                synced += 1
                                logger.info(
                                    f"  ✅ [{idx + 1}/{len(items_to_embed)}] Upserted '{tool_name}' (ID: {tool_id})"
                                )
                                # Add to classification queue
                                tools_to_classify.append(
                                    {
                                        "tool_id": tool_id,
                                        "tool_name": tool_name,
                                        "description": tool_data["description"],
                                    }
                                )
                            else:
                                logger.error(
                                    f"  ❌ [{idx + 1}/{len(items_to_embed)}] Upsert returned False for '{tool_name}' (ID: {tool_id})"
                                )
                                raise Exception(f"Upsert returned False for tool ID {tool_id}")
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

                    # 8. BR-002: Classify tools into skill categories (BATCH)
                    if tools_to_classify:
                        logger.debug(
                            f"Batch classifying {len(tools_to_classify)} newly embedded tools..."
                        )
                        try:
                            batch_results = await self.skill_service.classify_tools_batch(
                                tools_to_classify
                            )
                            classified = sum(1 for r in batch_results if r.get("primary_skill_id"))
                            logger.debug(f"Classified {classified}/{len(tools_to_classify)} tools")
                        except Exception as e:
                            logger.warning(f"Batch classification failed: {e}")

                except Exception as e:
                    logger.error(f"Batch embedding failed: {e}")
                    failed += len(items_to_embed)
                    errors.append({"error": f"Batch embedding failed: {str(e)}"})

            # 9. Classify tools that only need classification (BATCH, no re-embedding)
            classified_only = 0
            if items_to_classify_only:
                logger.debug(f"Batch classifying {len(items_to_classify_only)} existing tools...")
                # Convert to batch format
                tools_for_batch = [
                    {
                        "tool_id": int(db_record["id"]),
                        "tool_name": tool_data["name"],
                        "description": tool_data["description"],
                    }
                    for db_record, tool_data in items_to_classify_only
                ]
                try:
                    batch_results = await self.skill_service.classify_tools_batch(tools_for_batch)
                    classified_only = sum(1 for r in batch_results if r.get("primary_skill_id"))
                    for result in batch_results:
                        if result.get("primary_skill_id"):
                            logger.debug(f"  {result['tool_name']} -> {result['primary_skill_id']}")
                    logger.debug(
                        f"Classified {classified_only}/{len(items_to_classify_only)} existing tools"
                    )
                    # Count unclassified items as skipped (no skills available or classification N/A)
                    unclassified = len(items_to_classify_only) - classified_only
                    if unclassified > 0:
                        skipped += unclassified
                        logger.debug(
                            f"{unclassified} tools skipped (classification N/A - no skills)"
                        )
                except Exception as e:
                    logger.warning(f"Batch classification failed: {e}")
                    # If classification completely fails, count all as skipped (content is already synced)
                    skipped += len(items_to_classify_only)
                    logger.debug(
                        f"{len(items_to_classify_only)} tools skipped (classification unavailable)"
                    )

            logger.info(
                f"Tools sync: {synced} embedded, {classified_only} classified-only, {skipped} skipped, {failed} failed"
            )

            return {
                "total": len(mcp_tools),
                "synced": synced,
                "classified_only": classified_only,
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
                "classified_only": 0,
                "failed": 0,
                "deleted": 0,
                "errors": [str(e)],
            }

    async def _prepare_tool_for_sync(
        self,
        tool_name: str,
        tool_info: Dict[str, Any],
        existing_qdrant: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any], bool, bool]:
        """
        Prepare tool for sync (PostgreSQL update + change detection)

        Returns:
            (db_record, tool_data, needs_embedding, needs_classification)
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
            "is_default": tool_name in DEFAULT_TOOL_NAMES,
        }

        # Update or create in PostgreSQL FIRST
        if existing_tool:
            db_record = await self.tool_service.update_tool(tool_name, tool_data)
            logger.debug(f"Updated tool '{tool_name}' in PostgreSQL")
        else:
            db_record = await self.tool_service.register_tool(tool_data)
            logger.info(f"Registered new tool '{tool_name}' in PostgreSQL")

        # Check if embedding needs update
        # CRITICAL: Must check description, db_id, AND classification status
        needs_embedding = True
        needs_classification = True

        if existing_qdrant and existing_tool:
            # Normalize db_ids for comparison
            qdrant_db_id_int = _normalize_db_id(existing_qdrant.get("db_id"))
            pg_db_id_int = _normalize_db_id(db_record["id"])

            # Check if content AND db_id match
            description_matches = existing_qdrant.get("description") == tool_data["description"]
            db_id_matches = qdrant_db_id_int == pg_db_id_int and qdrant_db_id_int is not None
            content_matches = description_matches and db_id_matches

            # Check if already classified (has primary_skill_id)
            has_classification = bool(existing_qdrant.get("primary_skill_id"))

            if content_matches:
                needs_embedding = False
                if has_classification:
                    needs_classification = False
                    logger.debug(f"⏭️  Tool '{tool_name}' unchanged and classified, skipping")
                else:
                    logger.debug(f"Tool '{tool_name}' needs classification only")
            else:
                # Log why content doesn't match for debugging
                if not description_matches:
                    logger.debug(f"🔄 Tool '{tool_name}' description changed, forcing resync")
                elif not db_id_matches:
                    logger.warning(
                        f"🔄 Tool '{tool_name}' PostgreSQL ID changed: {qdrant_db_id_int} → {pg_db_id_int}, forcing resync"
                    )
        elif existing_qdrant and not existing_tool:
            # Qdrant exists but PostgreSQL was empty (database reset case)
            logger.warning(
                f"🔄 Tool '{tool_name}' found in Qdrant but PostgreSQL was empty, forcing resync"
            )

        # Return tuple with both flags
        return db_record, tool_data, needs_embedding, needs_classification

    def _build_search_text(self, item_data: Dict[str, Any]) -> str:
        """Build search-friendly text for embedding (unified for tool/prompt/resource)."""
        description = item_data.get("description", "")
        if description:
            return description
        name = item_data.get("name", "")
        if name:
            return name
        # Fallback for resources with uri
        return item_data.get("uri", "")

    def _build_tool_search_text(self, item_data: Dict[str, Any]) -> str:
        """Build search-friendly text for tools."""
        return self._build_search_text(item_data)

    def _build_prompt_search_text(self, item_data: Dict[str, Any]) -> str:
        """Build search-friendly text for prompts."""
        return self._build_search_text(item_data)

    def _build_resource_search_text(self, item_data: Dict[str, Any]) -> str:
        """Build search-friendly text for resources."""
        return self._build_search_text(item_data)

    async def sync_prompts(self) -> Dict[str, Any]:
        """Sync prompts from MCP Server API to database with BATCH embeddings"""
        logger.debug("Syncing prompts from MCP Server...")

        # Ensure fresh Qdrant connection (fixes "Channel is closed" errors)
        try:
            await self.vector_repo.client.reconnect()
        except Exception as e:
            logger.warning(f"Failed to reconnect Qdrant client: {e}")

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
            logger.debug(f"Retrieved {len(mcp_prompts)} prompts from MCP Server")

            # 2. Get existing prompts from Qdrant
            qdrant_prompts = await self.vector_repo.get_all_by_type("prompt")
            logger.debug(f"Found {len(qdrant_prompts)} existing prompts in Qdrant")

            # Build lookup dict and find duplicates
            qdrant_prompts_dict, duplicate_ids, _ = _build_qdrant_dict_and_find_duplicates(
                qdrant_prompts
            )

            if duplicate_ids:
                logger.info(f"🧹 Cleaning up {len(duplicate_ids)} duplicate prompt entries...")
                await self.vector_repo.delete_multiple_vectors(duplicate_ids)

            # 3. Find orphaned prompts
            mcp_prompt_names = {prompt.name for prompt in mcp_prompts}
            orphaned_ids = []
            orphaned_names = []

            for qdrant_prompt in qdrant_prompts_dict.values():
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
                                    "required": arg.required if hasattr(arg, "required") else False,
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
                        search_text = self._build_search_text(prompt_data)
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
                    f"Generating embeddings for {len(items_to_embed)} prompts via ISA Model BATCH API..."
                )
                search_texts = [item[2] for item in items_to_embed]

                try:
                    # BATCH embedding - single API call with all texts
                    # ISA Model supports Union[str, List[str]] for input parameter
                    response = await self.isa_model.embeddings.create(
                        input=search_texts, model=self.embedding_model  # Pass all texts as batch
                    )
                    # Extract embeddings in order (API returns in same order as input)
                    embeddings = [item.embedding for item in response.data]
                    logger.info(
                        f"✅ Generated {len(embeddings)} embeddings via ISA Model BATCH API"
                    )

                    # 7. Upsert to Qdrant and track for classification
                    prompts_to_classify = []
                    for (db_record, prompt_data, _), embedding in zip(items_to_embed, embeddings):
                        try:
                            success = await self.vector_repo.upsert_vector(
                                item_type="prompt",
                                name=prompt_data["name"],
                                description=prompt_data["description"],
                                embedding=embedding,
                                db_id=db_record["id"],
                                is_active=True,
                                metadata={
                                    "org_id": db_record.get("org_id"),
                                    "is_global": db_record.get("is_global", True),
                                },
                            )
                            if success:
                                synced += 1
                                # Track for classification
                                prompts_to_classify.append(
                                    {
                                        "id": db_record["id"],
                                        "name": prompt_data["name"],
                                        "description": prompt_data["description"],
                                    }
                                )
                        except Exception as e:
                            logger.error(f"Failed to sync prompt {prompt_data['name']}: {e}")
                            failed += 1
                            errors.append({"prompt": prompt_data["name"], "error": str(e)})

                    # 8. Classify prompts into skill categories (BATCH)
                    classified = 0
                    if prompts_to_classify:
                        logger.debug(f"Batch classifying {len(prompts_to_classify)} prompts...")
                        try:
                            batch_results = await self.skill_service.classify_entities_batch(
                                prompts_to_classify, entity_type="prompt"
                            )
                            classified = sum(1 for r in batch_results if r.get("primary_skill_id"))
                            logger.debug(
                                f"Classified {classified}/{len(prompts_to_classify)} prompts"
                            )
                        except Exception as e:
                            logger.warning(f"Prompt classification failed: {e}")

                except Exception as e:
                    logger.error(f"Batch embedding failed: {e}")
                    failed += len(items_to_embed)
                    errors.append({"error": f"Batch embedding failed: {str(e)}"})

            logger.info(f"Prompts sync: {synced} updated, {skipped} skipped, {failed} failed")

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
            db_record = await self.prompt_service.update_prompt(prompt_name, prompt_data)
        else:
            db_record = await self.prompt_service.register_prompt(prompt_data)

        # Check if embedding needs update (check both description AND db_id)
        needs_update = True
        if existing_qdrant and existing_prompt:
            # Normalize db_ids for comparison
            qdrant_db_id_int = _normalize_db_id(existing_qdrant.get("db_id"))
            pg_db_id_int = _normalize_db_id(db_record["id"])

            description_matches = existing_qdrant.get("description") == prompt_data["description"]
            db_id_matches = qdrant_db_id_int == pg_db_id_int and qdrant_db_id_int is not None

            if description_matches and db_id_matches:
                needs_update = False
                logger.debug(f"⏭️  Prompt '{prompt_name}' unchanged, skipping")
            elif not db_id_matches:
                logger.warning(
                    f"🔄 Prompt '{prompt_name}' PostgreSQL ID changed: {existing_qdrant.get('db_id')} → {db_record['id']}, forcing resync"
                )
            else:
                logger.debug(f"🔄 Prompt '{prompt_name}' description changed, forcing resync")
        elif existing_qdrant and not existing_prompt:
            logger.warning(
                f"🔄 Prompt '{prompt_name}' found in Qdrant but PostgreSQL was empty, forcing resync"
            )

        return db_record, prompt_data, needs_update

    async def sync_resources(self) -> Dict[str, Any]:
        """Sync resources from MCP Server API with BATCH embeddings"""
        logger.debug("Syncing resources from MCP Server...")

        # Ensure fresh Qdrant connection (fixes "Channel is closed" errors)
        try:
            await self.vector_repo.client.reconnect()
        except Exception as e:
            logger.warning(f"Failed to reconnect Qdrant client: {e}")

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
            logger.debug(f"Retrieved {len(mcp_resources)} resources from MCP Server")

            # 2. Get existing resources from Qdrant
            qdrant_resources = await self.vector_repo.get_all_by_type("resource")
            logger.debug(f"Found {len(qdrant_resources)} existing resources in Qdrant")

            # Build lookup dict and find duplicates
            qdrant_resources_dict, duplicate_ids, _ = _build_qdrant_dict_and_find_duplicates(
                qdrant_resources
            )

            if duplicate_ids:
                logger.info(f"🧹 Cleaning up {len(duplicate_ids)} duplicate resource entries...")
                await self.vector_repo.delete_multiple_vectors(duplicate_ids)

            # 3. Find orphaned resources
            mcp_resource_names = {
                resource.name or str(resource.uri).split("://")[-1] for resource in mcp_resources
            }
            orphaned_ids = []
            orphaned_names = []

            for qdrant_resource in qdrant_resources_dict.values():
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
                        "mime_type": (
                            resource.mimeType if hasattr(resource, "mimeType") else "text/plain"
                        ),
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
                        search_text = self._build_search_text(resource_data)
                        items_to_embed.append((db_record, resource_data, search_text))
                    else:
                        skipped += 1

                except Exception as e:
                    logger.error(f"Failed to prepare resource {resource.uri}: {e}")
                    failed += 1
                    errors.append({"resource": str(resource.uri), "error": str(e)})

            # 6. Generate embeddings via ISA Model BATCH API
            synced = 0
            if items_to_embed:
                logger.info(
                    f"Generating embeddings for {len(items_to_embed)} resources via ISA Model BATCH API..."
                )
                search_texts = [item[2] for item in items_to_embed]

                try:
                    # BATCH embedding - single API call with all texts
                    # ISA Model supports Union[str, List[str]] for input parameter
                    response = await self.isa_model.embeddings.create(
                        input=search_texts, model=self.embedding_model  # Pass all texts as batch
                    )
                    # Extract embeddings in order (API returns in same order as input)
                    embeddings = [item.embedding for item in response.data]
                    logger.info(
                        f"✅ Generated {len(embeddings)} embeddings via ISA Model BATCH API"
                    )

                    # 7. Upsert to Qdrant and track for classification
                    resources_to_classify = []
                    for (db_record, resource_data, _), embedding in zip(items_to_embed, embeddings):
                        try:
                            success = await self.vector_repo.upsert_vector(
                                item_type="resource",
                                name=resource_data["name"],
                                description=resource_data["description"],
                                embedding=embedding,
                                db_id=db_record["id"],
                                is_active=True,
                                metadata={
                                    "resource_type": resource_data.get("resource_type"),
                                    "uri": resource_data.get("uri"),
                                    "org_id": db_record.get("org_id"),
                                },
                            )
                            if success:
                                synced += 1
                                # Track for classification
                                resources_to_classify.append(
                                    {
                                        "id": db_record["id"],
                                        "name": resource_data["name"],
                                        "description": resource_data["description"],
                                    }
                                )
                        except Exception as e:
                            logger.error(f"Failed to sync resource {resource_data['name']}: {e}")
                            failed += 1
                            errors.append({"resource": resource_data["name"], "error": str(e)})

                    # 8. Classify resources into skill categories (BATCH)
                    classified = 0
                    if resources_to_classify:
                        logger.debug(f"Batch classifying {len(resources_to_classify)} resources...")
                        try:
                            batch_results = await self.skill_service.classify_entities_batch(
                                resources_to_classify, entity_type="resource"
                            )
                            classified = sum(1 for r in batch_results if r.get("primary_skill_id"))
                            logger.debug(
                                f"Classified {classified}/{len(resources_to_classify)} resources"
                            )
                        except Exception as e:
                            logger.warning(f"Resource classification failed: {e}")

                except Exception as e:
                    logger.error(f"Batch embedding failed: {e}")
                    failed += len(items_to_embed)
                    errors.append({"error": f"Batch embedding failed: {str(e)}"})

            logger.info(f"Resources sync: {synced} updated, {skipped} skipped, {failed} failed")

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
            db_record = await self.resource_service.update_resource(resource_uri, resource_data)
        else:
            db_record = await self.resource_service.register_resource(resource_data)

        # Check if embedding needs update (check both description AND db_id)
        needs_update = True
        if existing_qdrant and existing_resource:
            # Normalize db_ids for comparison
            qdrant_db_id_int = _normalize_db_id(existing_qdrant.get("db_id"))
            pg_db_id_int = _normalize_db_id(db_record["id"])

            description_matches = existing_qdrant.get("description") == resource_data["description"]
            db_id_matches = qdrant_db_id_int == pg_db_id_int and qdrant_db_id_int is not None

            if description_matches and db_id_matches:
                needs_update = False
                logger.debug(f"⏭️  Resource '{resource_uri}' unchanged, skipping")
            elif not db_id_matches:
                logger.warning(
                    f"🔄 Resource '{resource_uri}' PostgreSQL ID changed: {existing_qdrant.get('db_id')} → {db_record['id']}, forcing resync"
                )
            else:
                logger.debug(f"🔄 Resource '{resource_uri}' description changed, forcing resync")
        elif existing_qdrant and not existing_resource:
            logger.warning(
                f"🔄 Resource '{resource_uri}' found in Qdrant but PostgreSQL was empty, forcing resync"
            )

        return db_record, resource_data, needs_update

    async def sync_skills(self) -> Dict[str, Any]:
        """
        Sync skill categories from PostgreSQL to Qdrant mcp_skills collection.

        BR-004: Skill Embedding Generation
        - Batch sync | Update only changed skills

        This method:
        1. Gets all active skills from PostgreSQL via SkillService
        2. Gets existing skills from Qdrant mcp_skills collection
        3. Compares descriptions to detect changes
        4. Only generates embeddings for changed skills
        5. Upserts changed skills to Qdrant

        Returns:
            Sync results with total, synced, skipped, failed counts
        """
        logger.debug("Syncing skills from PostgreSQL to Qdrant...")

        try:
            # Ensure fresh Qdrant connection (same as sync_tools)
            qdrant_client = self.vector_repo.client
            try:
                await qdrant_client.reconnect()
                logger.debug("Reconnected to Qdrant for skills sync")
            except Exception as e:
                logger.warning(f"Failed to reconnect Qdrant client: {e}")

            # 1. Get all active skills from PostgreSQL
            skills = await self.skill_service.list_skills(is_active=True, limit=1000)
            logger.debug(f"Retrieved {len(skills)} active skills from PostgreSQL")

            if not skills:
                logger.debug("No skills to sync")
                return {
                    "total": 0,
                    "synced": 0,
                    "skipped": 0,
                    "failed": 0,
                    "errors": [],
                }

            # 2. Ensure mcp_skills collection exists BEFORE reading
            collections = await qdrant_client.list_collections()
            if self._skill_collection not in collections:
                logger.debug(f"Creating collection: {self._skill_collection}")
                await qdrant_client.create_collection(
                    collection_name=self._skill_collection,
                    vector_size=self.vector_repo.vector_dimension,
                    distance="Cosine",
                )
                # Collection just created, all skills need embedding
                existing_skills_dict = {}
            else:
                # 3. Get existing skills from Qdrant for change detection
                existing_skills_dict = await self._get_existing_skills_from_qdrant(qdrant_client)
                logger.debug(f"Found {len(existing_skills_dict)} existing skills in Qdrant")

            # 4. Prepare skills for batch embedding (only changed ones)
            items_to_embed = []
            skipped = 0

            for skill in skills:
                skill_id = skill.get("id")
                description = skill.get("description", "")
                if not description:
                    description = skill.get("name", skill_id)

                # Check if skill exists and is unchanged
                existing_skill = existing_skills_dict.get(skill_id)
                if existing_skill:
                    existing_description = existing_skill.get("description", "")
                    if existing_description == description:
                        logger.debug(f"⏭️  Skill '{skill_id}' unchanged, skipping")
                        skipped += 1
                        continue

                items_to_embed.append(
                    {
                        "skill": skill,
                        "search_text": description,
                    }
                )

            if not items_to_embed:
                logger.debug(f"All {len(skills)} skills unchanged, nothing to sync")
                return {
                    "total": len(skills),
                    "synced": 0,
                    "skipped": skipped,
                    "failed": 0,
                    "errors": [],
                }

            # 5. Generate embeddings via ISA Model BATCH API (only for changed skills)
            logger.debug(f"Generating embeddings for {len(items_to_embed)} changed skills...")
            search_texts = [item["search_text"] for item in items_to_embed]

            response = await self.isa_model.embeddings.create(
                input=search_texts, model=self.embedding_model
            )
            embeddings = [item.embedding for item in response.data]
            logger.debug(f"Generated {len(embeddings)} skill embeddings")

            # 6. Upsert changed skills to Qdrant
            synced = 0
            failed = 0
            errors = []

            for item, embedding in zip(items_to_embed, embeddings):
                skill = item["skill"]
                skill_id = skill.get("id")

                try:
                    # Build payload (keep original string ID in payload for lookup)
                    payload = {
                        "id": skill_id,  # Original string ID for reference
                        "name": skill.get("name", ""),
                        "description": skill.get("description", ""),
                        "tool_count": skill.get("tool_count", 0),
                        "is_active": skill.get("is_active", True),
                        "parent_domain": skill.get("parent_domain"),
                        "keywords": skill.get("keywords", []),
                    }

                    # Convert string skill_id to deterministic UUID for Qdrant
                    # Qdrant requires point IDs to be unsigned integer or UUID
                    skill_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"mcp.skill.{skill_id}"))

                    # Upsert to Qdrant (use UUID as point ID)
                    operation_id = await qdrant_client.upsert_points(
                        collection_name=self._skill_collection,
                        points=[
                            {
                                "id": skill_uuid,
                                "vector": embedding,
                                "payload": payload,
                            }
                        ],
                    )

                    if operation_id:
                        synced += 1
                        logger.debug(f"  ✅ Synced skill: {skill_id} (op: {operation_id})")
                    else:
                        logger.error(f"  ❌ Qdrant returned None for skill {skill_id}")
                        failed += 1
                        errors.append({"skill_id": skill_id, "error": "Qdrant returned None"})

                except Exception as e:
                    logger.error(f"  ❌ Failed to sync skill {skill_id}: {e}")
                    failed += 1
                    errors.append({"skill_id": skill_id, "error": str(e)})

            logger.debug(f"Skills sync: {synced} synced, {skipped} skipped, {failed} failed")

            return {
                "total": len(skills),
                "synced": synced,
                "skipped": skipped,
                "failed": failed,
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"Skills sync failed: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return {
                "total": 0,
                "synced": 0,
                "skipped": 0,
                "failed": 0,
                "errors": [str(e)],
            }

    async def _get_existing_skills_from_qdrant(self, qdrant_client) -> Dict[str, Dict[str, Any]]:
        """
        Get all existing skills from Qdrant mcp_skills collection.

        Returns:
            Dictionary mapping skill_id -> skill payload
        """
        try:
            existing_skills = {}
            offset_id = None

            while True:
                result = await qdrant_client.scroll(
                    collection_name=self._skill_collection,
                    filter_conditions=None,  # Get all skills
                    limit=1000,
                    offset_id=offset_id,
                    with_payload=True,
                    with_vectors=False,
                )

                if not result or "points" not in result:
                    break

                points = result["points"]
                if not points:
                    break

                # Extract skill data from points
                for point in points:
                    payload = point.get("payload", {})
                    skill_id = payload.get("id")
                    if skill_id:
                        existing_skills[skill_id] = {
                            "id": skill_id,
                            "name": payload.get("name", ""),
                            "description": payload.get("description", ""),
                            "tool_count": payload.get("tool_count", 0),
                        }

                # Check for next page
                offset_id = result.get("next_offset")
                if not offset_id:
                    break

            return existing_skills

        except Exception as e:
            logger.warning(f"Failed to get existing skills from Qdrant: {e}")
            return {}

    async def classify_all_tools(self, force_reclassify: bool = False) -> Dict[str, Any]:
        """
        Classify all tools that don't have primary_skill_id set.

        This is useful for:
        - Initial classification of existing tools after adding skill feature
        - Re-classifying tools after skill categories change

        Args:
            force_reclassify: If True, reclassify ALL tools even if already classified

        Returns:
            Classification results with counts
        """
        logger.info(f"🏷️  Starting bulk tool classification (force={force_reclassify})...")

        try:
            # Get all tools from Qdrant
            all_tools = await self.vector_repo.get_all_by_type("tool")
            logger.info(f"Found {len(all_tools)} tools in Qdrant")

            # Filter tools needing classification
            if force_reclassify:
                tools_to_classify = all_tools
            else:
                # Only classify tools without primary_skill_id
                tools_to_classify = [
                    t
                    for t in all_tools
                    if not t.get("metadata", {}).get("primary_skill_id")
                    and not self._get_primary_skill_from_payload(t)
                ]

            logger.info(f"  {len(tools_to_classify)} tools need classification")

            if not tools_to_classify:
                return {
                    "total": len(all_tools),
                    "classified": 0,
                    "skipped": len(all_tools),
                    "failed": 0,
                    "errors": [],
                }

            classified = 0
            failed = 0
            errors = []

            for idx, tool in enumerate(tools_to_classify):
                tool_id = tool.get("db_id") or tool.get("id")
                tool_name = tool.get("name", "unknown")
                description = tool.get("description", "")

                try:
                    # Skip if not a valid tool ID (must be int for PostgreSQL FK)
                    if not isinstance(tool_id, int):
                        try:
                            tool_id = int(tool_id)
                        except (ValueError, TypeError):
                            logger.warning(f"  Skipping tool '{tool_name}' - invalid ID: {tool_id}")
                            continue

                    logger.info(
                        f"  [{idx + 1}/{len(tools_to_classify)}] Classifying '{tool_name}' (ID: {tool_id})..."
                    )

                    result = await self.skill_service.classify_tool(
                        tool_id=tool_id,
                        tool_name=tool_name,
                        tool_description=description,
                        force_reclassify=force_reclassify,
                    )

                    if result.get("primary_skill_id"):
                        classified += 1
                        logger.info(f"    ✅ Classified as: {result['primary_skill_id']}")
                    elif result.get("skipped"):
                        logger.info("    ⏭️  Skipped (already classified)")
                    else:
                        logger.warning(f"    ⚠️  No skill matched for '{tool_name}'")

                except Exception as e:
                    logger.error(f"    ❌ Failed to classify '{tool_name}': {e}")
                    failed += 1
                    errors.append({"tool": tool_name, "id": tool_id, "error": str(e)})

            logger.info(
                f"🎯 Bulk classification completed: {classified} classified, {failed} failed"
            )

            return {
                "total": len(all_tools),
                "classified": classified,
                "skipped": len(all_tools) - len(tools_to_classify),
                "failed": failed,
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"Bulk classification failed: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return {
                "total": 0,
                "classified": 0,
                "skipped": 0,
                "failed": 0,
                "errors": [str(e)],
            }

    def _get_primary_skill_from_payload(self, tool: Dict[str, Any]) -> Optional[str]:
        """Extract primary_skill_id from tool payload, handling various formats."""
        # Direct field
        if tool.get("primary_skill_id"):
            return tool["primary_skill_id"]

        # In metadata
        metadata = tool.get("metadata", {})
        if metadata and metadata.get("primary_skill_id"):
            return metadata["primary_skill_id"]

        return None
